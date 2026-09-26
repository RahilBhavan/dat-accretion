import datetime as dt, json
import check


def ok(data_dir):
    return [check.result('a', '1 vs 1', True), check.result('b', '2 vs 2', True)]


def bad(data_dir):
    return [check.result('c', '1 vs 9', False)]


def offline(data_dir):
    raise OSError('network down')


def test_all_pass_exit_0_and_shape(tmp_path):
    assert check.main(str(tmp_path), [ok]) == 0
    d = json.loads((tmp_path / 'check.json').read_text())
    assert set(d) == {'status', 'run_at', 'checks'} and d['status'] == 'pass'
    assert dt.datetime.strptime(d['run_at'], '%Y-%m-%dT%H:%M:%SZ')
    assert d['checks'] == [{'name': 'a', 'compared': '1 vs 1', 'ok': True}, {'name': 'b', 'compared': '2 vs 2', 'ok': True}]


def test_one_failure_fails(tmp_path):
    assert check.main(str(tmp_path), [ok, bad]) == 1
    assert json.loads((tmp_path / 'check.json').read_text())['status'] == 'fail'


def test_network_error_is_a_failure_not_a_skip(tmp_path):
    d = check.run(str(tmp_path), [ok, offline])
    assert d['status'] == 'fail'
    assert d['checks'][-1] == {'name': 'offline', 'compared': 'error: OSError: network down', 'ok': False}


def test_no_checks_is_not_a_pass(tmp_path):
    assert check.run(str(tmp_path), [])['status'] == 'fail'


def test_residuals_offline_all_pass():
    rs = check.residuals('data')
    assert len(rs) >= 8 and all(r['ok'] for r in rs)


def test_crash_still_writes_fail_record(tmp_path):
    def boom(data_dir):
        raise KeyboardInterrupt  # escapes run()'s per-check except, like an unexpected crash
    try:
        check.main(str(tmp_path), [boom])
    except KeyboardInterrupt:
        pass
    d = json.loads((tmp_path / 'check.json').read_text())
    assert d['status'] == 'fail' and d['checks'][0]['name'] == 'check.py'
