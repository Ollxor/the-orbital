#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Building site ==="
cd web && bun run build
echo ""

echo "=== Deploying to Cloudflare Pages ==="
wrangler pages deploy dist --project-name theoverview --commit-dirty=true
