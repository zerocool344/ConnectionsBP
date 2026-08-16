# Plant Connections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily NYT-Connections-style word game themed around mechanical engineering at a chemical manufacturing site, built with Streamlit.

**Architecture:** Pure-Python game engine (`game_engine.py`, no Streamlit imports) and puzzle bank loader (`puzzle_bank.py`) are fully unit-tested; `app.py` is a thin Streamlit shell holding `GameState` in `st.session_state`, with all board drawing behind one `render_board()` seam for a possible later HTML-component upgrade.

**Tech Stack:** Python 3.10+, Streamlit (latest stable), pytest. No other dependencies.

**Spec:** `docs/superpowers/specs/2026-08-16-plant-connections-design.md`

## Global Constraints

- `game_engine.py` and `puzzle_bank.py` MUST NOT import streamlit.
- Tier emoji: tier 1 🟨, tier 2 🟩, tier 3 🟦, tier 4 🟪.
- Tier flavor names: 1 "Operator", 2 "Technician", 3 "Engineer", 4 "Plant Manager".
- Share text title line: `Plant Connections #N`.
- End-screen taglines by mistakes used: 0 → "Plant Manager material", 1 → "Senior Engineer", 2 → "Solid Technician", 3 → "Operator in training", loss → "Back to the control room".
- Daily selection: `day_number = (today - launch_date).days` clamped to ≥ 0; puzzle index `day_number % len(puzzles)`; display number `day_number + 1`.
- Validation failures raise `PuzzleBankError` naming the offending puzzle id; `app.py` shows an error page, never a stack trace.
- 4 mistakes max; duplicate guesses cost nothing and are not re-recorded.
- Commit after every task with the message given in the task.

---

### Task 1: Project scaffold + engine data model

**Files:**
- Create: `game_engine.py`
- Create: `tests/test_game_engine.py`
- Create: `requirements.txt`
- Create: `.gitignore`

**Interfaces:**
- Produces: `Group(tier: int, name: str, words: tuple[str, ...])` frozen dataclass; `Puzzle(id: int, groups: tuple[Group, ...])` frozen dataclass with property `all_words -> tuple[str, ...]`; `GameState(puzzle, found: list[Group], mistakes_left: int = 4, guesses: list[frozenset[str]], word_order: list[str])` mutable dataclass whose `word_order` auto-fills from `puzzle.all_words` when empty; `GuessResult` enum with members `CORRECT, ONE_AWAY, WRONG, ALREADY_GUESSED`; `TIER_EMOJI: dict[int, str]`.

- [ ] **Step 1: Create scaffold files**

`requirements.txt`:

```
streamlit
pytest
```

`.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

Create a virtualenv and install (Streamlit Cloud reads `requirements.txt`; locally we need both):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Use `.venv/bin/pytest` and `.venv/bin/streamlit` for every later step.

- [ ] **Step 2: Write the failing tests**

`tests/test_game_engine.py`:

```python
from game_engine import TIER_EMOJI, GameState, Group, Puzzle


def make_puzzle() -> Puzzle:
    return Puzzle(
        id=1,
        groups=(
            Group(1, "CENTRIFUGAL PUMP PARTS", ("IMPELLER", "VOLUTE", "WEAR RING", "SHAFT SLEEVE")),
            Group(2, "VALVE TYPES", ("GATE", "GLOBE", "BUTTERFLY", "CHECK")),
            Group(3, "___ SEAL", ("MECHANICAL", "LABYRINTH", "LIP", "GLAND")),
            Group(4, "P&ID ABBREVIATIONS", ("PSV", "FIC", "LT", "TE")),
        ),
    )


def test_puzzle_all_words_has_16_words():
    assert len(make_puzzle().all_words) == 16
    assert "IMPELLER" in make_puzzle().all_words


def test_game_state_defaults():
    state = GameState(puzzle=make_puzzle())
    assert state.mistakes_left == 4
    assert state.found == []
    assert state.guesses == []
    assert sorted(state.word_order) == sorted(make_puzzle().all_words)


