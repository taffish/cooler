"""Independent offline packaging checks; no production data or algorithms."""
import argparse
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

TD = Path("/opt/cooler/share/testdata")
VERSION = "0.12.1"


def run(*args, expected=0):
    result = subprocess.run([str(x) for x in args], text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=150)
    if (expected == 0 and result.returncode != 0) or (expected != 0 and result.returncode == 0):
        raise AssertionError(f"stage={args!r} exit={result.returncode}\n{result.stdout[-12000:]}")
    return result.stdout


def tiny(path):
    import cooler
    import numpy as np
    import pandas as pd
    bins = pd.DataFrame({"chrom": ["chr1"] * 6 + ["chr2"] * 6,
                         "start": list(range(0, 60, 10)) * 2,
                         "end": list(range(10, 70, 10)) * 2})
    i, j = np.triu_indices(len(bins))
    pixels = pd.DataFrame({"bin1_id": i, "bin2_id": j, "count": np.ones(len(i), dtype=int)})
    cooler.create_cooler(str(path), bins, pixels, ordered=True)
    return bins, pixels


def version_check():
    # Check the producer's exit status and exact single-line output together.
    import cooler
    assert cooler.__version__ == VERSION
    assert run("cooler", "--version") == f"cooler, version {VERSION}\n"


def buildtime(root):
    version_check()
    tiny(root / "tiny.cool")
    assert run("cooler", "info", "--field", "nbins", root / "tiny.cool").strip() == "12"


def identity(root):
    version_check()
    for name in ("Bio", "dask.array", "dask.dataframe", "ipytree", "ipywidgets",
                 "matplotlib", "psutil", "pyfaidx", "pysam", "pypairix", "h5py", "numpy", "pandas", "scipy"):
        importlib.import_module(name)
    for name in ("cload", "load", "makebins", "digest", "info", "dump", "show",
                 "balance", "coarsen", "zoomify", "merge", "ls", "cp", "ln", "mv", "tree", "attrs"):
        assert "Usage:" in run("cooler", name, "--help")
    for name in ("pairs", "tabix", "pairix", "hiclib"):
        assert "Usage:" in run("cooler", "cload", name, "--help")


def ingest(root):
    import cooler
    chroms = TD / "toy.chrom.sizes"
    out = root / "loaded.cool"
    run("cooler", "load", "--format", "bg2", f"{chroms}:2", TD / "toy.symm.upper.2.bg2", out)
    c = cooler.Cooler(str(out))
    assert c.shape == (32, 32) and c.info["nnz"] > 0
    assert "chr1\t0\t2" in run("cooler", "makebins", chroms, "2")
    # FASTA indexing writes beside the input, so copy the seed to scratch.
    fasta = root / "toy.fasta"
    shutil.copyfile(TD / "toy.fasta", fasta)
    run("cooler", "digest", chroms, fasta, "DpnII", "--out", root / "frags.bed")
    assert "chr1" in (root / "frags.bed").read_text()
    for index in ("tabix", "pairix"):
        # Keep both indexed-reader paths with sorted synthetic input. Upstream
        # removed csort; cload pairs directly accepts unsorted contacts.
        pairs = root / f"{index}.pairs.gz"
        plain = root / f"{index}.pairs"
        plain.write_text("Read1\tchr1\t1\tchr1\t3\nRead2\tchr1\t5\tchr1\t7\n")
        run("bgzip", plain)
        if index == "tabix":
            run("tabix", "-s", "2", "-b", "3", "-e", "3", pairs)
        else:
            run("pairix", "-s", "2", "-d", "4", "-b", "3", "-e", "3", "-u", "5", "-v", "5", pairs)
        assert "Read1" in run("bgzip", "-dc", pairs)
        run("cooler", "cload", index, "--nproc", "1", f"{chroms}:2", pairs, root / f"{index}.cool")
        assert cooler.Cooler(str(root / f"{index}.cool")).info["nnz"] > 0
    run("cooler", "cload", "pairs", "-c1", "2", "-p1", "3", "-c2", "4", "-p2", "5",
        f"{chroms}:2", TD / "toy.pairs", root / "pairs.cool")
    assert cooler.Cooler(str(root / "pairs.cool")).info["nnz"] > 0


