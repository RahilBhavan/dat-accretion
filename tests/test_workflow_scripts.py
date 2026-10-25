"""The refresh workflow's shell helpers, run against a fake `gh` (no network, no GitHub writes).

The fake answers each `gh` call from a table of (substring of the joined args -> JSON reply), applies `--jq` with the
real jq (as gh does), and logs every call, so the tests check which writes the scripts would make.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.github' / 'scripts'
pytestmark = pytest.mark.skipif(not (shutil.which('bash') and shutil.which('jq')), reason='needs bash and jq')

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, subprocess, sys
args = sys.argv[1:]
joined = ' '.join(args)
with open(os.environ['FAKE_GH_LOG'], 'a') as f:
    f.write(json.dumps(args) + '\n')
for key, reply in json.load(open(os.environ['FAKE_GH_TABLE'])):
    if key in joined:
        if reply == 'FAIL':
            sys.exit(1)
        out = json.dumps(reply)
        if '--jq' in args:
            out = subprocess.run(['jq', '-r', args[args.index('--jq') + 1]], input=out, capture_output=True,
                                 text=True, check=True).stdout
        sys.stdout.write(out)
        sys.exit(0)
sys.exit(0)   # writes (comment, create, DELETE) succeed silently unless the table says FAIL
'''


def run(tmp_path, script, args, table, env_extra=None):
    gh = tmp_path / 'bin' / 'gh'
    gh.parent.mkdir()
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    (tmp_path / 'table.json').write_text(json.dumps(table))
    log = tmp_path / 'calls.log'
    log.touch()
    env = dict(os.environ, PATH=f'{gh.parent}:{os.environ["PATH"]}', FAKE_GH_TABLE=str(tmp_path / 'table.json'),
               FAKE_GH_LOG=str(log), POLL_WAIT='0', **(env_extra or {}))
    p = subprocess.run(['bash', str(SCRIPTS / script), *args], capture_output=True, text=True, env=env, timeout=60)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    return p, calls


# alert_issue.sh: one open issue per exact title

def test_alert_opens_an_issue_when_none_with_that_exact_title_is_open(tmp_path):
    open_issues = [{'number': 7, 'title': 'Reanchor needed'}, {'number': 8, 'title': 'Weekly refresh failed twice'}]
    p, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'https://run/1'],
                   [['issues?state=open', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'create', '--title', 'Weekly refresh failed', '--body', 'Run: https://run/1'] in calls
    assert not any(c[:2] == ['issue', 'comment'] for c in calls)


def test_alert_comments_on_the_oldest_open_issue_with_that_title_instead_of_opening_another(tmp_path):
    open_issues = [{'number': 51, 'title': 'Weekly refresh failed'}, {'number': 42, 'title': 'Weekly refresh failed'},
                   {'number': 50, 'title': 'Reanchor needed'}]
    p, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'https://run/2'],
                   [['issues?state=open', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'comment', '42', '--body', 'Failed again: https://run/2'] in calls
    assert not any(c[:2] == ['issue', 'create'] for c in calls)


def test_alert_pages_through_open_issues_rather_than_searching(tmp_path):
    # the search index lags; a listing does not, so back-to-back failures cannot both open an issue
    _, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'u'], [['issues?state=open', []]])
    listing = next(c for c in calls if c[:1] == ['api'])
    assert '--paginate' in listing and 'state=open' in listing[-1]
    assert not any('--search' in c for c in calls)


def test_alert_finds_an_issue_beyond_the_first_200(tmp_path):
    open_issues = [{'number': n, 'title': f'other {n}'} for n in range(1, 251)]
    open_issues.append({'number': 251, 'title': 'Weekly refresh failed'})
    p, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'u'], [['issues?state=open', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'comment', '251', '--body', 'Failed again: u'] in calls
    assert not any(c[:2] == ['issue', 'create'] for c in calls)


def test_alert_ignores_pull_requests_and_handles_quotes_in_the_title(tmp_path):
    title = 'Weekly "refresh" failed'
    open_issues = [{'number': 3, 'title': title, 'pull_request': {}}, {'number': 9, 'title': title}]
    p, calls = run(tmp_path, 'alert_issue.sh', [title, 'u'], [['issues?state=open', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'comment', '9', '--body', 'Failed again: u'] in calls


# drop_unapproved_pr_runs.sh: delete only the zero-job pull_request run of this branch and commit

REPO, BRANCH, SHA, PR = 'o/r', 'refresh/2026-10-27', 'abc123', 'https://github.com/o/r/pull/9'
CLOSED = '2026-10-27T14:30:00Z'
AFTER = '2026-10-27T14:30:02Z'


def runs_reply(*runs):
    return {'workflow_runs': [{'id': i, 'status': s} for i, s in runs]}


def drop(tmp_path, table, closed=CLOSED):
    table = [['pr view', {'closedAt': closed}], *table]
    return run(tmp_path, 'drop_unapproved_pr_runs.sh', [REPO, BRANCH, SHA, PR], table)


def test_drop_deletes_the_zero_job_run_and_keeps_a_run_that_ran_jobs(tmp_path):
    table = [['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'), (222, 'completed'))],
             ['runs/111/jobs', {'total_count': 0}], ['runs/222/jobs', {'total_count': 1}],
             ['runs/111 --jq', {'conclusion': 'failure', 'updated_at': AFTER}]]
    p, calls = drop(tmp_path, table)
    assert p.returncode == 0, p.stderr
    assert ['api', '-X', 'DELETE', 'repos/o/r/actions/runs/111'] in calls
    assert not any('runs/222' in c[-1] and 'DELETE' in c for c in calls)
    assert 'deleted unapproved pull_request CI run 111 (failure, 0 jobs)' in p.stdout
    assert 'kept pull_request CI run 222: it ran 1 job(s)' in p.stdout


def test_drop_keeps_a_startup_failure_run_because_it_is_evidence_of_a_broken_ci_yml(tmp_path):
    table = [['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'))], ['runs/111/jobs', {'total_count': 0}],
             ['runs/111 --jq', {'conclusion': 'startup_failure', 'updated_at': AFTER}]]
    p, calls = drop(tmp_path, table)
    assert p.returncode == 0
    assert not any('DELETE' in c for c in calls)
    assert 'startup_failure' in p.stdout


def test_drop_keeps_a_run_that_concluded_before_the_pr_closed(tmp_path):
    table = [['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'))], ['runs/111/jobs', {'total_count': 0}],
             ['runs/111 --jq', {'conclusion': 'failure', 'updated_at': '2026-10-27T14:00:00Z'}]]
    p, calls = drop(tmp_path, table)
    assert not any('DELETE' in c for c in calls)
    assert 'before the PR closed' in p.stdout


def test_drop_deletes_nothing_when_the_pr_has_not_closed(tmp_path):
    table = [['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'))], ['runs/111/jobs', {'total_count': 0}],
             ['runs/111 --jq', {'conclusion': 'failure', 'updated_at': AFTER}]]
    p, calls = drop(tmp_path, table, closed=None)
    assert p.returncode == 0
    assert not any('DELETE' in c for c in calls)
    assert 'warning' in p.stdout


def test_drop_asks_only_for_pull_request_runs_of_this_branch_and_commit(tmp_path):
    _, calls = drop(tmp_path, [['actions/workflows/ci.yml/runs', runs_reply()]])
    url = next(c[1] for c in calls if 'actions/workflows/ci.yml/runs' in c[1])
    assert f'event=pull_request&branch={BRANCH}&head_sha={SHA}' in url


def test_drop_never_fails_the_step_when_the_delete_is_refused(tmp_path):
    table = [['-X DELETE', 'FAIL'], ['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'))],
             ['runs/111/jobs', {'total_count': 0}], ['runs/111 --jq', {'conclusion': 'failure', 'updated_at': AFTER}]]
    p, _ = drop(tmp_path, table)
    assert p.returncode == 0
    assert 'could not delete pull_request CI run 111' in p.stdout


def test_drop_warns_and_still_exits_0_when_the_list_call_fails(tmp_path):
    p, calls = drop(tmp_path, [['actions/workflows/ci.yml/runs', 'FAIL']])
    assert p.returncode == 0
    assert 'warning: could not list pull_request CI runs' in p.stdout
    assert sum('ci.yml/runs' in c[1] for c in calls if c[:1] == ['api']) == 6   # retried, never silent
    assert not any('DELETE' in c for c in calls)


def test_drop_gives_up_quietly_on_a_run_that_never_completes(tmp_path):
    p, calls = drop(tmp_path, [['actions/workflows/ci.yml/runs', runs_reply((111, 'waiting'))]])
    assert p.returncode == 0
    assert not any('DELETE' in c for c in calls)
    assert 'still not completed' in p.stdout


# pages_url.sh: the live URL must not depend on the event payload (a `schedule` event has no `repository` object)

def test_pages_url_uses_the_api_html_url_so_a_custom_domain_works(tmp_path):
    p, calls = run(tmp_path, 'pages_url.sh', ['o/r'], [['repos/o/r/pages', {'html_url': 'https://example.com/dat'}]])
    assert p.stdout == 'https://example.com/dat/\n'
    assert ['api', 'repos/o/r/pages', '--jq', '.html_url'] in calls


def test_pages_url_falls_back_to_github_repository_when_the_api_is_refused(tmp_path):
    p, _ = run(tmp_path, 'pages_url.sh', ['RahilBhavan/dat-accretion'], [['/pages', 'FAIL']])
    assert p.returncode == 0
    assert p.stdout == 'https://RahilBhavan.github.io/dat-accretion/\n'


def test_pages_url_is_right_with_no_event_payload_at_all(tmp_path):
    # a schedule run: GITHUB_EVENT_PATH holds no `repository`, and the script reads nothing from it
    event = tmp_path / 'event.json'
    event.write_text(json.dumps({'schedule': '0 14 * * 2'}))
    p, _ = run(tmp_path, 'pages_url.sh', ['RahilBhavan/dat-accretion'], [['/pages', 'FAIL']],
               env_extra={'GITHUB_EVENT_PATH': str(event), 'GITHUB_REPOSITORY': 'RahilBhavan/dat-accretion'})
    assert p.stdout == 'https://RahilBhavan.github.io/dat-accretion/\n'
    assert '//\n' not in p.stdout.replace('https://', '')


def test_pages_url_rejects_a_repository_without_an_owner(tmp_path):
    p, _ = run(tmp_path, 'pages_url.sh', ['dat-accretion'], [])
    assert p.returncode != 0


def test_refresh_workflow_builds_the_site_url_from_github_repository_only():
    text = (ROOT / '.github' / 'workflows' / 'refresh.yml').read_text()
    assert 'github.event.repository' not in text
    assert 'pages_url.sh "${{ github.repository }}"' in text


# verify_published.sh: the CDN keeps a cached CSV for up to 10 minutes

def test_verify_published_waits_out_the_cdns_ten_minute_cache():
    text = (SCRIPTS / 'verify_published.sh').read_text()
    retries = int(re.search(r'RETRIES:-(\d+)', text).group(1))
    wait = int(re.search(r'WAIT:-(\d+)', text).group(1))
    assert (retries - 1) * wait >= 11 * 60
    assert '?commit=' not in text and 'try=' not in text   # a query string does not bust the Pages CDN
    yml = (ROOT / '.github' / 'workflows' / 'refresh.yml').read_text()
    publish = re.search(r'id: publish\n(?:.*\n)*?\s+timeout-minutes: (\d+)', yml)
    assert int(publish.group(1)) * 60 >= (retries - 1) * wait + 10 * 60   # Pages run (<= 10 min) + the retry window


def test_refresh_step_timeouts_fit_inside_the_job_timeout():
    yml = (ROOT / '.github' / 'workflows' / 'refresh.yml').read_text()
    steps = sum(int(m) for m in re.findall(r'^        timeout-minutes: (\d+)', yml, re.M))
    job = int(re.search(r'^    timeout-minutes: (\d+)', yml, re.M).group(1))
    assert steps < job


def test_verify_published_retries_past_a_stale_copy_then_passes(tmp_path):
    repo = tmp_path / 'repo'
    (repo / 'data').mkdir(parents=True)
    (repo / 'data' / 'a.csv').write_text('x\n1\n')
    git = ['git', '-C', str(repo)]
    subprocess.run([*git, 'init', '-q'], check=True)
    subprocess.run([*git, '-c', 'user.name=t', '-c', 'user.email=t@t', 'add', '.'], check=True)
    subprocess.run([*git, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x'], check=True)
    sha = subprocess.run([*git, 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    curl = tmp_path / 'bin' / 'curl'
    curl.parent.mkdir()
    curl.write_text('#!/usr/bin/env bash\nc=$(cat "$COUNT" 2>/dev/null || echo 0); echo $((c+1)) > "$COUNT"\n'
                    'out=$3; if [ "$c" -lt 2 ]; then printf "x\\n0\\n" > "$out"; else printf "x\\n1\\n" > "$out"; fi\n')
    curl.chmod(0o755)
    env = dict(os.environ, PATH=f'{curl.parent}:{os.environ["PATH"]}', COUNT=str(tmp_path / 'count'), RETRIES='5', WAIT='0')
    p = subprocess.run(['bash', str(SCRIPTS / 'verify_published.sh'), 'https://x/', sha], cwd=repo, capture_output=True,
                       text=True, env=env, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert 'attempt 2: live differs' in p.stdout and 'published: all 1 CSVs' in p.stdout
