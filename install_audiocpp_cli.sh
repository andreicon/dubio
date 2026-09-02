#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  printf '%s\n' "install_audiocpp_cli.sh: Linux only" >&2
  exit 1
fi

WORK_DIR="${WORK_DIR:-/tmp/opencode/audiocpp-build}"
AUDIOCPP_REPO="${AUDIOCPP_REPO:-https://github.com/0xShug0/audio.cpp.git}"
AUDIOCPP_REF="${AUDIOCPP_REF:-main}"
BACKEND="${AUDIOCPP_BACKEND:-cuda}"
TARGET="audiocpp_cli"
CUDA_ARCHITECTURES="${AUDIOCPP_CUDA_ARCHITECTURES:-86;90}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s\n' "install_audiocpp_cli.sh: $1 is required" >&2
    exit 1
  fi
}

require_cmd git
require_cmd cmake
if ! command -v g++ >/dev/null 2>&1 && ! command -v c++ >/dev/null 2>&1; then
  printf '%s\n' "install_audiocpp_cli.sh: a C++ compiler is required" >&2
  exit 1
fi

mkdir -p "$WORK_DIR"

if [[ ! -d "$WORK_DIR/audio.cpp/.git" ]]; then
  git clone "$AUDIOCPP_REPO" "$WORK_DIR/audio.cpp"
fi

git -C "$WORK_DIR/audio.cpp" fetch --all --prune
git -C "$WORK_DIR/audio.cpp" checkout "$AUDIOCPP_REF"

BACKEND_FLAG="ENGINE_ENABLE_${BACKEND^^}"
BUILD_DIR="$WORK_DIR/audio.cpp/build/linux-${BACKEND}-release"

cmake -S "$WORK_DIR/audio.cpp" -B "$BUILD_DIR" -D"${BACKEND_FLAG}=ON" -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCHITECTURES"
cmake --build "$BUILD_DIR" --target "$TARGET" -j"${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"

CLI_PATH="$BUILD_DIR/bin/$TARGET"
if [[ ! -x "$CLI_PATH" ]]; then
  printf '%s\n' "install_audiocpp_cli.sh: build finished but $CLI_PATH is missing" >&2
  exit 1
fi

"$CLI_PATH" --help >/dev/null

printf '%s\n' "audiocpp_cli built: $CLI_PATH"
printf '%s\n' "add it to PATH or run it directly"
