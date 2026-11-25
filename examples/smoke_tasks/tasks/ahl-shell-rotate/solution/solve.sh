#!/bin/bash
set -e
cat > /app/rotate.sh <<'AHL_EOF'
#!/bin/bash
dir="$1"
keep="$2"
if [ ! -d "$dir" ]; then
  echo "rotate: not a directory: $dir" >&2
  exit 2
fi
i=0
while IFS= read -r -d '' f; do
  i=$((i + 1))
  if [ "$i" -gt "$keep" ]; then
    rm -f -- "$f"
  fi
done < <(find "$dir" -maxdepth 1 -type f -name '*.log' -print0 | LC_ALL=C sort -rz)
exit 0
AHL_EOF
chmod +x /app/rotate.sh
