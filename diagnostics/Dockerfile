FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bc bison build-essential bzip2 ca-certificates cpio file flex gawk git \
    gzip libelf-dev libncurses-dev libssl-dev patch perl python3 rsync sed \
    tar unzip wget xz-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /src/webcampi
