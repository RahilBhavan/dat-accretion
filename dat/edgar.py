"""EDGAR access: submissions index and cached document fetch. stdlib only.

SECClient copied from ~/projects/filing-tracker/filing_tracker/sec.py: identifying UA, 0.6s
throttle, 30s timeout, 25 MB cap, raise on failure (no synthetic fallback).
"""
import json, os, time, urllib.error, urllib.request

UA = 'dat-accretion rbhavanzim@gmail.com'
RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'raw')


class SECClient:
    def __init__(self, user_agent):
        if not user_agent or '@' not in user_agent:
            raise ValueError('Provide an identifying SEC User-Agent containing your contact email')
        self.user_agent = user_agent
        self.last_request = 0.0

    def get(self, url):
        delay = 0.6 - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        self.last_request = time.monotonic()
        request = urllib.request.Request(url, headers={'User-Agent': self.user_agent, 'Accept-Encoding': 'identity'})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read(25_000_001)
            if len(content) > 25_000_000:
                raise RuntimeError('SEC response exceeded the 25 MB local limit')
            return content
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f'SEC access failed; no synthetic substitute: {url}: {exc}') from exc


client = SECClient(UA)


def filings(cik, form='8-K', since='2026-06-01'):
    """Filings of `form` (and `form`/A) filed on or after `since`, oldest first."""
    recent = json.loads(client.get(f'https://data.sec.gov/submissions/CIK{int(cik):010d}.json'))['filings']['recent']
    out = []
    for i, f in enumerate(recent['form']):
        if f in (form, form + '/A') and recent['filingDate'][i] >= since:
            acc, doc = recent['accessionNumber'][i], recent['primaryDocument'][i]
            out.append({'accession': acc, 'form': f, 'filed': recent['filingDate'][i], 'primary_doc': doc,
                        'period': recent['reportDate'][i],
                        'url': f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace("-", "")}/{doc}'})
    return sorted(out, key=lambda r: (r['filed'], r['accession']))


def cache_path(url):
    """Where fetch() caches a document: data/raw/<accession>/<doc>."""
    parts = url.rstrip('/').split('/')
    return os.path.join(RAW, parts[-2], parts[-1])


def fetch(url):
    """Document text, cached at cache_path(url). A cache hit makes no request."""
    path = cache_path(url)
    if not os.path.exists(path):
        body = client.get(url)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(body)
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', errors='replace')
