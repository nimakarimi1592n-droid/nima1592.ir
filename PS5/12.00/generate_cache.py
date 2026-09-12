#!/usr/bin/env python3
"""
SlopKit AppCache Manifest Generator
Run from the project root: python3 generate_cache.py
Outputs: cache.appcache
"""

import os
import hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))

# Extensions to include in the cache
INCLUDE_EXT = {
    '.html', '.js', '.css', '.elf', '.bin'
}

# Files/dirs to always skip
SKIP_NAMES = {
    'generate_cache.py',
    'cache.appcache',
}

# These URLs are requested with ?v=final — we list both the bare path
# AND the versioned path so AppCache matches either request.
VERSIONED = [
    'main.css',
    'slopkit/rop.js',
    'slopkit/rop_slave.js',
    'slopkit/main.js',
    'slopkit/syscalls.js',
    'slopkit/core.js',
    'slopkit/mem.js',
    'slopkit/poops.js',
    'slopkit/int64.js',
]

# Offsets are loaded as ../offsets/{fw}.js?v=final from inside slopkit/
# so they appear as offsets/{fw}.js?v=final from root.
OFFSETS_DIR = os.path.join(ROOT, 'offsets')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def collect_files():
    """Walk root and return list of relative posix paths to include."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip hidden dirs
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        for fname in filenames:
            if fname in SKIP_NAMES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in INCLUDE_EXT:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, ROOT).replace('\\', '/')
            entries.append(rel)
    return sorted(entries)


def build_manifest():
    lines = ['CACHE MANIFEST', '']
    lines.append('CACHE:')

    # Root index.html → listed as "/" for Cloudflare redirect compatibility
    index_path = os.path.join(ROOT, 'index.html')
    if os.path.exists(index_path):
        h = sha256(index_path)
        lines.append(f'/ # {h}')

    versioned_set = set(VERSIONED)
    added = set()
    added.add('index.html')  # already handled as /

    files = collect_files()
    for rel in files:
        if rel in added:
            continue
        full = os.path.join(ROOT, rel)
        h = sha256(full)

        # Bare path
        lines.append(f'{rel} # {h}')
        added.add(rel)

        # Also add versioned path if this file is loaded with ?v=final
        if rel in versioned_set:
            lines.append(f'{rel}?v=final # {h}')

        # Offsets are loaded with ?v=final
        if rel.startswith('offsets/') and rel.endswith('.js'):
            lines.append(f'{rel}?v=final # {h}')

    lines.append('')
    lines.append('NETWORK:')
    lines.append('/__poops_log')  # remote telemetry — allow through
    lines.append('*')
    lines.append('')

    return '\n'.join(lines)


def main():
    manifest = build_manifest()
    out = os.path.join(ROOT, 'cache.appcache')
    with open(out, 'w', newline='\n') as f:
        f.write(manifest)
    # Count cache entries
    entries = [l for l in manifest.splitlines() if l and not l.startswith(('CACHE', 'NETWORK', '#', '/'))]
    root_entry = [l for l in manifest.splitlines() if l.startswith('/')]
    print(f"Generated: {out}")
    print(f"  Root entry (/): {len(root_entry)}")
    print(f"  File entries:   {len(entries)}")


if __name__ == '__main__':
    main()