def test_tier_emoji():
    assert TIER_EMOJI == {1: "🟨", 2: "🟩", 3: "🟦", 4: "🟪"}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'game_engine'`

- [ ] **Step 4: Write the implementation**

`game_engine.py`:

```python
"""Pure game logic for Plant Connections. No Streamlit imports allowed."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

TIER_EMOJI = {1: "🟨", 2: "🟩", 3: "🟦", 4: "🟪"}


@dataclass(frozen=True)
class Group:
    tier: int
    name: str
    words: tuple[str, ...]


@dataclass(frozen=True)
class Puzzle:
    id: int
    groups: tuple[Group, ...]

    @property
    def all_words(self) -> tuple[str, ...]:
        return tuple(word for group in self.groups for word in group.words)


class GuessResult(Enum):
    CORRECT = auto()
    ONE_AWAY = auto()
    WRONG = auto()
    ALREADY_GUESSED = auto()


@dataclass
class GameState:
    puzzle: Puzzle
    found: list[Group] = field(default_factory=list)
    mistakes_left: int = 4
    guesses: list[frozenset[str]] = field(default_factory=list)
    word_order: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.word_order:
            self.word_order = list(self.puzzle.all_words)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: 3 PASS

- [ ] **Step 6: Commit**

```bash
git add game_engine.py tests/test_game_engine.py requirements.txt .gitignore
git commit -m "feat: engine data model and project scaffold"
```

---

### Task 2: Guess submission and win/loss

**Files:**
- Modify: `game_engine.py`
- Test: `tests/test_game_engine.py`

**Interfaces:**
- Consumes: Task 1's `GameState`, `GuessResult`, `Group`, `Puzzle`.
- Produces: `submit_guess(state: GameState, words: set[str]) -> GuessResult`; `is_won(state: GameState) -> bool`; `is_lost(state: GameState) -> bool`; `remaining_groups(state: GameState) -> list[Group]` (unfound groups in tier order).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_game_engine.py`:

```python
import pytest

from game_engine import GuessResult, is_lost, is_won, remaining_groups, submit_guess


def test_correct_guess_moves_group_to_found_and_clears_words():
    state = GameState(puzzle=make_puzzle())
    result = submit_guess(state, {"GATE", "GLOBE", "BUTTERFLY", "CHECK"})
    assert result is GuessResult.CORRECT
    assert [g.name for g in state.found] == ["VALVE TYPES"]
    assert state.mistakes_left == 4
    assert "GATE" not in state.word_order
    assert len(state.word_order) == 12


def test_one_away_costs_a_mistake():
    state = GameState(puzzle=make_puzzle())
    result = submit_guess(state, {"GATE", "GLOBE", "BUTTERFLY", "PSV"})
    assert result is GuessResult.ONE_AWAY
    assert state.mistakes_left == 3


def test_wrong_guess_costs_a_mistake():
    state = GameState(puzzle=make_puzzle())
    result = submit_guess(state, {"GATE", "GLOBE", "PSV", "LIP"})
    assert result is GuessResult.WRONG
    assert state.mistakes_left == 3


def test_duplicate_guess_costs_nothing_and_not_rerecorded():
    state = GameState(puzzle=make_puzzle())
    submit_guess(state, {"GATE", "GLOBE", "PSV", "LIP"})
    result = submit_guess(state, {"LIP", "PSV", "GLOBE", "GATE"})
    assert result is GuessResult.ALREADY_GUESSED
    assert state.mistakes_left == 3
    assert len(state.guesses) == 1


def test_guess_must_have_exactly_four_words():
    state = GameState(puzzle=make_puzzle())
    with pytest.raises(ValueError):
        submit_guess(state, {"GATE", "GLOBE"})


def test_guess_words_must_be_on_board():
    state = GameState(puzzle=make_puzzle())
    with pytest.raises(ValueError):
        submit_guess(state, {"GATE", "GLOBE", "BUTTERFLY", "FLANGE"})


def test_win_after_all_four_groups():
    state = GameState(puzzle=make_puzzle())
    for group in make_puzzle().groups:
        submit_guess(state, set(group.words))
    assert is_won(state)
    assert not is_lost(state)
    assert state.word_order == []


def test_loss_after_four_mistakes():
    state = GameState(puzzle=make_puzzle())
    wrong_guesses = [
        {"GATE", "GLOBE", "PSV", "LIP"},
        {"GATE", "GLOBE", "PSV", "GLAND"},
        {"GATE", "GLOBE", "LT", "LIP"},
        {"GATE", "GLOBE", "TE", "LIP"},
    ]
    for guess in wrong_guesses:
        submit_guess(state, guess)
    assert is_lost(state)
    assert not is_won(state)


def test_remaining_groups_in_tier_order():
    state = GameState(puzzle=make_puzzle())
    submit_guess(state, {"MECHANICAL", "LABYRINTH", "LIP", "GLAND"})
    remaining = remaining_groups(state)
    assert [g.tier for g in remaining] == [1, 2, 4]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: new tests FAIL with `ImportError: cannot import name 'submit_guess'`

- [ ] **Step 3: Write the implementation**

Append to `game_engine.py`:

```python
def submit_guess(state: GameState, words: set[str]) -> GuessResult:
    if len(words) != 4:
        raise ValueError("A guess must contain exactly 4 words.")
    if not words <= set(state.word_order):
        raise ValueError("Guess contains words not on the board.")
    guess = frozenset(words)
    if guess in state.guesses:
        return GuessResult.ALREADY_GUESSED
    state.guesses.append(guess)

    unfound = [g for g in state.puzzle.groups if g not in state.found]
    for group in unfound:
        if words == set(group.words):
            state.found.append(group)
            state.word_order = [w for w in state.word_order if w not in words]
            return GuessResult.CORRECT

    state.mistakes_left -= 1
    if any(len(words & set(g.words)) == 3 for g in unfound):
        return GuessResult.ONE_AWAY
    return GuessResult.WRONG


def is_won(state: GameState) -> bool:
    return len(state.found) == 4


def is_lost(state: GameState) -> bool:
    return state.mistakes_left == 0


def remaining_groups(state: GameState) -> list[Group]:
    return sorted(
        (g for g in state.puzzle.groups if g not in state.found),
        key=lambda g: g.tier,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add game_engine.py tests/test_game_engine.py
git commit -m "feat: guess submission, win/loss, remaining groups"
```

---

### Task 3: Share text (emoji grid)

**Files:**
- Modify: `game_engine.py`
- Test: `tests/test_game_engine.py`

**Interfaces:**
- Consumes: Task 1's `GameState`, `TIER_EMOJI`; Task 2's `submit_guess`.
- Produces: `emoji_grid(state: GameState, puzzle_number: int) -> str`. One row per recorded guess in order; within a row, emoji sorted by (tier, word) for deterministic output (frozensets are unordered).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_game_engine.py`:

```python
from game_engine import emoji_grid


def test_emoji_grid_title_and_rows():
    state = GameState(puzzle=make_puzzle())
    submit_guess(state, {"IMPELLER", "VOLUTE", "WEAR RING", "SHAFT SLEEVE"})  # correct tier 1
    submit_guess(state, {"GATE", "GLOBE", "BUTTERFLY", "PSV"})  # one away
    grid = emoji_grid(state, puzzle_number=12)
    lines = grid.split("\n")
    assert lines[0] == "Plant Connections #12"
    assert lines[1] == "🟨🟨🟨🟨"
    assert sorted(lines[2]) == sorted("🟩🟩🟩🟪")


def test_emoji_grid_row_is_deterministic():
    state_a = GameState(puzzle=make_puzzle())
    state_b = GameState(puzzle=make_puzzle())
    submit_guess(state_a, {"GATE", "GLOBE", "BUTTERFLY", "PSV"})
    submit_guess(state_b, {"PSV", "BUTTERFLY", "GLOBE", "GATE"})
    assert emoji_grid(state_a, 1) == emoji_grid(state_b, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: FAIL with `ImportError: cannot import name 'emoji_grid'`

- [ ] **Step 3: Write the implementation**

Append to `game_engine.py`:

```python
def emoji_grid(state: GameState, puzzle_number: int) -> str:
    tier_of = {word: g.tier for g in state.puzzle.groups for word in g.words}
    lines = [f"Plant Connections #{puzzle_number}"]
    for guess in state.guesses:
        ordered = sorted(guess, key=lambda w: (tier_of[w], w))
        lines.append("".join(TIER_EMOJI[tier_of[w]] for w in ordered))
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_game_engine.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add game_engine.py tests/test_game_engine.py
git commit -m "feat: emoji share grid"
```

---

### Task 4: Puzzle bank loading and validation

**Files:**
- Create: `puzzle_bank.py`
- Create: `tests/test_puzzle_bank.py`

**Interfaces:**
- Consumes: Task 1's `Group`, `Puzzle`.
- Produces: `PuzzleBankError(Exception)`; `PuzzleBank(launch_date: datetime.date, puzzles: tuple[Puzzle, ...])` frozen dataclass; `load_bank(path: str | Path) -> PuzzleBank`.

- [ ] **Step 1: Write the failing tests**

`tests/test_puzzle_bank.py`:

```python
import json

import pytest

from puzzle_bank import PuzzleBankError, load_bank


def valid_bank_dict() -> dict:
    return {
        "launch_date": "2026-08-17",
        "puzzles": [
            {
                "id": 1,
                "groups": [
                    {"tier": 1, "name": "CENTRIFUGAL PUMP PARTS", "words": ["IMPELLER", "VOLUTE", "WEAR RING", "SHAFT SLEEVE"]},
                    {"tier": 2, "name": "VALVE TYPES", "words": ["GATE", "GLOBE", "BUTTERFLY", "CHECK"]},
                    {"tier": 3, "name": "___ SEAL", "words": ["MECHANICAL", "LABYRINTH", "LIP", "GLAND"]},
                    {"tier": 4, "name": "P&ID ABBREVIATIONS", "words": ["PSV", "FIC", "LT", "TE"]},
                ],
            }
        ],
    }


def write_bank(tmp_path, bank_dict):
    path = tmp_path / "puzzles.json"
    path.write_text(json.dumps(bank_dict), encoding="utf-8")
    return path


def test_loads_valid_bank(tmp_path):
    bank = load_bank(write_bank(tmp_path, valid_bank_dict()))
    assert bank.launch_date.isoformat() == "2026-08-17"
    assert len(bank.puzzles) == 1
    assert bank.puzzles[0].groups[0].name == "CENTRIFUGAL PUMP PARTS"


def test_rejects_wrong_group_count(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"].pop()
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_bad_tiers(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][3]["tier"] = 2
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_wrong_word_count(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][0]["words"].append("CASING")
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_duplicate_words_case_insensitive(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"][0]["groups"][0]["words"][0] = "gate"
    with pytest.raises(PuzzleBankError, match="puzzle 1"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_duplicate_puzzle_ids(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"].append(json.loads(json.dumps(bad["puzzles"][0])))
    with pytest.raises(PuzzleBankError, match="duplicate"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_bad_launch_date(tmp_path):
    bad = valid_bank_dict()
    bad["launch_date"] = "yesterday"
    with pytest.raises(PuzzleBankError, match="launch_date"):
        load_bank(write_bank(tmp_path, bad))


def test_rejects_empty_puzzle_list(tmp_path):
    bad = valid_bank_dict()
    bad["puzzles"] = []
    with pytest.raises(PuzzleBankError, match="at least one"):
        load_bank(write_bank(tmp_path, bad))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'puzzle_bank'`

- [ ] **Step 3: Write the implementation**

`puzzle_bank.py`:

```python
"""Loads and validates puzzles.json. No Streamlit imports allowed."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from game_engine import Group, Puzzle


