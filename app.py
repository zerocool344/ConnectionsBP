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
/* Selected tiles and Submit: neutral dark, not the theme's error red. */
div.stButton > button[kind="primary"],
div.stButton > button[kind="primary"]:hover,
div.stButton > button[kind="primary"]:focus,
div.stButton > button[kind="primary"]:focus:not(:active) {
    background-color: #5a594e;
    border-color: #5a594e;
    color: #ffffff;
    box-shadow: none;
}
div.stButton > button[kind="primary"]:hover { background-color: #4a493f; }
div.stButton > button[kind="primary"]:disabled {
    background-color: #d7d7d0;
    border-color: #d7d7d0;
    color: #8b8b83;
}
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
                width="stretch",
            )


def render_controls(state: GameState) -> None:
    dots = "🔵" * state.mistakes_left + "⚪" * (4 - state.mistakes_left)
    st.markdown(f'<div class="mistake-dots">{dots}</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.button(
        "Shuffle",
        on_click=lambda: random.shuffle(state.word_order),
        width="stretch",
    )
    c2.button(
        "Deselect all",
        on_click=lambda: st.session_state.selected.clear(),
        width="stretch",
    )
    c3.button(
        "Submit",
        type="primary",
        disabled=len(st.session_state.selected) != 4,
        on_click=handle_submit,
        width="stretch",
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
