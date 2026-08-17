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


def _parse_puzzle(raw: object, index: int) -> Puzzle:
    if not isinstance(raw, dict):
        raise PuzzleBankError(f"bank: puzzle at index {index} must be an object")

    puzzle_id = raw.get("id")
    if not isinstance(puzzle_id, int) or isinstance(puzzle_id, bool):
        raise PuzzleBankError(f"bank: puzzle at index {index} must have an integer 'id'")

    groups = raw.get("groups", [])
    if not isinstance(groups, list) or not all(isinstance(g, dict) for g in groups):
        raise PuzzleBankError(f"puzzle {puzzle_id}: 'groups' must be a list of objects")
    if len(groups) != 4:
        raise PuzzleBankError(f"puzzle {puzzle_id}: expected 4 groups, got {len(groups)}")

    for g in groups:
        tier = g.get("tier")
        if not isinstance(tier, int) or isinstance(tier, bool):
            raise PuzzleBankError(f"puzzle {puzzle_id}: group tier must be an integer, got {tier!r}")
        name = g.get("name")
        if not isinstance(name, str):
            raise PuzzleBankError(f"puzzle {puzzle_id}: group name must be a string, got {name!r}")
        words = g.get("words")
        if not isinstance(words, list) or not all(isinstance(w, str) for w in words):
            raise PuzzleBankError(f"puzzle {puzzle_id}: group '{name}' words must be a list of strings")

    tiers = sorted(g["tier"] for g in groups)
    if tiers != [1, 2, 3, 4]:
        raise PuzzleBankError(f"puzzle {puzzle_id}: tiers must be exactly 1-4, got {tiers}")
    for g in groups:
        if len(g["words"]) != 4:
            raise PuzzleBankError(f"puzzle {puzzle_id}: group '{g['name']}' must have 4 words")
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

    if not isinstance(raw, dict):
        raise PuzzleBankError("bank: top-level JSON must be an object")

    try:
        launch_date = date.fromisoformat(raw.get("launch_date", ""))
    except (ValueError, TypeError) as exc:
        raise PuzzleBankError(f"invalid launch_date: {raw.get('launch_date')!r}") from exc

    raw_puzzles = raw.get("puzzles", [])
    if not isinstance(raw_puzzles, list):
        raise PuzzleBankError("bank: 'puzzles' must be a list")
    if not raw_puzzles:
        raise PuzzleBankError("puzzle bank must contain at least one puzzle")

    puzzles = tuple(_parse_puzzle(p, i) for i, p in enumerate(raw_puzzles))
    ids = [p.id for p in puzzles]
    if len(set(ids)) != len(ids):
        raise PuzzleBankError("duplicate puzzle ids in bank")
    return PuzzleBank(launch_date=launch_date, puzzles=puzzles)


def puzzles_for_date(bank: PuzzleBank, today: date) -> tuple[tuple[Puzzle, int], tuple[Puzzle, int]]:
    day = max(0, (today - bank.launch_date).days)
    idx1 = (day * 2) % len(bank.puzzles)
    idx2 = (day * 2 + 1) % len(bank.puzzles)
    return (bank.puzzles[idx1], idx1 + 1), (bank.puzzles[idx2], idx2 + 1)