class PuzzleBankError(Exception):
    pass


@dataclass(frozen=True)
class PuzzleBank:
    launch_date: date
    puzzles: tuple[Puzzle, ...]


def _parse_puzzle(raw: dict) -> Puzzle:
    puzzle_id = raw.get("id")
    groups = raw.get("groups", [])
    if len(groups) != 4:
        raise PuzzleBankError(f"puzzle {puzzle_id}: expected 4 groups, got {len(groups)}")
    tiers = sorted(g.get("tier") for g in groups)
    if tiers != [1, 2, 3, 4]:
        raise PuzzleBankError(f"puzzle {puzzle_id}: tiers must be exactly 1-4, got {tiers}")
    for g in groups:
        if len(g.get("words", [])) != 4:
            raise PuzzleBankError(f"puzzle {puzzle_id}: group '{g.get('name')}' must have 4 words")
    all_words = [w.upper() for g in groups for w in g["words"]]
    if len(set(all_words)) != 16:
        raise PuzzleBankError(f"puzzle {puzzle_id}: words must be 16 unique terms (case-insensitive)")
    return Puzzle(
        id=puzzle_id,
        groups=tuple(
            Group(tier=g["tier"], name=g["name"], words=tuple(w.upper() for w in g["words"]))
            for g in sorted(groups, key=lambda g: g["tier"])
        ),
    )


