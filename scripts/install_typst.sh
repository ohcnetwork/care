#!/bin/sh

# This script installs Typst binary based on the given version and path
# Supported platforms: Linux(x86_64, aarch64), Darwin(x86_64, arm64)
#
# Environment variables:
# TYPST_VERSION: The version of Typst to install
# TYPST_INSTALL_DIR: The directory to install Typst to. Defaults to /usr/local/bin
#
# Example usage:
# TYPST_VERSION=0.12.0 ./scripts/install_typst.sh
# TYPST_VERSION=0.12.0 TYPST_INSTALL_DIR=./bin ./scripts/install_typst.sh


INSTALL_PATH="${TYPST_INSTALL_DIR:-/usr/local/bin}"

if [ -z "${TYPST_VERSION}" ]; then
  echo "TYPST_VERSION is not set. Exiting."
  exit 1
fi

if ! command -v wget >/dev/null 2>&1; then
  echo "wget is required but not installed. Exiting."
  exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
  echo "tar is required but not installed. Exiting."
  exit 1
fi


get_arch() {
  OS=$(uname -s)
  MACHINE=$(uname -m)
  case "$OS" in
    Darwin)
      case "$MACHINE" in
        x86_64)
          echo "x86_64-apple-darwin"
          ;;
        arm64)
          echo "aarch64-apple-darwin"
          ;;
        *)
          echo "Unsupported architecture: $MACHINE on Darwin" >&2
          exit 1
          ;;
      esac
      ;;
    Linux)
      case "$MACHINE" in
        x86_64|amd64)
          echo "x86_64-unknown-linux-musl"
          ;;
        arm64|aarch64)
          echo "aarch64-unknown-linux-musl"
          ;;
        *)
          echo "Unsupported architecture: $MACHINE on Linux" >&2
          exit 1
          ;;
      esac
      ;;
    *)
      echo "Unsupported OS: $OS" >&2
      exit 1
      ;;
  esac
}

TYPST_ARCH=$(get_arch)

wget -qO typst.tar.xz \
    "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${TYPST_ARCH}.tar.xz"

tar -xf typst.tar.xz

mkdir -p "${INSTALL_PATH}"
mv "typst-${TYPST_ARCH}/typst" "${INSTALL_PATH}/typst"
chmod +x "${INSTALL_PATH}/typst"

rm -rf "typst.tar.xz" "typst-${TYPST_ARCH}"

echo "Typst v${TYPST_VERSION} has been installed to ${INSTALL_PATH}/typst"
