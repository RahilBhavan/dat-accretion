"""BitMine ETH held as a share of ETH supply, as each weekly release states it (`python -m dat.supply_share [data_dir]`).

Every BitMine release says "Bitmine's ETH holdings are X% of the ETH supply (of Y million ETH)" and, in its headline,
"Bitmine owns X% of the total ETH coin supply of Y million". This reads both from the cached release of each stated
week, requires them to agree, and writes data/bmnr_supply_share.csv and docs/bmnr-supply-share.md with a filing link per
row. The percentage is the filing's own, at the precision it prints (4.8%, 4.95%); supply is the filing's own rounded
million. `computed_pct` is ETH held / stated supply, a check only: the rounded supply limits it to about +-0.04 points.
A release without the sentence raises; nothing is carried forward or estimated. stdlib only.
"""
import html, os, re, sys
from dat import edgar
from dat.balances import read, write

FIELDS = ['week_end', 'filed', 'eth_held', 'stated_pct', 'supply_million', 'computed_pct', 'filing_url']
BODY = r'ETH holdings are (\d+(?:\.\d+)?)% of the ETH supply \(of (\d+(?:\.\d+)?) million ETH\)'
HEAD = r'owns (\d+(?:\.\d+)?)% of the total ETH coin supply of (\d+(?:\.\d+)?) million'


def text(doc):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', doc)).replace('\xa0', ' '))


def parse(doc, where):
    """(stated pct, supply in millions) as printed, both strings, from the body sentence checked against the headline."""
    t = text(doc)
    body, head = (set(re.findall(rx, t)) for rx in (BODY, HEAD))
    if len(body) != 1:
        raise ValueError(f'{where}: expected one "ETH holdings are X% of the ETH supply" sentence, found {sorted(body)}')
    if head and head != body:
        raise ValueError(f'{where}: headline {sorted(head)} disagrees with the body sentence {sorted(body)}')
    return next(iter(body))


def rows(stated, fetch=edgar.fetch):
    out = []
    for s in sorted((r for r in stated if r['firm'] == 'BMNR'), key=lambda r: r['week_end']):
        pct, supply = parse(fetch(s['filing_url']), f"{s['week_end']} {s['filing_url']}")
        out.append({'week_end': s['week_end'], 'filed': s['filed'], 'eth_held': s['coins'], 'stated_pct': pct,
                    'supply_million': supply, 'computed_pct': f"{100 * int(s['coins']) / (float(supply) * 1e6):.2f}",
                    'filing_url': s['filing_url']})
    return out


def table(rs):
    lines = ['# BitMine ETH held as a share of ETH supply, by week', '',
             "Each row is the share BitMine's own weekly 8-K release states (Exhibit 99.1), at the precision it prints, "
             'with the ETH held and the supply figure from the same release. `Computed` divides ETH held by the stated supply '
             'as a check; the supply is rounded to 0.1 million, so it can differ from the stated share by about 0.04 points. '
             'Nothing is estimated: a release without the sentence stops the build.', '',
             '| Week ending | Filed | ETH held | Stated share of supply | Supply stated (million ETH) | Computed | Filing |',
             '|---|---|---|---|---|---|---|']
    for r in rs:
        lines.append(f"| {r['week_end']} | {r['filed']} | {int(r['eth_held']):,} | {r['stated_pct']}% | {r['supply_million']} | "
                     f"{r['computed_pct']}% | [Exhibit 99.1]({r['filing_url']}) |")
    return '\n'.join(lines) + '\n'


def main(data_dir='data', docs_dir='docs'):
    rs = rows(read(os.path.join(data_dir, 'stated.csv')))
    write(os.path.join(data_dir, 'bmnr_supply_share.csv'), FIELDS, rs)
    with open(os.path.join(docs_dir, 'bmnr-supply-share.md'), 'w') as f:
        f.write(table(rs))
    print(f'{len(rs)} weeks, {rs[0]["week_end"]} {rs[0]["stated_pct"]}% to {rs[-1]["week_end"]} {rs[-1]["stated_pct"]}% of supply')
    return 0


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