def load_bank(path: str | Path) -> PuzzleBank:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PuzzleBankError(f"cannot read puzzle bank: {exc}") from exc

    try:
        launch_date = date.fromisoformat(raw.get("launch_date", ""))
    except ValueError as exc:
        raise PuzzleBankError(f"invalid launch_date: {raw.get('launch_date')!r}") from exc

    raw_puzzles = raw.get("puzzles", [])
    if not raw_puzzles:
        raise PuzzleBankError("puzzle bank must contain at least one puzzle")

    puzzles = tuple(_parse_puzzle(p) for p in raw_puzzles)
    ids = [p.id for p in puzzles]
    if len(set(ids)) != len(ids):
        raise PuzzleBankError("duplicate puzzle ids in bank")
    return PuzzleBank(launch_date=launch_date, puzzles=puzzles)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py -v`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add puzzle_bank.py tests/test_puzzle_bank.py
git commit -m "feat: puzzle bank loading and validation"
```

---

### Task 5: Daily puzzle selection

**Files:**
- Modify: `puzzle_bank.py`
- Test: `tests/test_puzzle_bank.py`

**Interfaces:**
- Consumes: Task 4's `PuzzleBank`, `load_bank`.
- Produces: `puzzle_for_date(bank: PuzzleBank, today: datetime.date) -> tuple[Puzzle, int]` — returns (puzzle, display number). Day number clamps to 0 before launch date; index = `day % len(puzzles)`; display number = `day + 1`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_puzzle_bank.py`:

```python
from datetime import date

from puzzle_bank import puzzle_for_date


def two_puzzle_bank(tmp_path):
    bank_dict = valid_bank_dict()
    second = json.loads(json.dumps(bank_dict["puzzles"][0]))
    second["id"] = 2
    second["groups"][0]["words"] = ["BEARING", "COUPLING", "CASING", "BASEPLATE"]
    bank_dict["puzzles"].append(second)
    return load_bank(write_bank(tmp_path, bank_dict))


def test_launch_day_is_puzzle_one(tmp_path):
    bank = two_puzzle_bank(tmp_path)
    puzzle, number = puzzle_for_date(bank, date(2026, 8, 17))
    assert puzzle.id == 1
    assert number == 1


def test_next_day_is_puzzle_two(tmp_path):
    bank = two_puzzle_bank(tmp_path)
    puzzle, number = puzzle_for_date(bank, date(2026, 8, 18))
    assert puzzle.id == 2
    assert number == 2


def test_cycles_when_bank_exhausted(tmp_path):
    bank = two_puzzle_bank(tmp_path)
    puzzle, number = puzzle_for_date(bank, date(2026, 8, 19))
    assert puzzle.id == 1
    assert number == 3


