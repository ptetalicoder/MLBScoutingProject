# Evaluating and Calling Up Minor League Players

This document explains how the assistant should reason about whether a minor league player is ready to be promoted (especially to MLB) and how to evaluate whether a call-up is appropriate.

## 1. Overall Principles

- Promotions should balance **player development**, **team needs**, and **service-time/contract** considerations.
- Do not focus on a single hot streak; prefer **sustained performance**, age-relative-to-level, and underlying skills.
- Consider both **floor** (can they at least be replacement-level now?) and **ceiling** (upside over 13 years).

## 2. Performance Evaluation

When evaluating a minor leaguer, use a mix of **box-score stats**, **underlying metrics**, and **context**.

### 2.1 Hitters

Key quantitative indicators (when available):

- **Playing time**: games, plate appearances.
- **Production**: AVG, OBP, SLG, OPS, ISO, HR, RBI.
- **Plate discipline**: BB%, K%, K/BB, chase rate if available.
- **Contact quality**: hard-hit%, line-drive%, pull vs opposite-field patterns.
- **Value metrics**: WAR, wOBA, wRC+ relative to league/park.

Contextual questions:

- Is performance **sustained** over a meaningful sample (e.g., half-season or more)?
- How does performance compare to **league-average at that level**?
- Is the player **younger or older** than typical for the level?

### 2.2 Pitchers

Key quantitative indicators (when available):

- **Role**: starter vs reliever; innings pitched.
- **Run prevention**: ERA, xERA, FIP.
- **Dominance**: K%, K/9, whiff%.
- **Control**: BB%, BB/9, K/BB.
- **Contact management**: HR/9, groundball/flyball profile, hard-hit%.
- **Durability**: innings built up, recent workload.

Contextual questions:

- Has the pitcher **handled current level** over a sustained period?
- Does the stuff/command profile suggest they can handle **MLB hitters**?

## 3. Age, Level, and Development Stage

Always consider **age-relative-to-level**:

- Young for level + strong performance = often a sign of advanced talent.
- Old for level + average performance = may be more of a depth piece.

Stages:

- **Lower minors (A-ball)**: focus on tools and development; usually not ready for MLB.
- **Upper minors (AA/AAA)**: performance matters more; players here can be **near-MLB ready**.

The assistant should be cautious about suggesting MLB call-ups for players who:

- Have **minimal upper-minors experience**, or
- Have **large holes** in their game (extreme K rates, poor control, severe platoon issues).

## 4. Positional and Organizational Need

Call-up decisions must consider **team context**:

- Is there a **clear MLB opening** from injury, underperformance, or roster construction?
- Would the player fill a **defined role** (e.g., platoon bat vs RHP, defensive replacement, long reliever)?
- Is there **adequate MLB/AAA depth** already, or is this a true need?

For borderline cases, prefer call-ups when:

- The team is **rebuilding** and can tolerate growing pains.
- The team is out of contention and can evaluate future pieces.

Be more conservative when:

- The team is in a **tight playoff race** and needs reliability.

## 5. Risk, Floor, and Fit

Key questions before recommending a call-up:

1. **Floor**: If this player struggles, can they still provide **defense, baserunning, or innings** at replacement level?
2. **Risk**: Are there red flags (swing-and-miss, control problems, injury history) that make MLB failure likely?
3. **Fit**: Does the players profile (position, handedness, defense) address a **specific need**?

If the answer is "no" to these, it may be better to **keep the player in the minors**.

## 6. Service Time, Options, and Contracts (High Level)

While detailed CBA rules may not be explicitly modeled, the assistant should be aware of:

- **Service time**: calling up a player starts or adds to MLB service time.
- **Option years**: teams typically have several years where they can move a player between MLB and AAA without exposing them to waivers.
- **Super Two / arbitration timing**: early call-ups can accelerate arbitration eligibility and salary.

Guideline:

- For **core long-term prospects**, teams may delay debut slightly to maintain extra control, especially for non-contending seasons.
- For **older prospects or depth pieces**, timing is less critical; focus more on present need.

## 7. Structured Recommendation Format

When the assistant evaluates a potential call-up, responses should include:

1. **Current level and performance**: brief stat summary and context vs league.
2. **Strengths and weaknesses**: tools/skills most relevant to MLB role.
3. **Readiness assessment**: clear statement such as:
   - "Ready for MLB now as a role player/reliever/bench bat."
   - "Needs more time at AA/AAA, especially to improve X."
4. **Recommended role if promoted**: starter, bench/utility, platoon, low-leverage relief, etc.
5. **Risks and upside**: what could go wrong and what the upside outcome could be.

The assistant should avoid definitive guarantees and instead provide **probabilistic, reasoned language** (e.g., "likely to be", "projects as", "could develop into").