FROM ubuntu:22.04

LABEL maintainer="Sangphukieo <sangphukieo@gmail.com>"
LABEL description="CirRealign v1.2: HPV16 circular genome realignment pipeline"
LABEL version="1.2"

ENV DEBIAN_FRONTEND=noninteractive

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        wget \
        curl \
        ca-certificates \
        zlib1g-dev \
        libbz2-dev \
        liblzma-dev \
        libncurses5-dev \
        libcurl4-openssl-dev \
        libssl-dev \
        openjdk-17-jre-headless \
        python3 \
        python3-pip \
        procps \
    && rm -rf /var/lib/apt/lists/*

# ── SAMtools 1.19 ────────────────────────────────────────────────────────────
RUN wget -q https://github.com/samtools/samtools/releases/download/1.19/samtools-1.19.tar.bz2 \
    && tar xjf samtools-1.19.tar.bz2 \
    && cd samtools-1.19 \
    && ./configure --prefix=/usr/local \
    && make -j$(nproc) \
    && make install \
    && cd .. && rm -rf samtools-1.19 samtools-1.19.tar.bz2

# ── HTSlib 1.19 (for bgzip / tabix) ─────────────────────────────────────────
RUN wget -q https://github.com/samtools/htslib/releases/download/1.19/htslib-1.19.tar.bz2 \
    && tar xjf htslib-1.19.tar.bz2 \
    && cd htslib-1.19 \
    && ./configure --prefix=/usr/local \
    && make -j$(nproc) \
    && make install \
    && cd .. && rm -rf htslib-1.19 htslib-1.19.tar.bz2

# ── BWA 0.7.18 ───────────────────────────────────────────────────────────────
RUN wget -q https://github.com/lh3/bwa/releases/download/v0.7.18/bwa-0.7.18.tar.bz2 \
    && tar xjf bwa-0.7.18.tar.bz2 \
    && cd bwa-0.7.18 \
    && make -j$(nproc) \
    && cp bwa /usr/local/bin/ \
    && cd .. && rm -rf bwa-0.7.18 bwa-0.7.18.tar.bz2

# ── ABRA2 2.23 ───────────────────────────────────────────────────────────────
RUN mkdir -p /opt/abra2 \
    && wget -q -O /opt/abra2/abra2.jar \
        https://github.com/mozack/abra2/releases/download/v2.23/abra2-2.23.jar \
    && printf '#!/bin/bash\njava -Xmx16g -jar /opt/abra2/abra2.jar "$@"\n' > /usr/local/bin/abra2 \
    && chmod +x /usr/local/bin/abra2

# ── CircularMapper (realignsamfile) ──────────────────────────────────────────
RUN wget -q -O /opt/CircularMapper.jar \
        https://github.com/apeltzer/CircularMapper/releases/download/v1.93.5/CircularMapper-1.93.5.jar \
    && printf '#!/bin/bash\njava -jar /opt/CircularMapper.jar realign "$@"\n' > /usr/local/bin/realignsamfile \
    && chmod +x /usr/local/bin/realignsamfile

# ── Nextflow 22.10.8 (DSL1 compatible) ──────────────────────────────────────
RUN curl -s https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin/ \
    && chmod +x /usr/local/bin/nextflow
ENV NXF_VER=22.10.8

# ── Verify installations ────────────────────────────────────────────────────
RUN samtools --version | head -1 \
    && bwa 2>&1 | head -3 \
    && abra2 --help 2>&1 | head -1 || true \
    && nextflow -version 2>&1 | head -5

# ── Pipeline files ───────────────────────────────────────────────────────────
WORKDIR /pipeline
COPY CirRealign.nf .
COPY nextflow.config .

ENTRYPOINT ["nextflow"]
CMD ["run", "CirRealign.nf", "--help"]
