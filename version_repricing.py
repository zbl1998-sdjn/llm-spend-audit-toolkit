"""Re-price requests that ran on an OLDER model version at the NEWER version's rates, counting only requests made on/after
the first time the newer version was used (proxy for 'it was available'). Naive repricing of the whole period overstates
the saving; this is the conservative number.

Assumes same token counts and comparable quality (to be confirmed by a client-approved evaluation before acting).
Usage: python -B -X utf8 version_repricing.py --raw claude-usage-raw.csv
"""
import argparse
import csv

from analyze_claude_usage import cost_cats, load_prices, rates

MOVES = {'claude-opus-5': 'claude-opus-5-5', 'claude-opus-4-8': 'claude-opus-5-5',
         'claude-opus-4-7': 'claude-opus-5-5', 'claude-sonnet-5': 'claude-sonnet-5-5'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    a = ap.parse_args()
    prices = load_prices()
    with open(a.raw, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    first = {}
    for r in rows:
        first[r['model']] = min(first.get(r['model'], r['ts']), r['ts'])
    total_all = sum_cost = naive = avail = 0.0
    per = {}
    for r in rows:
        prompt = int(r['input_tokens']) + int(r['cache_write_5m']) + int(r['cache_write_1h']) + int(r['cache_read'])
        cur = sum(cost_cats(r, rates(prices, r['model'], prompt)).values())
        total_all += cur
        tgt = MOVES.get(r['model'])
        if not tgt:
            continue
        alt = sum(cost_cats(r, rates(prices, tgt, prompt)).values())
        naive += cur - alt
        if r['ts'] >= first[tgt]:
            avail += cur - alt
            d = per.setdefault((r['model'], tgt), [0, 0.0, 0.0])
            d[0] += 1
            d[1] += cur
            d[2] += alt
    for (m, t), (n, c, al) in per.items():
        print(f'{m:<16} -> {t:<17} requests={n:>5}  now=${c:>8,.2f}  at-target=${al:>8,.2f}  saving=${c - al:>7,.2f}')
    print(f'naive saving (whole period): ${naive:,.2f} = {naive / total_all:.1%} of ${total_all:,.2f}')
    print(f'available-at-the-time saving: ${avail:,.2f} = {avail / total_all:.1%}  (overstatement if naive: {naive / avail:.1f}x)')


if __name__ == '__main__':
    main()
