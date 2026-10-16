"""Price the owner's own Claude Code usage at Anthropic's public API rates and tabulate where the money would go.

Input : per-request CSV from extract_claude_usage.py (usage counters only, anonymised project labels)
Prices: price_table_anthropic_2026-10-16.csv (official page, fetched 2026-10-16; see its `source` column)
Output: aggregated CSVs + summary.json in --out-dir. Costs are API-EQUIVALENT estimates computed from token counters
and public prices; no invoice is used. Hypothetical findings are counterfactual re-pricing, not realised savings.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CATS = ['input', 'cache_write_5m', 'cache_write_1h', 'cache_read', 'output']


def load_prices():
    with open(HERE / 'price_table_anthropic_2026-10-16.csv', encoding='utf-8') as f:
        return {r['model_id'] + ('' if not r['tier'] else '|' + r['tier']): r for r in csv.DictReader(f)}


def rates(prices, model, prompt_tokens):
    if model + '|<=100k' in prices:
        return prices[model + ('|<=100k' if prompt_tokens <= 100_000 else '|>100k')]
    return prices.get(model)


def cost_cats(r, p):
    q = {'input': int(r['input_tokens']), 'cache_write_5m': int(r['cache_write_5m']),
         'cache_write_1h': int(r['cache_write_1h']), 'cache_read': int(r['cache_read']),
         'output': int(r['output_tokens'])}
    return {c: q[c] * float(p['p_' + c]) / 1e6 for c in CATS}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--swap-to', default='claude-sonnet-5-5', help='counterfactual model for subagent requests')
    a = ap.parse_args()
    prices = load_prices()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    agg = {k: defaultdict(lambda: defaultdict(float)) for k in ('model', 'day', 'kind', 'project')}
    unpriced, rows_n, tok = defaultdict(int), 0, defaultdict(float)
    swap_base = swap_alt = 0.0
    with open(a.raw, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            prompt = int(r['input_tokens']) + int(r['cache_write_5m']) + int(r['cache_write_1h']) + int(r['cache_read'])
            p = rates(prices, r['model'], prompt)
            if not p:
                unpriced[r['model']] += 1
                continue
            c = cost_cats(r, p)
            tot = sum(c.values())
            rows_n += 1
            kind = 'subagent' if r['sidechain'] == '1' else 'main'
            for key, name in (('model', r['model']), ('day', r['date']), ('kind', kind), ('project', r['project'])):
                d = agg[key][name]
                d['requests'] += 1
                d['cost_usd'] += tot
                for k, v in c.items():
                    d['cost_' + k] += v
            for k in ('input_tokens', 'output_tokens', 'cache_write_5m', 'cache_write_1h', 'cache_read'):
                tok[k] += int(r[k])
            if kind == 'subagent' and r['model'] != a.swap_to and float(p['p_output']) > float(prices[a.swap_to]['p_output']):
                alt = cost_cats(r, prices[a.swap_to])
                swap_base += tot
                swap_alt += sum(alt.values())
    for key, table in agg.items():
        cols = ['requests', 'cost_usd'] + ['cost_' + c for c in CATS]
        with open(out / f'by_{key}.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow([key] + cols)
            for name, d in sorted(table.items(), key=lambda x: -x[1]['cost_usd'] if key != 'day' else x[0]):
                w.writerow([name] + [round(d[c], 2) if c != 'requests' else int(d[c]) for c in cols])
    total = sum(d['cost_usd'] for d in agg['model'].values())
    summary = {'requests_priced': rows_n, 'unpriced_requests': dict(unpriced), 'total_cost_usd_api_equivalent': round(total, 2),
               'tokens_millions': {k: round(v / 1e6, 2) for k, v in tok.items()},
               'cache_read_share_of_input_side_tokens': round(tok['cache_read'] / (tok['cache_read'] + tok['cache_write_5m'] + tok['cache_write_1h'] + tok['input_tokens']), 4),
               'subagent_requests_on_pricier_models': {'current_cost_usd': round(swap_base, 2), 'repriced_on': a.swap_to,
                                                       'repriced_cost_usd': round(swap_alt, 2), 'gross_saving_usd': round(swap_base - swap_alt, 2)}}
    (out / 'summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
