"""Counterfactual: would a 5-minute prompt-cache TTL have been cheaper than the 1-hour TTL actually used?

Model (per (session, main/subagent) request stream, ordered by timestamp):
  * gap <= 300 s  : cache hit under a 5m TTL too; 1h-write tokens would be written at the cheaper 5m rate.
  * gap  > 300 s  : a 5m cache would have expired -> the tokens that were cache READS are re-WRITTEN at the 5m write rate,
                    and 1h-write tokens are written at the 5m rate.
  * first request of a stream: unchanged except 1h writes -> 5m rate.
Limits (stated in the report): subagent streams of one session are merged (gaps look shorter than reality);
the model ignores that a re-write could re-use partial prefixes; prices are the 2026-10-16 public sheet.
Usage: python -B -I -X utf8 ttl_counterfactual.py --raw claude-usage-raw.csv
"""
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from analyze_claude_usage import cost_cats, load_prices, rates


def parse(ts):
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    a = ap.parse_args()
    prices = load_prices()
    streams = defaultdict(list)
    with open(a.raw, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            streams[(r['project'], r['session'], r['sidechain'])].append(r)
    res = defaultdict(lambda: defaultdict(float))
    for (_, _, side), rows in streams.items():
        rows.sort(key=lambda r: r['ts'])
        prev = None
        for r in rows:
            prompt = int(r['input_tokens']) + int(r['cache_write_5m']) + int(r['cache_write_1h']) + int(r['cache_read'])
            p = rates(prices, r['model'], prompt)
            actual = sum(cost_cats(r, p).values())
            gap = (parse(r['ts']) - parse(prev)).total_seconds() if prev else 1e9
            prev = r['ts']
            w5 = float(p['p_cache_write_5m']) / 1e6
            cf = actual - int(r['cache_write_1h']) * float(p['p_cache_write_1h']) / 1e6 + int(r['cache_write_1h']) * w5
            expired = gap > 300 and int(r['cache_read']) > 0
            if expired:
                cf += int(r['cache_read']) * (w5 - float(p['p_cache_read']) / 1e6)
            kind = 'subagent' if side == '1' else 'main'
            for k in (kind, 'ALL'):
                d = res[k]
                d['requests'] += 1
                d['actual_usd'] += actual
                d['cf_5m_usd'] += cf
                d['expired_requests'] += int(expired)
                d['cache_read_tokens'] += int(r['cache_read'])
                d['cache_read_tokens_after_gap'] += int(r['cache_read']) if expired else 0
    for k, d in res.items():
        print(f"{k:<9} requests={int(d['requests'])} actual=${d['actual_usd']:,.2f} if-5m-TTL=${d['cf_5m_usd']:,.2f} "
              f"delta={d['cf_5m_usd'] - d['actual_usd']:+,.2f} | requests after >5min gap with cache read: "
              f"{d['expired_requests'] / d['requests']:.1%} | cache-read tokens that a 5m TTL would have lost: "
              f"{d['cache_read_tokens_after_gap'] / max(d['cache_read_tokens'], 1):.1%}")


if __name__ == '__main__':
    main()
