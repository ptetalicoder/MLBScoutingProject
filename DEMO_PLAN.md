# Demo Plan — public Streamlit deployment

Goal: a free, public, click-through demo of this project on Streamlit Community Cloud,
with no database server and a capped OpenAI bill.

**Target architecture:** SQLite file committed to the repo → Streamlit Community Cloud →
local ONNX embeddings for retrieval → one OpenAI generation call per question, rate
limited.

Work through the steps in order. Each step ends in a working state, so it is safe to stop
between them.

---

## Status

- [x] **Step 1 — SQLite ETL.** `db.py`, `init_sqlite_db.py`,
      `05_DDL_schema_v1_sqlite.sql`, and all 8 `data_import_*.py` scripts migrated.
      `mlb_scouting.db` built: 5,765 players across 5 levels, 10,005 hitter-season rows,
      12,043 pitcher-season rows, 5,765 scouting reports, 733 contracts, 150 teams,
      120 team-season records, seasons 2021–2024.
- [x] **Step 2** — Finish the SQLite migration (app, CRUD, RAG builders)
- [x] **Step 3** — Get the app running locally end to end
- [x] **Step 4** — Demo safety (read-only SQL, per-session CRUD, rate limits)
- [x] **Step 5** — Local embeddings for RAG
- [ ] **Step 6** — Deploy to Streamlit Community Cloud
- [ ] **Step 7** — Screenshots, README, portfolio link

