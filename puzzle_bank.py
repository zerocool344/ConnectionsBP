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


def puzzle_for_date(bank: PuzzleBank, today: date) -> tuple[Puzzle, int]:
    day = max(0, (today - bank.launch_date).days)
    return bank.puzzles[day % len(bank.puzzles)], day + 1
