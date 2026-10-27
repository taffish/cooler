"""Independent offline packaging checks; no production data or algorithms."""
import argparse
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

TD = Path("/opt/cooler/share/testdata")


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


def buildtime(root):
    import cooler
    assert cooler.__version__ == "0.11.0"
    assert run("cooler", "--version").strip() == "cooler, version 0.11.0"
    tiny(root / "tiny.cool")
    assert run("cooler", "info", "--field", "nbins", root / "tiny.cool").strip() == "12"


def identity(root):
    import cooler
    assert cooler.__version__ == "0.11.0"
    assert run("cooler", "--version").strip() == "cooler, version 0.11.0"
    for name in ("Bio", "dask.array", "dask.dataframe", "ipytree", "ipywidgets",
                 "matplotlib", "psutil", "pysam", "pypairix", "h5py", "numpy", "pandas", "scipy"):
        importlib.import_module(name)
    for name in ("cload", "load", "csort", "makebins", "digest", "info", "dump", "show",
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
        pairs = root / f"{index}.pairs.gz"
        run("cooler", "csort", "--index", index, "-c1", "2", "-p1", "3", "-c2", "4",
            "-p2", "5", "--nproc", "1", TD / "toy.pairs", chroms, "-o", pairs)
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
    run("cooler", "mv", root / "copy.cool", str(root / "links.cool") + "::/matrix")
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


def main():
    modes = {name: value for name, value in globals().items()
             if name in ("buildtime", "identity", "ingest", "matrix", "scool", "negative", "plot")}
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
