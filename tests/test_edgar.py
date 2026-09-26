import io, urllib.error
import pytest
from dat import edgar


def fake(codes, monkeypatch):
    """urlopen that raises HTTPError for each code in turn, then returns b'ok'."""
    calls = []
    def urlopen(req, timeout):
        calls.append(req.full_url)
        if len(calls) <= len(codes):
            raise urllib.error.HTTPError(req.full_url, codes[len(calls) - 1], 'x', {}, io.BytesIO())
        return io.BytesIO(b'ok')
    monkeypatch.setattr(edgar.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(edgar.time, 'sleep', lambda s: None)
    return calls


def test_retries_503_then_succeeds(monkeypatch):
    calls = fake([503, 429], monkeypatch)
    assert edgar.SECClient(edgar.UA).get('https://www.sec.gov/x') == b'ok'
    assert len(calls) == 3


def test_gives_up_after_backoff(monkeypatch):
    calls = fake([503] * 4, monkeypatch)
    with pytest.raises(RuntimeError, match='503'):
        edgar.SECClient(edgar.UA).get('https://www.sec.gov/x')
    assert len(calls) == 4


def test_404_fails_at_once(monkeypatch):
    calls = fake([404], monkeypatch)
    with pytest.raises(RuntimeError, match='404'):
        edgar.SECClient(edgar.UA).get('https://www.sec.gov/x')
    assert len(calls) == 1
