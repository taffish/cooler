# The multi-platform base digest fixes today's Python 3.12.15 contents, not
# future registry availability. Recover identical verified bytes if removed;
# adopting another digest requires a new reviewed build and full validation.
ARG BASE=python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
FROM ${BASE} AS builder

ENV DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=5 PYTHONNOUSERSITE=1
# Debian packages are resolved from an active repository and can change or
# disappear. Inspect repository errors first; do not weaken integrity checks.
# This is not an archival APT snapshot or a promise of permanent rebuildability.
RUN apt-get -o Acquire::Retries=3 update \
 && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
      ca-certificates gcc g++ make libc6-dev zlib1g-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/build
# The primary wheel and source archive are pinned and checked. PyPI transitive
# dependencies/build requirements still resolve dynamically: the recorded
# inventory is a build receipt, not an input lock. Missing or changed artifacts
# must be investigated; changing materials requires a reviewed update/retest,
# never merely replacing an expected hash or removing a failed assertion.
RUN python -m venv /opt/cooler \
 && /opt/cooler/bin/python -m pip install --upgrade pip setuptools wheel \
 && /opt/cooler/bin/python -m pip download --no-deps --only-binary=:all: cooler==0.12.1 \
 && echo '2d48b6e4cfbc10e3ef3e3a32ca51029806ed4a7ec4734b924b3d50ebf7780234  cooler-0.12.1-py3-none-any.whl' | sha256sum -c - \
 && /opt/cooler/bin/python -m pip install './cooler-0.12.1-py3-none-any.whl[all]' \
 && /opt/cooler/bin/python -m pip check \
 && python -c "import urllib.request; urllib.request.urlretrieve('https://files.pythonhosted.org/packages/39/5d/0e74febdeb6ab16bc9748aa7e03c608e3a1d28e0b0356c265fb5f8e8f495/cooler-0.12.1.tar.gz', 'cooler.tar.gz')" \
 && echo '0298597dd630e77883314f795255abb815774a76732bcc8a4d3b2adc4bb3d05e  cooler.tar.gz' | sha256sum -c - \
 && tar -xzf cooler.tar.gz \
 && install -d -m 0755 /opt/cooler/share/doc/cooler /opt/cooler/share/licenses/cooler /opt/cooler/share/testdata \
 && install -m 0644 cooler-0.12.1/LICENSE /opt/cooler/share/licenses/cooler/LICENSE \
 && cp -a cooler-0.12.1/README.md cooler-0.12.1/CHANGES.md cooler-0.12.1/CITATION.cff cooler-0.12.1/pyproject.toml /opt/cooler/share/doc/cooler/ \
 && cp -a cooler-0.12.1/tests/data/. /opt/cooler/share/testdata/ \
 && /opt/cooler/bin/python -m pip freeze --all > /opt/cooler/share/doc/cooler/requirements.freeze.txt \
 && /opt/cooler/bin/python -m pip inspect > /opt/cooler/share/doc/cooler/python-inventory.json \
 && find /opt/cooler -type d -name __pycache__ -prune -exec rm -rf '{}' + \
 && find /opt/cooler/share -type d -exec chmod 0755 '{}' + \
 && find /opt/cooler/share -type f -exec chmod 0644 '{}' +

# Pairix 0.3.9 fixes the upstream compiler compatibility issue. Keep its own
# source identity and licenses; do not shadow Debian's bgzip with its older one.
# GitHub/PyPI archive availability is not guaranteed; preserve these checksums.
# An explicitly selected verified mirror can recover the identical archive when
# a long download is interrupted. The source hashes below are never overridden.
ARG PAIRIX_SOURCE_URL=https://codeload.github.com/4dn-dcic/pairix/tar.gz/refs/tags/0.3.9
ARG PYPAIRIX_SOURCE_URL=https://files.pythonhosted.org/packages/03/dd/c07c30421975664c8b3716542c2c22331606856019852229bf6974fd5caa/pypairix-0.3.9.tar.gz
RUN python -c "import os, urllib.request; urllib.request.urlretrieve(os.environ['PAIRIX_SOURCE_URL'], 'pairix.tar.gz'); urllib.request.urlretrieve(os.environ['PYPAIRIX_SOURCE_URL'], 'pypairix.tar.gz')" \
 && echo '84851aac4fe7aa74988a107ae7b93fbd4b191fd96459ca81fffbdbd39b041d2c  pairix.tar.gz' | sha256sum -c - \
 && echo 'a1dc8b11b35ab6b7763935898ec45abf422e060517295a1dadc33b6e9eaad03a  pypairix.tar.gz' | sha256sum -c - \
 && tar -xzf pairix.tar.gz \
 && make -C pairix-0.3.9 -j2 \
 && install -m 0755 pairix-0.3.9/bin/pairix pairix-0.3.9/bin/pairs_merger pairix-0.3.9/bin/streamer_1d /opt/cooler/bin/ \
 && /opt/cooler/bin/python -m pip install ./pypairix.tar.gz tornado \
 && /opt/cooler/bin/python -m pip check \
 && install -d -m 0755 /opt/cooler/share/licenses/pairix /opt/cooler/share/doc/pairix \
 && install -m 0644 pairix-0.3.9/LICENSE.txt /opt/cooler/share/licenses/pairix/LICENSE.txt \
 && install -m 0644 pairix-0.3.9/README.md pairix-0.3.9/VERSION.txt /opt/cooler/share/doc/pairix/ \
 && /opt/cooler/bin/python -m pip freeze --all > /opt/cooler/share/doc/cooler/requirements.freeze.txt \
 && /opt/cooler/bin/python -m pip inspect > /opt/cooler/share/doc/cooler/python-inventory.json

FROM ${BASE}
ENV DEBIAN_FRONTEND=noninteractive PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLBACKEND=Agg XDG_CACHE_HOME=/tmp \
    PATH=/opt/cooler/bin:/usr/local/bin:/usr/bin:/bin \
    COOLER_HOME=/opt/cooler COOLER_TESTDATA=/opt/cooler/share/testdata
# Runtime APT has the same active-repository boundary described above.
RUN apt-get -o Acquire::Retries=3 update \
 && apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
      bash bzip2 ca-certificates coreutils fontconfig fonts-dejavu-core gawk \
      grep gzip libgomp1 libstdc++6 pigz sed tabix xz-utils \
 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/cooler /opt/cooler
COPY docker/cooler_smoke.py /opt/cooler/share/cooler_smoke.py
COPY docker/cooler_gui_smoke.py /opt/cooler/share/cooler_gui_smoke.py
COPY docker/cooler-gui /opt/cooler/bin/cooler-gui
# Explicit parent traversal matters with current BuildKit COPY semantics.
RUN chmod 0755 /opt /opt/cooler /opt/cooler/share \
 && chmod 0644 /opt/cooler/share/cooler_smoke.py /opt/cooler/share/cooler_gui_smoke.py \
 && chmod 0755 /opt/cooler/bin/cooler-gui \
 && cooler-gui --help >/dev/null \
 && python /opt/cooler/share/cooler_smoke.py buildtime
# Rendering, full pipelines and interactive sessions are runtime checks only.
WORKDIR /tmp
ENV TAFFISH_ENV=TAFFISH TAFFISH_NAME=cooler