def matrix(root):
    import cooler
    import numpy as np
    src = root / "tiny.cool"
    tiny(src)
    run("cooler", "balance", "--ignore-diags", "0", "--min-nnz", "0", "--min-count", "0",
        "--mad-max", "0", "--nproc", "1", "--tol", "0.000001", src)
    c = cooler.Cooler(str(src))
    arr = c.matrix(balance=True)[:]
    assert np.all(np.isfinite(arr)) and np.allclose(arr.sum(axis=0), 1, atol=1e-5)
    with c.open("r+") as f:
        f["bins"].create_dataset("custom", data=f["bins/weight"][:])
    text = run("cooler", "dump", "--weight-name", "custom", "-H", src)
    assert "balanced" in text and len(text.splitlines()) > 1
    run("cooler", "coarsen", "-k", "2", "-p", "1", "-o", root / "coarse.cool", src)
    assert cooler.Cooler(str(root / "coarse.cool")).binsize == 20
    run("cooler", "zoomify", "-r", "20,30", "-p", "1", "-o", root / "multi.mcool", src)
    assert "/resolutions/20" in run("cooler", "ls", root / "multi.mcool")
    run("cooler", "merge", root / "merged.cool", src, src)
    assert cooler.Cooler(str(root / "merged.cool")).info["sum"] == 2 * c.info["sum"]
    run("cooler", "cp", src, root / "copy.cool")
    run("cooler", "cp", root / "copy.cool", str(root / "links.cool") + "::/original")
    run("cooler", "mv", str(root / "links.cool") + "::/original", str(root / "links.cool") + "::/matrix")
    run("cooler", "ln", str(root / "links.cool") + "::/matrix", str(root / "links.cool") + "::/hard")
    run("cooler", "ln", "-s", str(root / "links.cool") + "::/matrix", str(root / "links.cool") + "::/soft")
    assert "matrix" in run("cooler", "tree", root / "links.cool")
    assert "format" in run("cooler", "attrs", src)
    for kind, content in enumerate(("chr1\t0\t10\n", "", "track name=bl\nchrom\tstart\tend\nchr1\t0\t10\n")):
        bl = root / f"blacklist-{kind}.bed"
        bl.write_text(content)
        run("cooler", "balance", "--ignore-diags", "0", "--min-nnz", "0", "--mad-max", "0",
            "--nproc", "1", "--blacklist", bl, "--stdout", src)


def scool(root):
    import cooler
    import h5py
    bins, pixels = tiny(root / "base.cool")
    dest = str(root / "cells.scool")
    cooler.create_scool(dest, bins, {"cell1": pixels, "cell2": pixels})
    cooler.create_scool(dest, bins, {"cell3": pixels}, mode="a")
    cooler.create_scool(dest, bins, {}, mode="a")
    with h5py.File(dest, "r") as f:
        assert f.attrs["ncells"] == 3
        addr = h5py.h5o.get_info(f["bins/start"].id).addr
        assert all(h5py.h5o.get_info(f[f"cells/{cell}/bins/start"].id).addr == addr for cell in f["cells"])
    changed = bins.copy()
    changed["end"] -= 1
    try:
        cooler.create_scool(dest, changed, {"cell4": pixels}, mode="a")
    except ValueError:
        pass
    else:
        raise AssertionError("incompatible bins accepted")
    assert cooler.Cooler(dest + "::/cells/cell1").info["nnz"] == len(pixels)


def negative(root):
    import cooler
    bad = root / "bad.chrom.sizes"
    bad.write_text("chr1\tnot-an-integer\n")
    assert "integer length" in run("cooler", "makebins", bad, "10", expected=1)
    assert not (root / "missing.cool").exists()
    assert "Error" in run("cooler", "info", root / "missing.cool", expected=1)
    src = root / "valid.cool"
    tiny(src)
    assert "absent" in run("cooler", "dump", "--weight-name", "absent", src, expected=1)
    assert "Error" in run("cooler", "not-a-command", expected=1)


def plot(root):
    from PIL import Image
    import xml.etree.ElementTree as ET
    src = root / "tiny.cool"
    tiny(src)
    for ext in ("png", "svg", "pdf", "jpg", "ps", "eps"):
        out = root / ("matrix." + ext)
        run("cooler", "show", src, "chr1:0-60", "--scale", "linear", "--out", out, "--dpi", "72")
        assert out.stat().st_size > 500
    with Image.open(root / "matrix.png") as image:
        assert image.width > 500 and image.height > 500
        assert image.convert("L").getextrema()[0] < 200
    assert ET.parse(root / "matrix.svg").getroot().tag.endswith("svg")
    assert (root / "matrix.pdf").read_bytes().startswith(b"%PDF")


