# RAG Query Enricher Guidelines

The goal of the query enricher is to turn the user's free-text scenario into a richer search signal
that helps retrieve the most relevant player and team documents from Chroma.

**It never changes the user's original question.**  
It only outputs a short "hint string" that will be appended to the query used for retrieval.

---

## 1) Team / Organization Context

Recognize when the user is talking about a specific team or organization and add hints.

- Map common phrases to canonical team names, e.g.:
  - "Yankees", "New York Yankees", "NYY" → `team=New York Yankees`
  - "Red Sox", "Boston Red Sox" → `team=Boston Red Sox`
  - "Dodgers", "Los Angeles Dodgers", "LAD` → `team=Los Angeles Dodgers`
  - "Orioles", "Baltimore Orioles" → `team=Baltimore Orioles`
  - (The enrichment code may maintain a simple mapping of common aliases to full names.)

- Generic organization phrases:
  - "in our system", "our farm system", "our prospects" → add `scope=organization_prospects`.

- Trade counterpart:
  - "trade with the Dodgers", "send him to the Mariners" → add an additional
    `counterparty_team=<Team Name>` hint.

Hints to include:
- `team=<Canonical Team Name>`
- `scope=organization_prospects`
- `counterparty_team=<Canonical Team Name>`

---

## 2) Position / Role Hints

Recognize positions and roles to bias retrieval to appropriate players.

- Position keywords and their canonical forms:
  - "catcher" → `positions=C`
  - "first base", "1B" → `positions=1B`
  - "second base", "2B" → `positions=2B`
  - "third base", "3B" → `positions=3B`
  - "shortstop", "SS", "short stop" → `positions=SS`
  - "left field", "LF", "left fielder" → `positions=LF`
  - "center field", "CF", "center fielder" → `positions=CF`
  - "right field", "RF", "right fielder" → `positions=RF`
  - "outfield", "outfielder" → `positions=LF,CF,RF`
  - "utility", "super-utility" → `positions=UT`
  - "DH", "designated hitter" → `positions=DH`

- Pitching roles:
  - "starting pitcher", "starter", "rotation" → `roles=SP`
  - "reliever", "relief pitcher" → `roles=RP`
  - "closer", "ninth-inning guy" → `roles=CP`
  - "high-leverage reliever", "setup man" → `roles=RP,high_leverage`

Hints to include:
- `positions=<comma-separated canonical position codes>`
- `roles=<comma-separated role hints>`

---

## 3) Level / Development Stage

Detect which levels are relevant for the question.

- Level keywords:
  - "MLB", "big leagues", "majors" → `levels=MLB`
  - "AAA", "Triple-A", "Triple A" → `levels=AAA`
  - "AA", "Double-A", "Double A" → `levels=AA`
  - "High-A" → `levels=High-A`
  - "A-ball", "A ball", "Low-A" → `levels=A`
  - "rookie ball", "complex league" → `levels=Rookie`
  - "college" → `levels=College`

- Implicit for call-ups:
  - If a "call up / promotion" question mentions an MLB team but no level,
    assume `levels=AAA,AA` ("upper minors").

- Implicit for long-term prospect interest:
  - Phrases like "long-term upside", "3–5 year horizon" can justify adding
    `levels=MiLB_all` (do not exclude lower levels).

Hints to include:
- `levels=<comma-separated levels>`
- `levels_inferred_from_callup=AAA,AA` when relevant.

---

## 4) Timeframe / Season

Infer which seasons or timeframe matter.

- Explicit:
  - "in 2021", "for the 2022 season" → `years=2021`, `years=2022`
  - "over the last three years" → if current year ~2024, treat as `years=2022,2023,2024`.

- Implicit:
  - "this year", "this season" → current season, e.g. `years=2024`.
  - "last season" → `years=2023` (assuming current season 2024).

If no explicit or obvious hint:
- Favor the most recent seasons, e.g. `years_prioritized=2022,2023,2024`.

Hints to include:
- `years=<comma-separated years>`
- `years_prioritized=<comma-separated years>`

---

## 5) Decision Type / Intent

Classify the user question into one (or more) of these decision types:

1. **Call-up decision**
   - Keywords:
     - "call up", "call-up", "promote", "promotion to the majors",
       "is he ready for the majors?", "bring him up".
   - Hint: `intent=CALL_UP_DECISION`.

2. **Trade proposal / evaluation**
   - Keywords:
     - "trade", "swap", "deal", "package", "deadline move", "sell high", "buy low".
   - Hint: `intent=TRADE_EVALUATION`.

3. **Roster construction / role change**
   - Keywords:
     - "roster construction", "depth chart", "move him to", "platoon",
       "bench role", "starting job", "change positions".
   - Hint: `intent=ROSTER_CONSTRUCTION`.

4. **Contract / salary decision**
   - Keywords:
     - "extension", "contract", "arbitration", "arb", "club control",
       "team control", "free agency", "FA", "non-tender", "option year".
   - Hint: `intent=CONTRACT_DECISION`.

Hints to include:
- `intent=<one of the above>`
- Multiple intents can be included if necessary, separated by commas.

---

## 6) Constraints / Preferences

Capture higher-level preferences that affect what kinds of players/teams are ideal.

- Competitive window:
  - "we are rebuilding", "rebuild", "long-term focus" → `competitive_window=REBUILD`.
  - "contending", "title window", "World Series or bust" → `competitive_window=CONTEND`.
  - "fringe playoff team", "wild card race", "on the bubble" → `competitive_window=FRINGE_CONTENDER`.

- Risk tolerance:
  - "we want to be conservative", "minimize risk" → `risk_tolerance=LOW`.
  - "willing to gamble", "high-upside swing" → `risk_tolerance=HIGH`.

- Time horizon:
  - "this year only", "short term", "rest of this season" → `time_horizon=SHORT_TERM`.
  - "next 3–5 years", "long-term core", "multi-year window" → `time_horizon=LONG_TERM`.

Hints to include:
- `competitive_window=<value>`
- `risk_tolerance=<value>`
- `time_horizon=<value>`

---

## 7) Specific Player / Team Mentions

Extract explicit named entities and reflect them as hints.

- Player names:
  - E.g., "Adley Rutschman", "Corbin Burnes" → `players=Adley Rutschman,Corbin Burnes`.
  - Use simple heuristics like capitalized word pairs to detect likely player names.

- Additional team aliases:
  - "O's" → `team=Baltimore Orioles`
  - "Cards", "Redbirds" → `team=St. Louis Cardinals`
  - "Halos" → `team=Los Angeles Angels`
  - (The enricher code can maintain a small alias dict.)

Hints to include:
- `players=<comma-separated player names>`
- Additional `team=<Canonical Team Name>` hints if discovered via alias.

---

## Enricher Output Format

Given the user's raw question, the enricher should output a concise hint string like:

`[HINTS] team=Baltimore Orioles; positions=CF,OF; levels=AAA,AA; intent=CALL_UP_DECISION; time_horizon=SHORT_TERM; competitive_window=CONTEND`

The application will combine this hint string with the user's original question when querying Chroma:

`<user_question>\n\n[HINTS] ...`

Downstream, the retrieval code also parses some of these hints to build
metadata filters for Chroma. In particular:

- When `team=<Canonical Team Name>` is present, player retrieval is
  biased to documents whose metadata includes
  `parent_mlb_team_name=<Canonical Team Name>`. This means a question
  about the Baltimore Orioles will preferentially search across players
  in the Orioles organization (MLB + affiliates) when looking for
  call-ups or depth options.

The LLM is **not** passed the hint string directly; it is only used to
steer vector search and metadata filtering.
