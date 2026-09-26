# Splitting a Week Into Parts

> Every week's change in net coins per share, cut into named pieces that add back up exactly.

**Type:** Build
**Files:** `dat/engine.py` (`attribute()`, `week_rows()`, `dn_first_order()`), `dat/balances.py` (`net()`), `data/attribution.csv`
**Prerequisites:** 00-03, 00-04
**Time:** ~40 minutes

## Learning Objectives

- List the fixed order the engine uses to split a week: price, itm_flip, each action at its own price, carry, est_issuance (BitMine), residual
- Explain why each part is an exact recompute of n through `net()` rather than a first-order estimate
- Compute "value to common" (Δn × S × p) for one row of `data/attribution.csv`
- Read the gap between `dn_first_order` and `dn_exact` for the BMNP issue and say where it comes from
- Run the identity check that proves the parts sum to the observed change

## The Problem

Lesson 00-03 gives one number per firm-week: n, net coins per share. Two weeks give an observed change, Δn. That change mixes several causes. The coin price moved. The share price moved, which can push a convertible note (debt that converts into shares at a set price) into or out of the money. The firm sold stock, retired preferred, bought coins and paid dividends.

The first-order formulas from lesson 00-04 give each action's effect alone. They don't add up to the observed change, because the causes interact: a price move changes n, which changes the m at which the next stock sale lands. A table of first-order values next to an observed change that differs by an unexplained amount is hard to check. The engine needs parts that sum to the observed Δn exactly, with whatever the filings can't explain left in one labeled row.

## The Concept

Start from last week's state. Change one thing at a time, in a fixed order, and recompute n after each change. The difference in n at each step is that part's `dn_exact`. What remains between the last recomputed n and this week's actual n is the residual.

```mermaid
flowchart LR
  A[last week state] --> P[price: new p]
  P --> F[itm_flip: new s]
  F --> X[each action in actions.csv order]
  X --> C[carry rows]
  C --> E[est_issuance BMNR only]
  E --> R[residual: rest of observed dn]
```

