#!/usr/bin/env python3
"""
Chunker for Step B — splits documents into overlapping chunks for parallel AI extraction.

Usage:
    python3 chunker.py <input_file> [--chunk-words 800] [--overlap-words 100] [--out-dir chunks/]

Outputs numbered JSON files, each containing:
    {
        "chunk_index": 0,
        "total_chunks": N,
        "source_file": "...",
        "text": "...",
        "word_count": 812
    }
"""
import argparse
import json
import os
import re
import sys


def split_into_chunks(text: str, chunk_words: int = 800, overlap_words: int = 100) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries."""
    # Split into sentences (rough but effective)
    sentences = re.split(r'(?<=[.!?|])\s+(?=[A-Z|#\-*])', text)
    # Fallback: if few sentence breaks (e.g., tables), split on newlines too
    if len(sentences) < 5:
        sentences = text.split('\n')

    chunks = []
    current_words = []
    current_count = 0
    overlap_buffer = []  # sentences to prepend to next chunk

    i = 0
    while i < len(sentences):
        sent = sentences[i]
        sent_words = sent.split()
        sent_len = len(sent_words)

        current_words.append(sent)
        current_count += sent_len

        if current_count >= chunk_words:
            # Emit chunk
            chunks.append('\n'.join(current_words))

            # Calculate overlap: take last N words worth of sentences
            overlap_count = 0
            overlap_buffer = []
            for s in reversed(current_words):
                s_len = len(s.split())
                if overlap_count + s_len > overlap_words:
                    break
                overlap_buffer.insert(0, s)
                overlap_count += s_len

            # Start new chunk with overlap
            current_words = list(overlap_buffer)
            current_count = overlap_count

        i += 1

    # Don't forget the last chunk
    if current_words and (not chunks or '\n'.join(current_words) != chunks[-1]):
        # Only add if it has substantial content beyond just overlap
        remaining_text = '\n'.join(current_words)
        if len(remaining_text.split()) > overlap_words * 1.5:
            chunks.append(remaining_text)
        elif chunks:
            # Append remainder to last chunk instead of making a tiny chunk
            chunks[-1] = chunks[-1] + '\n' + remaining_text
        else:
            chunks.append(remaining_text)

    return chunks


def main():
    parser = argparse.ArgumentParser(description="Split a document into overlapping chunks for AI extraction")
    parser.add_argument("input_file", help="Path to the input document")
    parser.add_argument("--chunk-words", type=int, default=800, help="Target words per chunk (default: 800)")
    parser.add_argument("--overlap-words", type=int, default=100, help="Overlap words between chunks (default: 100)")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: chunks/<filename>/)")
    args = parser.parse_args()

    with open(args.input_file, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()

    basename = os.path.splitext(os.path.basename(args.input_file))[0]
    # Sanitize basename for use as directory name
    basename = re.sub(r'[^\w\-.]', '_', basename)[:80]

    out_dir = args.out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "chunks", basename)
    os.makedirs(out_dir, exist_ok=True)

    chunks = split_into_chunks(text, args.chunk_words, args.overlap_words)

    total_words = len(text.split())
    print(f"Input: {total_words} words")
    print(f"Split into {len(chunks)} chunks (target: {args.chunk_words}w, overlap: {args.overlap_words}w)")

    for i, chunk in enumerate(chunks):
        chunk_data = {
            "chunk_index": i,
            "total_chunks": len(chunks),
            "source_file": os.path.basename(args.input_file),
            "text": chunk,
            "word_count": len(chunk.split())
        }
        out_path = os.path.join(out_dir, f"chunk_{i:03d}.json")
        with open(out_path, 'w') as f:
            json.dump(chunk_data, f, indent=2)
        print(f"  chunk_{i:03d}.json: {chunk_data['word_count']} words")

    # Also write a manifest
    manifest = {
        "source_file": os.path.basename(args.input_file),
        "source_path": os.path.abspath(args.input_file),
        "total_words": total_words,
        "total_chunks": len(chunks),
        "chunk_words": args.chunk_words,
        "overlap_words": args.overlap_words,
        "chunks": [f"chunk_{i:03d}.json" for i in range(len(chunks))]
    }
    with open(os.path.join(out_dir, "manifest.json"), 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nOutput: {out_dir}/")
    return out_dir


if __name__ == "__main__":
    main()
