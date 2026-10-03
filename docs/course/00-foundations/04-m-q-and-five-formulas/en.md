# m, q and the Five Formulas

> Two ratios decide the sign of every capital action; their diagonal decides both rotations.

**Type:** Build
**Files:** `dat/engine.py` (`dn_first_order`, `strategy_rotation`, `bitmine_rotation`), `tests/test_engine.py`, `data/weekly.csv`, `.claude/rules/method.md`
**Prerequisites:** 00-03
**Time:** ~40 minutes

## Learning Objectives

- Derive the change in n for issuing common and for retiring preferred from n = N / S
- Write all five first-order formulas with k = x / (p · S) and say when each adds
- Combine two legs into a rotation and express it in value-to-common dollars
- Find a week's break-even price for STRC or BMNP from its m
- Reproduce the $3.895M STRC test anchor and explain why the 7/26 data row gives $3.893M

## The Problem

Lesson 00-03 gives one number per week, n. A week's n moves for many reasons at once: the coin price, share sales, preferred retirements. To say what one action did, the project needs a formula for that action alone, in terms anyone can check: the dollars spent and the price paid.

Without it, "Strategy sold $544.5M of stock" is a fact with no sign. The formulas turn it into "that sale added this many coins per share, and it would have subtracted below this price".

## The Concept

Two ratios, both a price over what that security is backed by:

- **m, net mNAV** = s / (p · n): the common share price over the net coin value one share owns.
- **q** = preferred price / $100 notional. STRC at $99 on $100 gives q = 0.99.

Take an action of x dollars and let k = x / (p · S), the action's size in coins per share.

**Issue common at m.** The firm sells x of new shares at price s, so R rises by x and N rises by x / p. S rises by x / s. Then n' = (N + x/p) / (S + x/s). Keeping terms of first order in x:

```
Δn ≈ x/(p·S) − (N/S) · x/(s·S)
   = k − n · k · p/s
   = k · (1 − p·n/s)
   = k · (1 − 1/m)
```

It adds when m > 1: each $1.00 of coin value the new shares claim brings in $m of cash.

**Retire preferred at q.** The firm pays x and retires x / q of notional, so R falls by x and F falls by x / q. S does not change:

```
Δn = ((x/q − x) / p) / S = k · (1/q − 1)
```

This one is exact. In dollars, Δn · p · S = x/q − x: the notional retired less the cash paid.

The other three follow by symmetry:

| # | action | Δn | adds when |
|---|---|---|---|
| 1 | issue_common | k·(1 − 1/m) | m > 1 |
| 2 | buyback_common | k·(1/m − 1) | m < 1 |
| 3 | issue_pref | k·(1 − 1/q) | q > 1 |
| 4 | retire_pref | k·(1/q − 1) | q < 1 |
| 5 | buy_coin / sell_coin | 0 | neutral on day one |

A coin trade swaps x of R for x / p of C at the coin price, so N does not change.

**Rotations.** A rotation is two legs with the same x. Multiply Δn by p · S to get dollars, the page's "value to common":

```
Strategy (1 + 4): issue common, retire STRC   value = x · (1/q − 1/m)   adds while m > q
BitMine  (3 + 2): issue BMNP, buy back common value = x · (1/m − 1/q)   adds while m < q
```

Both change sign on the same line, m = q. Strategy's rotation stops adding when STRC trades above $100 × m. BitMine's stops adding when BMNP trades below its $100 liquidation preference × m. SharpLink has no preferred, so the map draws it at q = 1, where the line is m = 1.

```widget
calc
```

```widget
map
```

## Build It

### Step 1: Read the formulas

From `dat/engine.py`:

```python
def dn_first_order(action, x, p, S, m=None, q=None):
    """method.md table: k = x/(p·S), x dollars. Coin trades are 0 on day one."""
    k = x / (p * S)
    return {'issue_common': lambda: k * (1 - 1 / m), 'buyback_common': lambda: k * (1 / m - 1),
            'issue_pref': lambda: k * (1 - 1 / q), 'retire_pref': lambda: k * (1 / q - 1),
            'buy_coin': lambda: 0.0, 'sell_coin': lambda: 0.0}[action]()
```

```python
def strategy_rotation(x, p, S, m, q):
    """Issue common (1) and retire preferred (4) with the same x: k·(1/q − 1/m), adds while m > q."""
    return dn_first_order('issue_common', x, p, S, m=m) + dn_first_order('retire_pref', x, p, S, q=q)
```

`bitmine_rotation` is the same shape with `issue_pref` and `buyback_common`. In the weekly attribution each action uses its own price, not the week's close: common at m = avg_price / (p · n), preferred at q = avg_price / 100.

### Step 2: The STRC anchor

Bitcoin Magazine reported that Strategy spent $24.998M to retire $28.893M of STRC notional in the 7/26 week. The 8-K states $25.0M. Run both through `dn_first_order`:

```python
import csv
from dat.engine import dn_first_order
p, S = 64092.65, 388_176_305  # MSTR 7/26: weekly.csv p, balances.csv shares_diluted
a = next(r for r in csv.DictReader(open('data/actions.csv'))
         if r['ticker'] == 'STRC' and r['week_end'] == '2026-07-26')
for label, x, notional in (('8-K row', float(a['usd']), float(a['units'])),
                           ('article', 24_998_000, 28_893_000)):
    q = x / notional
    value = dn_first_order('retire_pref', x, p, S, q=q) * p * S
    print(f'{label:8} x = ${x:,.0f}  notional = ${notional:,.0f}  q = {q:.4f}  value to common = ${value:,.0f}')
```

