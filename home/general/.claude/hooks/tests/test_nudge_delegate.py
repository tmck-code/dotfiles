'''Tests for nudge-delegate.py, run as a subprocess with JSON on stdin.'''
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / 'nudge-delegate.py'
SHIPPED = Path(__file__).resolve().parents[4] / 'linux' / '.claude' / 'delegate-routing.json'

FOUR = ['main', 'orchestrator', 'spec-implementer', 'spec-author']
BASH_READ = {'tool': 'Bash', 'kind': 'bashRead', 'maxLines': 100, 'maxBytes': 20000,
             'action': 'deny', 'appliesTo': FOUR, 'hint': 'grep and read a range'}


class Env:
    def __init__(self, root: Path):
        self.root = root
        self.config = root / 'config'
        self.project = root / 'project'
        (self.project / '.claude').mkdir(parents=True)
        self.config.mkdir()

    def rules(self, rules: list) -> None:
        (self.project / '.claude' / 'delegate-routing.json').write_text(
            json.dumps({'rules': rules}))

    def run(self, payload: dict, cwd: Path = None) -> dict:
        proc = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(payload),
            capture_output=True, text=True, cwd=cwd or self.root,
            env={'HOME': str(self.root), 'CLAUDE_CONFIG_DIR': str(self.config),
                 'CLAUDE_PROJECT_DIR': str(self.project), 'PATH': '/usr/bin:/bin'},
        )
        assert proc.returncode == 0, proc.stderr
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def bash(self, command: str, **extra) -> dict:
        return self.run({'tool_name': 'Bash', 'tool_input': {'command': command}, **extra})

    def state_files(self) -> list:
        return sorted((self.config / 'hooks' / 'state').glob('calls-*.json'))


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def decision(out: dict) -> str:
    return out.get('hookSpecificOutput', {}).get('permissionDecision', '')


def text(out: dict) -> str:
    spec = out.get('hookSpecificOutput', {})
    return spec.get('permissionDecisionReason') or spec.get('additionalContext', '')


def make_file(root: Path, name: str, lines: int, width: int = 10) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join('x' * width + '\n' for _ in range(lines)))
    return path


# --- caller identity -------------------------------------------------------------

REGEX_RULE = {'tool': 'Bash', 'match': 'pytest', 'hint': 'run tests elsewhere'}


def test_main_matches_default_rule(env):
    env.rules([REGEX_RULE])
    assert decision(env.bash('pytest -q')) == 'allow'


@pytest.mark.parametrize('agent_type', ['worker', 'general-purpose', 'Explore', 'orchestrator'])
def test_subagent_silent_without_applies_to(env, agent_type):
    env.rules([REGEX_RULE])
    assert env.bash('pytest -q', agent_id='a1', agent_type=agent_type) == {}


def test_orchestrator_matches_when_listed(env):
    env.rules([{**REGEX_RULE, 'appliesTo': ['orchestrator']}])
    assert decision(env.bash('pytest', agent_id='a1', agent_type='orchestrator')) == 'allow'
    assert env.bash('pytest') == {}  # main not listed
    assert env.bash('pytest', agent_id='a1', agent_type='worker') == {}


def test_unknown_agent_type_matches_nothing(env):
    env.rules([{**REGEX_RULE, 'appliesTo': ['main', 'orchestrator']}])
    assert env.bash('pytest', agent_id='a1', agent_type='') == {}
    assert env.bash('pytest', agent_id='a1') == {}


# --- deny on regex rules ---------------------------------------------------------

def test_regex_rule_deny(env):
    env.rules([{**REGEX_RULE, 'action': 'deny'}])
    out = env.bash('pytest -q')
    assert out['hookSpecificOutput']['hookEventName'] == 'PreToolUse'
    assert decision(out) == 'deny'
    assert 'run tests elsewhere' in text(out)


def test_orchestrator_scratch_write_allowed_and_code_denied(env):
    rules = json.loads(SHIPPED.read_text())['rules']
    env.rules([r for r in rules if r.get('tool') != 'Read'])
    agent = {'agent_id': 'a1', 'agent_type': 'orchestrator'}
    ok = env.run({'tool_name': 'Write', 'tool_input': {'file_path': '/r/.scratch/master/plan.md'}, **agent})
    bad = env.run({'tool_name': 'Write', 'tool_input': {'file_path': 'src/x.py'}, **agent})
    bad_edit = env.run({'tool_name': 'Edit', 'tool_input': {'file_path': '/r/src/x.py'}, **agent})
    assert decision(ok) == ''
    assert decision(bad) == 'deny'
    assert decision(bad_edit) == 'deny'
    assert 'worker' in text(bad)