1. `price`: last week's balances revalued at this week's coin price p. Only the (R − D − F)/p term moves.
2. `itm_flip`: the same balances at this week's share price s. Converts or STRK that cross their conversion price move between D or F and S.
3. Each action row, in `actions.csv` order, at its own price: common at its `avg_price`, preferred at q = `avg_price`/100, coins at their stated dollars.
4. `carry` rows: preferred dividends and convert interest (Strategy's `DIV_INT`, BitMine's BMNP dividends as `DIV`, e.g. two rows in the week ending 2026-06-28), inferred staking (SharpLink's `STAKE`). These make the parts reach the observed change; they are not actions.
5. `est_issuance`: BitMine only, the week's estimated share issuance booked at that week's BMNR close.
6. `residual`: observed Δn minus the sum of the rows above.

Order matters because every step changes the state the next one starts from. One fixed order makes the split reproducible.

The unit is Δn in coins per share. The page converts it to dollars, "value to common" = Δn × S × p, at this week's S and p. Here is Strategy's week ending 2026-09-20:

```widget
weekparts MSTR 2026-09-20
```

## Build It

### Step 1: Read the loop

`dat/engine.py`, `attribute()`. Each `step()` recomputes n through `state_net()`, which calls `balances.net()`:

```python
def attribute(prev, cur, rows):
    """-> (out rows, observed Δn). rows are applied in the given order after price and itm_flip; a row's
    'label' (default: its action) names it in the output. Residual = observed − sum of the rest."""
    out, st = [], prev

    def step(label, new, **kw):
        nonlocal st
        out.append({'action': label, 'dn_exact': state_net(new)['n'] - state_net(st)['n'], **kw})
        st = new

    step('price', {**st, 'p': cur['p']})
    step('itm_flip', {**st, 's': cur['s']})
    for a in rows:
        act, x, pre = a['action'], float(a['usd']), state_net(st)
        m = float(a['avg_price']) / (st['p'] * pre['n']) if act in COMMON else None
        q = float(a['avg_price']) / 100 if act in PREF else None
        new = apply(st, a)
        dn = state_net(new)['n'] - pre['n']
        is_act = act != 'carry'
        step(a.get('label', act), new, ticker=a['ticker'], usd=x, m=m, q=q,
             dn_first_order=dn_first_order(act, x, st['p'], pre['S'], m, q) if is_act else None,
             dn_per_dollar=dn / x if is_act else None, filing_url=a.get('filing_url', ''))
    obs = state_net(cur)['n'] - state_net(prev)['n']
    out.append({'action': 'residual', 'dn_exact': obs - math.fsum(r['dn_exact'] for r in out)})
    return out, obs
```

`week_rows()` supplies the rows: the week's actions, then its carry rows, then (BitMine only) an `est_issuance` row labeled from `issue_common`.

### Step 2: Rebuild the file and check the identity

The engine writes `attribution.csv` into the directory it is given, so run it on a copy:

```
d=$(mktemp -d) && cp data/*.csv $d && .venv/bin/python -m dat.engine $d | tail -2 && diff -q $d/attribution.csv data/attribution.csv && echo identical
```

```
residual test (MSTR from 2026-08-02; <5% or within R rounding): 8/8 in-scope weeks pass (reported here; check.py enforces); no failures
identity OK: every week, rows incl. residual sum to observed dn within 1e-12 relative
identical
```

The identity line is the engine's own check: for every firm-week, the rows including the residual sum to the observed Δn within 1e-12 relative.

### Step 3: Convert one week to dollars

Save this as `parts.py` in the repo root and run it with `.venv/bin/python parts.py`:

```python
import csv, math
w = '2026-09-20'
wk = next(r for r in csv.DictReader(open('data/weekly.csv')) if r['firm'] == 'MSTR' and r['week_end'] == w)
S = float(next(r for r in csv.DictReader(open('data/balances.csv')) if r['firm'] == 'MSTR' and r['date'] == w)['shares_diluted'])
to_usd = S * float(wk['p'])
rows = [r for r in csv.DictReader(open('data/attribution.csv')) if r['firm'] == 'MSTR' and r['week_end'] == w]
for r in rows:
    print(f"{r['action']:<15}{r['ticker']:<8}{float(r['dn_exact']) * to_usd / 1e6:>+9.1f}M")
print(f"{'sum':<23}{math.fsum(float(r['dn_exact']) for r in rows) * to_usd / 1e6:>+9.1f}M")
```

```
price                     +711.7M
itm_flip                  +125.3M
buy_coin       BTC          +1.1M
retire_pref    STRC         +3.1M
carry          DIV_INT     -57.4M
residual                    -2.9M
sum                       +780.9M
```

The STRC retirement matches the formula: $174.0M at q = 0.982364 gives (1/q − 1) × 174.0M = $3.1M. The coin purchase is +$1.1M rather than 0 because the BTC was bought at an average price that differs from the week's close.

### Step 4: First order against exact

The first-order value uses the price (q or m). The exact value uses the cash actually received. BitMine's BMNP preferred issue in the week ending 2026-06-14 shows the difference. Save this as `gap.py` in the repo root and run it with `.venv/bin/python gap.py`. It converts the `issue_pref` row's `dn_first_order` and `dn_exact` to dollars the same way as Step 3, at that week's S and p:

```python
import csv
w = '2026-06-14'
wk = next(r for r in csv.DictReader(open('data/weekly.csv')) if r['firm'] == 'BMNR' and r['week_end'] == w)
b = next(r for r in csv.DictReader(open('data/balances.csv')) if r['firm'] == 'BMNR' and r['date'] == w)
to_usd = float(b['shares_diluted']) * float(wk['p'])
r = next(r for r in csv.DictReader(open('data/attribution.csv')) if r['firm'] == 'BMNR' and r['week_end'] == w and r['action'] == 'issue_pref')
fo, ex = float(r['dn_first_order']) * to_usd / 1e6, float(r['dn_exact']) * to_usd / 1e6
print(f"q {float(r['q']):.6f}  cash received ${float(r['usd']) / 1e6:.1f}M  notional ${float(b['pref_notional']) / 1e6:.1f}M")
print(f"first order {fo:.2f}M   exact {ex:.2f}M   gap {fo - ex:.2f}M")
```

```
q 0.800000  cash received $273.8M  notional $350.0M
first order -69.30M   exact -77.15M   gap 7.85M
```

BitMine issued 3.5M BMNP shares ($350.0M of notional, the $100 liquidation preference per share) at $80, so q = 0.80. At $80 the gross is $280.0M; net cash was $273.8M, so fees were $6.2M. First order reads the $273.8M as notional sold at q = 0.80, which is $342.25M. Exact books the $350.0M actually issued. The difference, $7.75M, is the $6.2M of fees divided by q. Both figures are converted at the week's closing S, which is 1.2% above S before the issue (estimated BitMine issuance that week), so the gap prints as $7.85M.

## Use It

- The page's attribution bars stack `dn_exact` × S × p per category (lesson 03-01).
- `check.py` check 4 reruns `attribute()` for every Strategy week from 2026-08-02 and tests the residual (lesson 02-02).
- `dat/build_site.py` recomputes the observed change through the same `states()` so the bars can be checked against it.

## Ship It

This step produced `dat/engine.py`, `data/attribution.csv` (198 rows) and `tests/test_engine.py`, including `test_identity_two_weeks`, which crosses a convert and an option in one week:

```
.venv/bin/python -m pytest -q tests/test_engine.py
```

```
16 passed in 0.02s
```

## Decisions

```widget
decisions A1,A2,R8,B4,S7
```

## What Went Wrong

Build note #5: the first version of the engine booked a `disclosure` row for the USD Cash that appeared on 2026-08-23. The residual for that week came out at exactly $1,570.1M, which pointed at the rule rather than the data. Lesson 02-02 tells that story.

## Exercises

1. Change `w` in `parts.py` to `2026-08-23` and confirm the sum equals the observed value in `check.py`'s residual line for that week ($4,140.0M).
2. In `attribute()`, swap the `price` and `itm_flip` steps, rerun the engine on a copy, and compare the 2026-09-20 `price` and `itm_flip` rows with the committed file. Which rows change, and does the identity still hold?
3. Using the 2026-06-14 BMNR `issue_pref` row, compute what `dn_first_order` would be if BitMine had received the full $280.0M, and compare it with `dn_exact`.
