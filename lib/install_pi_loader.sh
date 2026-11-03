#!/usr/bin/env bash
# Private exact-version Pi loader for verification of a compiled Pi (e.g. Pi-Bolt).
# A compiled Pi ships package.json without dist/, so offline verifiers cannot load its
# resource/model APIs. Install @earendil-works/pi-coding-agent at exactly that version
# under $MEGAI_HOME/pi-loader/<version>; never touches PATH, global packages or the Pi CLI.
# No-op when `pi` is absent or already an npm Pi with dist/.
set -euo pipefail
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PI_BIN="${1:-$(command -v pi || true)}"
[ -n "$PI_BIN" ] || { printf 'pi-loader: pi not found; nothing to do\n'; exit 0; }

version="$(node --input-type=module -e '
import { existsSync, readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
for (let dir = dirname(realpathSync(process.argv[1])); ; dir = dirname(dir)) {
  try {
    const m = JSON.parse(readFileSync(join(dir, "package.json"), "utf8"));
    if (typeof m.name === "string" && m.name.endsWith("/pi-coding-agent")) {
      process.stdout.write(existsSync(join(dir, "dist/index.js")) ? "" : String(m.version ?? ""));
      break;
    }
  } catch {}
  if (dirname(dir) === dir) break;
}' "$PI_BIN")"
[ -n "$version" ] || { printf 'pi-loader: pi has its own loader or no Pi manifest; nothing to do\n'; exit 0; }
case "$version" in *[!0-9A-Za-z.+-]*) printf 'pi-loader: unexpected Pi version %s\n' "$version" >&2; exit 1 ;; esac

target="$MEGAI_HOME/pi-loader/$version"
package="$target/node_modules/@earendil-works/pi-coding-agent"
if [ -f "$package/dist/index.js" ] && [ "$(node -p 'require(process.argv[1]).version' "$package/package.json")" = "$version" ]; then
  printf 'pi-loader: Pi %s loader already present\n' "$version"; exit 0
fi
[ ! -L "$MEGAI_HOME/pi-loader" ] && [ ! -L "$target" ] || { printf 'pi-loader: symlinked destination refused\n' >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { printf 'pi-loader: npm is required to install the Pi %s loader\n' "$version" >&2; exit 1; }

mkdir -p "$MEGAI_HOME/pi-loader"
staging="$(mktemp -d "$MEGAI_HOME/pi-loader/.staging.XXXXXX")"
trap 'rm -rf "$staging"' EXIT
# Registry integrity is checked by npm; lifecycle scripts are not needed for the loader API.
npm install --prefix "$staging" --ignore-scripts --no-audit --no-fund --omit=dev --loglevel=error \
  "@earendil-works/pi-coding-agent@$version" >/dev/null
installed="$(node -p 'require(process.argv[1]).version' "$staging/node_modules/@earendil-works/pi-coding-agent/package.json")"
[ "$installed" = "$version" ] && [ -f "$staging/node_modules/@earendil-works/pi-coding-agent/dist/index.js" ] \
  || { printf 'pi-loader: npm installed %s, expected %s\n' "$installed" "$version" >&2; exit 1; }
[ ! -e "$target" ] || mv "$target" "$target.replaced.$(date +%s)"
mv "$staging" "$target"
trap - EXIT
chmod -R go-w "$target"
printf 'pi-loader: installed private Pi %s loader at %s\n' "$version" "$target"
