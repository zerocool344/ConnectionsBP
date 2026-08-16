# Plant Connections — Design Spec

A daily NYT-Connections-style word game themed around mechanical engineering at a chemical manufacturing site. Built with Streamlit, deployed to Streamlit Cloud.

## Goal

Coworkers at a chemical manufacturing site play one shared puzzle per day: group 16 terms into 4 hidden categories drawn from plant equipment, instrumentation, maintenance, and process safety. Shareable emoji results drive a daily habit in Teams/chat.

## Architecture

Three units, one seam:

1. **`game_engine.py`** — pure Python game logic. No Streamlit imports. Fully unit-testable.
2. **`puzzle_bank.py`** — loads and validates `puzzles.json`; deterministic daily puzzle selection.
3. **`app.py`** — Streamlit shell. Holds `GameState` in `st.session_state`, injects CSS once, renders UI. All board drawing goes through a single `render_board(state)` function — the seam that lets a custom HTML/JS component replace pure-Streamlit rendering later (approach C: start simple, keep the upgrade path).

Data flow: today's date → `puzzle_bank.puzzle_for_date()` → `game_engine.GameState` → `render_board()`. No backend, no accounts, no server-side storage.

### File layout

```
app.py
game_engine.py
puzzle_bank.py
puzzles.json
requirements.txt
tests/test_game_engine.py
tests/test_puzzle_bank.py
```

## Game engine

### Data model

- `Group`: `tier: int` (1–4), `name: str`, `words: tuple[str, ...]` (exactly 4).
- `Puzzle`: `id: int`, `groups: tuple[Group, ...]` (exactly 4, tiers 1–4 each appearing once). Property `all_words` → 16 words.
- `GameState`: `puzzle: Puzzle`, `found: list[Group]` (in order found), `mistakes_left: int` (starts 4), `guesses: list[frozenset[str]]` (every submitted guess, correct and wrong, in order), `word_order: list[str]` (current board arrangement).

### Guess results

`submit_guess(state, words: set[str]) -> GuessResult` where `GuessResult` is an enum:

- `CORRECT` — the 4 words exactly match an unfound group. Group moves to `found`; its words leave the board.
- `ONE_AWAY` — exactly 3 of the 4 words belong to one unfound group. Costs a mistake.
- `WRONG` — anything else. Costs a mistake.
- `ALREADY_GUESSED` — the same 4-word set was submitted before. No mistake charged, guess not re-recorded.

All submitted guesses (except `ALREADY_GUESSED`) append to `guesses` for the share grid.

- `is_won(state)` — all 4 groups found.
- `is_lost(state)` — `mistakes_left == 0`.
- On loss, the UI reveals remaining groups in tier order (1 → 4).

### Share text

`emoji_grid(state, puzzle_number: int) -> str` produces:

```
Plant Connections #12
🟨🟨🟨🟨
🟩🟦🟩🟩
🟩🟩🟩🟩
...
```

One row per recorded guess, in order. Each word maps to its group's tier emoji: tier 1 🟨, tier 2 🟩, tier 3 🟦, tier 4 🟪. Wrong guesses show mixed rows — that's the story people share.

## Puzzle bank

### Format (`puzzles.json`)

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
    }
  ]
}
```

### Validation (at load, fail loud)

- Exactly 4 groups per puzzle; tiers are exactly {1, 2, 3, 4}.
- Exactly 4 words per group; 16 words unique within a puzzle (case-insensitive).
- Unique puzzle ids; `launch_date` parses as ISO date.
- Invalid bank → `PuzzleBankError` with a message naming the offending puzzle id; `app.py` shows a clear error page instead of crashing.

### Daily selection

`puzzle_for_date(bank, today) -> tuple[Puzzle, int]`:

- `day_number = (today - launch_date).days` (before launch date: day 0's puzzle, numbered #1).
- Puzzle index = `day_number % len(puzzles)` — deterministic, same for everyone, cycles when the bank runs out.
- Puzzle number for display/share = `day_number + 1`.

### Content

15 starter puzzles drafted by Claude, reviewed/corrected by the user for site accuracy. Category domains: rotating equipment, valves/piping, instrumentation & P&ID, maintenance/reliability (bearings, lubrication, vibration analysis), process safety (PSM, relief systems, permits). Each puzzle includes deliberate trap words that plausibly fit two categories (e.g. GLAND fits both pump parts and seal types) — the tier-4 category leans on wordplay or abbreviation knowledge.

## Gameplay & UI

NYT-standard rules:

- 16 tiles in a 4×4 grid. Click to select/deselect; max 4 selected. Submit enabled only at exactly 4.
- 4 mistakes allowed, shown as dots that deplete.
- `ONE_AWAY` → toast "One away!". `ALREADY_GUESSED` → toast "Already guessed", no penalty.
- Wrong guess → CSS shake on selected tiles.
- Correct guess → group collapses into a colored banner (tier color) with fade-in; banners stack above the remaining grid in the order found.
- Shuffle and Deselect-all buttons.
- Loss → remaining groups auto-reveal in tier order.
- End screen (win or loss): all four banners, result emoji grid, copy-to-clipboard share text, title "Plant Connections #N".

### Tier theming

| Tier | Color | Flavor name |
|------|-------|-------------|
| 1 | Yellow | Operator |
| 2 | Green | Technician |
| 3 | Blue | Engineer |
| 4 | Purple | Plant Manager |

End-screen tagline by mistakes used: 0 → "Plant Manager material", 1 → "Senior Engineer", 2 → "Solid Technician", 3 → "Operator in training", loss → "Back to the control room". (Copy editable in one dict in `app.py`.)

### State & rendering

- `GameState` lives in `st.session_state`; survives Streamlit reruns within a session. Page refresh resets the game — acceptable for v1, no persistence.
- CSS (tile colors, shake animation, banner fade) injected once per run via `st.markdown(unsafe_allow_html=True)`.
- Animations are CSS-only in v1. If they feel weak, `render_board()` is the single function a custom HTML/JS component replaces — no engine or bank changes.

## Error handling

- Malformed `puzzles.json` → friendly error page ("Puzzle bank problem: <detail>"), app does not crash.
- Engine functions raise `ValueError` on invalid input (guess size ≠ 4, words not on board) — UI prevents these; the raise is a test-visible contract, not a user path.

## Testing

- **pytest, engine:** correct/one-away/wrong/duplicate guesses, mistake accounting, win/loss detection, loss reveal order, emoji grid output (exact string), word removal after correct guess.
- **pytest, bank:** validation rejects each malformation class (wrong group count, dup words, bad tiers, dup ids), date selection determinism (fixed dates → fixed puzzle + number), modulo cycling.
- **UI:** no automated tests; manual verification by running the app.

## Deployment

- Streamlit Cloud, `requirements.txt` pins `streamlit` (latest stable at build time).
- Repo pushed to GitHub (user's account) — required by Streamlit Cloud. Public repo acceptable: content is a word game, no site-confidential data. Puzzle words/categories stay generic industry terminology, not site-specific unit names.

## Out of scope (v1)

- Streaks, stats, or any persistence across sessions
- Accounts/auth
- Puzzle editor UI (JSON edited by hand)
- Custom HTML/JS board component (seam exists; build only if CSS animations disappoint)
- Mobile-specific layout work beyond Streamlit defaults
