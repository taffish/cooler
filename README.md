# cooler

TAFFISH packaging of [Cooler 0.11.0](https://github.com/open2c/cooler/releases/tag/v0.11.0),
the Open2C CLI/Python toolkit for local contact matrices. Default execution stays
CLI-first. Static images and an opt-in Matplotlib WebAgg browser viewer are included.

## Identity and scope

- Package: `cooler 0.11.0-r1`; command: `taf-cooler`.
- Image: `ghcr.io/taffish/cooler:0.11.0-r1`; native Linux amd64 and arm64 targets.
- Packaging license: Apache-2.0. Cooler license: BSD-3-Clause.
- Official upstream source is unchanged; no algorithm or numerical patch.
- Python 3.12, all published Cooler extras, Pairix/pypairix 0.3.9, bgzip/tabix,
  pigz and standard sorting/compression utilities are included.

## Quick start

After this version is published and indexed, install it with
`taf update` followed by `taf install cooler 0.11.0-r1`.
For an unpublished local candidate, use `taf build` and its frozen wrapper as
shown below; do not assume the registry already contains this image.

Run inside a writable project directory containing your inputs:

```sh
taf-cooler --help
taf-cooler -- --version
taf-cooler cooler load --format bg2 chrom.sizes:10000 pixels.bg2 sample.cool
taf-cooler cooler info sample.cool
taf-cooler cooler dump -t pixels sample.cool > pixels.tsv
taf-cooler cooler show sample.cool chr1:0-1000000 --out chr1.png
```

`--help` and `--version` without the separator describe the TAFFISH wrapper.
`-- --help` and `-- --version` reach the default upstream executable.
In command mode, write the executable explicitly before a subcommand:

```sh
taf-cooler cooler load --help
taf-cooler python -c '"import cooler; print(cooler.__version__)"'
taf-cooler cooler info "'input with spaces.cool'"
```

The inner quotes are intentional: the current TAFFISH command mode parses a
shell command. Ordinary outer quotes alone do not preserve every argument.
For complicated scripts use a local Python file, e.g. `taf-cooler python analysis.py`.
Do not construct a command by interpolating untrusted shell text.

## Functional surface

| Task | Interface and boundary |
| --- | --- |
| Matrix ingestion | `load` BG2/COO; `cload pairs/tabix/pairix/hiclib` |
| Pair preparation | `csort` with tabix or Pairix; explicit column mapping |
| Bins and fragments | `makebins`, `digest` with local chromosome sizes/FASTA |
| Matrix operations | `balance`, `coarsen`, `zoomify`, `merge` |
| Inspection and HDF5 objects | `info/dump/ls/tree/attrs/cp/mv/ln` |
| Single-cell files | upstream Python `create_scool` and `.scool::/cells/ID` |
| Static viewing | `show --out`: PNG, JPG, SVG, PDF, PS, EPS |
| Interactive viewing | `cooler-gui`: unchanged `cooler show` via official WebAgg |
| Python ecosystem | upstream `all` extras, including dask, widgets and ipytree |

Coordinates are zero-based, half-open. A multi-resolution URI must select an
existing resolution, e.g. `sample.mcool::/resolutions/10000`.
`balance` modifies its input; work on a copy rather than a shared read-only matrix.
FASTA indexing may create `.fai` beside the FASTA: prepare it once or copy the
input to writable scratch before `digest`.

Pairix is now included because its official 0.3.9 release resolves the compiler
issue cited by Cooler's disabled extra. Its own source and Python distribution
are independently checksum-pinned. Debian's current bgzip remains the default;
Pairix's older bgzip is not placed on PATH.
The official Pairix **0.3.9 tag** still contains `VERSION.txt` and a C CLI
help banner saying **0.3.8**; these are retained unchanged. Its archive/commit
identify the selected source, while Python package metadata reports pypairix
0.3.9. Use `pairix --help`, not unsupported `--version`/`-V`, to inspect the CLI.

```sh
taf-cooler cooler csort --index pairix -c1 2 -p1 3 -c2 4 -p2 5 \
  sample.pairs chrom.sizes -o sorted.pairs.gz
taf-cooler cooler cload pairix --nproc 4 chrom.sizes:10000 sorted.pairs.gz out.cool
```

For tabix, change both `--index pairix` and `cload pairix` to `tabix`.
This app does not generate alignments or replace pairtools/Juicer pipelines.
Legacy hiclib **input conversion** does not include the legacy hiclib analysis stack.

## Browser viewer

First generate a valid `sample.cool` using the Quick start command, or supply an
existing local matrix. The viewer does not create a matrix or infer a resolution.

```sh
TAFFISH_CONTAINER_BACKEND=docker \
  TAFFISH_DOCKER_RUN_ARGS="-p 127.0.0.1:8765:8000" \
  taf-cooler cooler-gui sample.cool chr1:0-1000000 \
    --bind 0.0.0.0 --port 8000 --host-port 8765

TAFFISH_CONTAINER_BACKEND=podman \
  TAFFISH_PODMAN_RUN_ARGS="-p 127.0.0.1:8765:8000" \
  taf-cooler cooler-gui sample.cool chr1:0-1000000 \
    --bind 0.0.0.0 --port 8000 --host-port 8765

TAFFISH_CONTAINER_BACKEND=apptainer \
  taf-cooler cooler-gui sample.cool chr1:0-1000000 --port 8765
```

Open `http://127.0.0.1:8765/1` after the separate ready message. The toolbar
supports navigation and figure downloads. The upstream region callback updates
the matrix after pan/zoom; the algorithm is not replaced by a TAFFISH renderer.
Use a bounded region or coarser resolution rather than forcing a huge matrix.
After the Home/Back/Forward toolbar changes the axes, **click inside the plot
once** to refresh the matrix before interpreting or exporting it. Cooler's
unchanged interactive callback listens to canvas mouse-release events, not
toolbar history events; a toolbar-only reset can temporarily leave the previous
cropped matrix in the restored axes. This upstream behavior is retained.

WebAgg retains its native fixed-size figure: on a narrow window scroll horizontally
and vertically to reach the whole canvas and toolbar, or use a desktop window.
PNG/SVG/PDF and the other non-PGF menu formats are supported. The upstream
download button opens an image/document tab for some formats; save that result
using the browser. **PGF is unsupported for this raster matrix through WebAgg**:
upstream still lists PGF, but its streamed-PGF writer rejects raster graphics.
Choosing it returns an upstream HTTP 500 without stopping the viewer; select
PNG/SVG/PDF instead. Installing TeX alone does not resolve this streamed-raster
limitation. No upstream renderer is patched; a full TeX toolchain is not bundled.

For a remote server use `ssh -N -L 8765:127.0.0.1:8765 user@server`.
The helper defaults to listening on loopback. Docker/Podman examples explicitly
listen on all **container** interfaces but publish only host loopback. Apptainer
shares the host network and must keep loopback; it has no Docker-style `-p`.
On a Linux host whose default Podman `pasta` cannot open its network namespace,
add `--network slirp4netns` to `TAFFISH_PODMAN_RUN_ARGS`, keeping the same loopback
port mapping. This requires the host's slirp4netns executable and uses Podman's
[supported user-mode network option](https://docs.podman.io/en/latest/markdown/podman-run.1.html#network-mode-net).
The validation host required this explicit GUI-only alternative; the failure
also occurred with `podman run ... true` before Cooler started. It is not fixed
by changing this image. No host security policy or engine setting was changed.
For another port adjust the mapping and `--host-port`; with Apptainer adjust
`--port` too. No public IP is guessed.

Options include `--port`, `--host-port`, `--bind`, `--url-host`, `--label`,
`--ready-timeout`, `--range2`, `--scale`, `--balanced`, `--weight-name`,
`--cmap`, `--zmin` and `--zmax`. For spaces:

```sh
TAFFISH_CONTAINER_BACKEND=docker \
  TAFFISH_DOCKER_RUN_ARGS="-p 127.0.0.1:8765:8000" \
  taf-cooler cooler-gui "'input with spaces.cool'" chr1:0-1000000 \
    --bind 0.0.0.0 --host-port 8765 --label "'My matrix'"
```

The app-owned helper supplies safe bind defaults, host URL/SSH instructions,
unbuffered startup information, readiness tied to its own listening child,
ongoing process supervision and bounded cleanup. It does not proxy or patch
Cooler/Matplotlib code. All logs, font caches and configuration live in one
private `/tmp/cooler-gui-*` directory, removed on exit. Failure prints the internal
log tail. Ctrl-C stops the attached foreground session (130); TERM to the
attached runtime stops it (143). Killing only an outer generic launcher PID is
not a supported service-manager contract. The viewer is not a persistent daemon.
If startup/ready output cannot be delivered, the helper fails closed instead of
leaving an unannounced server. Diagnostic write/flush failures never bypass
owned child, port or session cleanup; closed stdout/stderr retain INT/TERM's
130/143 status rather than Python's final-flush status 120. Keep output connected
until ready. Logs are best effort when their output destination is unavailable.

There is **no authentication or TLS**. Use localhost, SSH or a separately secured
site proxy; matrix names, coordinates and metadata may be visible to visitors.
There are no cloud accounts, telemetry or production dataset downloads in the
viewer. Raw `cooler show` remains available; without `--out` it requires a suitable
Matplotlib backend. Use `cooler-gui` for this packaged browser path.

HiGlass's independent server/data-ingestion infrastructure and Jupyter's arbitrary
code execution/authentication lifecycle are not bundled. Those require separate
service/security contracts; this image includes the upstream Python widgets,
not a notebook server. No X11/noVNC, GPU, desktop window manager or browser engine
is required in the container.

For local candidate development, use the frozen wrapper for a long-running GUI:

```sh
taf build
TAFFISH_CONTAINER_BACKEND=docker \
  TAFFISH_DOCKER_RUN_ARGS="-p 127.0.0.1:8765:8000" \
  ./target/taf-cooler-v0.11.0-r1 cooler-gui sample.cool chr1:0-1000000 \
    --bind 0.0.0.0 --host-port 8765
```

The current TAFFISH 0.11.0 Linux development runner was tested separately:
`taf run -b docker -- cooler load ...` generated a valid tiny matrix, but a
long-running GUI reached container readiness while its starting/ready text
remained buffered by `taf run`; PTY Ctrl-C returned 1, not 130. No owned container
or listener remained. This is a core development-runner boundary, not an upstream
Cooler or helper algorithm patch. Use the frozen/installed wrapper for services;
do not infer service output/signal equivalence from a short `taf run` command.

## Reference inputs and shared use

There is no Cooler model, taxonomy database, mandatory reference bundle or
automatic assembly selection. Contact matrices/pairs/bins are project inputs.
Chromosome sizes and FASTA are explicitly selected reference inputs; compatible
assembly and chromosome ordering are the caller's responsibility.

The upstream Python convenience API `cooler.fetch_chromsizes(db)` explicitly
fetches a small UCSC table; `read_chromsizes` also accepts explicit URLs through
pandas. These are opt-in network calls, not a missing-local-file fallback.
They are preserved unchanged, including their mutable upstream source semantics.
A result is not a versioned installation receipt. Normal CLI examples and all
smoke tests use explicit local files with networking disabled.

A separate automatic database/model installer and discovery hook are not added:
Cooler consumes ordinary input filenames, the convenience fetch returns a table
rather than installing a managed resource, and the small chromosome table has
no Cooler-defined release catalog/checksum contract. This is an evaluated
manual-file reuse path, not a claim that reference downloading does not exist.
For repeatable use, save the chosen table once, record source URL, assembly,
retrieval date, byte size, SHA256 and applicable source terms, and use that fixed
file thereafter. Prepare FASTA plus its index together. Do not silently refresh
a shared assembly or overwrite users' inputs.

A user can prepare under
`~/.local/share/taffish/resources/cooler/ASSEMBLY-CHECKSUM/`; an administrator
can prepare once under `/usr/local/share/taffish/resources/cooler/ASSEMBLY-CHECKSUM/`
or `/opt/taffish/resources/cooler/ASSEMBLY-CHECKSUM/`.
Use traversable 0755 directories and readable 0644 input files owned by the
preparer. Ordinary users need read access, not write access or duplicate downloads.
Keep outputs elsewhere. Review assembly/provider terms before site sharing:
this app's Apache-2.0 and Cooler's BSD license do not relicense external data.
For the explicit UCSC fetch API, [UCSC's data licensing guidance](https://genome.ucsc.edu/license/)
permits public/commercial reuse of its raw tables in general, subject to the
original provider and each assembly download directory's README exceptions.
There is no blanket claim that every third-party FASTA/annotation is redistributable.
This route is classified as explicit reference-file input/reuse, **not** as a
login- or license-restricted download that would justify evading a resource helper.

Bind the prepared directory explicitly and select its filenames:

```sh
TAFFISH_CONTAINER_BACKEND=docker \
  TAFFISH_DOCKER_RUN_ARGS="-v /absolute/references:/references:ro" \
  taf-cooler cooler makebins /references/chrom.sizes 10000 > bins.bed

TAFFISH_CONTAINER_BACKEND=podman \
  TAFFISH_PODMAN_RUN_ARGS="-v /absolute/references:/references:ro" \
  taf-cooler cooler makebins /references/chrom.sizes 10000 > bins.bed

TAFFISH_CONTAINER_BACKEND=apptainer \
  TAFFISH_APPTAINER_RUN_ARGS="--bind /absolute/references:/references:ro" \
  taf-cooler cooler makebins /references/chrom.sizes 10000 > bins.bed
```

No automatic path priority or hidden fallback overrides these selections.
macOS VM mounts must expose the chosen host path; Apptainer uses Linux site
permissions. Missing files and malformed chromosome lengths fail explicitly.
Manual installation has no app-owned transaction, lock, partial-cache deletion,
`--force` or resumable download semantics; those installer tests are N/A here.
Shared tiny-input read-only behavior is distinct from a real production assembly
installation or scientific validation.

## Build provenance and reproducibility boundary

- Cooler tag `v0.11.0`: commit `5506008e865545e53abd66447b953e75438b8340`.
- Wheel SHA256: `c38930549945bb261174d0598528bc4139206e0e3053f4809f24ed4e673b2048`.
- Sdist SHA256: `11a527bde867c31fe392589d0f947056b9200a70cdb033866ddfce3db031a91a`.
- Pairix tag `0.3.9`: `5df7a5b0ae6a766c03d05bc10cfad7e49e43c607`.
- Pairix archive SHA256: `84851aac4fe7aa74988a107ae7b93fbd4b191fd96459ca81fffbdbd39b041d2c`.
- pypairix archive SHA256: `a1dc8b11b35ab6b7763935898ec45abf422e060517295a1dadc33b6e9eaad03a`.
- Python base index digest is fixed in the Dockerfile; native child digests differ.
- APT and transitive PyPI/build dependencies use live repositories. Their inventory
  is a receipt, **not an input lock or archival guarantee**. Fixed hashes verify
  bytes, not future availability. Investigate missing artifacts; do not silently
  weaken checks or substitute versions. Risk comments are at each download step.

The builder defaults to official Pairix/PyPI URLs. Optional build arguments
`PAIRIX_SOURCE_URL` and `PYPAIRIX_SOURCE_URL` may point at a verified archive
mirror when a long download is unreliable; the fixed SHA256 checks cannot be
overridden. This is identical-byte source recovery, not permission to substitute
a different release. Record the selected transport alongside the build receipt.

The image preserves upstream test fixtures and notices under
`/opt/cooler/share`; dependency inventory is in `share/doc/cooler`.
Build-time checks are limited to version/help/tiny I/O. Rendering, full CLI
regressions and services run as independent runtime checks, not fragile ARM64
build gates. Runtime cache is private scratch, not the installation tree.

## Validation status

As of 2026-10-26 the local candidate's runtime validation is complete; it is
prepared for maintainer publication, **not published**.
Native builds passed: amd64 image 760,228,182 bytes; arm64 794,124,796 bytes.
xjp's native Docker, Podman and Apptainer suites passed in full; ARM64 Docker
and Podman also passed. Across the five native axes, 252 fresh/offline smoke
checks and 165 real-wrapper checks passed on the rebuilt final images.
All 25 GUI lifecycle checks and five extended format/dependency checks passed.
The wrapper checks include eight actual output-failure scenarios per axis:
first-write failures, closed stdout/stderr, INT/TERM and child failure. They
verify owned-process, port and temporary-directory cleanup, unchanged inputs
and recovery sentinels, and exit status 1/130/143 rather than 120. Separately,
18 controlled early-signal/write/flush injections passed, including ENOSPC.
Final real-wrapper browser rendering, zoom, refresh and PNG export also passed.
The initial regression incorrectly assumed Apptainer's isolated /dev contained
/dev/full; that test failure is retained. Portable closed-pipe tests replaced
that device assumption, followed by final rebuilds and complete five-axis reruns.
No engine restart, device exposure, quota or security change was needed for
this repair. Earlier keyring/client failures and the original output-cleanup
failure remain in the maintainer evidence, not hidden by the final results.
A publish dry-run plans publication; it does not establish public
Action/GHCR/Index success.
ARM64 Apptainer is not inferred from the other five native axes. Production-scale
datasets, external reference installation and scientific correctness remain outside
the synthetic/tiny packaging checks.

Citation: Abdennur N, Mirny LA. Cooler: scalable storage for Hi-C data and other
genomically labeled arrays. Bioinformatics (2020).
[doi:10.1093/bioinformatics/btz540](https://doi.org/10.1093/bioinformatics/btz540).