> **Already handled:** Step 1's work is committed (`5708618 Add SQLite adapter and
> migrate ETL pipeline off MySQL`). `Trade` and `TradeDetails` are empty — no trade
> data was ever imported — and that's already noted in `schema_notes.md`.

---

## Step 2 — Finish the SQLite migration

Three files still talk to MySQL.

**`07_mlb_assistant_app.py`**

- Replace `import mysql.connector` + the `DB_CONFIG` dict + the local
  `create_db_connection()` with `from db import create_db_connection`.
- Replace every `mysql.connector.Error` with `sqlite3.Error` (appears at roughly lines
  146, 164, 185, 237, 289, 311, and further down).
- Convert every `%s` query placeholder to `?`.
- **Remove `mysql.connector`-only API calls that don't exist on `sqlite3` objects.**
  `conn.is_connected()` and `cursor(dictionary=True)` both appear in this file and
  will raise at runtime even after the connection swap. Drop `is_connected()` checks
  (a `sqlite3.Connection` is either open or the call already failed) and drop the
  `dictionary=True` kwarg — `db.py`'s `create_db_connection()` already sets
  `row_factory = sqlite3.Row`, so rows support dict-style `row["col"]` access without it.
- **`get_db_schema(conn)` needs rewriting.** It currently introspects MySQL. For SQLite,
  read `sqlite_master` for table names and `PRAGMA table_info(<table>)` for columns.
- **The SQL-generation prompt tells the model it is writing MySQL.** Change it to SQLite,
  or the model will emit MySQL-only syntax that fails at execution.

**`player_crud.py`** — 10 `%s` placeholders to convert to `?`, and its connection call.

**`rag_build_player_profiles.py`** and **`rag_build_team_profiles.py`** — same connection
swap. Leave their embedding function alone for now; Step 5 handles that.

**Done when:** `grep -rn "mysql" *.py` returns nothing, and
`grep -rn "is_connected(\|dictionary=True" *.py` also returns nothing.

> **Also found and fixed while migrating:** `CONCAT(FirstName, ' ', LastName)` isn't
> valid SQLite (switched to `||`), and ~130 call sites do `row.get(...)` on query
> results — inherited from mysql.connector's `dictionary=True` dict rows — which
> breaks against plain `sqlite3.Row` (no `.get()`). Added `dict_row_factory` to
> `db.py`: the connection keeps `sqlite3.Row` as its default (positional-tuple code in
> the Analytics Dashboard depends on it), and any cursor that needs `.get()` sets
> `cursor.row_factory = dict_row_factory` individually.

---

## Step 3 — Get it running locally

```bash
.venv/Scripts/python.exe -m streamlit run 07_mlb_assistant_app.py
```

Walk all four sidebar modules and fix what breaks.

**Expect breakage here.** The venv has **pandas 3.0** and **altair 6**, both a major
version ahead of what this code was written against. pandas 3 changed copy-on-write
semantics; altair 6 adjusted chart APIs. The Analytics Dashboard is the likely casualty.
Fix forward — do not downgrade, since the pinned versions are what Streamlit Cloud will
install.

> **What actually broke (pandas 3/altair 6 turned out fine):** three unrelated bugs,
> all fixed:
> 1. `sqlite3.connect()` defaults to `check_same_thread=True`, but Streamlit runs each
>    rerun on a fresh thread while `@st.cache_resource` keeps the same connection alive
>    across reruns — every interaction after the first crashed with "SQLite objects
>    created in a thread can only be used in that same thread." Fixed by passing
>    `check_same_thread=False` in `db.py` (safe here: one query at a time, no real
>    concurrent access).
> 2. `client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))` at module level now raises
>    immediately when the key is missing (no local `.env` exists yet), instead of
>    failing lazily on first call like the code assumed — this crashed the app on
>    every section, not just the ones that call OpenAI. Fixed by only constructing the
>    client when a key is present and checking `client is None` at the two call sites.
> 3. The no-key SQL Chat fallback and the scatter-plot's "no top players" branch both
>    had pre-existing bugs (a `Player.FullName`/`TeamID` column that never existed, and
>    an `if df_scatter.empty:` block dedented outside the `else:` that defines
>    `df_scatter`, so it read the variable unset when the query returned zero rows).
>    Fixed both.

The Scouting Assistant will fail until Step 5 builds the Chroma collections. That is
expected; skip it for now.

**Done when:** SQL Chat, Analytics Dashboard, and CRUD all work against `mlb_scouting.db`.

---

## Step 4 — Demo safety

This app will be public. Three things must change.

**Block non-SELECT SQL.** The app executes LLM-generated SQL directly. On a public demo
that is a `DROP TABLE` waiting to happen. Parse the generated statement and reject
anything that is not a single `SELECT`. Also open the demo connection in read-only mode
(`file:mlb_scouting.db?mode=ro` via `sqlite3.connect(..., uri=True)`).

**Per-session CRUD sandbox.** CRUD needs writes, so it cannot use the read-only
connection. On session start, copy `mlb_scouting.db` to a temp file and point CRUD at the
copy. Every visitor gets their own sandbox that resets on refresh, and the committed
database is never mutated. Cache it on `st.session_state`.

**Rate limit the LLM.** Cap questions per session (5–10 is plenty to demo), cap
`max_tokens`, and read the key from `st.secrets` with a fallback to `os.getenv` for local
runs. When the cap trips, show a canned example answer and a short note explaining the
demo limit rather than an error.

**Done when:** a hostile visitor cannot damage the data or run up the bill.

> **Implemented:** `db.py` gained `create_readonly_connection()` (SQLite URI
> `?mode=ro`, confirmed writes raise `OperationalError: attempt to write a readonly
> database`) for SQL Chat + Analytics Dashboard, and `create_sandbox_connection()`
> (copies `mlb_scouting.db` to a temp file) for CRUD, cached per-session on
> `st.session_state["crud_conn"]` — confirmed a write through the sandbox does not
> appear in the real database. `run_sql_query()` now rejects anything that isn't a
> single `SELECT` via `is_safe_select_query()` (regex-based: single statement, starts
> with `SELECT`, no `INSERT`/`DROP`/`ATTACH`/`PRAGMA`/etc. anywhere) before it ever
> reaches the connection — defense in depth alongside the read-only connection.
> Both `generate_sql_from_prompt()` and `call_scouting_llm()` now cap paid OpenAI
> calls at 8 per browser session (`st.session_state["llm_calls_used"]`); once tripped,
> SQL Chat falls back to an example query and the Scouting Assistant returns a
> labeled example answer, both with a note instead of an error. The API key now reads
> from `st.secrets` first (for Streamlit Cloud) and falls back to `os.getenv` (for
> local `.env` runs) — `st.secrets.get(...)` was confirmed to raise
> `StreamlitSecretNotFoundError` when no `secrets.toml` exists at all, so that read is
> wrapped in a try/except.

---

## Step 5 — Local embeddings

Right now every retrieval calls OpenAI to embed the query. Moving to Chroma's built-in
ONNX embedder makes retrieval free and offline, leaving exactly one OpenAI call per
question.

- In both `rag_build_*.py` scripts and in the app's `get_chroma_client_and_collections()`,
  swap `embedding_functions.OpenAIEmbeddingFunction(...)` for
  `embedding_functions.DefaultEmbeddingFunction()`. (Verified present in chromadb 1.5.9.)
- Delete any existing `.chromadb/` and rebuild both collections — embeddings from a
  different model are not compatible with the old ones.
- **Do not use `sentence-transformers`.** It pulls in PyTorch and will exceed Streamlit
  Community Cloud's memory limit. The ONNX default is the point.
- Commit `.chromadb/`. It is currently gitignored, so un-ignore it deliberately. Check the
  size first — if it lands near 100 MB, reconsider.

**Done when:** the Scouting Assistant answers with no OpenAI key set for embeddings, and
`player_season_profiles` / `team_season_profiles` both rebuild cleanly.

> **Implemented, with a scope change from the size check:** embedding all four seasons
> (2021–2024) produced a 244MB `chroma.sqlite3` — over GitHub's 100MB hard per-file push
> limit, not just "large." Discussed with the user; chose to scope
> `player_season_profiles` down to 2024 only (`rag_build_player_profiles.py`'s `__main__`
> now calls `build_player_profiles(2024, 2024)` — 5,768 docs instead of 22,051).
> `team_season_profiles` stays the full 2021–2024 range (120 docs, never the size
> problem). Final `.chromadb/` is 73MB. **Trade-off to know about:** the Scouting
> Assistant's RAG retrieval only has 2024 player-season context now — SQL Chat and the
> Analytics Dashboard are unaffected since they query `mlb_scouting.db` directly across
> the full 2021–2024 range. Verified end-to-end: `retrieve_rag_context()` returns real
> player + team context (22.6k chars) with zero OpenAI calls and no key set; the
> Scouting Assistant's final answer step correctly still asks for a key (by design —
> the one paid call per question is generation, not retrieval).

---

## Step 6 — Deploy

**`.gitignore` currently ignores `*.db`.** The demo requires `mlb_scouting.db` in the
repo. Add an exception (`!mlb_scouting.db`) and commit it — 4.4 MB is fine.

Add `.streamlit/config.toml` if any theming is wanted, then:

1. Push everything.
2. Go to **share.streamlit.io**, connect the GitHub repo, set the main file to
   `07_mlb_assistant_app.py`.
3. Paste `OPENAI_API_KEY` into the app's **Secrets** box. Never commit it.
4. **Set a hard spend limit on the OpenAI account before sharing the URL anywhere.**

First boot installs everything in `requirements.txt` and takes a few minutes. If it OOMs,
the cause is almost certainly the embedding model — revisit Step 5.

**Done when:** the public URL loads and all four modules work for a logged-out visitor in
a private window.

---

## Step 7 — Wire it up

- Take three screenshots: the Analytics Dashboard, a SQL Chat query showing its generated
  SQL, and a Scouting Assistant answer with the retrieved-context panel.
- Save to `docs/` as `screenshot-dashboard.png`, `screenshot-sql-chat.png`,
  `screenshot-scouting-assistant.png`, then delete the `<!--` / `-->` markers around the
  three image tags in `README.md`.
- Update the README: replace the "not deployable as a click-through demo" note near the
  top with the live URL, and revise the setup section, which still describes MySQL.
- Add the demo link to the portfolio. In `Portfolio/src/data/resume.js`, the MLB project's
  `links` array takes a second entry:

  ```js
  links: [
    { label: 'Live demo', href: 'https://<your-app>.streamlit.app' },
    { label: 'View source on GitHub', href: 'https://github.com/ptetalicoder/MLBScoutingProject' },
  ]
  ```

  The first entry becomes the card's click target, so putting the demo first sends
  visitors to the running app rather than the code.

---

## Notes

- The MLB Stats API needs no key, so the dataset is always reproducible: `init_sqlite_db.py`
  then the eight import scripts in dependency order (leagues/teams → players → stats →
  contracts → synthetic).
- Minor league stats and scouting grades are synthetic. The README says so; keep it that
  way.
- If Step 4 or 5 turns into a slog, ship without the Scouting Assistant. A live dashboard
  beats a stalled deploy — hide that sidebar option and add it in a follow-up.
