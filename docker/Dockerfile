ARG COOLER_VERSION=0.10.4
ARG COOLER_WHEEL_SHA256=f245de63d05cd9e25961f85a8226929faa3607575be38dd5b6e33a200cef319e
ARG COOLER_SDIST_SHA256=1c25626d5970cedd1ff651966c36d97073a697a7830d369b43b2d0e59ce405ba
ARG COOLER_SDIST_URL=https://files.pythonhosted.org/packages/64/76/2527cef69c2f71f18341be4e29e017bfe2af054afe8b2d106465391fc51e/cooler-0.10.4.tar.gz
ARG DEBIAN_MIRROR=http://deb.debian.org/debian
ARG DEBIAN_SECURITY_MIRROR=http://deb.debian.org/debian-security
ARG PIP_INDEX_URL=https://pypi.org/simple

FROM python:3.12-slim-bookworm AS builder

ARG COOLER_VERSION
ARG COOLER_WHEEL_SHA256
ARG COOLER_SDIST_SHA256
ARG COOLER_SDIST_URL
ARG DEBIAN_MIRROR
ARG DEBIAN_SECURITY_MIRROR
ARG PIP_INDEX_URL

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5
ENV PIP_INDEX_URL=${PIP_INDEX_URL}
ENV PYTHONNOUSERSITE=1
ENV MPLBACKEND=Agg
ENV XDG_CACHE_HOME=/tmp

RUN set -eux; \
    sed -i \
      -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
      -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
      /etc/apt/sources.list.d/debian.sources; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=5 update \
       && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
            ca-certificates \
            g++ \
            gcc \
            libc6-dev \
            make \
            tar; then \
        break; \
      fi; \
      if [ "$attempt" = "5" ]; then exit 1; fi; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/build/cooler

RUN set -eux; \
    python -m venv /opt/cooler; \
    /opt/cooler/bin/python -m pip install --upgrade pip setuptools wheel; \
    /opt/cooler/bin/python -m pip download --only-binary=:all: --no-deps --dest /tmp \
      "cooler==${COOLER_VERSION}"; \
    echo "${COOLER_WHEEL_SHA256}  /tmp/cooler-${COOLER_VERSION}-py3-none-any.whl" | sha256sum -c -; \
    /opt/cooler/bin/python -m pip install --no-cache-dir \
      "/tmp/cooler-${COOLER_VERSION}-py3-none-any.whl" \
      biopython \
      "dask[array,dataframe]" \
      ipytree \
      ipywidgets \
      matplotlib \
      psutil \
      pysam; \
    /opt/cooler/bin/python -m pip check; \
    /opt/cooler/bin/python -c "import urllib.request; urllib.request.urlretrieve('${COOLER_SDIST_URL}', '/tmp/cooler-${COOLER_VERSION}.tar.gz')"; \
    echo "${COOLER_SDIST_SHA256}  /tmp/cooler-${COOLER_VERSION}.tar.gz" | sha256sum -c -; \
    tar -xzf "/tmp/cooler-${COOLER_VERSION}.tar.gz" --strip-components=1; \
    mkdir -p /opt/cooler/share/doc/cooler /opt/cooler/share/licenses/cooler /opt/cooler/share/testdata; \
    cp -a README.md CHANGES.md CITATION.cff pyproject.toml /opt/cooler/share/doc/cooler/; \
    install -m 0644 LICENSE /opt/cooler/share/licenses/cooler/LICENSE; \
    printf "%s\n" "${COOLER_VERSION}" > /opt/cooler/share/doc/cooler/VERSION; \
    for f in \
      tests/data/toy.chrom.sizes \
      tests/data/toy.fasta \
      tests/data/toy.pairs \
      tests/data/toy.bins.8.bed \
      tests/data/toy.symm.upper.2.bg2 \
      tests/data/toy.symm.upper.2.cool \
      tests/data/toy.symm.upper.2.mcool \
      tests/data/hg19.bins.2000kb.bed.gz \
      tests/data/hg19.GM12878-MboI.pairs.subsample.sorted.txt.gz \
      tests/data/hg19.GM12878-MboI.pairs.subsample.sorted.txt.gz.tbi \
      tests/data/hg19.GM12878-MboI.matrix.2000kb.cool; do \
        cp -a "$f" /opt/cooler/share/testdata/; \
    done; \
    /opt/cooler/bin/cooler --version 2>&1 | grep -F "${COOLER_VERSION}" >/dev/null; \
    /opt/cooler/bin/python -c "import cooler, Bio, dask, h5py, matplotlib, numpy, pandas, psutil, pysam, scipy; assert cooler.__version__ == '${COOLER_VERSION}'"; \
    /opt/cooler/bin/cooler --help | grep -F "Type -h or --help after any subcommand" >/dev/null; \
    /opt/cooler/bin/cooler load --help | grep -F "Create a cooler from a pre-binned matrix" >/dev/null; \
    /opt/cooler/bin/cooler digest --help | grep -F "Generate fragment-delimited genomic bins" >/dev/null; \
    /opt/cooler/bin/cooler show --help | grep -F "Display and browse a cooler in matplotlib" >/dev/null

