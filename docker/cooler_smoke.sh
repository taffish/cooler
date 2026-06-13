#!/usr/bin/env bash
set -euo pipefail

tmp="${1:-/tmp/taf-cooler-smoke-$$}"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

td="${COOLER_TESTDATA:-/opt/cooler/share/testdata}"

cooler --version 2>&1 | grep -F "0.10.4" >/dev/null
python - <<'PY'
import cooler
import Bio
import dask
import h5py
import matplotlib
import numpy
import pandas
import psutil
import pysam
import scipy

assert cooler.__version__ == "0.10.4"
PY

cooler makebins "$td/toy.chrom.sizes" 2 > "$tmp/toy.bins.2.bed"
test -s "$tmp/toy.bins.2.bed"
grep -F $'chr1\t0\t2' "$tmp/toy.bins.2.bed" >/dev/null

cooler load --format bg2 "$td/toy.chrom.sizes:2" "$td/toy.symm.upper.2.bg2" "$tmp/load.cool"
test -s "$tmp/load.cool"
test "$(cooler info --field bin-size "$tmp/load.cool")" = "2"
cooler dump -t chroms "$tmp/load.cool" | grep -F $'chr1\t32' >/dev/null
cooler dump -t pixels "$tmp/load.cool" | grep -F $'0\t8\t2' >/dev/null
cooler ls "$tmp/load.cool" | grep -F "::/" >/dev/null

cooler digest "$td/toy.chrom.sizes" "$td/toy.fasta" DpnII --out "$tmp/frags.bed"
test -s "$tmp/frags.bed"
grep -F "chr1" "$tmp/frags.bed" >/dev/null

cooler show "$tmp/load.cool" chr1 --out "$tmp/show.png" --dpi 72
test -s "$tmp/show.png"

cooler zoomify "$tmp/load.cool" --resolutions 4 --out "$tmp/load.mcool" --nproc 1
test -s "$tmp/load.mcool"
cooler ls "$tmp/load.mcool" | grep -F "/resolutions/2" >/dev/null

cooler csort \
  --chrom1 2 --pos1 3 --chrom2 4 --pos2 5 \
  --index tabix --nproc 1 \
  "$td/toy.pairs" "$td/toy.chrom.sizes" \
  --out "$tmp/toy.possrt.pairs.gz"
test -s "$tmp/toy.possrt.pairs.gz"
test -s "$tmp/toy.possrt.pairs.gz.tbi"
bgzip -dc "$tmp/toy.possrt.pairs.gz" | grep -F "Read1" >/dev/null

cooler cload tabix \
  --nproc 1 --assembly hg19 \
  "$td/hg19.bins.2000kb.bed.gz" \
  "$td/hg19.GM12878-MboI.pairs.subsample.sorted.txt.gz" \
  "$tmp/tabix.cool"
test -s "$tmp/tabix.cool"
cooler dump -t chroms "$tmp/tabix.cool" | grep -F $'chr1\t249250621' >/dev/null
cooler dump -t pixels "$tmp/tabix.cool" | grep -E '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+' >/dev/null

python - "$tmp/load.cool" "$tmp/tabix.cool" <<'PY'
import sys
import cooler

c = cooler.Cooler(sys.argv[1])
assert c.shape == (32, 32)
assert int(c.info["nnz"]) > 0

t = cooler.Cooler(sys.argv[2])
assert t.shape[0] > 0
assert t.shape[1] > 0
assert int(t.info["nnz"]) > 0
PY