```
8-K row  x = $25,000,000  notional = $28,893,000  q = 0.8653  value to common = $3,893,000
article  x = $24,998,000  notional = $28,893,000  q = 0.8652  value to common = $3,895,000
```

Both equal notional less cash. The data follows the filing's rounded $25.0M; the test anchors to the published $3.895M.

### Step 3: Two weeks against the line

```python
import csv
for w in csv.DictReader(open('data/weekly.csv')):
    if w['week_end'] in ('2026-08-23', '2026-09-20') and w['firm'] != 'SBET':
        m, q = float(w['m']), float(w['q'])
        rot = 1/q - 1/m if w['firm'] == 'MSTR' else 1/m - 1/q
        print(f"{w['firm']} {w['week_end']}  m = {m:.4f}  q = {q:.4f}  per $100M rotated: ${100e6 * rot:+,.0f}  line at ${100 * m:.2f}")
```

```
BMNR 2026-08-23  m = 0.9376  q = 0.9326  per $100M rotated: $-569,994  line at $93.76
BMNR 2026-09-20  m = 1.0281  q = 0.9791  per $100M rotated: $-4,864,968  line at $102.81
MSTR 2026-08-23  m = 0.9838  q = 0.9618  per $100M rotated: $+2,324,217  line at $98.38
MSTR 2026-09-20  m = 1.2171  q = 0.9851  per $100M rotated: $+19,346,709  line at $121.71
```

At the 9/20 net mNAV of 1.2171, Strategy's STRC rotation adds net sats per share while STRC trades below $121.71. BitMine's 8/23 week sits 0.53% above the line (m / q − 1).

### Step 4: Run the tests

```
.venv/bin/python -m pytest tests/test_engine.py -k "anchor or par or rotations or matches_exact" -o addopts="" -v
```

```
tests/test_engine.py::test_strc_anchor PASSED                            [  7%]
tests/test_engine.py::test_zero_at_par[issue_common] PASSED              [ 14%]
tests/test_engine.py::test_zero_at_par[buyback_common] PASSED            [ 21%]
tests/test_engine.py::test_zero_at_par[issue_pref] PASSED                [ 28%]
tests/test_engine.py::test_zero_at_par[retire_pref] PASSED               [ 35%]
tests/test_engine.py::test_zero_at_par[buy_coin] PASSED                  [ 42%]
tests/test_engine.py::test_zero_at_par[sell_coin] PASSED                 [ 50%]
tests/test_engine.py::test_rotations_zero_at_m_eq_q[0.6] PASSED          [ 57%]
tests/test_engine.py::test_rotations_zero_at_m_eq_q[0.87] PASSED         [ 64%]
tests/test_engine.py::test_rotations_zero_at_m_eq_q[1.0] PASSED          [ 71%]
tests/test_engine.py::test_rotations_zero_at_m_eq_q[1.4] PASSED          [ 78%]
tests/test_engine.py::test_rotations_zero_at_m_eq_q[2.5] PASSED          [ 85%]
tests/test_engine.py::test_first_order_matches_exact[row0] PASSED        [ 92%]
tests/test_engine.py::test_first_order_matches_exact[row1] PASSED        [100%]
======================= 14 passed, 2 deselected in 0.02s =======================
```

These are the four method.md anchors: the $3.895M STRC case to the dollar, each formula zero at m = 1 or q = 1, each rotation zero at m = q, and first order within 1% of an exact recompute for an action under 1% of market cap.

## Use It

- `data/attribution.csv` stores `dn_first_order` next to `dn_exact` for every action row. For the 7/26 MSTR sale of $544.5M (1.5% of market cap, larger than the 1% test scope), first order gives $46.93M to common and the exact recompute $46.27M.
- The page's break-even map plots q across and m up for every firm-week, with m = q as the diagonal.
- `sentence()` in `dat/build_site.py` writes each firm's headline in the form set by `framing.md`, with the break-even price; `dat/memo.py` reuses those sentences.

## Ship It

This step produced the formula functions in `dat/engine.py` and their anchors in `tests/test_engine.py`. Run the whole file:

```
.venv/bin/python -m pytest -q tests/test_engine.py
```

## Decisions

```widget
decisions R8,R10,A7,A8,M2,M7,L6
```

## What Went Wrong

- Notes #11: the spec's hypothesis was that both rotations add. The data: Strategy's rotation sat on its adding side in 18 of 18 filed weeks, BitMine's in 0 of 15. BitMine's closest week, 8/23, is 0.53% above the line, near the 0.43% upward bias in its estimated share count. The memo states the counts and the margin.

## Exercises

1. Call `strategy_rotation(100e6, p, S, m, q)` with the MSTR 2026-09-20 values from `data/weekly.csv` and `data/balances.csv`, multiply by p · S, and confirm you get the $19,346,709 from Step 3.
2. Derive the exact (not first-order) Δn for issue_common from n' = (N + x/p) / (S + x/s), then compare it with `dn_first_order` for x = $544.5M in the 7/26 week.
3. BMNP's liquidation preference floats to max($100, last sale price, 10-day average) after BitMine's first follow-on sale. Rewrite BitMine's break-even price for a preference of $105 and say how q changes.
