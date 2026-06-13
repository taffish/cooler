# cooler

TAFFISH wrapper for [cooler](https://github.com/open2c/cooler), the Open2C
command-line and Python toolkit for storing, querying, balancing, coarsening,
and visualizing Hi-C contact matrices in `.cool` / `.mcool` HDF5 format.

Package identity:

- name: `cooler`
- command: `taf-cooler`
- kind: `tool`
- version: `0.10.4-r1`
- license: Apache-2.0
- container image: `ghcr.io/taffish/cooler:0.10.4-r1`
- upstream: [open2c/cooler](https://github.com/open2c/cooler) `v0.10.4`
- runtime version: `cooler, version 0.10.4`

## Quick Start

```bash
taf-cooler -- --help
taf-cooler cooler info sample.cool
taf-cooler cooler dump -t pixels sample.cool > pixels.tsv
taf-cooler cooler show sample.cool chr1:0-1000000 --out chr1.png
```

Create a cooler from pre-binned 2D bedGraph-style pixels:

```bash
taf-cooler cooler load \
  --format bg2 \
  chrom.sizes:10000 \
  pixels.bg2 \
  sample.cool
```

Sort and tabix-index a pairs file, then load it:

```bash
taf-cooler cooler csort \
  --index tabix \
  -c1 2 -p1 3 -c2 4 -p2 5 \
  sample.pairs chrom.sizes \
  -o sample.sorted.pairs.gz

taf-cooler cooler cload tabix \
  --nproc 4 \
  bins.bed \
  sample.sorted.pairs.gz \
  sample.cool
```

## What Is Packaged

- `cooler` 0.10.4.
- Python 3.12 runtime with the core cooler dependencies.
- Upstream optional extras used by CLI and Python workflows: `biopython`,
  `dask`, `matplotlib`, `psutil`, `pysam`, `ipytree`, and `ipywidgets`.
- External utilities used by `cooler csort`: `bgzip`, `tabix`, Unix `sort`,
  `gzip`, and `pigz`.
- Tiny upstream test fixtures under `/opt/cooler/share/testdata` for smoke
  validation.

## Command Mode

The default command is `cooler`, and TAFFISH command mode is enabled. For cooler
subcommands, use the upstream executable name explicitly:

```bash
taf-cooler cooler info sample.cool
taf-cooler cooler load --help
taf-cooler python -c 'import cooler; print(cooler.__version__)'
```

Use `--` mainly when passing option-leading arguments to the default upstream
command:

```bash
taf-cooler -- --version
taf-cooler -- --help
```

## Inputs And Outputs

Common inputs are `.cool`, `.mcool`, `.scool`, chromosome sizes files, BED bins,
BG2/COO sparse pixel tables, `.pairs` files, tabix-indexed `.pairs.gz`, and
FASTA files for `cooler digest`.

Outputs depend on the subcommand and include cooler HDF5 files, multi-resolution
coolers, tabular dumps, sorted/indexed pairs files, BED fragment bins, static
plots, and metadata/info text.

## Pairix Boundary

This r1 image supports the tabix route:

```bash
taf-cooler cooler csort --index tabix ...
taf-cooler cooler cload tabix ...
```

Upstream cooler also exposes pairix-specific paths. `pairix`/`pypairix` are not
bundled here because they are optional external components, and upstream cooler
0.10.4 does not include `pypairix` in its `all` extra because of build issues.
Use the tabix route unless you intentionally build a custom image with pairix.

## Boundaries

This app is an offline cooler runtime. It does not download Hi-C data, reference
genomes, or chrom sizes, and it does not include mappers, pairtools pipelines,
Juicer Tools, HiGlass services, or a workflow manager.

## Version

- TAFFISH package: `0.10.4-r1`
- Upstream package: `cooler` `v0.10.4`
- Upstream license: BSD-3-Clause
- Citation: Abdennur N, Mirny LA. Cooler: scalable storage for Hi-C data and
  other genomically labeled arrays. *Bioinformatics* (2020).
  doi: `10.1093/bioinformatics/btz540`