def test_main_write_not_denied_by_orchestrator_rule(env):
    rules = json.loads(SHIPPED.read_text())['rules']
    env.rules(rules)
    out = env.run({'tool_name': 'Write', 'tool_input': {'file_path': 'src/x.py'}})
    assert decision(out) == 'allow'  # existing nudge, not deny


# --- bashRead --------------------------------------------------------------------

@pytest.fixture
def big(env):
    env.rules([BASH_READ])
    return make_file(env.root, 'big.txt', 150)


@pytest.fixture
def small(env):
    env.rules([BASH_READ])
    return make_file(env.root, 'small.txt', 20)


@pytest.mark.parametrize('template, fires', [
    ('cat {big}', True),
    ('cat {small}', False),
    ('head -n 150 {big}', True),
    ('head -n 50 {big}', False),
    ('head -120 {big}', True),
    ('head {big}', False),
    ('tail -n 120 {big}', True),
    ('tail -n 20 {big}', False),
    ("sed -n '1,120p' {big}", True),
    ("sed -n '10,20p' {big}", False),
    ("sed -n '5,+119p' {big}", True),
    ('cat {small} {small} {small} {small} {small} {small}', True),
    ('echo hi; cat {big}', True),
    ('true && cat {big}', True),
    ('cat {big} | grep x', False),
    ('cat {big} > /tmp/out.txt', False),
    ('cat {big} >> /tmp/out.txt', False),
    ('cat {big} 2>/dev/null', True),
    ('cat > {small} <<EOF\nhello\nEOF', False),
    ('cat <<EOF\ncat {big}\nEOF', False),
    ('cat /does/not/exist', False),
    ("cat 'unterminated", False),
    ('echo $(cat {big})', False),
])
def test_bash_read(env, big, small, template, fires):
    out = env.bash(template.format(big=big, small=small))
    assert (decision(out) == 'deny') is fires


def test_bash_read_names_file_and_size(env, big):
    out = env.bash(f'cat {big}')
    assert str(big) in text(out)
    assert '150 lines' in text(out)
    assert 'grep and read a range' in text(out)


def test_bash_read_byte_arm(env):
    env.rules([BASH_READ])
    wide = make_file(env.root, 'wide.txt', 5, width=5000)
    assert decision(env.bash(f'cat {wide}')) == 'deny'


def test_bash_read_binary_suffix_skipped(env):
    env.rules([BASH_READ])
    path = env.root / 'img.png'
    path.write_bytes(b'\n' * 500)
    assert env.bash(f'cat {path}') == {}


def test_bash_read_cd_relative(env):
    env.rules([BASH_READ])
    make_file(env.root, 'sub/f.txt', 150)
    out = env.bash(f'cd {env.root}/sub && cat f.txt')
    assert decision(out) == 'deny'
    assert env.bash('cat f.txt') == {}  # not under hook cwd


def test_bash_read_tool_input_cwd(env):
    env.rules([BASH_READ])
    make_file(env.root, 'sub/f.txt', 150)
    out = env.run({'tool_name': 'Bash',
                   'tool_input': {'command': 'cat f.txt', 'cwd': str(env.root / 'sub')}})
    assert decision(out) == 'deny'


def test_bash_read_nudge_action(env, big):
    env.rules([{**BASH_READ, 'action': 'nudge'}])
    assert decision(env.bash(f'cat {big}')) == 'allow'


def test_bash_read_applies_to_subagents(env, big):
    assert decision(env.bash(f'cat {big}', agent_id='a', agent_type='orchestrator')) == 'deny'
    assert env.bash(f'cat {big}', agent_id='a', agent_type='worker') == {}


# --- callBudget ------------------------------------------------------------------

BUDGET = {'kind': 'callBudget', 'appliesTo': ['orchestrator'], 'maxCalls': 3,
          'hint': 'made {count} calls'}


def orch(env, command='ls', session='s1', agent_id='a1'):
    return env.bash(command, session_id=session, agent_id=agent_id, agent_type='orchestrator')


