#!/usr/bin/env python3
"""Step C — Search Expansion: search phrases via brave-cli, output results for AI evaluation."""
import sqlite3
import subprocess
import json
import os
import sys
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garden.db")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.local")

def load_env():
    """Load .env.local into environment."""
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

def search_brave(query, count=10):
    """Run brave-cli and return parsed results."""
    try:
        result = subprocess.run(
            ["brave-cli", "--query", query, "--count", str(count)],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return {"error": result.stderr.strip()}
        return json.loads(result.stdout)
    except Exception as e:
        return {"error": str(e)}

def main():
    load_env()

    priority_filter = sys.argv[1] if len(sys.argv) > 1 else "high"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        "SELECT id, phrase, priority FROM search_phrases WHERE last_searched IS NULL AND priority = ? ORDER BY id",
        (priority_filter,)
    )
    phrases = cur.fetchall()

    if not phrases:
        print(f"No unsearched {priority_filter}-priority phrases.")
        return

    print(f"Processing {len(phrases)} {priority_filter}-priority phrases...\n")

    all_results = []

    for row in phrases:
        pid, phrase, priority = row['id'], row['phrase'], row['priority']
        print(f"[{pid}] Searching: {phrase}")
        data = search_brave(phrase, count)

        if "error" in data:
            print(f"  ERROR: {data['error']}")
            continue

        results = data.get("results", [])
        print(f"  Got {len(results)} results")

        # Check which URLs already exist in sources
        urls = [r['url'] for r in results]
        existing = set()
        for url in urls:
            cur.execute("SELECT id FROM sources WHERE url = ?", (url,))
            if cur.fetchone():
                existing.add(url)

        entry = {
            "phrase_id": pid,
            "phrase": phrase,
            "results": []
        }

        for r in results:
            is_existing = r['url'] in existing
            entry["results"].append({
                "url": r['url'],
                "title": r.get('title', ''),
                "description": r.get('description', ''),
                "already_in_db": is_existing
            })

        all_results.append(entry)

    # Write results to JSON for AI evaluation
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step_c_results.json")
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nWrote {len(all_results)} phrase results to step_c_results.json")
    conn.close()

if __name__ == "__main__":
    main()
