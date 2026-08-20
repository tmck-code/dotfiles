#!/usr/bin/env python3
'''skill-overseer: lease disabled skills to live sessions, reap dead ones.

State lives in ~/.claude/skill-overseer/. Skill enable/disable is expressed as
edits to <project>/.claude/settings.local.json -> skillOverrides.

Liveness is read straight off Claude Code's own transcripts: each session writes
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl continuously, so its mtime is
the session's last-activity time. A session is 'alive' if that mtime is within
the liveness window (plus the current session, always treated as alive).

Subcommands:
  init                     seed config.json from current overrides + on-disk skills
  reap                     prune dead sessions' claims, reconcile overrides
  enable  <skill> [<skill>...]   lease skill(s) to this session (enables them)
  release <skill> [<skill>...]   drop this session's lease (disables if no live lease)
  search  <query...>       rank disabled skills whose name/description match query
  status                   show alive sessions, leases, managed overrides

All commands accept --session <id> (default: auto-detect newest transcript for cwd)
and --project-dir <path> (default: $CLAUDE_PROJECT_DIR or cwd).
'''
import argparse
import datetime as dt
import glob
import json
import os
import sys

HOME = os.path.expanduser('~')
STATE_DIR = os.path.join(HOME, '.claude', 'skill-overseer')
CONFIG_PATH = os.path.join(STATE_DIR, 'config.json')
STATE_PATH = os.path.join(STATE_DIR, 'state.json')
PROJECTS_DIR = os.path.join(HOME, '.claude', 'projects')

# Skills that must never be auto-disabled, regardless of leases.
DEFAULT_KEEP_ON = [
    'skill-overseer', 'find-skills', 'write-a-skill', 'handoff',
    'code-review', 'simplify', 'verify', 'fewer-permission-prompts',
    'python-style', 'init', 'review', 'security-review',
    'yas-pr', 'yas-pr-screenshots', 'tmck-code-statusline',
    'opsx:apply', 'opsx:archive', 'opsx:propose',
]
DEFAULT_CONFIG = {
    'liveness_minutes': 30,
    # On-disk skill roots the overseer scans for descriptions (search) and tidy.
    'skill_roots': ['~/.claude/skills', '~/.agents/skills', '.claude/skills'],
    'keep_on': DEFAULT_KEEP_ON,
    # Default-off, enable-on-demand skills the overseer searches and manages.
    'pool': [],
    # Also disable on-disk skills that are enabled, not kept-on, and unleased.
    'tidy_unclaimed': True,
}


# --- small json helpers -----------------------------------------------------

def load_json(path, default):
    try:
        with open(path) as f:
            txt = f.read().strip()
        return json.loads(txt) if txt else default
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def now_iso():
    return dt.datetime.now().replace(microsecond=0).isoformat()


# --- config / state ---------------------------------------------------------

def load_config():
    cfg = load_json(CONFIG_PATH, None)
    if cfg is None:
        return dict(DEFAULT_CONFIG)
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)
    return cfg


def load_state():
    return load_json(STATE_PATH, {'projects': {}})


def project_leases(state, project):
    proj = state['projects'].setdefault(project, {})
    return proj.setdefault('claims', {})  # {skill: {session_id: iso_ts}}


# --- settings.local.json overrides -----------------------------------------

def settings_path(project):
    return os.path.join(project, '.claude', 'settings.local.json')


def load_overrides(project):
    data = load_json(settings_path(project), {})
    return data, data.get('skillOverrides', {})


def save_overrides(project, data, overrides):
    if overrides:
        data['skillOverrides'] = overrides
    else:
        data.pop('skillOverrides', None)
    save_json(settings_path(project), data)


def enable_in(overrides, skill):
    overrides.pop(skill, None)  # absence => on (default)


def disable_in(overrides, skill):
    overrides[skill] = 'off'


# --- liveness ---------------------------------------------------------------

def encode_cwd(path):
    return path.replace('/', '-')


def transcript_dir(project):
    return os.path.join(PROJECTS_DIR, encode_cwd(os.path.abspath(project)))


