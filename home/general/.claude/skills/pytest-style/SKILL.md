---
name: pytest-style
description: Write pytest tests for this repo — correct structure, no unnecessary mocking, xdist-safe, consistent setup/result/expected/assert shape. Use when writing or editing test files, adding test coverage, or reviewing tests for style.
---

# Pytest Style

## Rules

### File layout

- Test files live in `test/`.
- Shared utilities go in `test/helper.py` — import from there, not from conftest.
- `test/conftest.py` holds only pytest fixtures (e.g. `tmp_home`, `strip_ansi`).
- Never create a new conftest; extend the existing one.

### helper.py

- Put any function used by more than one test file in `test/helper.py`.
- Name helpers after what they build or return, not after the test that first needed them.
- No fixtures in helper.py — only plain functions.

### Grouping

- Group related tests into a class when they test the same function or a closely related family of behaviours.
- Name classes `Test<Subject>` (e.g., `TestFmtTok`, `TestSessionCost`).
- Do not group unrelated tests into a class just to have a class.
- Module-level tests are fine when there is only one or two and no natural grouping.

### Test names

- Name tests after the behaviour they assert.
  - Good: `test_returns_zero_for_empty_log`, `test_stale_rows_pruned`
  - Bad: `test_3_4_empty_log`, `test_feature_REQ042`
- No numbers in test function names.
- No spec IDs, ticket numbers, or section labels in names.

### Test body shape

Every test follows this order — no exceptions, no skipping steps:

```python
def test_<behaviour>(self):
    # setup
    html = '<p>hello</p>'

    # run
    result = parse(html)

    # expected
    expected = 'hello'

    # assert
    assert result == expected
```

- One blank line between each section.
- `result` holds the actual value; `expected` holds the expected value.
- Put `result` before `expected` in the assert: `assert result == expected`.
- For void calls being tested for side effects, omit `result`/`expected` and assert directly.

### Assertions

- Compare whole objects, not indexes or attribute extractions.

  ```python
  # good
  result = list(chunk_daterange(start, end, days=7))
  expected = [
      (datetime(2020, 1, 1), datetime(2020, 1, 8)),
      (datetime(2020, 1, 8), datetime(2020, 1, 15)),
  ]
  assert result == expected

  # bad
  assert result[0][0] == datetime(2020, 1, 1)
  assert result[1][1] == datetime(2020, 1, 15)
  ```

- When asserting on multi-line output, build the full expected string, not fragments.
- Use `assert x in y` only when the test intentionally checks membership, not as a shortcut for incomplete comparison.

### Mocking

- Do not mock real interactions — file I/O, subprocess calls, class methods that contain logic.
- Acceptable to monkeypatch:
  - Constants or module-level variables that control thresholds (e.g., `sl.TokenRate.WINDOW`).
  - Time (`time.time`, `datetime.now`) using a minimal stub class or `monkeypatch.setattr`.
  - `sl.HOME` via the `tmp_home` fixture so tests never touch the real `$HOME`.
- The test should exercise real code paths. If you feel the need to mock a method body, restructure the test or the production code instead.

### Filesystem and isolation (xdist safety)

- Tests must not share mutable state. No module-level variables written by tests.
- Use `tmp_path` (or the `tmp_home` fixture) for any filesystem writes.
- Never hardcode paths that could collide across workers.
- Tests must pass in any order and in parallel.
- Do not use `@pytest.mark.serial` unless you can justify why isolation is structurally impossible.

### Comments

- No banner comments (`# ===== Section =====` etc.).
- Only add a comment when the why is non-obvious — a hidden constraint, a workaround, a subtle invariant.
- A docstring on a test is acceptable when the behaviour being tested is subtle; keep it to one short line.

### Fixtures

- Define fixtures in `conftest.py`, not in individual test files.
- Prefer `monkeypatch` over class-level setup/teardown.
- Keep fixture scope as narrow as possible (function scope is the default and usually correct).

### Style

- Single quotes throughout (strings, docstrings).
- No type annotations required on test functions, but add them on helpers in `helper.py`.
- Vertical kwarg alignment is fine; ruff format is excluded from `test/` for this reason.

## Checklist before declaring done

- [ ] No new mocks of real logic (only constants/time/HOME)
- [ ] Related tests grouped into a `Test<Subject>` class
- [ ] Shared helpers in `test/helper.py`, not duplicated inline
- [ ] Every test: setup → result → expected → assert shape
- [ ] Whole-object comparison, not index access
- [ ] No numbers in test function names
- [ ] No banner comments
- [ ] `tmp_path` / `tmp_home` used for all filesystem writes
- [ ] Tests pass with `pytest -x -p no:randomly` and with `pytest -n auto`
