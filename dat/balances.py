"""Strategy's net definition: net coins N, per share n, mNAV, amplification. stdlib only.

Source: glossary in the 2026-08-24 FWP,
https://www.sec.gov/Archives/edgar/data/1050446/000119312526363557/d431748dfwp.htm
In-the-money (s > conversion price) converts and prefs leave D/F and add their shares to S.
Other debt (the secured term loan) is not deducted.
"""


def net(coins, usd_assets, converts, prefs, basic_shares, awards, p, s):
    """converts: list of (face_usd, conv_price). prefs: list of (notional_usd, conv_price_or_None, shares_if_converted_or_0).
    Returns dict: D, F, S, N (net coins), n (net coins per share), net_sats_per_share (n*1e8),
    net_reserve_usd (N*p), amplification (coins*p / (N*p)), mnav (s / (N*p/S))."""
    D, F, S = 0.0, 0.0, basic_shares + awards
    for face, cp in converts:
        if s > cp:
            S += face / cp
        else:
            D += face
    for notional, cp, shares in prefs:
        if cp is not None and s > cp:
            S += shares
        else:
            F += notional
    N = coins + (usd_assets - D - F) / p
    n = N / S
    return {'D': D, 'F': F, 'S': S, 'N': N, 'n': n, 'net_sats_per_share': n * 1e8,
            'net_reserve_usd': N * p, 'amplification': coins / N, 'mnav': s / (N * p / S)}
