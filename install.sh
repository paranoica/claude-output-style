#!/usr/bin/env bash
# Installs the claude-output-style rules into ~/.claude without overwriting existing content.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install.sh [--with-style] [--keep-style] [--uninstall]

Adds or updates the rules block in ~/.claude/CLAUDE.md ($CLAUDE_CONFIG_DIR/CLAUDE.md if set),
between begin/end markers. Text outside the markers is left as is. Every file is backed up to
<name>.bak-<timestamp> before it changes.

  --with-style  also install output-styles/plain.md (select it with /output-style)
  --keep-style  leave an active outputStyle setting alone (by default it is unset, because a
                style that mirrors the user's register overrides these rules)
  --uninstall   remove the block and an unmodified plain.md; settings are not touched
EOF
}

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target_dir="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
target="$target_dir/CLAUDE.md"
style_src="$repo/output-styles/plain.md"
style_dst="$target_dir/output-styles/plain.md"
begin='<!-- claude-output-style:begin -->'
end='<!-- claude-output-style:end -->'
stamp="$(date +%Y%m%d-%H%M%S)"

mode=install
with_style=0
keep_style=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) mode=uninstall ;;
    --with-style) with_style=1 ;;
    --keep-style) keep_style=1 ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $arg" >&2
      usage >&2
      exit 2
      ;;
  esac
done

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

backup() {
  cp -p -- "$1" "$1.bak-$stamp"
  echo "backup: $1.bak-$stamp"
}

# 0: exactly one well-formed block, 1: no markers at all.
# Anything else exits, so a hand-edited file is never rewritten blindly.
has_block() {
  local file=$1 b e bl el
  b=$(grep -cxF -- "$begin" "$file" || true)
  e=$(grep -cxF -- "$end" "$file" || true)
  if [[ $b -eq 0 && $e -eq 0 ]]; then
    return 1
  fi
  if [[ $b -eq 1 && $e -eq 1 ]]; then
    bl=$(grep -nxF -- "$begin" "$file" | cut -d: -f1)
    el=$(grep -nxF -- "$end" "$file" | cut -d: -f1)
    if ((bl < el)); then
      return 0
    fi
  fi
  echo "error: $file has broken claude-output-style markers (begin: $b, end: $e); fix them by hand" >&2
  exit 1
}

# Writes $2 over $1 only when the content differs. Uses cat so the file keeps its mode.
replace_if_changed() {
  local file=$1 new=$2
  if [[ -f $file ]] && cmp -s "$new" "$file"; then
    return 1
  fi
  if [[ -f $file ]]; then
    backup "$file"
  fi
  cat "$new" >"$file"
}

install_block() {
  local new="$workdir/new" verb
  mkdir -p "$target_dir"
  if [[ ! -f $target ]]; then
    cp "$workdir/block" "$new"
    verb="added to"
  elif has_block "$target"; then
    awk -v b="$begin" -v e="$end" -v src="$workdir/block" '
      $0 == b { while ((getline line < src) > 0) print line; skip = 1; next }
      skip { if ($0 == e) skip = 0; next }
      { print }
    ' "$target" >"$new"
    verb="updated in"
  else
    cat "$target" >"$new"
    if [[ -s $new ]]; then
      if [[ -n "$(tail -c1 "$new")" ]]; then
        echo >>"$new"
      fi
      echo >>"$new"
    fi
    cat "$workdir/block" >>"$new"
    verb="added to"
  fi
  if replace_if_changed "$target" "$new"; then
    echo "rules: $verb $target"
  else
    echo "rules: up to date in $target"
  fi
}

uninstall_block() {
  local new="$workdir/new"
  if [[ ! -f $target ]] || ! has_block "$target"; then
    echo "rules: not installed in $target"
    return 0
  fi
  # Drops the block and the one blank line install put before it.
  awk -v b="$begin" -v e="$end" '
    $0 == b { held = 0; skip = 1; next }
    skip { if ($0 == e) skip = 0; next }
    held { print ""; held = 0 }
    $0 == "" { held = 1; next }
    { print }
    END { if (held) print "" }
  ' "$target" >"$new"
  replace_if_changed "$target" "$new" || true
  echo "rules: removed from $target"
}

install_style() {
  mkdir -p "$(dirname "$style_dst")"
  if [[ -f $style_dst ]] && cmp -s "$style_src" "$style_dst"; then
    echo "output style: up to date in $style_dst"
    return 0
  fi
  if [[ -f $style_dst ]]; then
    backup "$style_dst"
  fi
  cp -- "$style_src" "$style_dst"
  echo "output style: installed $style_dst (select it with /output-style)"
}

uninstall_style() {
  if [[ ! -f $style_dst ]]; then
    return 0
  fi
  if cmp -s "$style_src" "$style_dst"; then
    rm -f -- "$style_dst"
    echo "output style: removed $style_dst"
  else
    echo "output style: $style_dst was modified, left in place"
  fi
}

reset_output_style() {
  local f
  for f in "$target_dir/settings.json" "$target_dir/settings.local.json"; do
    if [[ ! -f $f ]]; then
      continue
    fi
    if ! command -v python3 >/dev/null 2>&1; then
      echo "warning: python3 not found; check outputStyle in $f by hand"
      continue
    fi
    python3 -I - "$f" "$keep_style" "$stamp" <<'PY'
import json
import shutil
import sys

path, keep, stamp = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
except (OSError, ValueError) as exc:
    print(f"warning: cannot parse {path} ({exc}); check outputStyle there by hand")
    sys.exit(0)
style = data.get("outputStyle") if isinstance(data, dict) else None
if style is None or str(style).lower() in ("default", "plain"):
    sys.exit(0)
if keep:
    print(f"note: outputStyle '{style}' in {path} stays active and may override these rules")
    sys.exit(0)
shutil.copy2(path, f"{path}.bak-{stamp}")
del data["outputStyle"]
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print(f"outputStyle '{style}' removed from {path} (backup: {path}.bak-{stamp})")
PY
  done
}

if ! has_block "$repo/CLAUDE.md"; then
  echo "error: $repo/CLAUDE.md has no rules block" >&2
  exit 1
fi
awk -v b="$begin" -v e="$end" '$0 == b { on = 1 } on { print } $0 == e { on = 0 }' \
  "$repo/CLAUDE.md" >"$workdir/block"

if [[ $mode == install ]]; then
  install_block
  if ((with_style)); then
    install_style
  fi
  reset_output_style
  echo "done. New Claude Code sessions pick up the rules."
else
  uninstall_block
  uninstall_style
fi