def test_before_launch_clamps_to_day_zero(tmp_path):
    bank = two_puzzle_bank(tmp_path)
    puzzle, number = puzzle_for_date(bank, date(2026, 8, 1))
    assert puzzle.id == 1
    assert number == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py -v`
Expected: FAIL with `ImportError: cannot import name 'puzzle_for_date'`

- [ ] **Step 3: Write the implementation**

Append to `puzzle_bank.py`:

```python
def puzzle_for_date(bank: PuzzleBank, today: date) -> tuple[Puzzle, int]:
    day = max(0, (today - bank.launch_date).days)
    return bank.puzzles[day % len(bank.puzzles)], day + 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py -v`
Expected: 12 PASS

- [ ] **Step 5: Commit**

```bash
git add puzzle_bank.py tests/test_puzzle_bank.py
git commit -m "feat: deterministic daily puzzle selection"
```

---

### Task 6: Starter puzzle bank content

**Files:**
- Create: `puzzles.json`
- Test: `tests/test_puzzle_bank.py`

**Interfaces:**
- Consumes: Task 4's `load_bank`.
- Produces: the real `puzzles.json` at repo root with 15 puzzles; a regression test that the shipped bank always validates.

**Note:** Content drafted for user review — the user corrects terminology for site accuracy afterward. Cross-puzzle word repeats are allowed; uniqueness matters only within a puzzle.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_puzzle_bank.py`:

```python
from pathlib import Path


def test_shipped_bank_is_valid():
    bank = load_bank(Path(__file__).parent.parent / "puzzles.json")
    assert len(bank.puzzles) == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py::test_shipped_bank_is_valid -v`
Expected: FAIL with `PuzzleBankError: cannot read puzzle bank` (file missing)

- [ ] **Step 3: Create `puzzles.json`**

