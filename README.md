# cooler

TAFFISH packaging of [Cooler 0.12.1](https://github.com/open2c/cooler/releases/tag/v0.12.1),
the Open2C CLI/Python toolkit for local contact matrices. Default execution stays
CLI-first. Static images and an opt-in Matplotlib WebAgg browser viewer are included.

## Identity and scope

- Package: `cooler 0.12.1-r1`; command: `taf-cooler`.
- Image: `ghcr.io/taffish/cooler:0.12.1-r1`; native Linux amd64 and arm64 targets.
- Packaging license: Apache-2.0. Cooler license: BSD-3-Clause.
- Official upstream source is unchanged; no algorithm or numerical patch.
- Python 3.12, all published Cooler extras, Pairix/pypairix 0.3.9, bgzip/tabix,
  pigz and standard sorting/compression utilities are included.

## Quick start

After this version is published and indexed, install it with
`taf update` followed by `taf install cooler 0.12.1-r1`.
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
| Pair preparation | `cload pairs` accepts unsorted pairs; external sorting is a separate workflow |
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

| Input/output | Meaning |
| --- | --- |
| `chrom.sizes`, bins BED, pixels BG2/COO, pairs | Explicit local inputs; chromosome names/order and coordinate conventions must match. |
| `sample.cool` | One HDF5 matrix with chromosome, bin and pixel tables; normal `load` output. |
| `sample.mcool` | Multiple resolutions in one HDF5 file; select `::/resolutions/N`, not an unqualified file. |
| `sample.scool` | Per-cell matrices; select `::/cells/ID`. This is not an analysis report. |
| `dump` stdout | Tabular data; redirect to a host file. Select columns explicitly for fixed-schema consumers. |
| `balance` weights | Added to the input matrix; copy a shared input before modifying it. |
| `show --out` | A static image at the chosen output filename; the interactive viewer is a temporary service. |

Pairix is included because its official 0.3.9 release resolves the compiler
issue cited by Cooler's disabled extra. Its own source and Python distribution
are independently checksum-pinned. Debian's current bgzip remains the default;
Pairix's older bgzip is not placed on PATH.
The official Pairix **0.3.9 tag** still contains `VERSION.txt` and a C CLI
help banner saying **0.3.8**; these are retained unchanged. Its archive/commit
identify the selected source, while Python package metadata reports pypairix
0.3.9. Use `pairix --help`, not unsupported `--version`/`-V`, to inspect the CLI.

```sh
taf-cooler cooler cload pairs -c1 2 -p1 3 -c2 4 -p2 5 \
  chrom.sizes:10000 sample.pairs out.cool
```

For already sorted/indexed input, use `cload tabix` or `cload pairix` with its
matching index and chromosome order. Upstream removed `csort`; a separate
pairtools workflow is recommended when sorted pairs are needed elsewhere.
This app does not generate alignments or replace pairtools/Juicer pipelines.
Legacy hiclib **input conversion** does not include the legacy hiclib analysis stack.

### Changes when upgrading from 0.11

This is the unmodified upstream 0.12 behavior, not a packaging algorithm patch:

- The 0.12.1 patch reports an error if a parallel worker dies instead of waiting
  indefinitely; reduce processes/chunk sizes when memory is insufficient.
  Whole-number float bin sizes now produce integer coordinates. These paths
  are covered by tiny regressions, not a production memory benchmark.
- Trans-only balancing targets and filters, chromosome-end diagonal filtering,
  and empty bins are corrected; weights can differ from 0.11. Keep old results
  tied to their original version rather than assuming numerical equivalence.
- `balance --no-rescale-marginals` retains the original marginal scale.
- `cload pairs --field v=8:agg=sum_squares` supports exact summary statistics;
  `mean`/`median` aggregators are rejected. Store sum and count, then divide.
- `dump` includes every pixel column by default; select explicit columns if a
  downstream parser expects only counts. Coarsen/zoomify retain requested fields.
- `mv` only moves within one HDF5 file; use `cp` to copy between files.
  Failed writes/overwrites retain the previous complete cooler.
- `zoomify --legacy`, `cooler.sandbox` and deprecated append APIs are removed.
  Custom multiprocessing callbacks must be picklable; lambdas are not supported.
- Inputs are checked more strictly, including chromosome-end bounds, bin tiling,
  duplicate pixels and integer overflow. Fix invalid inputs instead of bypassing
  these checks. See the [upstream release](https://github.com/open2c/cooler/releases/tag/v0.12.1).

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
PNG/SVG browser export and PNG/JPG/SVG/PDF/PS/EPS static output are validated;
other menu formats are retained from Matplotlib, not individually qualified. The upstream
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
private `/tmp/cooler-gui-*` directory, removed after successful cleanup. Failure prints the internal
log tail. Ctrl-C stops the attached foreground session (130); TERM to the
attached runtime stops it (143). Killing only an outer generic launcher PID is
not a supported service-manager contract. The viewer is not a persistent daemon.
If startup/ready output cannot be delivered, the helper fails closed instead of
leaving an unannounced server. Diagnostic write/flush failures never bypass
owned child, port or session cleanup; closed stdout/stderr retain INT/TERM's
130/143 status rather than Python's final-flush status 120. Keep output connected
until ready. Logs are best effort when their output destination is unavailable.
Cleanup checks the private directory's identity and uses descriptor-relative,
non-symlink traversal. A replaced directory or uncertain child termination fails
closed and preserves the recovery path; it is not reported as a successful stop.
Do not remove a reported recovery path until its ownership and contents are checked.

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
  ./target/taf-cooler-v0.12.1-r1 cooler-gui sample.cool chr1:0-1000000 \
    --bind 0.0.0.0 --host-port 8765
```

On 2026-10-29, the TAFFISH 0.11.0 Linux development runner was tested separately:
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

### Backend-sensitive paths

| Capability | Docker | Podman | Apptainer |
| --- | --- | --- | --- |
| Browser viewer | Container bind `0.0.0.0:8000`; host loopback `-p 127.0.0.1:8765:8000` | Same mapping; xjp uses explicit `--network slirp4netns` | Shared host network: loopback `--port 8765`, no `-p` |
| Shared reference input | `-v /absolute/references:/references:ro` | Same read-only bind | `--bind /absolute/references:/references:ro` |
| Process initialization | `--init` is already encoded in the app | `--init` is already encoded in the app | Native runtime handling; no Docker flag injection |

The examples above select the corresponding `TAFFISH_*_RUN_ARGS`; ports and
site paths are not hard-coded in the wrapper. Actual platform/backend evidence
and untested combinations are recorded below, separately from these usage rules.

## Build provenance and reproducibility boundary

- Cooler tag `v0.12.1`: commit `0b07e2330016e3b2710737c30a26fa7156a0a1e4`.
- Wheel SHA256: `2d48b6e4cfbc10e3ef3e3a32ca51029806ed4a7ec4734b924b3d50ebf7780234`.
- Sdist SHA256: `0298597dd630e77883314f795255abb815774a76732bcc8a4d3b2adc4bb3d05e`.
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

The 0.12.1-r1 candidate completed local packaging validation on 2026-10-29;
actual publication remains a maintainer action. Both native builds and all 261
independent offline manifest checks passed. xjp native amd64
Docker/Podman/Apptainer and local ARM64 Docker/Podman passed 120 real-wrapper
checks, 25 GUI lifecycle scenarios, and five groups each of extended and
ordinary-user permission checks. These cover explicit reference binds, spaces,
missing inputs, read-only sharing, and startup/ready INT/TERM cleanup.

Earlier ARM64 Docker attempts were interrupted by the host filesystem-sharing
service. After the maintainer restarted Docker, the same final image and frozen
wrapper passed the complete remaining group without an engine-setting or app
code change. Failed attempts are retained in maintainer evidence, not counted
as PASS; this recovery does not establish a permanent Docker Desktop fix.
Earlier release/0.12.0 results are not reused for this candidate.

The current image sizes are 744,936,759 bytes (amd64) and 777,793,625 bytes
(ARM64). Multi-stage packaging keeps build compilers out of the final image;
the scientific Python closure accounts for most of the remaining size.
Browser navigation, PNG/SVG export and narrow desktop-window scrolling passed
on the current xjp wrapper; this is not mobile-responsive UI certification.
ARM64 Apptainer is not separately validated. Production-scale data, external
assembly installation and scientific accuracy are outside tiny packaging
checks. Public Action/GHCR/Index evidence follows actual publication.

Citation: Abdennur N, Mirny LA. Cooler: scalable storage for Hi-C data and other
genomically labeled arrays. Bioinformatics (2020).
[doi:10.1093/bioinformatics/btz540](https://doi.org/10.1093/bioinformatics/btz540).
