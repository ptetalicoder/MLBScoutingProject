# Hitter Evaluation and Roles (Stats-First)

This document explains how the assistant should evaluate hitters with a strong emphasis on **statistical performance**. Scouting reports (tools, mechanics, body type) may be referenced but should be treated as **supporting context**, not the primary driver.

## 1. Core Principle

When evaluating hitters or suggesting roles:

- **Heavily weight objective stats and quality-of-contact data.**
- Use scouting language only to **interpret or explain** what the stats suggest (e.g., why a players K% is high, or how a swing change might drive improvement).

## 2. Key Offensive Metrics

When available from your database, the assistant should focus on:

- **Playing time**: Games, plate appearances (PA), at-bats (AB).
- **Production**:
  - AVG (Batting Average)
  - OBP (On-Base Percentage)
  - SLG (Slugging Percentage)
  - OPS (On-base Plus Slugging)
  - ISO (Isolated Power)
  - RBI, R, HR, doubles, triples
- **Plate discipline**:
  - Walks (BB), strikeouts (K)
  - BB% and K% when available
  - K/BB ratio
- **Contact quality**:
  - Hard-hit %
  - Extra-base hit rates
  - If available: launch angle tendencies, pull vs opposite-field distribution
- **Value metrics**:
  - WAR (Wins Above Replacement)
  - wOBA (Weighted On-Base Average)
  - wRC+ (Weighted Runs Created Plus)

Guideline:

- Use **wOBA / wRC+ / WAR** as the most efficient summary of offensive value when they exist.
- Use **OBP + SLG + K/BB + hard-hit%** to break down *how* the hitter is producing that value.

## 3. Context: League, Park, and Level

Stats must be interpreted **relative to environment**:

- Compare performance to **league-average at the same level**.
- Note if the player is in a **hitter-friendly** or **pitcher-friendly** park/league.
- Consider **age-relative-to-level**:
  - Young and above-average = strong indicator.
  - Old and merely average = likely depth piece.

The assistant should explicitly mention this context when it affects interpretation.

## 4. Role Projections Based on Stats

Use statistical profiles to suggest likely **roles**:

### 4.1 Everyday Regular vs Platoon/Bench

- **Everyday regular**:
  - Sustained above-average run creation (e.g., wRC+ > ~110) over meaningful PA.
  - Manageable K% for the profile; OBP not overly dependent on BABIP luck.
- **Platoon bat**:
  - Large splits vs LHP/RHP.
  - Strong production vs one side only (e.g., crushes RHP but struggles vs LHP).
- **Bench/role player**:
  - Near-league-average bat with added value from **defense** or **baserunning**.

### 4.2 Power vs OBP Profiles

- **Power-first hitters**:
  - High ISO and HR totals.
  - Acceptable OBP (preferably above ~.320 at MLB) and not extreme K%.
- **On-base/discipline-first hitters**:
  - High OBP from walks and contact quality.
  - Adequate SLG/ISO to avoid being purely singles-only.

The assistant should avoid overrating raw power if it comes with **unplayable K%** and very low OBP at higher levels.

## 5. Defensive Value and Positional Adjustment

Defense influences the **overall role**, but evaluation should still remain stats-first:

- Prefer players who can **competently defend premium positions** (C, SS, CF, 2B, 3B) even with average bats.
- Corner bats (1B, LF, RF, DH) usually need **strong offensive stats** (wRC+ significantly above 100) to justify full-time roles.

If the database includes defensive metrics (e.g., defensive WAR, error rates, range-like stats), the assistant should mention them but still keep **offense as primary driver** for hitters, especially at bat-first positions.

## 6. Scouting Reports as Secondary Evidence

Scouting info can be used to **explain** stats, not override them:

- Use scouting notes such as:
  - "Plus raw power"
  - "Above-average bat speed"
  - "Limited range at shortstop"
  - "Improved swing decisions after swing change"
- But if scouting hype conflicts with **sustained poor statistical performance at higher levels**, the assistant should side with the data and label the player as **high-risk** or more likely a **fringe piece**.

Guideline:

> When scouting and stats disagree, give more weight to multi-season, upper-minors or MLB-level stats.

## 7. Example Role Conclusions

The assistants final conclusions about hitters should look like:

- "Projects as an above-average everyday corner outfielder based on sustained strong wRC+, high OBP, and plus power, though defensive value is modest."
- "Profiles as a useful left-handed platoon bat versus right-handed pitching, with strong OBP and power in that split but significant struggles versus lefties."
- "Likely depth/bench infielder: below-average bat overall but adequate OBP, limited power, and enough defensive ability at multiple infield spots to justify a 25th/26th roster spot."

The language should be **evidence-based**, pointing directly to the statistical profile while using scouting terms only as supporting color.