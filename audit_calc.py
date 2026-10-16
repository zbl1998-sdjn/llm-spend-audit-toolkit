"""Deterministic LLM spend audit on a client usage export (no LLM calls, no network).

Inputs : usage CSV (date, workflow, provider, model, input_tokens, output_tokens, cached_input_tokens,
                    batch, async_ok, simple_task, invoice_cost_usd)
         price CSV (provider, model, input_per_mtok, output_per_mtok, cached_input_per_mtok,
                    batch_discount, as_of, source)
         optional --swap workflow=candidate_model (repeatable; needs a client quality evaluation before acting)
Output : reconciliation, spend by workflow, savings register (monthly + annualised, lower bound after haircut).
Only conservative, de-duplicated findings are counted: a workflow gets the larger of its batch or swap saving,
never both.
"""
import argparse
import csv
from collections import defaultdict


def load(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def cost_of(row, p, batch=None):
    itok = float(row['input_tokens'])
    otok = float(row['output_tokens'])
    ctok = float(row['cached_input_tokens'])
    c = ((itok - ctok) * float(p['input_per_mtok']) + ctok * float(p['cached_input_per_mtok'])
         + otok * float(p['output_per_mtok'])) / 1e6
    use_batch = int(row['batch']) if batch is None else batch
    return c * (1 - float(p['batch_discount'])) if use_batch else c


def findings(usage, pt, swaps, months, haircut):
    reg = []
    for wf in dict.fromkeys(r['workflow'] for r in usage):
        rows = [r for r in usage if r['workflow'] == wf]
        base = sum(cost_of(r, pt[r['model']]) for r in rows)
        opts = []
        if all(r['async_ok'] == '1' for r in rows) and any(r['batch'] == '0' for r in rows):
            opts.append(('batch', base - sum(cost_of(r, pt[r['model']], batch=1) for r in rows)))
        if wf in swaps and swaps[wf] in pt and all(r['simple_task'] == '1' for r in rows):
            alt = pt[swaps[wf]]
            opts.append((f'swap->{swaps[wf]}', base - sum(cost_of(r, alt) for r in rows)))
        if opts:
            kind, s = max(opts, key=lambda x: x[1])
            m = s / months * haircut
            reg.append([wf, kind, round(s / months, 2), round(m, 2), round(m * 12, 2)])
    return sorted(reg, key=lambda x: -x[4])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--usage', required=True)
    ap.add_argument('--prices', required=True)
    ap.add_argument('--swap', action='append', default=[], help='workflow=candidate_model')
    ap.add_argument('--haircut', type=float, default=0.8, help='fraction of a computed saving to keep')
    ap.add_argument('--out', help='write savings register CSV here')
    a = ap.parse_args()
    usage, prices = load(a.usage), load(a.prices)
    pt = {p['model']: p for p in prices}
    swaps = dict(s.split('=', 1) for s in a.swap)
    days = len({r['date'] for r in usage})
    months = days / 30.0

    observed = sum(float(r['invoice_cost_usd']) for r in usage)
    computed = sum(cost_of(r, pt[r['model']]) for r in usage)
    var = (computed - observed) / observed
    print(f'rows={len(usage)} days={days}  invoice=${observed:,.2f}  recomputed=${computed:,.2f}  variance={var:+.2%}')
    if abs(var) > 0.03:
        print('WARNING: >3% variance - reconcile (credits, discounts, missing line items) before trusting any saving')

    by_wf = defaultdict(float)
    for r in usage:
        by_wf[r['workflow']] += float(r['invoice_cost_usd'])
    print('\nspend by workflow (monthly-equivalent):')
    for wf, c in sorted(by_wf.items(), key=lambda x: -x[1]):
        print(f'  {wf:<20} ${c / months:>10,.2f}  {c / observed:>6.1%}')

    reg = findings(usage, pt, swaps, months, a.haircut)
    print('\nsavings register (one finding per workflow, haircut applied):')
    print(f'  {"workflow":<20}{"finding":<24}{"gross/mo":>10}{"lower/mo":>10}{"annual":>11}')
    for r in reg:
        print(f'  {r[0]:<20}{r[1]:<24}{r[2]:>10,.2f}{r[3]:>10,.2f}{r[4]:>11,.2f}')
    print(f'  {"TOTAL annualised lower bound":<54}{sum(r[4] for r in reg):>11,.2f}')
    print('\nCAVEAT: swap findings need a client-approved quality evaluation; batch needs the workflow to tolerate ~24h latency.')
    if a.out:
        with open(a.out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['workflow', 'finding', 'gross_monthly_usd', 'lower_monthly_usd', 'annual_lower_usd'])
            w.writerows(reg)


if __name__ == '__main__':
    main()
