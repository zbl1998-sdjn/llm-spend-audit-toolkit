"""Extract per-request token usage from the owner's own Claude Code transcripts (usage fields ONLY).

Reads ~/.claude/projects/**/*.jsonl, keeps assistant lines, de-duplicates by message id (max of each counter),
and writes a per-request CSV. Message CONTENT is never read into the output. Project folder names are replaced by
anonymous labels (P01, P02, ...) ordered by volume, so the output can be shared after a final review.

Usage: python -B -I -X utf8 extract_claude_usage.py --out claude-usage-raw.csv
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
from collections import defaultdict

ROOT = os.path.expanduser('~/.claude/projects')
FIELDS = ['ts', 'date', 'hour_utc', 'project', 'session', 'sidechain', 'entrypoint', 'model', 'input_tokens',
          'output_tokens', 'cache_write_5m', 'cache_write_1h', 'cache_read']


def scan(path, label, best):
    """Merge one transcript file into `best` (message id -> record); ids can repeat across files, count each once."""
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if '"type":"assistant"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            m = o.get('message') or {}
            u = m.get('usage')
            if o.get('type') != 'assistant' or not u or not m.get('id'):
                continue
            model = m.get('model') or ''
            if model.startswith('<'):  # synthetic placeholders
                continue
            cc = u.get('cache_creation') or {}
            w1 = cc.get('ephemeral_1h_input_tokens')
            w5 = cc.get('ephemeral_5m_input_tokens')
            total_w = u.get('cache_creation_input_tokens') or 0
            if w1 is None and w5 is None:
                w1, w5 = 0, total_w
            rec = {'input_tokens': u.get('input_tokens') or 0, 'output_tokens': u.get('output_tokens') or 0,
                   'cache_write_5m': w5 or 0, 'cache_write_1h': w1 or 0,
                   'cache_read': u.get('cache_read_input_tokens') or 0}
            prev = best.get(m['id'])
            if prev:
                for k in rec:
                    rec[k] = max(rec[k], prev[k])
            ts = o.get('timestamp') or ''
            rec.update(ts=ts, date=ts[:10], hour_utc=ts[11:13], project=label, session=(o.get('sessionId') or '')[:8],
                       sidechain=int(bool(o.get('isSidechain'))), entrypoint=o.get('entrypoint') or '', model=model)
            best[m['id']] = rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    files = glob.glob(os.path.join(ROOT, '**', '*.jsonl'), recursive=True)
    size = defaultdict(int)
    for f in files:
        size[os.path.relpath(f, ROOT).split(os.sep)[0]] += os.path.getsize(f)
    labels = {d: f'P{i + 1:02d}' for i, d in enumerate(sorted(size, key=lambda d: -size[d]))}
    t0, n = time.time(), 0
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        best = {}
        for f in files:
            scan(f, labels[os.path.relpath(f, ROOT).split(os.sep)[0]], best)
        for rec in best.values():
            w.writerow(rec)
            n += 1
    print(f'files={len(files)} projects={len(labels)} requests={n} seconds={time.time() - t0:.0f}', file=sys.stderr)


if __name__ == '__main__':
    main()
