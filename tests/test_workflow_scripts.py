"""The refresh workflow's shell helpers, run against a fake `gh` (no network, no GitHub writes).

The fake answers each `gh` call from a table of (substring of the joined args -> JSON reply), applies `--jq` with the
real jq (as gh does), and logs every call, so the tests check which writes the scripts would make.
"""
import json
import os
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


def run(tmp_path, script, args, table):
    gh = tmp_path / 'bin' / 'gh'
    gh.parent.mkdir()
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    (tmp_path / 'table.json').write_text(json.dumps(table))
    log = tmp_path / 'calls.log'
    log.touch()
    env = dict(os.environ, PATH=f'{gh.parent}:{os.environ["PATH"]}', FAKE_GH_TABLE=str(tmp_path / 'table.json'),
               FAKE_GH_LOG=str(log), POLL_WAIT='0')
    p = subprocess.run(['bash', str(SCRIPTS / script), *args], capture_output=True, text=True, env=env, timeout=60)
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    return p, calls


# alert_issue.sh: one open issue per exact title

def test_alert_opens_an_issue_when_none_with_that_exact_title_is_open(tmp_path):
    open_issues = [{'number': 7, 'title': 'Reanchor needed'}, {'number': 8, 'title': 'Weekly refresh failed twice'}]
    p, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'https://run/1'],
                   [['issue list', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'create', '--title', 'Weekly refresh failed', '--body', 'Run: https://run/1'] in calls
    assert not any(c[:2] == ['issue', 'comment'] for c in calls)


def test_alert_comments_on_the_oldest_open_issue_with_that_title_instead_of_opening_another(tmp_path):
    open_issues = [{'number': 51, 'title': 'Weekly refresh failed'}, {'number': 42, 'title': 'Weekly refresh failed'},
                   {'number': 50, 'title': 'Reanchor needed'}]
    p, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'https://run/2'],
                   [['issue list', open_issues]])
    assert p.returncode == 0, p.stderr
    assert ['issue', 'comment', '42', '--body', 'Failed again: https://run/2'] in calls
    assert not any(c[:2] == ['issue', 'create'] for c in calls)


def test_alert_lists_open_issues_rather_than_searching(tmp_path):
    # the search index lags; a listing does not, so back-to-back failures cannot both open an issue
    _, calls = run(tmp_path, 'alert_issue.sh', ['Weekly refresh failed', 'u'], [['issue list', []]])
    listing = next(c for c in calls if c[:2] == ['issue', 'list'])
    assert '--search' not in listing and listing[listing.index('--state') + 1] == 'open'


# drop_unapproved_pr_runs.sh: delete only the zero-job pull_request run of this branch and commit

REPO, BRANCH, SHA = 'o/r', 'refresh/2026-10-27', 'abc123'


def runs_reply(*runs):
    return {'workflow_runs': [{'id': i, 'status': s} for i, s in runs]}


def test_drop_deletes_the_zero_job_run_and_keeps_a_run_that_ran_jobs(tmp_path):
    table = [['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'), (222, 'completed'))],
             ['runs/111/jobs', {'total_count': 0}], ['runs/222/jobs', {'total_count': 1}],
             ['runs/111 --jq', {'conclusion': 'failure'}]]
    p, calls = run(tmp_path, 'drop_unapproved_pr_runs.sh', [REPO, BRANCH, SHA], table)
    assert p.returncode == 0, p.stderr
    assert ['api', '-X', 'DELETE', 'repos/o/r/actions/runs/111'] in calls
    assert not any('runs/222' in c[-1] and 'DELETE' in c for c in calls)
    assert 'deleted unapproved pull_request CI run 111 (failure, 0 jobs)' in p.stdout
    assert 'kept pull_request CI run 222: it ran 1 job(s)' in p.stdout


def test_drop_asks_only_for_pull_request_runs_of_this_branch_and_commit(tmp_path):
    _, calls = run(tmp_path, 'drop_unapproved_pr_runs.sh', [REPO, BRANCH, SHA],
                   [['actions/workflows/ci.yml/runs', runs_reply()]])
    url = next(c[1] for c in calls if 'actions/workflows/ci.yml/runs' in c[1])
    assert f'event=pull_request&branch={BRANCH}&head_sha={SHA}' in url


def test_drop_never_fails_the_step_when_the_delete_is_refused(tmp_path):
    table = [['-X DELETE', 'FAIL'], ['actions/workflows/ci.yml/runs', runs_reply((111, 'completed'))],
             ['runs/111/jobs', {'total_count': 0}], ['runs/111 --jq', {'conclusion': 'failure'}]]
    p, _ = run(tmp_path, 'drop_unapproved_pr_runs.sh', [REPO, BRANCH, SHA], table)
    assert p.returncode == 0
    assert 'could not delete pull_request CI run 111' in p.stdout


def test_drop_gives_up_quietly_on_a_run_that_never_completes(tmp_path):
    p, calls = run(tmp_path, 'drop_unapproved_pr_runs.sh', [REPO, BRANCH, SHA],
                   [['actions/workflows/ci.yml/runs', runs_reply((111, 'waiting'))]])
    assert p.returncode == 0
    assert not any('DELETE' in c for c in calls)
    assert 'still not completed' in p.stdout
