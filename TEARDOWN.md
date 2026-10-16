# We re-priced six weeks of our own AI coding-agent usage. The "obvious" saving was 5.5× too big.

Over 46 days (35 of them active), one person's coding agent made **61,955 requests**. There was no invoice for this exercise — a real client audit starts by reconciling to one — so we did what you do without one: we re-priced every request at the vendor's **public, dated price sheet** (retrieved 2026-10-16) and asked where the money would go. Every dollar figure below is **API-equivalent**, not what anyone was billed.

The total came to **$7,882**. Three things in it surprised us.

## 1. Almost all of it is re-reading
**66% of the cost was cache reads**, and 99% of input-side tokens were cache hits. Output — the thing people optimise prompts for — was 12%. Spend is driven by *how long the context is × how many turns run on it*, and one project accounted for 63% of it. The lever is context length and session hygiene, not a cleverer prompt.

## 2. The headline saving was 5.5× too big
Newer model versions are cheaper per token. If you re-price every request that ran on an older version at the newer version's rates, you "save" **$1,625 (20.6%)**. But most of those requests were made *before* the newer version existed. Counting only requests made after it was available: **$293 (3.7%)**. A saving you couldn't have taken at the time isn't a saving.

## 3. The expensive-looking setting was the right one
85% of cache-write tokens used the 1-hour prompt cache, which costs more to write than the 5-minute cache. We tested the opposite: if every cache write had used the 5-minute cache, anything idle for more than five minutes would have to be re-written at write prices. Only 2.5% of cache-read tokens came after such a gap, but those requests carried very large contexts. Net result: the 5-minute cache would have cost **$1,781 more (+22.6%)**. Keep the 1-hour cache. (And moving subagent work to a cheaper model saved $62 — not worth the quality risk.)

## What this is, and isn't
It is a re-pricing from token counters, not realised savings. We did not evaluate output quality. Subagent streams were merged when measuring idle gaps, so those gaps look shorter than they were. The aggregated CSVs in `teardown-data/` let you check the totals, and the scripts in this repository reproduce them from your own usage logs.

## How we'd do this for your bill
- **Export-only.** Billing/usage exports — no API keys, no prompts, no production access.
- **Deterministic analysis** — scripts on your numbers, not a model reading your data.
- **Reconcile first**: recomputed spend must match your invoice within ±3% before any saving is counted.
- **Only conservative, de-duplicated, available-at-the-time findings** — a lower bound, with the formula next to each number.
- Fixed price, fixed scope. If we can't see a credible path beyond our fee at your spend level, we say so before you pay.

If you spend **$3,000+/month** on LLM APIs and want a second pair of eyes: **hello@currawongweb.com**.

*Prices: Anthropic's public pricing page, retrieved 2026-10-16 (`price_table_anthropic_2026-10-16.csv`).*
