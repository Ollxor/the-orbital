#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

LIMIT=""
DISCOVER=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --limit) LIMIT="--limit $2"; shift 2 ;;
    --discover) DISCOVER=true; shift ;;
    *) echo "Usage: ./crawl.sh [--discover] [--limit N]"; exit 1 ;;
  esac
done

if $DISCOVER; then
  echo "=== Discovering feeds ==="
  python3 crawl_feeds.py --discover-only
  echo ""
fi

echo "=== Crawling feeds ==="
python3 crawl_feeds.py --crawl-only $LIMIT
