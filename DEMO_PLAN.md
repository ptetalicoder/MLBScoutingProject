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
- [ ] **Step 2** — Finish the SQLite migration (app, CRUD, RAG builders)
- [ ] **Step 3** — Get the app running locally end to end
- [ ] **Step 4** — Demo safety (read-only SQL, per-session CRUD, rate limits)
- [ ] **Step 5** — Local embeddings for RAG
- [ ] **Step 6** — Deploy to Streamlit Community Cloud
- [ ] **Step 7** — Screenshots, README, portfolio link

> **Before anything else:** Step 1's work is currently uncommitted. Commit it.
> Note that `Trade` and `TradeDetails` are empty — no trade data was ever imported. Either
> leave them out of the demo's scope or note it in `schema_notes.md` so the SQL generator
> does not write queries against empty tables.

---

## Step 2 — Finish the SQLite migration

Three files still talk to MySQL.

**`07_mlb_assistant_app.py`**

- Replace `import mysql.connector` + the `DB_CONFIG` dict + the local
  `create_db_connection()` with `from db import create_db_connection`.
- Replace every `mysql.connector.Error` with `sqlite3.Error` (appears at roughly lines
  146, 164, 185, 237, 289, 311, and further down).
- Convert every `%s` query placeholder to `?`.
- **`get_db_schema(conn)` needs rewriting.** It currently introspects MySQL. For SQLite,
  read `sqlite_master` for table names and `PRAGMA table_info(<table>)` for columns.
- **The SQL-generation prompt tells the model it is writing MySQL.** Change it to SQLite,
  or the model will emit MySQL-only syntax that fails at execution.

**`player_crud.py`** — 10 `%s` placeholders to convert to `?`, and its connection call.

**`rag_build_player_profiles.py`** and **`rag_build_team_profiles.py`** — same connection
swap. Leave their embedding function alone for now; Step 5 handles that.

**Done when:** `grep -rn "mysql" *.py` returns nothing.

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