def _worker_exit(value):
    # Deliberately stop only our own synthetic pool worker, never a host PID.
    if value == 1:
        os._exit(7)
    return value * value


def worker(root):
    import multiprocessing
    from cooler.parallel import _ProcessPool, WorkerDiedError
    for method in ("map", "imap_unordered"):
        try:
            with _ProcessPool(2) as pool:
                list(getattr(pool, method)(_worker_exit, range(4)))
        except WorkerDiedError as error:
            assert "worker process exited unexpectedly" in str(error)
        else:
            raise AssertionError("worker death was not reported")
        assert not multiprocessing.active_children(), "owned pool workers remain"


def update(root):
    """Exercise new 0.12 contracts, not production scientific accuracy."""
    import cooler
    import numpy as np
    import pandas as pd
    bins = cooler.binnify(pd.Series({"chr1": 25, "chr2": 0}), 10.0)
    assert bins["start"].tolist() == [0, 10, 20]
    assert bins["end"].tolist() == [10, 20, 25]
    assert bins["start"].dtype.kind == bins["end"].dtype.kind == "i"
    for size in (0, -1, 1.5, float("inf"), float("nan")):
        try:
            cooler.binnify(pd.Series({"chr1": 25}), size)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid binsize accepted: {size}")
    assert "PASS worker" in run("python", __file__, "worker")
    cs = root / "chrom.sizes"
    cs.write_text("chr1\t100\nchr2\t50\n")
    pairs = root / "values.pairs"
    pairs.write_text("r1\tchr1\t2\tchr1\t8\t+\t+\t2\n"
                     "r2\tchr1\t3\tchr1\t9\t+\t+\t3\n")
    src = root / "values.cool"
    args = ["cooler", "cload", "pairs", "-c1", "2", "-p1", "3", "-c2", "4", "-p2", "5"]
    run(*args, "--chunksize", "1", "--field", "v=8", "--field", "n=8:agg=count",
        "--field", "ss=8:agg=sum_squares", f"{cs}:10", pairs, src)
    row = cooler.Cooler(str(src)).pixels()[:].iloc[0]
    assert (row["v"], row["n"], row["ss"], row["count"]) == (5, 2, 13, 2)
    run("cooler", "coarsen", "-k", "2", "-p", "2", "--field", "count", "--field", "v",
        "--field", "n", "--field", "ss", "-o", root / "coarse.cool", src)
    coarse = cooler.Cooler(str(root / "coarse.cool")).pixels()[:].iloc[0]
    assert (coarse["v"], coarse["n"], coarse["ss"]) == (5, 2, 13)
    dumped = run("cooler", "dump", "-H", src).splitlines()[0].split()
    assert {"count", "v", "n", "ss"}.issubset(dumped)
    assert "Unsupported aggregation" in run(*args, "--field", "v=8:agg=mean",
                                            f"{cs}:10", pairs, root / "bad.cool", expected=1)
    assert "No such command" in run("cooler", "csort", expected=1)
    before = src.read_bytes()
    run("cooler", "cp", "-w", str(src) + "::/missing", src, expected=1)
    assert src.read_bytes() == before
    run("cooler", "zoomify", "-o", src, src, expected=1)
    assert src.read_bytes() == before
    pairs.write_text("bad\tchr1\t1\tchr1\t101\n")
    run(*args, f"{cs}:10", pairs, src, expected=1)
    assert src.read_bytes() == before, "failed ingestion overwrote an existing matrix"
    balanced = root / "balanced.cool"
    tiny(balanced)
    run("cooler", "balance", "--nproc", "2", "--ignore-diags", "0", "--min-nnz", "0",
        "--mad-max", "0", "--no-rescale-marginals", balanced)
    c = cooler.Cooler(str(balanced))
    with c.open() as h5:
        scale = h5["bins/weight"].attrs["scale"]
    assert np.allclose(c.matrix(balance=True)[:].sum(axis=0), scale, rtol=1e-5)


def main():
    modes = {name: value for name, value in globals().items()
             if name in ("buildtime", "identity", "ingest", "matrix", "scool", "negative", "plot", "update", "worker")}
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=modes)
    args = p.parse_args()
    # Allocate and clean only our own private directory, never a caller's path.
    with tempfile.TemporaryDirectory(prefix="taf-cooler-", dir="/tmp") as directory:
        root = Path(directory)
        os.environ["MPLCONFIGDIR"] = str(root / "matplotlib")
        modes[args.mode](root)
    print("PASS " + args.mode, flush=True)


if __name__ == "__main__":
    main()