COPY docker/cooler_smoke.sh /opt/cooler/share/testdata/cooler_smoke.sh

RUN set -eux; \
    chmod 0755 /opt/cooler/share/testdata/cooler_smoke.sh; \
    /opt/cooler/bin/python -m pip freeze --all > /opt/cooler/share/doc/cooler/requirements.freeze.txt

FROM python:3.12-slim-bookworm

ARG DEBIAN_MIRROR
ARG DEBIAN_SECURITY_MIRROR

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONNOUSERSITE=1
ENV MPLBACKEND=Agg
ENV OPENBLAS_NUM_THREADS=1
ENV OMP_NUM_THREADS=1
ENV XDG_CACHE_HOME=/tmp
ENV PATH=/opt/cooler/bin:/usr/local/bin:/usr/bin:/bin
ENV COOLER_HOME=/opt/cooler
ENV COOLER_TESTDATA=/opt/cooler/share/testdata

RUN set -eux; \
    sed -i \
      -e "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
      -e "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
      /etc/apt/sources.list.d/debian.sources; \
    for attempt in 1 2 3 4 5; do \
      if apt-get -o Acquire::Retries=5 update \
       && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
            bash \
            bzip2 \
            ca-certificates \
            coreutils \
            fontconfig \
            fonts-dejavu-core \
            gawk \
            grep \
            gzip \
            libgomp1 \
            libstdc++6 \
            pigz \
            sed \
            tabix \
            xz-utils; then \
        break; \
      fi; \
      if [ "$attempt" = "5" ]; then exit 1; fi; \
      apt-get clean; \
      rm -rf /var/lib/apt/lists/*; \
      sleep 5; \
    done; \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/cooler /opt/cooler

RUN set -eux; \
    command -v cooler >/dev/null; \
    command -v python >/dev/null; \
    command -v python3 >/dev/null; \
    command -v bgzip >/dev/null; \
    command -v tabix >/dev/null; \
    command -v sort >/dev/null; \
    command -v gzip >/dev/null; \
    command -v pigz >/dev/null; \
    command -v bash >/dev/null; \
    cooler --version 2>&1 | grep -F "0.10.4" >/dev/null; \
    python -c "import cooler, Bio, dask, h5py, matplotlib, numpy, pandas, psutil, pysam, scipy; assert cooler.__version__ == '0.10.4'"; \
    cooler --help | grep -F "Type -h or --help after any subcommand" >/dev/null; \
    cooler load --help | grep -F "Create a cooler from a pre-binned matrix" >/dev/null; \
    cooler csort --help | grep -F "Requires Unix tools" >/dev/null; \
    /opt/cooler/share/testdata/cooler_smoke.sh /tmp/taf-cooler-runtime-check; \
    rm -rf /tmp/taf-cooler-runtime-check

WORKDIR /root

ENV TAFFISH_ENV=TAFFISH
ENV TAFFISH_NAME=cooler
