#!/bin/sh
# Task-local OCR CLI install.  Never installs globally and never touches the
# live Pi/Paseo configuration.  Pins the released npm version and verifies the
# native binary against the checksum frozen for this benchmark.
set -eu

VERSION=1.12.4
# npm integrity of @alibaba-group/open-code-review@1.12.4 (registry tarball):
# sha512-eGBbfmsCQI15ernq/2kmUPVIooKPycK/4a2RO72K1Adxgu/5k1QQv88AlA0bfragRWr17Urog45yTB/NvNemBA==
# (platform package @alibaba-group/ocr-darwin-arm64@1.12.4:
#  sha512-BfM6FdJNLAvpcgFe4c4Aw0rxWZa+bnaaSOps2T0HWif8T2+YWbRO5irLWYa14GqHTQ3NAVjcThtNDNVfKdH52w==)
# sha256 of the native darwin-arm64 binary shipped by that platform package.
EXPECTED_SHA256=b2944c8823075fd4edbedf521956d4893b4e973e5d47ed12f2f223cd21e792db

ROOT=$(cd "$(dirname "$0")/.." && pwd)
PREFIX="$ROOT/tools/ocr"
CACHE="$ROOT/tools/npm-cache"
mkdir -p "$PREFIX" "$CACHE"

# npm 11 blocks lifecycle scripts by default; the platform optionalDependency
# already ships the binary, so the postinstall download is not required.
npm install --prefix "$PREFIX" --cache "$CACHE" --no-fund --no-audit \
  "@alibaba-group/open-code-review@$VERSION"

BIN="$PREFIX/node_modules/@alibaba-group/ocr-darwin-arm64/bin/opencodereview"
if [ ! -x "$BIN" ]; then
  echo "expected native binary missing: $BIN" >&2
  echo "on another platform, inspect $PREFIX/node_modules/@alibaba-group/" >&2
  exit 1
fi

actual=$(shasum -a 256 "$BIN" | awk '{print $1}')
if [ "$actual" != "$EXPECTED_SHA256" ]; then
  echo "checksum mismatch for $BIN" >&2
  echo "expected $EXPECTED_SHA256" >&2
  echo "actual   $actual" >&2
  exit 1
fi

echo "ocr $VERSION installed at $BIN (sha256 $actual)"
"$BIN" --version
