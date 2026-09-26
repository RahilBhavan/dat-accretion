# Test Catalogue

> Every test in `tests/`, one line each: what it guards against.

**Type:** Reference
**Files:** `tests/test_*.py` (12 files), `.claude/rules/method.md` (Test anchors)
**Prerequisites:** None
**Time:** ~20 minutes

## How to Run

The suite runs offline. Tests that read `data/*.csv` use the committed files; `tests/test_build_site.py` builds the site from cached releases ("offline: cached releases only", its fixture says); every other test builds its input from snippets that copy the filings' wording.

```
.venv/bin/python -m pytest -q --collect-only -q
```

```
tests/test_balances.py: 12
tests/test_build_site.py: 11
tests/test_check.py: 6
tests/test_edgar.py: 3
tests/test_engine.py: 16
tests/test_memo.py: 4
tests/test_parse_bmnr.py: 21
tests/test_parse_mstr.py: 29
tests/test_parse_sbet.py: 19
tests/test_prices.py: 5
tests/test_refresh.py: 6
tests/test_snapshot_kpi.py: 5
```

That is 137 collected tests (counts include each parameter case). The full run:

```
.venv/bin/python -m pytest -q
........................................................................ [ 52%]
.................................................................        [100%]
137 passed in 0.45s
```

Run one file with `.venv/bin/python -m pytest -q tests/test_engine.py`, or one test with `-k strc_anchor`. `.github/workflows/ci.yml` runs the same suite (`python -m pytest -q tests`) as the `tests` check that protects `main` (decision P4), and `refresh.yml` runs it again before each weekly merge. A **fixture** here is plain test input; a **parameterized** test runs once per listed case.

## test_balances.py

| test | guards against |
|---|---|
| `test_matches_api` (4 cases) | the rebuild of Strategy's net sats per share, net reserve, amplification and mNAV drifting past 0.5% of the API snapshot of 2026-09-25T16:19:32Z (decision R2) |
| `test_only_2030a_itm` | any convert other than the 2030A note ($149.77) counted in S at $158.93 |
| `test_2028_flips_at_190` | the in-the-money flip not moving $1,010M from D to S at $190 (decision R3) |
| `test_pref_roll_both_directions` | preferred notional rolling the wrong way from the 6/30 anchor, before or after it |
| `test_class_a_roll_direction` | class A shares rolling the wrong way from the 7/24 cover count |
| `test_reserve_check_pass_fail_and_kinds` | the R check picking the wrong kind (reserve vs R), tolerance or verdict (decision S4) |
| `test_bmnr_flows_unexplained` | wrong unexplained ΔR for BitMine, the input to its share estimate |
| `test_bmnr_basic_scales_to_anchor_then_accumulates` | BitMine S not landing on the 7/09 anchor exactly, or negative cash adding shares (decision B3) |
| `test_bmnr_buyback_in_anchor_week_raises` | a buyback in the anchor week being rolled without a split |

## test_build_site.py

| test | guards against |
|---|---|
| `test_headline_break_even_is_100_m` | a headline whose break-even is not $100 × m, or a SharpLink headline with a break-even or an em dash |
| `test_every_map_point_links_to_a_filing` | a map dot without an `https://www.sec.gov/` link, or SharpLink missing its 4 dates |
| `test_bars_sum_to_observed` | bars plus price plus itm_flip not summing to the observed change within $1 |
| `test_deterministic_apart_from_generated_at` | two builds of the same data differing |
| `test_excluded_holdings_0921` | the page's sentence on BitMine's excluded BTC and stakes misreading the 9/21 release (decision B1) |
| `test_excluded_holdings_missing_is_omitted` | a crash when the holdings sentence or cached release is missing |
| `test_dollars_moved_excludes_carry` | carry rows counted as dollars moved (MSTR 9/20: $249.7M) |
| `test_est_issuance_in_issue_common_and_flagged` | BitMine's estimated issuance missing from its issue bar (9/20: 6,583,230) |
| `test_bad_check_json_is_not_yet_run` (3 cases) | an empty, non-JSON or non-object `check.json` breaking the build (decision O2) |

## test_check.py