```json
{
  "launch_date": "2026-08-17",
  "puzzles": [
    {
      "id": 1,
      "groups": [
        {"tier": 1, "name": "CENTRIFUGAL PUMP PARTS", "words": ["IMPELLER", "VOLUTE", "WEAR RING", "SHAFT SLEEVE"]},
        {"tier": 2, "name": "VALVE TYPES", "words": ["GATE", "GLOBE", "BUTTERFLY", "CHECK"]},
        {"tier": 3, "name": "___ SEAL", "words": ["MECHANICAL", "LABYRINTH", "LIP", "GLAND"]},
        {"tier": 4, "name": "P&ID ABBREVIATIONS", "words": ["PSV", "FIC", "LT", "TE"]}
      ]
    },
    {
      "id": 2,
      "groups": [
        {"tier": 1, "name": "HEAT EXCHANGER PARTS", "words": ["TUBE", "SHELL", "BAFFLE", "TUBESHEET"]},
        {"tier": 2, "name": "COMPRESSOR TYPES", "words": ["SCREW", "RECIPROCATING", "CENTRIFUGAL", "AXIAL"]},
        {"tier": 3, "name": "MATERIAL FAILURE MODES", "words": ["FATIGUE", "CORROSION", "EROSION", "CAVITATION"]},
        {"tier": 4, "name": "STEAM ___", "words": ["TRAP", "TRACE", "DRUM", "JACKET"]}
      ]
    },
    {
      "id": 3,
      "groups": [
        {"tier": 1, "name": "MEASURED PROCESS VARIABLES", "words": ["FLOW", "LEVEL", "PRESSURE", "TEMPERATURE"]},
        {"tier": 2, "name": "CONTROL LOOP COMPONENTS", "words": ["SENSOR", "TRANSMITTER", "CONTROLLER", "ACTUATOR"]},
        {"tier": 3, "name": "PLANT CONTROL SYSTEMS", "words": ["DCS", "PLC", "HMI", "SCADA"]},
        {"tier": 4, "name": "___ VALVE", "words": ["RELIEF", "NEEDLE", "BALL", "PLUG"]}
      ]
    },
    {
      "id": 4,
      "groups": [
        {"tier": 1, "name": "BEARING TYPES", "words": ["BALL", "ROLLER", "THRUST", "JOURNAL"]},
        {"tier": 2, "name": "VIBRATION ANALYSIS TERMS", "words": ["AMPLITUDE", "FREQUENCY", "HARMONIC", "IMBALANCE"]},
        {"tier": 3, "name": "COUPLING TYPES", "words": ["GEAR", "GRID", "DISC", "JAW"]},
        {"tier": 4, "name": "LUBRICATION TERMS", "words": ["GREASE", "VISCOSITY", "ADDITIVE", "FILM"]}
      ]
    },
    {
      "id": 5,
      "groups": [
        {"tier": 1, "name": "PPE", "words": ["HARD HAT", "GOGGLES", "GLOVES", "RESPIRATOR"]},
        {"tier": 2, "name": "WORK PERMIT TYPES", "words": ["HOT WORK", "CONFINED SPACE", "LOTO", "EXCAVATION"]},
        {"tier": 3, "name": "OVERPRESSURE PROTECTION", "words": ["RUPTURE DISK", "SAFETY VALVE", "CONSERVATION VENT", "FLAME ARRESTOR"]},
        {"tier": 4, "name": "PSM ELEMENT ABBREVIATIONS", "words": ["MOC", "PHA", "PSSR", "MI"]}
      ]
    },
    {
      "id": 6,
      "groups": [
        {"tier": 1, "name": "PIPE FITTINGS", "words": ["ELBOW", "TEE", "REDUCER", "FLANGE"]},
        {"tier": 2, "name": "PIPE MATERIALS", "words": ["CARBON STEEL", "STAINLESS", "HDPE", "COPPER"]},
        {"tier": 3, "name": "WELDING PROCESSES", "words": ["TIG", "MIG", "STICK", "ORBITAL"]},
        {"tier": 4, "name": "___ JOINT", "words": ["EXPANSION", "LAP", "BUTT", "SLIP"]}
      ]
    },
    {
      "id": 7,
      "groups": [
        {"tier": 1, "name": "ELECTRIC MOTOR PARTS", "words": ["STATOR", "ROTOR", "WINDING", "FRAME"]},
        {"tier": 2, "name": "ELECTRICAL UNITS", "words": ["VOLT", "AMP", "OHM", "WATT"]},
        {"tier": 3, "name": "MOTOR CONTROL EQUIPMENT", "words": ["BREAKER", "STARTER", "OVERLOAD", "VFD"]},
        {"tier": 4, "name": "___ PHASE", "words": ["SINGLE", "THREE", "GAS", "LIQUID"]}
      ]
    },
    {
      "id": 8,
      "groups": [
        {"tier": 1, "name": "DISTILLATION COLUMN PARTS", "words": ["TRAY", "PACKING", "REBOILER", "CONDENSER"]},
        {"tier": 2, "name": "REACTOR TYPES", "words": ["BATCH", "CSTR", "PFR", "SEMI-BATCH"]},
        {"tier": 3, "name": "PLANT UTILITIES", "words": ["STEAM", "NITROGEN", "INSTRUMENT AIR", "COOLING WATER"]},
        {"tier": 4, "name": "___ POINT", "words": ["FLASH", "BUBBLE", "DEW", "SET"]}
      ]
    },
    {
      "id": 9,
      "groups": [
        {"tier": 1, "name": "MAINTENANCE WORK TYPES", "words": ["PREVENTIVE", "CORRECTIVE", "PREDICTIVE", "EMERGENCY"]},
        {"tier": 2, "name": "PRECISION MEASURING TOOLS", "words": ["TORQUE WRENCH", "FEELER GAUGE", "DIAL INDICATOR", "MICROMETER"]},
        {"tier": 3, "name": "NDT METHODS", "words": ["ULTRASONIC", "RADIOGRAPHY", "DYE PENETRANT", "MAG PARTICLE"]},
        {"tier": 4, "name": "___ TEST", "words": ["HYDRO", "LEAK", "BUMP", "SPARK"]}
      ]
    },
    {
      "id": 10,
      "groups": [
        {"tier": 1, "name": "STORAGE TANK FEATURES", "words": ["MANWAY", "NOZZLE", "VENT", "DIKE"]},
        {"tier": 2, "name": "LEVEL INSTRUMENT TYPES", "words": ["RADAR", "DP CELL", "FLOAT", "SIGHT GLASS"]},
        {"tier": 3, "name": "GASKET MATERIALS", "words": ["PTFE", "GRAPHITE", "RUBBER", "SPIRAL WOUND"]},
        {"tier": 4, "name": "___ FLANGE", "words": ["WELD NECK", "SLIP ON", "BLIND", "SOCKET"]}
      ]
    },
    {
      "id": 11,
      "groups": [
        {"tier": 1, "name": "PUMP CURVE TERMS", "words": ["HEAD", "NPSH", "EFFICIENCY", "BEP"]},
        {"tier": 2, "name": "FLOW REGIMES", "words": ["LAMINAR", "TURBULENT", "TRANSITIONAL", "SLUG"]},
        {"tier": 3, "name": "DIMENSIONLESS NUMBERS", "words": ["REYNOLDS", "PRANDTL", "NUSSELT", "FROUDE"]},
        {"tier": 4, "name": "___ HAMMER", "words": ["WATER", "JACK", "SLEDGE", "CLAW"]}
      ]
    },
    {
      "id": 12,
      "groups": [
        {"tier": 1, "name": "CORROSION TYPES", "words": ["PITTING", "CREVICE", "GALVANIC", "UNIFORM"]},
        {"tier": 2, "name": "MECHANICAL PROPERTY TESTS", "words": ["HARDNESS", "TENSILE", "CREEP", "IMPACT"]},
        {"tier": 3, "name": "PROTECTIVE COATINGS", "words": ["EPOXY", "GALVANIZING", "PAINT", "LINING"]},
        {"tier": 4, "name": "___ STEEL", "words": ["CARBON", "MILD", "TOOL", "SPRING"]}
      ]
    },
    {
      "id": 13,
      "groups": [
        {"tier": 1, "name": "BOILER COMPONENTS", "words": ["ECONOMIZER", "SUPERHEATER", "BURNER", "STACK"]},
        {"tier": 2, "name": "WATER TREATMENT EQUIPMENT", "words": ["SOFTENER", "RO UNIT", "DEAERATOR", "CLARIFIER"]},
        {"tier": 3, "name": "COMBUSTION REQUIREMENTS", "words": ["FUEL", "AIR", "IGNITION", "FLAME"]},
        {"tier": 4, "name": "___ WATER", "words": ["FEED", "COOLING", "FIRE", "RAW"]}
      ]
    },
    {
      "id": 14,
      "groups": [
        {"tier": 1, "name": "STEAM TURBINE PARTS", "words": ["BLADE", "NOZZLE RING", "CASING", "GOVERNOR"]},
        {"tier": 2, "name": "INDUSTRIAL FAN TYPES", "words": ["AXIAL", "FORCED DRAFT", "INDUCED DRAFT", "BLOWER"]},
        {"tier": 3, "name": "SEAL SUPPORT FLUIDS", "words": ["FLUSH", "QUENCH", "BARRIER", "BUFFER"]},
        {"tier": 4, "name": "___ SPEED", "words": ["CRITICAL", "TRIP", "RATED", "OVER"]}
      ]
    },
    {
      "id": 15,
      "groups": [
        {"tier": 1, "name": "PLANT DOCUMENTS", "words": ["PFD", "SOP", "DATASHEET", "ISOMETRIC"]},
        {"tier": 2, "name": "CONTROLLER TUNING TERMS", "words": ["GAIN", "RESET", "RATE", "DEADBAND"]},
        {"tier": 3, "name": "ALARM MANAGEMENT TERMS", "words": ["PRIORITY", "ACKNOWLEDGE", "FLOOD", "SHELVE"]},
        {"tier": 4, "name": "___ ORDER", "words": ["WORK", "CHANGE", "PURCHASE", "BATCH"]}
      ]
    }
  ]
}
```