def alive_sessions(window_secs):
    '''All session ids (across every project) active within the window.'''
    import time
    cutoff = time.time() - window_secs
    live = set()
    for jl in glob.glob(os.path.join(PROJECTS_DIR, '*', '*.jsonl')):
        try:
            if os.path.getmtime(jl) >= cutoff:
                live.add(os.path.splitext(os.path.basename(jl))[0])
        except OSError:
            pass
    return live


def detect_session(project):
    '''Newest transcript for this project == the current session.'''
    cands = glob.glob(os.path.join(transcript_dir(project), '*.jsonl'))
    if not cands:
        return None
    newest = max(cands, key=os.path.getmtime)
    return os.path.splitext(os.path.basename(newest))[0]


# --- on-disk skill discovery -----------------------------------------------

def discover_skills(roots):
    '''Return {name: (path, description)} for every SKILL.md under roots.'''
    found = {}
    for root in roots:
        root = os.path.expanduser(root)
        for sk in glob.glob(os.path.join(root, '*', 'SKILL.md')):
            name, desc = parse_frontmatter(sk)
            name = name or os.path.basename(os.path.dirname(sk))
            found[name] = (sk, desc)
    return found


def parse_frontmatter(path):
    name = desc = ''
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except OSError:
        return name, desc
    if not lines or lines[0].strip() != '---':
        return name, desc
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if line.startswith('name:'):
            name = line.split(':', 1)[1].strip()
        elif line.startswith('description:'):
            desc = line.split(':', 1)[1].strip()
    return name, desc


# --- core reconcile ---------------------------------------------------------

def reconcile(project, session, cfg, state, verbose=True):
    window = cfg['liveness_minutes'] * 60
    alive = alive_sessions(window)
    if session:
        alive.add(session)
    keep_on = set(cfg['keep_on'])
    pool = set(cfg['pool'])
    leases = project_leases(state, project)
    data, overrides = load_overrides(project)
    actions = []

    # 1. drop leases held by dead sessions
    for skill in list(leases):
        for sid in list(leases[skill]):
            if sid not in alive:
                del leases[skill][sid]
                actions.append(f'lease dropped: {skill} <- dead session {sid[:8]}')
        if not leases[skill]:
            del leases[skill]

    # 2. enforce pool + leased skills
    for skill in pool | set(leases):
        if skill in keep_on:
            continue
        if skill in leases:  # at least one live lease
            if overrides.get(skill) == 'off':
                enable_in(overrides, skill)
                actions.append(f'enabled (leased): {skill}')
        else:
            if overrides.get(skill) != 'off':
                disable_in(overrides, skill)
                actions.append(f'disabled (unleased): {skill}')

    # 3. tidy: disable on-disk skills enabled but never leased / kept-on
    if cfg['tidy_unclaimed']:
        for skill in discover_skills(cfg['skill_roots']):
            if skill in keep_on or skill in leases or skill in pool:
                continue
            if overrides.get(skill) != 'off':
                disable_in(overrides, skill)
                pool.add(skill)
                actions.append(f'disabled (stray install): {skill}')
        cfg['pool'] = sorted(pool)

    save_overrides(project, data, overrides)
    save_json(CONFIG_PATH, cfg)
    save_json(STATE_PATH, state)
    if verbose:
        for a in actions:
            print('  ' + a)
        if not actions:
            print('  (no changes)')
    return actions


# --- subcommands ------------------------------------------------------------

def cmd_init(args, cfg, state):
    data, overrides = load_overrides(args.project_dir)
    pool = sorted(set(cfg['pool']) | {k for k, v in overrides.items() if v == 'off'})
    on_disk = set(discover_skills(cfg['skill_roots']))
    keep = sorted(set(cfg['keep_on']) | (on_disk - set(pool)))
    cfg['pool'] = pool
    cfg['keep_on'] = keep
    save_json(CONFIG_PATH, cfg)
    print(f'config seeded at {CONFIG_PATH}')
    print(f'  pool ({len(pool)}): {", ".join(pool) or "-"}')
    print(f'  keep_on ({len(keep)}): {", ".join(keep) or "-"}')


def cmd_reap(args, cfg, state):
    print(f'reap (session {(args.session or "?")[:8]}, project {args.project_dir}):')
    reconcile(args.project_dir, args.session, cfg, state)