| test | guards against |
|---|---|
| `test_all_pass_exit_0_and_shape` | a wrong `check.json` shape or exit code on success |
| `test_one_failure_fails` | one failed check not failing the run |
| `test_network_error_is_a_failure_not_a_skip` | a network error counted as a skip (decision A5) |
| `test_no_checks_is_not_a_pass` | an empty run reported as a pass |
| `test_residuals_offline_all_pass` | a committed in-scope Strategy week failing the residual test |
| `test_crash_still_writes_fail_record` | a crash leaving no `check.json` |

## test_edgar.py

| test | guards against |
|---|---|
| `test_retries_503_then_succeeds` | a 503 or 429 failing without a retry (decision O6) |
| `test_gives_up_after_backoff` | retrying forever |
| `test_404_fails_at_once` | retrying errors that are not transient |

## test_engine.py

| test | guards against |
|---|---|
| `test_strc_anchor` | the Bitcoin Magazine STRC week not giving $3,895,000 to the dollar (decision A7) |
| `test_zero_at_par` (6 cases) | any formula non-zero at m = 1 and q = 1 |
| `test_rotations_zero_at_m_eq_q` (5 cases) | either rotation non-zero at m = q, or the wrong sign off the line |
| `test_first_order_matches_exact` (2 cases) | first order more than 1% from the exact recompute for an action under 1% of market cap (decision R8) |
| `test_identity_two_weeks` | attribution rows in the wrong order or not summing to observed Δn (decision A1) |
| `test_residual_test` | the <5% / rounding / FAIL verdicts on an 8/30-like week (decision A3) |

## test_memo.py

| test | guards against |
|---|---|
| `test_main_writes_memo_with_computed_counts` | a memo title whose counts are not computed from `weekly.csv` (decision M4) |
| `test_stale_bias_fails` | a new BitMine week passing without a recomputed bias (decision M5) |
| `test_each_week_uses_its_own_bias` | a week judged by the latest bias instead of its own |
| `test_bias_that_flips_a_week_fails` | a bias large enough to move a week across the line passing |

## test_parse_bmnr.py

| test | guards against |
|---|---|
| `test_weekly_release` | misreading holdings, cash, acquired ETH, staking, yield or buyback in the 9/21 release shape |
| `test_early_cash_wording_and_pref_closing` | missing the June "total cash" wording or the BMNP closing ($273.8M net) |
| `test_no_holdings_skips` | a release without holdings being parsed instead of skipped |
| `test_unknown_near_variant_raises` (10 cases) | an unknown capital sentence passing silently (decision S11) |
| `test_date_before_prior_week_raises` | a release dated before the prior one |
| `test_dividends_prose_and_table` | missing a BMNP dividend in prose or in a payment table |
| `test_build_rows` | wrong usd, notes or dividend carry on BitMine rows (decision B6) |
| `test_ser_bmnr_reads_escaped_page_data` | failing to read the site's embedded data |
| `test_site_check_at_snapshot_week_and_age` | the site check off tolerance or accepting a stale snapshot (decision B9) |
| `test_no_staking_carry_rows` | staking booked as carry for BitMine (decision B2) |
| `test_holdings_change_without_acquired_raises` (2 cases) | a holdings change with no purchase sentence passing (decision B8) |

## test_parse_mstr.py

| test | guards against |
|---|---|
| `test_no_sale_week_with_buy_repurchase_and_reserve` | misreading the 9/21 8-K shape: buy, STRC retirement, carry, stated row |
| `test_atm_sale_week_and_btc_sale` | misreading ATM sales, a STRC issue and a BTC sale |
| `test_unknown_ticker_raises` | an unknown ticker or row label passing (decision S1) |
| `test_no_section_skips_but_trades_without_btc_raise` | trades without a BTC section being skipped |
| `test_stre_retirement_raises` | a STRE retirement converted at a guessed rate (decision S8) |
| `test_trade_table_under_renamed_heading_raises` | a renamed section hiding its table |
| `test_roll` | a 1-BTC miss passing unless listed, or a listed gap over 1 BTC passing (decision S3) |
| `test_dividend_carry_from_every_source` | missing a dividend paid from ATM, BTC-sale or reserve funds |
| `test_reserve_in_and_precision` | wrong `reserve_in` or precision; a capacity sentence read as a flow |
| `test_unknown_reserve_flow_raises` | a new inflow wording passing |
| `test_dividend_footnote_repeated_in_reserve_paragraph_counts_once` | one dividend booked twice |
| `test_unknown_reserve_outflow_raises` (14 cases) | outflow wordings outside the known phrases passing |
| `test_remaining_clause_does_not_borrow_amount` | "the remaining proceeds" taking another clause's amount |
| `test_sentence_split_keeps_numbers_and_abbreviations` | splitting "$5.04" and "U.S." (decision S12) |
| `test_hypothetical_or_negated_reserve_flow_raises` (2 cases) | "may use up to" or "did not use" read as a flow |

