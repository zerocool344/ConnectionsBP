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