def cmd_enable(args, cfg, state):
    reconcile(args.project_dir, args.session, cfg, state, verbose=False)
    leases = project_leases(state, args.project_dir)
    pool = set(cfg['pool'])
    data, overrides = load_overrides(args.project_dir)
    for skill in args.skills:
        leases.setdefault(skill, {})[args.session] = now_iso()
        enable_in(overrides, skill)
        pool.add(skill)
        print(f'enabled + leased: {skill}')
    cfg['pool'] = sorted(pool)
    save_overrides(args.project_dir, data, overrides)
    save_json(CONFIG_PATH, cfg)
    save_json(STATE_PATH, state)


def cmd_release(args, cfg, state):
    leases = project_leases(state, args.project_dir)
    keep_on = set(cfg['keep_on'])
    data, overrides = load_overrides(args.project_dir)
    for skill in args.skills:
        if skill in leases:
            leases[skill].pop(args.session, None)
            if not leases[skill]:
                del leases[skill]
        if skill not in leases and skill not in keep_on:
            disable_in(overrides, skill)
            print(f'released + disabled: {skill}')
        else:
            print(f'released (still leased/kept): {skill}')
    save_overrides(args.project_dir, data, overrides)
    save_json(STATE_PATH, state)


def cmd_search(args, cfg, state):
    query = ' '.join(args.query).lower()
    terms = [t for t in query.split() if t]
    _, overrides = load_overrides(args.project_dir)
    on_disk = discover_skills(cfg['skill_roots'])
    rows = []
    # on-disk skills with descriptions
    for name, (_path, desc) in on_disk.items():
        disabled = overrides.get(name) == 'off'
        hay = (name + ' ' + desc).lower()
        score = sum(hay.count(t) for t in terms)
        if score:
            rows.append((score, name, disabled, desc[:120]))
    # pooled built-ins (no on-disk file) — name-only match
    for name in cfg['pool']:
        if name in on_disk:
            continue
        score = sum(name.lower().count(t) for t in terms)
        if score:
            rows.append((score, name, overrides.get(name) == 'off', '(built-in, no description on disk)'))
    rows.sort(reverse=True)
    if not rows:
        print('no matching skills')
        return
    for score, name, disabled, desc in rows[:12]:
        flag = 'DISABLED' if disabled else 'enabled '
        print(f'[{flag}] {name}\n           {desc}')


def cmd_status(args, cfg, state):
    window = cfg['liveness_minutes'] * 60
    alive = alive_sessions(window)
    if args.session:
        alive.add(args.session)
    leases = project_leases(state, args.project_dir)
    _, overrides = load_overrides(args.project_dir)
    print(f'project: {args.project_dir}')
    print(f'current session: {(args.session or "?")[:8]}')
    print(f'alive sessions ({len(alive)}): {", ".join(s[:8] for s in sorted(alive)) or "-"}')
    print('leases:')
    for skill, sess in sorted(leases.items()):
        live = [s[:8] for s in sess if s in alive]
        print(f'  {skill}: {", ".join(live) or "(none alive)"}')
    if not leases:
        print('  (none)')
    managed = sorted(set(cfg['pool']))
    off = [s for s in managed if overrides.get(s) == 'off']
    print(f'pool off ({len(off)}): {", ".join(off) or "-"}')


COMMANDS = {
    'init': cmd_init, 'reap': cmd_reap, 'enable': cmd_enable,
    'release': cmd_release, 'search': cmd_search, 'status': cmd_status,
}


def main():
    p = argparse.ArgumentParser(prog='overseer')
    p.add_argument('command', choices=COMMANDS)
    p.add_argument('args', nargs='*')
    p.add_argument('--session')
    p.add_argument('--project-dir')
    a = p.parse_args()
    a.project_dir = os.path.abspath(
        a.project_dir or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd())
    if not a.session:
        a.session = detect_session(a.project_dir)
    # map positional args to the names each command expects
    a.skills = a.args
    a.query = a.args
    cfg, state = load_config(), load_state()
    COMMANDS[a.command](a, cfg, state)


if __name__ == '__main__':
    main()
