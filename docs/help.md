taf-cooler 0.12.1-r1

Use cooler for local contact matrices; save plots or view them in a browser.
Supply your own .cool/.mcool, pairs, bins, chromosome sizes and FASTA inputs.

Quick start:
  taf-cooler --help
  taf-cooler -- --help
  taf-cooler -- --version
  taf-cooler cooler load --help
  taf-cooler cooler info sample.cool

Create and inspect:
  taf-cooler cooler load --format bg2 chrom.sizes:10000 pixels.bg2 sample.cool
  taf-cooler cooler dump -t pixels sample.cool > pixels.tsv
  taf-cooler cooler balance --nproc 4 sample.cool
  taf-cooler cooler zoomify -r 10000,20000,50000 -o sample.mcool sample.cool
  taf-cooler cooler show sample.cool chr1:0-1000000 --out chr1.png

Pairs:
  taf-cooler cooler cload pairs -c1 2 -p1 3 -c2 4 -p2 5 \
    chrom.sizes:10000 sample.pairs out.cool
  csort was removed; cload pairs accepts unsorted pairs directly.
  Existing indexed pairs: use cload tabix or cload pairix with the matching index.

Paths and command mode:
  taf-cooler cooler info "'input with spaces.cool'"
  taf-cooler python -c '"import cooler; print(cooler.__version__)"'
  Keep the inner quotes in these examples: command mode parses a shell command.
  Use cooler before a subcommand; use -- for leading options of default cooler.
  Regions are zero-based, half-open. For .mcool, select an existing resolution:
  taf-cooler cooler info sample.mcool::/resolutions/10000
  Write outputs to your working directory or an explicitly writable host mount.
  balance modifies its input; copy a shared read-only matrix before balancing.
  digest may create a FASTA .fai beside its input; prepare it before sharing.

Browser view (requires sample.cool from load above):
  Docker:
  TAFFISH_CONTAINER_BACKEND=docker \
    TAFFISH_DOCKER_RUN_ARGS="-p 127.0.0.1:8765:8000" \
    taf-cooler cooler-gui sample.cool chr1:0-1000000 \
      --bind 0.0.0.0 --port 8000 --host-port 8765

  Podman:
  TAFFISH_CONTAINER_BACKEND=podman \
    TAFFISH_PODMAN_RUN_ARGS="-p 127.0.0.1:8765:8000" \
    taf-cooler cooler-gui sample.cool chr1:0-1000000 \
      --bind 0.0.0.0 --port 8000 --host-port 8765

  Apptainer (Linux; shared host network, no -p):
  TAFFISH_CONTAINER_BACKEND=apptainer \
    taf-cooler cooler-gui sample.cool chr1:0-1000000 --port 8765

  Open http://127.0.0.1:8765/1 after the ready message; pan, zoom or download.
  After Home/Back/Forward, click inside the plot once to refresh the matrix.
  Narrow window: scroll to reach the canvas/toolbar. Downloads may open a new tab.
  PGF cannot stream this raster matrix; choose PNG/SVG/PDF instead.
  If Linux Podman fails in pasta before startup, add --network slirp4netns
  to TAFFISH_PODMAN_RUN_ARGS (requires host slirp4netns); keep loopback -p.
  Remote: ssh -N -L 8765:127.0.0.1:8765 user@server
  Press Ctrl-C to stop. Successful cleanup removes temporary logs/cache.
  Keep output open until ready; a failed startup message stops the session.
  Cleanup errors fail with a recovery path; never delete an unfamiliar directory.
  This viewer has no login or TLS: use localhost/SSH, never a public port.
  taf-cooler cooler-gui --help
  Use --out PNG/SVG/PDF for static output; raw show without --out is not a server.

Shared local reference input:
  Select a compatible assembly explicitly. No reference is chosen or fetched
  automatically; missing local input fails. Do not edit a shared reference.
  For a prepared directory, bind it read-only to /references:
  Docker: TAFFISH_DOCKER_RUN_ARGS="-v /absolute/references:/references:ro"
  Podman: TAFFISH_PODMAN_RUN_ARGS="-v /absolute/references:/references:ro"
  Apptainer: TAFFISH_APPTAINER_RUN_ARGS="--bind /absolute/references:/references:ro"
  Set the relevant variable with your backend, then use /references/chrom.sizes
  in place of chrom.sizes above. Mount syntax requires an absolute host path.
  Ask the administrator to prepare/check references once with readable files.
  Python fetch_chromsizes() or explicit remote URLs opt into network access;
  prefer a saved, checksum-verified local file for repeatable offline work.

Troubleshooting:
  Missing weights: run balance on a writable copy, or omit --balanced.
  0.12: trans-only weights change; mean aggregation is replaced by sum/count.
  Port busy: choose another host port and update mapping and --host-port.
  For Apptainer change --port as well. Keep its default loopback --bind.
  A matrix that is too large: select a smaller region or coarser resolution.
  No GPU is required. macOS uses Docker/Podman; Apptainer requires Linux.

Full documentation: https://github.com/taffish/cooler
Upstream CLI: https://cooler.readthedocs.io/en/latest/cli.html
