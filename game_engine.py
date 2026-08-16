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
