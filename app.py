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
    get_hint,
    calculate_score
)
from puzzle_bank import PuzzleBankError, load_bank, puzzles_for_date
from leaderboard import get_top_scores, save_score

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
.leaderboard-box {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
    border: 1px solid #e9ecef;
}
</style>
"""


def init_state() -> None:
    if "game_daily" in st.session_state:
        return
    bank = load_bank("puzzles.json")
    (p1, n1), (p2, n2) = puzzles_for_date(bank, date.today())
    
    state1 = GameState(puzzle=p1)
    random.shuffle(state1.word_order)
    st.session_state.game_daily = state1
    st.session_state.puzzle_number_daily = n1
    st.session_state.selected_daily = set()

    state2 = GameState(puzzle=p2)
    random.shuffle(state2.word_order)
    st.session_state.game_bonus = state2
    st.session_state.puzzle_number_bonus = n2
    st.session_state.selected_bonus = set()


def toggle_word(word: str, prefix: str) -> None:
    selected: set[str] = st.session_state[f"selected_{prefix}"]
    if word in selected:
        selected.remove(word)
    elif len(selected) < 4:
        selected.add(word)


def handle_submit(prefix: str) -> None:
    state: GameState = st.session_state[f"game_{prefix}"]
    selected: set[str] = st.session_state[f"selected_{prefix}"]
    result = submit_guess(state, set(selected))
    if result is GuessResult.CORRECT:
        st.session_state[f"selected_{prefix}"] = set()
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


def render_board(state: GameState, prefix: str) -> None:
    for group in state.found:
        render_banner(group)
    words = state.word_order
    selected = st.session_state[f"selected_{prefix}"]
    for row_start in range(0, len(words), 4):
        cols = st.columns(4)
        for col, word in zip(cols, words[row_start : row_start + 4]):
            is_sel = word in selected
            col.button(
                word,
                key=f"tile-{prefix}-{word}",
                type="primary" if is_sel else "secondary",
                on_click=toggle_word,
                args=(word, prefix),
                width="stretch",
            )


def render_controls(state: GameState, prefix: str) -> None:
    dots = "🔵" * state.mistakes_left + "⚪" * (4 - state.mistakes_left)
    st.markdown(f'<div class="mistake-dots">{dots}</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.button(
        "Shuffle",
        key=f"shuffle-{prefix}",
        on_click=lambda: random.shuffle(state.word_order),
        width="stretch",
    )
    c2.button(
        "Deselect",
        key=f"deselect-{prefix}",
        on_click=lambda: st.session_state[f"selected_{prefix}"].clear(),
        width="stretch",
    )
    
    def apply_hint():
        get_hint(state)
        
    c3.button(
        "Hint",
        key=f"hint-{prefix}",
        on_click=apply_hint,
        disabled=state.hint_used,
        width="stretch",
    )
    c4.button(
        "Submit",
        key=f"submit-{prefix}",
        type="primary",
        disabled=len(st.session_state[f"selected_{prefix}"]) != 4,
        on_click=handle_submit,
        args=(prefix,),
        width="stretch",
    )
    
    if state.hint_used and not is_won(state) and not is_lost(state):
        unfound = remaining_groups(state)
        if unfound:
            st.info(f"💡 Hint: Look for the category **'{unfound[0].name}'**")


def render_end_screen(state: GameState, prefix: str) -> None:
    score = calculate_score(state)
    puzzle_number = st.session_state[f"puzzle_number_{prefix}"]
    
    if is_won(state):
        mistakes_used = 4 - state.mistakes_left
        st.success(f"Solved it! {TAGLINES[mistakes_used]} | **Score: {score}**")
    else:
        st.error(f"{LOSS_TAGLINE} | **Score: 0**")
        for group in remaining_groups(state):
            render_banner(group)
            
    if is_won(state):
        st.subheader("Submit your score")
        if f"score_submitted_{prefix}" not in st.session_state:
            st.session_state[f"score_submitted_{prefix}"] = False
            
        if not st.session_state[f"score_submitted_{prefix}"]:
            with st.form(key=f"score_form_{prefix}"):
                name = st.text_input("Your Name", max_chars=20)
                if st.form_submit_button("Submit Score"):
                    if name.strip():
                        save_score(name.strip(), score, puzzle_number)
                        st.session_state[f"score_submitted_{prefix}"] = True
                        st.rerun()
                    else:
                        st.warning("Please enter a name.")
        else:
            st.info("Score submitted to leaderboard!")
            
    st.subheader("Share your result")
    st.code(emoji_grid(state, puzzle_number), language=None)
    st.caption("Copy icon in the top-right of the box — paste it in Teams.")


def render_game_tab(prefix: str, title: str) -> None:
    state: GameState = st.session_state[f"game_{prefix}"]
    puzzle_number = st.session_state[f"puzzle_number_{prefix}"]
    
    st.subheader(f"🏭 {title} #{puzzle_number}")
    st.caption("Group the 16 terms into 4 categories. Four mistakes allowed.")
    if is_won(state) or is_lost(state):
        for group in state.found:
            render_banner(group)
        render_end_screen(state, prefix)
    else:
        render_board(state, prefix)
        render_controls(state, prefix)


def render_leaderboard() -> None:
    st.subheader("🏆 Leaderboard")
    scores = get_top_scores(20)
    if not scores:
        st.info("No scores yet. Be the first!")
    else:
        st.markdown('<div class="leaderboard-box">', unsafe_allow_html=True)
        for i, entry in enumerate(scores):
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
            st.markdown(f"**{medal} {entry.name}**: {entry.score} pts *(Puzzle #{entry.puzzle_id})*")
        st.markdown('</div>', unsafe_allow_html=True)

def main() -> None:
    st.set_page_config(page_title="Plant Connections", page_icon="🏭", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    try:
        init_state()
    except PuzzleBankError as exc:
        st.error(f"Puzzle bank problem: {exc}")
        st.stop()
        
    st.title("Plant Connections")
    
    col_main, col_leaderboard = st.columns([2.5, 1])
    
    with col_main:
        tab1, tab2 = st.tabs(["Daily Puzzle", "Bonus Puzzle"])
        with tab1:
            render_game_tab("daily", "Daily Puzzle")
        with tab2:
            render_game_tab("bonus", "Bonus Puzzle")
            
    with col_leaderboard:
        render_leaderboard()


main()
