"""Guards for the dependency pins and for numbers typed by hand into the docs."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pinned():
    pins = {}
    for line in (ROOT / 'requirements-dev.txt').read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        name, sep, version = line.partition('==')
        assert sep and version, f'requirements-dev.txt line is not an exact pin: {line!r}'
        pins[name.lower()] = version
    return pins


def test_requirements_dev_pins_every_pyproject_dependency():
    pyproject = (ROOT / 'pyproject.toml').read_text()
    declared = re.findall(r'"([A-Za-z0-9_.-]+)\s*(?:[<>=!~][^"]*)?"', pyproject.split('dependencies =', 1)[1])
    names = {d.lower() for d in declared if d.lower() in ('numpy', 'pytest')}
    assert names == {'numpy', 'pytest'}, 'pyproject.toml dependency list changed; update this test and recompile'
    assert names <= pinned().keys()


def test_numpy_pin_satisfies_pyproject_floor():
    assert int(pinned()['numpy'].split('.')[0]) >= 2


def test_workflows_install_only_from_the_pinned_file():
    for wf in (ROOT / '.github' / 'workflows').glob('*.yml'):
        for line in wf.read_text().splitlines():
            if 'pip install' in line and not line.lstrip().startswith('#'):
                assert 'pip install -r requirements-dev.txt' in line, f'{wf.name}: {line.strip()}'


def test_docs_carry_no_hand_typed_pytest_count():
    typed = re.compile(r'\b\d[\d,]*\s+(?:pytest cases|offline tests|passed)\b')
    for doc in ('README.md', 'docs/overview.md'):
        hits = typed.findall((ROOT / doc).read_text())
        assert not hits, f'{doc} types a test count by hand ({hits}); the ci badge reports it'
