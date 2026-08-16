# 🏭 Plant Connections

A daily Connections-style word game for mechanical engineers at a
chemical manufacturing site. Group 16 plant terms into 4 hidden
categories. New puzzle every day; four mistakes allowed.

## Run locally

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
    .venv/bin/streamlit run app.py

## Tests

    .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
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
