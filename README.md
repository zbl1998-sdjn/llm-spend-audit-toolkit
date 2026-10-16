# llm-spend-audit-toolkit

Deterministic scripts for auditing LLM spend from usage exports. **No LLM calls, no network.**

Start with the write-up: **[TEARDOWN.md](TEARDOWN.md)** — six weeks of one person's coding-agent usage, re-priced at public API rates (61,955 requests, $7,882 API-equivalent), and why the "obvious" saving was 5.5× too big.

## What's inside
- `audit_calc.py` — reconcile a usage export to its invoice, break spend down by workflow, and produce a conservative savings register (one finding per workflow, no stacking, 80% haircut by default). Inputs: a usage CSV and a dated price CSV.
- `make_synthetic.py` + `sample/` — **synthetic** usage and **illustrative** prices to try the tool (fake model names).
- `extract_claude_usage.py`, `analyze_claude_usage.py`, `version_repricing.py`, `ttl_counterfactual.py` — the scripts behind the teardown: per-request usage extraction (token counters only), pricing by category, "available-at-the-time" version repricing, and the 5-minute vs 1-hour cache counterfactual. The raw per-request file is not published; the aggregated CSVs are in `teardown-data/`.
- `price_table_anthropic_2026-10-16.csv` — the public price sheet used, with source URL and retrieval date.

## Quick start
```
python make_synthetic.py
python audit_calc.py --usage sample/usage_SYNTHETIC.csv --prices sample/price_table_ILLUSTRATIVE.csv --swap support-reply=model-small
```
Expected: recomputed spend within 3% of the (synthetic) invoice, then a savings register with lower bounds.

## Principles
1. Reconcile before you claim. 2. Lower bound, not best case. 3. Count only what was available at the time. 4. Show the formula next to every number. 5. Never send customer data to a model you haven't approved in writing.

## Limits
No quality evaluation, no latency analysis, no tokenizer-difference correction, no real client data. Savings are re-pricing estimates until verified against your next invoice.

## Want a second pair of eyes on your bill?
If your team spends **$3,000+/month** on LLM APIs, we do fixed-price audits from billing/usage exports only — no API keys, no prompts, no production access. We reconcile to your invoice first, and if we can't see a credible saving beyond our fee, we tell you before you pay.
Contact: **hello@currawongweb.com** · Currawong Web, operated by Jinan Shenyu International Trade Co., Ltd. (China).

## Licence
MIT — see [LICENSE](LICENSE).
