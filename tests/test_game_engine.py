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