- [ ] **Step 4: Run the full bank test suite**

Run: `.venv/bin/pytest tests/test_puzzle_bank.py -v`
Expected: all PASS (validation proves 16 unique words per puzzle, tiers 1-4, etc.)

- [ ] **Step 5: Commit**

```bash
git add puzzles.json tests/test_puzzle_bank.py
git commit -m "feat: 15-puzzle starter bank"
```

---

### Task 7: Streamlit app — board and gameplay

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `GameState`, `GuessResult`, `submit_guess`, `is_won`, `is_lost`, `remaining_groups` from `game_engine`; `PuzzleBankError`, `load_bank`, `puzzle_for_date` from `puzzle_bank`.
- Produces: runnable Streamlit app; `render_board(state)` as the single board-drawing seam.

No automated tests for UI (per spec). Manual verification steps below.

**Spec deviation (accepted):** the spec's "CSS shake on wrong guess" cannot target individual Streamlit buttons after a rerun. V1 signals a wrong guess with the toast + mistake dot; a true tile shake is exactly what the `render_board()` seam's HTML-component upgrade is for. Do not fight Streamlit over this.

- [ ] **Step 1: Write `app.py`**

```python
import random
from datetime import date

import streamlit as st

from game_engine import (
    GameState,
    GuessResult,
    emoji_grid,
    is_lost,
    is_won,
    remaining_groups,
    submit_guess,
)
from puzzle_bank import PuzzleBankError, load_bank, puzzle_for_date

TIER_COLORS = {1: "#f9df6d", 2: "#a0c35a", 3: "#b0c4ef", 4: "#ba81c5"}
TIER_NAMES = {1: "Operator", 2: "Technician", 3: "Engineer", 4: "Plant Manager"}
TAGLINES = {
    0: "Plant Manager material",
    1: "Senior Engineer",
    2: "Solid Technician",
    3: "Operator in training",
}
LOSS_TAGLINE = "Back to the control room"

CSS = """
<style>
div.stButton > button {
    width: 100%;
    min-height: 3.2rem;
    font-weight: 700;
    font-size: 0.78rem;
    border-radius: 8px;
    transition: transform 0.1s ease;
}
div.stButton > button:active { transform: scale(0.96); }
.group-banner {
    border-radius: 8px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.4rem;
    text-align: center;
    color: #1a1a1a;
    animation: fadein 0.6s ease;
}
.group-banner .gname { font-weight: 800; }
.group-banner .gwords { font-size: 0.85rem; }
@keyframes fadein {
    from { opacity: 0; transform: translateY(-6px); }
    to { opacity: 1; transform: translateY(0); }
}
.mistake-dots { text-align: center; font-size: 1.2rem; letter-spacing: 0.4rem; }
</style>
"""


def init_state() -> None:
    if "game" in st.session_state:
        return
    bank = load_bank("puzzles.json")
    puzzle, number = puzzle_for_date(bank, date.today())
    state = GameState(puzzle=puzzle)
    random.shuffle(state.word_order)
    st.session_state.game = state
    st.session_state.puzzle_number = number
    st.session_state.selected = set()


def toggle_word(word: str) -> None:
    selected: set[str] = st.session_state.selected
    if word in selected:
        selected.remove(word)
    elif len(selected) < 4:
        selected.add(word)


def handle_submit() -> None:
    state: GameState = st.session_state.game
    result = submit_guess(state, set(st.session_state.selected))
    if result is GuessResult.CORRECT:
        st.session_state.selected = set()
    elif result is GuessResult.ONE_AWAY:
        st.toast("One away!", icon="⚠️")
    elif result is GuessResult.ALREADY_GUESSED:
        st.toast("Already guessed", icon="🔁")
    else:
        st.toast("Not a group", icon="❌")


def render_banner(group) -> None:
    words = ", ".join(group.words)
    st.markdown(
        f'<div class="group-banner" style="background:{TIER_COLORS[group.tier]}">'
        f'<div class="gname">{group.name} · {TIER_NAMES[group.tier]}</div>'
        f'<div class="gwords">{words}</div></div>',
        unsafe_allow_html=True,
    )


def render_board(state: GameState) -> None:
    """Single seam for board drawing — replace internals with an HTML
    component later without touching engine or bank."""
    for group in state.found:
        render_banner(group)
    words = state.word_order
    for row_start in range(0, len(words), 4):
        cols = st.columns(4)
        for col, word in zip(cols, words[row_start : row_start + 4]):
            selected = word in st.session_state.selected
            col.button(
                word,
                key=f"tile-{word}",
                type="primary" if selected else "secondary",
                on_click=toggle_word,
                args=(word,),
            )


def render_controls(state: GameState) -> None:
    dots = "🔵" * state.mistakes_left + "⚪" * (4 - state.mistakes_left)
    st.markdown(f'<div class="mistake-dots">{dots}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.button("Shuffle", on_click=lambda: random.shuffle(state.word_order))
    c2.button("Deselect all", on_click=lambda: st.session_state.selected.clear())
    c3.button(
        "Submit",
        type="primary",
        disabled=len(st.session_state.selected) != 4,
        on_click=handle_submit,
    )


def render_end_screen(state: GameState) -> None:
    if is_won(state):
        mistakes_used = 4 - state.mistakes_left
        st.success(f"Solved it! {TAGLINES[mistakes_used]}")
    else:
        st.error(LOSS_TAGLINE)
        for group in remaining_groups(state):
            render_banner(group)
    st.subheader("Share your result")
    st.code(emoji_grid(state, st.session_state.puzzle_number), language=None)
    st.caption("Copy icon in the top-right of the box — paste it in Teams.")


def main() -> None:
    st.set_page_config(page_title="Plant Connections", page_icon="🏭", layout="centered")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        init_state()
    except PuzzleBankError as exc:
        st.error(f"Puzzle bank problem: {exc}")
        st.stop()
    state: GameState = st.session_state.game
    st.title(f"🏭 Plant Connections #{st.session_state.puzzle_number}")
    st.caption("Group the 16 terms into 4 categories. Four mistakes allowed.")
    if is_won(state) or is_lost(state):
        for group in state.found:
            render_banner(group)
        render_end_screen(state)
    else:
        render_board(state)
        render_controls(state)


main()
```

