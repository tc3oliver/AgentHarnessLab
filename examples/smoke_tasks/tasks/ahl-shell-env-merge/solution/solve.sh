#!/bin/bash
set -e
cat > /app/merge_env.sh <<'AHL_EOF'
#!/bin/bash
for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "merge_env: missing file: $f" >&2
    exit 1
  fi
done
declare -A env
for f in "$@"; do
  while IFS= read -r line || [ -n "$line" ]; do
    key="${line%%=*}"
    [ "$key" = "$line" ] && continue
    val="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    case "$key" in
      "" | "#"*) continue ;;
      "export "*) key="${key#export }"; key="${key#"${key%%[![:space:]]*}"}" ;;
    esac
    env["$key"]="$val"
  done < "$f"
done
for k in "${!env[@]}"; do
  printf '%s\0' "$k"
done | LC_ALL=C sort -z | while IFS= read -r -d '' k; do
  printf '%s=%s\n' "$k" "${env[$k]}"
done
AHL_EOF
chmod +x /app/merge_env.sh