## test_parse_sbet.py

| test | guards against |
|---|---|
| `test_8k_0630_real_text` | misreading the 6/30 8-K's purchase, buyback, holdings parts and summaries |
| `test_q2_release_two_dates_and_cash` | missing a date or the 6/30 cash in the Q2 release |
| `test_direct_offering` | misreading the 6/23 offering (10,013,351 shares at $7.49) |
| `test_unknown_number_raises` (5 cases) | an unknown capital number passing |
| `test_parts_must_sum_to_total` | parts that don't sum to the total passing (decision L3) |
| `test_summary_without_detail_raises` | a summary booked with no detailed sentence |
| `test_equity_statement` | misreading the 10-Q equity statement, or an unknown row passing (decision L8) |
| `test_build_rows_per_filed_date` | rows on dates SharpLink did not file, or wrong carry (949, 156, 2,057 ETH) (decisions L1, L4) |
| `test_action_after_last_holdings_date_raises` | an action with no filed date to hold it |
| `test_site_check_staleness_is_against_own_last_filing` | the site check failing while SharpLink is silent (decision L10) |
| `test_later_10q_keeps_q2_net_proceeds_and_treasury_cost` | a Q3 10-Q overwriting Q2 figures (decision L9) |
| `test_non_capital_8k_is_skipped` (2 cases) | a 5.02 or 5.07 8-K stopping the refresh |
| `test_same_sentence_under_801_raises` (2 cases) | the same numbers under item 8.01 being skipped |

## test_prices.py

| test | guards against |
|---|---|
| `test_yahoo_rows_skip_null_and_use_close` | adjusted closes or null closes entering `prices.csv` (decision R9) |
| `test_yahoo_rows_drop_today_until_1630_local` | a live intraday price saved as a close |
| `test_gecko_rows_midnight_is_prior_day_close` | the 00:00 UTC point assigned to the wrong day |
| `test_close_on_or_before_weekend_uses_friday` | a weekend week not using Friday's close |
| `test_close_on_or_before_raises_past_7_days` | a close over 7 days old used silently |

## test_refresh.py

| test | guards against |
|---|---|
| `test_steps_order` | pipeline steps running out of order |
| `test_reanchor_watches_sharplink_after_its_q2_anchor` | SharpLink's next 10-Q not raising the reanchor alert (decision O4) |
| `test_reanchor_filter_keeps_only_periods_after_the_anchor` | the anchor's own 10-Q triggering the alert |
| `test_bmnr_s_bias_pin` | the BitMine S bias moving off 0.43% at 2026-09-20 (decision B5) |
| `test_bmnr_s_bias_zero_before_first_estimate` | a bias before the first estimated week |
| `test_newer_8k_text` | wrong text naming a newer 8-K than the repo holds |

## test_snapshot_kpi.py

| test | guards against |
|---|---|
| `test_row` | a KPI row with wrong fields or order |
| `test_bad_net_sats` (3 cases) | a missing, zero or string value being saved |
| `test_save_appends` | overwriting instead of appending, or losing the raw JSON (decision P6) |

## Exercises

1. Run `.venv/bin/python -m pytest -q tests/test_engine.py -k strc_anchor -v` and read which assertion pins $3,895,000. Then compute (1/q − 1) × x with x = $24,998,000 and q = 24,998,000 / 28,893,000 by hand.
2. Add a parameter case to `test_unknown_reserve_outflow_raises` with a new outflow wording of your own and confirm it passes (the parser raises). If it fails, you found a gap.
3. Run the suite with the residual limit tightened from 5% to 1%, without editing any file: `.venv/bin/python -c "import dat.engine, pytest; dat.engine.LIMIT = 0.01; pytest.main(['-q', 'tests'])"`. One test fails (`test_residual_test`). `data/check.json` is gitignored, so run `.venv/bin/python check.py` first (needs network) or use the check.py output shown in lesson 03-03, and use it to explain why `test_residuals_offline_all_pass` still passes (hint: decision A3).