def test_budget_fires_at_n_and_2n_only(env):
    env.rules([BUDGET])
    results = [orch(env) for _ in range(7)]
    fired = [i + 1 for i, out in enumerate(results) if out]
    assert fired == [3, 6]
    assert decision(results[2]) == 'allow'
    assert 'made 3 calls' in text(results[2])
    assert 'made 6 calls' in text(results[5])


def test_budget_counters_are_per_caller(env):
    env.rules([BUDGET])
    for _ in range(2):
        orch(env, agent_id='a1')
    assert orch(env, agent_id='a2') == {}
    assert decision(orch(env, agent_id='a1')) == 'allow'
    assert len(env.state_files()) == 2


def test_budget_ignores_callers_not_listed(env):
    env.rules([BUDGET])
    for _ in range(5):
        assert env.bash('ls', session_id='s', agent_id='a', agent_type='worker') == {}
        assert env.bash('ls', session_id='s') == {}
    assert env.state_files() == []


def test_budget_tolerates_corrupt_state(env):
    env.rules([BUDGET])
    orch(env)
    state = env.state_files()[0]
    state.write_text('{not json')
    assert orch(env) == {}
    assert json.loads(state.read_text()) == {'count': 1}


def test_budget_with_nudge_combines(env):
    env.rules([{**REGEX_RULE, 'appliesTo': ['orchestrator']}, BUDGET])
    orch(env, 'pytest')
    orch(env, 'pytest')
    out = orch(env, 'pytest')
    assert decision(out) == 'allow'
    assert 'run tests elsewhere' in text(out)
    assert 'made 3 calls' in text(out)


def test_budget_with_deny_denies_and_combines(env):
    env.rules([{**REGEX_RULE, 'action': 'deny', 'appliesTo': ['orchestrator']}, BUDGET])
    orch(env, 'ls')
    orch(env, 'ls')
    out = orch(env, 'pytest')
    assert decision(out) == 'deny'
    assert 'run tests elsewhere' in text(out)
    assert 'made 3 calls' in text(out)


def test_budget_before_other_rule_does_not_stop_it(env):
    env.rules([BUDGET, {**REGEX_RULE, 'action': 'deny', 'appliesTo': ['orchestrator']}])
    orch(env)
    orch(env)
    out = orch(env, 'pytest')
    assert decision(out) == 'deny'
    assert 'made 3 calls' in text(out)


# --- hook robustness and shipped table ------------------------------------------

def test_bad_stdin_is_silent(env):
    proc = subprocess.run([sys.executable, str(HOOK)], input='nope',
                          capture_output=True, text=True)
    assert proc.returncode == 0 and proc.stdout == ''


KNOWN_KEYS = {'tool', 'match', 'agent', 'hint', 'action', 'appliesTo', 'kind',
              'maxLines', 'maxBytes', 'maxCalls'}
KNOWN_TOOLS = {'Bash', 'Edit', 'Write', 'Read', 'Grep', 'Glob'}


def test_shipped_table_shapes():
    rules = json.loads(SHIPPED.read_text())['rules']
    assert rules
    for rule in rules:
        assert set(rule) <= KNOWN_KEYS, rule
        assert rule.get('action', 'nudge') in ('nudge', 'deny')
        assert isinstance(rule.get('appliesTo', ['main']), list)
        tools = rule.get('tool', 'Bash')
        assert set([tools] if isinstance(tools, str) else tools) <= KNOWN_TOOLS
        kind = rule.get('kind')
        if kind == 'callBudget':
            assert isinstance(rule['maxCalls'], int) and rule['maxCalls'] > 0
            assert '{count}' in rule['hint']
            assert 'tool' not in rule
        elif kind == 'bashRead':
            assert rule['tool'] == 'Bash'
            assert 'maxLines' in rule or 'maxBytes' in rule
        elif kind is None:
            assert 'match' in rule or 'maxLines' in rule or 'maxBytes' in rule
        else:
            pytest.fail(f'unknown kind {kind}')


def test_shipped_orchestrator_rules(env):
    rules = json.loads(SHIPPED.read_text())['rules']
    kinds = [r.get('kind') for r in rules]
    assert 'bashRead' in kinds and 'callBudget' in kinds
    budget = next(r for r in rules if r.get('kind') == 'callBudget')
    assert budget['maxCalls'] == 30
    assert set(budget['appliesTo']) == {'orchestrator', 'spec-implementer', 'spec-author'}
