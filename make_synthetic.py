"""Generate SYNTHETIC usage + price files for demoing the audit calculator.

Nothing here is real client data and the prices are ILLUSTRATIVE (fake model names).
A real audit must use the provider's dated public price sheet.
"""
import csv
import random
from pathlib import Path

random.seed(7)
OUT = Path(__file__).parent / 'sample'
OUT.mkdir(exist_ok=True)

# provider, model, input $/Mtok, output $/Mtok, cached-input $/Mtok, batch_discount, as_of, source
PRICES = [
    ('prov-x', 'model-large', 5.00, 20.00, 0.50, 0.5, '2026-10-16', 'ILLUSTRATIVE - fake price'),
    ('prov-x', 'model-small', 0.50, 2.00, 0.05, 0.5, '2026-10-16', 'ILLUSTRATIVE - fake price'),
]
# name, model, daily requests, in tok, out tok, cached share, batch used, async_ok, simple_task
WORKFLOWS = [
    ('support-reply', 'model-large', 900, 2200, 350, 0.00, 0, 0, 1),
    ('nightly-classify', 'model-large', 1500, 1200, 40, 0.00, 0, 1, 1),
    ('contract-summary', 'model-large', 60, 9000, 900, 0.00, 0, 0, 0),
    ('tagging', 'model-small', 2500, 400, 20, 0.00, 1, 1, 1),
]
price = {p[1]: p for p in PRICES}
with (OUT / 'price_table_ILLUSTRATIVE.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['provider', 'model', 'input_per_mtok', 'output_per_mtok', 'cached_input_per_mtok',
                'batch_discount', 'as_of', 'source'])
    w.writerows(PRICES)
rows = []
for day in range(1, 31):
    for name, model, n, tin, tout, cshare, batch, async_ok, simple in WORKFLOWS:
        k = int(n * random.uniform(0.85, 1.15))
        itok, otok = k * tin, k * tout
        ctok = int(itok * cshare)
        p = price[model]
        cost = ((itok - ctok) * p[2] + ctok * p[4] + otok * p[3]) / 1e6
        if batch:
            cost *= (1 - p[5])
        cost *= random.uniform(0.99, 1.01)  # invoice noise
        rows.append([f'2026-09-{day:02d}', name, p[0], model, itok, otok, ctok, batch, async_ok, simple,
                     round(cost, 4)])
with (OUT / 'usage_SYNTHETIC.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['date', 'workflow', 'provider', 'model', 'input_tokens', 'output_tokens', 'cached_input_tokens',
                'batch', 'async_ok', 'simple_task', 'invoice_cost_usd'])
    w.writerows(rows)
print('wrote', len(rows), 'usage rows to', OUT)
