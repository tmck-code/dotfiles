---
name: python-style
description: Apply personal Python code style — stdlib-first, single quotes, low nesting, named ANSI constants, performance-driven, vertical kwarg alignment. Use when writing or editing Python (.py files), setting up pyproject.toml, choosing between implementations, or naming tests.
---

# Python Style

## Rules

### Dependencies
- Prefer the standard library. Reach for third-party packages only when stdlib genuinely lacks the capability — say so explicitly in the commit/PR.
- Avoid `typing.cast`. Fix the types or change the design first. Only reach for `cast` when there is literally no other way, or when the alternative is dramatically more complex — and say why in a comment.
- Avoid `Any` at all costs. Use a precise type, a `Protocol`, a `TypeVar`, or `object` + `isinstance` narrowing before falling back to `Any`.
- For self-referential type hints (a class referring to itself, or forward references), use `from __future__ import annotations` at the top of the file rather than quoting the type name as a string.
  ```python
  from __future__ import annotations

  class Node:
      def add_child(self, child: Node) -> None: ...   # not 'Node'
  ```

### Structure
- Keep nesting shallow: 2 levels is the usual ceiling, 3 the hard maximum.
  - Use early return / `continue` to flatten.
  - If early return won't work, extract a helper method.
- Never write banner comments (`# ===== Section =====` etc.).

### Quoting
- Single quotes for strings: `'hello'`, not `"hello"`.
- Single-line docstrings use single quotes too:
  ```python
  def yolo() -> None:
      'A test function to demonstrate docstring style'
      ...
  ```

### Performance
- Performance is a first-class concern. When multiple implementations are plausible, benchmark them.
- Benchmark options, in order of preference:
  1. `bench.py` from [laser-prynter](https://github.com/tmck-code/laser-prynter/blob/main/laser_prynter/bench.py) — for comparing multiple Python implementations on the same input set.
  2. `ipython` with `%timeit` — for ad-hoc one-liners.
  3. `hyperfine` — for whole-process / CLI comparisons.
- Prefer `'sep'.join([...])` over repeated `+=` string append in loops.
- Prefer `yield` (generator) over building a list with `for`+`append` then returning it.

### Constants
- Always use named constants for ANSI colour/style codes. Never inline `'\033[31m'` etc.
  ```python
  RED   = '\033[31m'
  RESET = '\033[0m'
  print(f'{RED}error{RESET}')
  ```

### Tests
- Name tests after what they test, not after spec numbers, ticket IDs, or section labels.
  - Good: `test_parses_iso_date_with_offset`
  - Bad:  `test_REQ_042_3`, `test_spec_section_2_1`

### Vertical alignment of kwargs
- I prefer aligned `=` in long kwarg lists. Ruff's formatter strips these spaces.
- Workaround: keep the file in `tool.ruff.exclude` (see template). The file is still linted only if removed from exclude — but format won't touch alignment.
- Example shape:
  ```python
  return cls(
      session_id      = d.get('session_id', ''),
      transcript_path = d.get('transcript_path', ''),
      cwd             = d.get('cwd', ''),
  )
  ```

## Project setup

Drop `pyproject-template.toml` (in this skill dir) into new repos as the starting point. It encodes:
- `mypy` strict mode with `disallow_untyped_defs`
- `ruff check` with single-quote enforcement (`flake8-quotes`)
- `ruff format` with `quote-style = "preserve"` so existing single quotes survive
- Excludes for `.claude/`, `.venv/`, and any dir holding vertically-aligned code

## Checklist before declaring done

- [ ] No new `cast(...)` calls (or one with a justifying comment)
- [ ] No `Any` introduced
- [ ] Self-referential hints use `from __future__ import annotations`, not stringified types
- [ ] No banner comments
- [ ] Single quotes throughout (including docstrings where single-line)
- [ ] Nesting ≤ 2 levels (3 only if justified)
- [ ] ANSI codes pulled out into named constants
- [ ] If multiple implementations considered: benchmark numbers in the commit/PR
- [ ] Test names describe behaviour, not spec IDs
- [ ] `ruff check` clean, `mypy --strict` clean (outside exclude list)