- [ ] **Step 2: Run the full test suite (regression)**

Run: `.venv/bin/pytest -v`
Expected: all PASS (engine and bank untouched, but prove it)

- [ ] **Step 3: Manual verification**

Run: `.venv/bin/streamlit run app.py`

Check in the browser:
1. 16 tiles appear, today's puzzle title shows "Plant Connections #N".
2. Clicking a tile highlights it (primary color); a 5th click on a new tile does nothing.
3. Submit disabled until exactly 4 selected.
4. Correct guess → colored banner appears above grid with fade-in; tiles vanish.
5. Wrong guess → "Not a group" toast, one mistake dot turns white.
6. 3-of-4 guess → "One away!" toast.
7. Resubmitting the same wrong 4 → "Already guessed" toast, no dot lost.
8. Shuffle rearranges tiles; Deselect all clears highlights.
9. Win → success banner + tagline + emoji grid in copyable code box.
10. Lose (4 mistakes) → remaining groups auto-reveal in tier order, loss tagline.

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit board, gameplay, end screen"
```

---

### Task 8: README + deploy prep

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: everything prior; no code changes.

- [ ] **Step 1: Write `README.md`**

```markdown
# 🏭 Plant Connections

A daily Connections-style word game for mechanical engineers at a
chemical manufacturing site. Group 16 plant terms into 4 hidden
categories. New puzzle every day; four mistakes allowed.

## Run locally

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/streamlit run app.py

## Tests

    .venv/bin/pytest

## Deploy (Streamlit Cloud)

1. Push this repo to GitHub.
2. At share.streamlit.io, create an app pointing at `app.py`.
3. Done — `requirements.txt` is picked up automatically.

## Editing puzzles

Puzzles live in `puzzles.json`. Each puzzle: 4 groups × 4 words,
tiers 1 (easy) → 4 (tricky), 16 unique words. The bank validates on
load and the app refuses to start on malformed content — run
`.venv/bin/pytest tests/test_puzzle_bank.py` after editing.

Daily rotation: `(today - launch_date) % puzzle_count`, same puzzle
for everyone on a given day.
```

- [ ] **Step 2: Final full-suite run**

Run: `.venv/bin/pytest -v`
Expected: all PASS

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: README with run, test, deploy instructions"
```

---

## Verification checklist (post-plan)

- [ ] `.venv/bin/pytest -v` — every test green
- [ ] `.venv/bin/streamlit run app.py` — full manual pass from Task 7 Step 3
- [ ] User reviews `puzzles.json` terminology for site accuracy (content was Claude-drafted)
- [ ] Push to GitHub + connect Streamlit Cloud (user action — needs their account)
