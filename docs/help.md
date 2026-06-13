taf-cooler 0.10.4-r1

Purpose:
  TAFFISH runtime for cooler 0.10.4, the Open2C CLI/Python toolkit for Hi-C
  contact matrices in .cool/.mcool HDF5 format.

Usage:
  taf-cooler --help
  taf-cooler --version
  taf-cooler -- --help
  taf-cooler -- --version
  taf-cooler cooler info sample.cool
  taf-cooler cooler load --format bg2 chrom.sizes:10000 pixels.bg2 sample.cool
  taf-cooler cooler zoomify sample.cool -r 10000,20000,50000 -o sample.mcool

Wrapper options:
  -h, --help       Show this TAFFISH help.
  -v, --version    Show the TAFFISH package version.
  --compile        Print generated shell code instead of running it.
  --               Pass following option-leading arguments to the default
                   upstream command, cooler.

  taf-cooler --help shows this TAFFISH manual.
  taf-cooler -- --help shows upstream cooler help.
  taf-cooler -- --version should print: cooler, version 0.10.4

Main cooler subcommands:
  cload, load, csort, makebins, digest, info, dump, show, balance, coarsen,
  zoomify, merge, ls, cp, ln, mv, tree, attrs.

Command mode:
  This app keeps TAFFISH command mode enabled. Non-option-leading arguments run
  commands inside the same container.

  Examples:
    taf-cooler cooler info sample.cool
    taf-cooler cooler load --help
    taf-cooler python -c '"import cooler; print(cooler.__version__)"'

  For cooler subcommands, prefer taf-cooler cooler <subcommand> ...
  Use -- mainly for option-leading arguments to the default cooler command.

Packaged runtime:
  Python 3.12 with cooler 0.10.4, core dependencies, and common upstream
  optional extras for CLI/Python workflows: biopython, dask, matplotlib,
  psutil, pysam, ipytree, and ipywidgets.
  External utilities include bgzip, tabix, Unix sort, gzip, pigz, bash, grep,
  and sed.

Inputs:
  .cool/.mcool/.scool  Cooler HDF5 files and cooler URIs.
  chrom.sizes          Two-column chromosome sizes table.
  BED bins             BED-like genomic bins used by load and cload.
  bg2/coo pixels       Pre-binned sparse matrix inputs for cooler load.
  .pairs text/gz       Genomic pairs input for csort and cload.
  FASTA                Genome FASTA for cooler digest.

Outputs:
  Outputs include .cool/.mcool/.scool files, tabular dumps, sorted/indexed
  pairs files, BED bins, static plots, and metadata/info text.

Examples:
  taf-cooler cooler info sample.cool
  taf-cooler cooler dump -t bins sample.cool > bins.tsv
  taf-cooler cooler load --format bg2 chrom.sizes:10000 pixels.bg2 sample.cool
  taf-cooler cooler csort --index tabix -c1 2 -p1 3 -c2 4 -p2 5 pairs.tsv chrom.sizes -o pairs.sorted.gz
  taf-cooler cooler cload tabix --nproc 4 bins.bed pairs.sorted.gz sample.cool

Boundaries:
  Offline runtime: no Hi-C data, genomes, chrom sizes, or external references
  are downloaded during normal use or smoke tests.

  Packaged pairs path: cooler csort --index tabix and cooler cload tabix.
  pairix/pypairix are optional external components and are not bundled in r1.

  This app does not include read mappers, pairtools pipelines, Juicer Tools,
  HiGlass services, web servers, or a workflow manager. Use taf-pairtools or
  other dedicated TAFFISH tools for upstream pairs generation.

Platform:
  Native linux/amd64 and linux/arm64 builds are intended. No GPU, device,
  service, or network runtime arguments are configured.

More information:
  TAFFISH app README: https://github.com/taffish/cooler
  Upstream docs: https://cooler.readthedocs.io/
  Upstream source: https://github.com/open2c/cooler
