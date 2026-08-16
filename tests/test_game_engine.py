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
