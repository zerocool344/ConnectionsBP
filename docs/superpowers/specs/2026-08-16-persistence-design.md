# Plant Connections — Persistence & Cross-Device Design Spec

Sub-project 1 of 2. Adds durable game state so a refresh, a closed tab, or a
switch from desktop to phone resumes the same day's puzzle. Sub-project 2
(stats, streaks, and their UI) reads the history this project writes and is
specified separately.

## Goal

A player opens the app on any device and continues exactly where they left
off, with no login, no password, and nothing to remember during normal play.
Setup cost for the operator is one Supabase project and one pasted connection
string.

## Design priorities

Stated by the project owner, and binding on every decision below:

1. **One-time setup.** Anything the operator would otherwise do by hand — schema
   creation, migrations — the application does for itself.
2. **Seamless play.** No login screen, no code entry, no prompts during the
   normal daily flow. The identity mechanism is invisible unless the player
   deliberately goes looking for it.
3. **Never block the game.** Persistence is an enhancement. If it fails, the
   puzzle still plays.

## Architecture

Five modules, each with one responsibility. `game_engine.py` and
`puzzle_bank.py` are not modified — the engine stays pure and knows nothing
about storage.

1. **`serialization.py`** (pure, no I/O) — converts `GameState` to and from a
   plain dict suitable for a database row, and back.
2. **`store.py`** — the `GameStore` protocol and `InMemoryStore`, an in-process
   implementation used by every test. No network, no database driver.
3. **`db.py`** — `PostgresStore`, the only module that opens a socket. Owns the
   connection, the schema bootstrap, and the SQL.
4. **`player.py`** — player-code generation and browser-side storage of that
   code, including the fallback path.
5. **`app.py`** — wiring only: resolve the player, load the day's game, save
   after each guess, and render the device-linking expander.

### Data flow

On page load: read player code from browser storage → if absent, generate one
and insert a player row → load `(code, today's puzzle_number)` from the games
table → if a row exists, rehydrate `GameState` from it; otherwise start a fresh
game. After every guess that changes state, write the row back.

## Identity: the player code

- Generated on first visit; the player is never asked for anything.
- Eight characters drawn from a 28-character alphabet — the digits and
  uppercase letters, minus `0`, `O`, `1`, `I`, and `L`, which are the pairs
  people confuse when retyping. Displayed grouped as `XXXX-XXXX`; input is
  normalized by uppercasing and stripping non-alphabet characters, so the
  hyphen is cosmetic and paste-friendly.
- Stored in browser localStorage. Cleared storage or a private window means a
  new code and a fresh history — the accepted cost of having no accounts.
- **The code is a bearer token.** Anyone who has it can read and overwrite that
  player's games. There is no password and no recovery. At 28⁸ ≈ 3.8×10¹¹
  combinations it is not guessable, and the asset is a word-game score, so this
  is a deliberate trade of security for zero-friction access. The linking UI
  states it in one line: "Anyone with this code can see and change your games."
- Linking a device: the player opens "Play on another device", reads their code
  from device A, and types it on device B. Entering a code that does not exist
  is rejected with a clear message rather than silently creating a new player,
  so a typo cannot orphan a history.

### Browser storage and its fallback

`streamlit-local-storage` is the primary mechanism. Custom-component iframes
are sandboxed and localStorage access is not guaranteed on every browser and
embed configuration, so `player.py` falls back to a `?player=CODE` query
parameter when a localStorage read fails or returns nothing on a session where
a code was already issued. The fallback keeps the URL shareable-but-private:
the code lives in the address bar, which the linking UI warns about.

## Storage

**Supabase Postgres**, reached with `psycopg` over the connection string in
`st.secrets["postgres"]["url"]`. The Supabase Python client is deliberately not
used: a direct connection can execute DDL, which is what makes self-bootstrapping
schema possible.

### Schema

Created by the application on startup, idempotently:

```sql
create table if not exists players (
  code       text primary key,
  created_at timestamptz not null default now()
);

create table if not exists games (
  code          text not null references players(code) on delete cascade,
  puzzle_number int  not null,
  puzzle_id     int  not null,
  found_tiers   int[]  not null default '{}',
  mistakes_left int    not null,
  guesses       jsonb  not null default '[]',
  word_order    text[] not null,
  status        text   not null,
  updated_at    timestamptz not null default now(),
  primary key (code, puzzle_number)
);
```

One row per player per day. `found_tiers` stores the tiers of solved groups in
the order they were found; the groups themselves rehydrate from `puzzles.json`,
keeping puzzle content canonical in exactly one place. `status` is
`in_progress`, `won`, or `lost`. Writes are `INSERT ... ON CONFLICT (code,
puzzle_number) DO UPDATE`, so a save is idempotent and last-write-wins — the
correct semantic when the same player has two tabs open.

The schema bootstrap runs once per process, guarded by an `@st.cache_resource`
connection factory, so it does not re-run on every rerun.

### Secrets

`.streamlit/secrets.toml` holds the connection string locally and is
git-ignored. On Streamlit Cloud the same content is pasted into the app's
secrets box. The connection string is never committed, logged, or displayed —
including in error messages, which are caught and replaced with a generic
warning before reaching the UI.

## Failure handling

Persistence failures degrade; they never crash and never block play.

- Any store error on load → start a fresh session-only game, show one warning:
  "Progress saving is unavailable right now — your game will still work, but it
  won't be saved."
- Any store error on save → keep playing, keep the same warning visible, do not
  retry in a loop and do not lose in-memory state.
- Missing or malformed secrets → same degraded mode. A developer running the
  app with no database configured gets a working game, not a stack trace.
- The warning is rendered once per session, not once per rerun.

## Testing

Everything except the Postgres adapter is tested without a network:

- **Serialization:** round-trip `GameState` → row → `GameState` preserves found
  groups and their order, mistakes, guess history, and board order; a completed
  game round-trips with the right status; an unstarted game round-trips.
- **Store contract:** `InMemoryStore` covers create/exists/load/save, save
  overwrites the same (code, puzzle) key, loading an absent game returns `None`,
  and loading another player's game does not leak across codes.
- **Player code:** generated codes are 8 characters, contain no ambiguous
  characters, are formatted `XXXX-XXXX` for display, and normalize correctly
  from messy input (lowercase, spaces, missing hyphen).
- **Degradation:** a store stubbed to raise on every call still yields a
  playable game and sets the warning flag exactly once.

`PostgresStore` itself is verified manually against a real Supabase project —
its logic is thin SQL, and mocking a database driver would test the mock. The
manual check is written into the plan as an explicit step.

## Operator setup (one time)

1. Create a free Supabase project.
2. Copy the connection string (Session pooler) from Project Settings → Database.
3. Paste it into `.streamlit/secrets.toml` locally and into the Streamlit Cloud
   secrets box for the deployed app.

No SQL to run and no schema step: the app creates its tables on first start.

## Out of scope (this sub-project)

- Stats, streaks, win-rate, guess distribution, and the stats panel — sub-project 2
- Accounts, passwords, email, SSO, and code recovery
- Server-side leaderboards or any comparison between players
- Offline play and conflict resolution between simultaneous devices
  (last-write-wins is the stated semantic)
- Data retention or deletion policy beyond `on delete cascade`
