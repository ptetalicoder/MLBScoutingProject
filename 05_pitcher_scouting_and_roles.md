# Pitcher Evaluation and Roles (Stats-First)

This document explains how the assistant should evaluate pitchers and assign likely roles, with a strong emphasis on **statistical performance**. Scouting reports (velocity, pitch shapes, arm slot) can be used to interpret stats but should not override clear, sustained performance trends.

## 1. Core Principle

When evaluating pitchers:

- **Rely primarily on objective metrics** (run prevention, strikeouts, walks, batted-ball profile) over multiple seasons/levels.
- Use scouting information to **explain why** the stats look the way they do or how they might change, not to contradict extended statistical evidence.

## 2. Key Pitching Metrics

Where available, the assistant should focus on:

- **Run prevention**:
  - ERA (Earned Run Average)
  - xERA (Expected ERA)
  - FIP (Fielding Independent Pitching)
- **Dominance and strikeout ability**:
  - Strikeouts (K), K/9
  - K% and whiff%
- **Control and command**:
  - Walks (BB), BB/9, BB%
  - K/BB ratio
- **Contact management**:
  - Home runs allowed (HR), HR/9
  - Groundball vs flyball tendencies (if available)
  - Hard-hit%
- **Durability and workload**:
  - Innings pitched
  - Games started vs relief appearances

WAR or similar value metrics can be used as a **summary measure** when present.

## 3. Role Determination from Stats

Use statistical patterns to infer likely roles:

### 3.1 Starters vs Relievers

- **Starter profile**:
  - Can handle **longer outings**: consistent innings totals, multiple trips through the order.
  - **Solid K% with manageable BB%**; does not have extreme platoon splits.
  - ERA/xERA/FIP roughly in line or better than league average for a starter at that level.
- **Reliever profile**:
  - Shorter outings; may have big stuff but **command issues** or limited pitch mix.
  - Extreme platoon splits or difficulty turning lineups over multiple times.
  - May have higher K% but also higher BB%.

When the stats show repeated difficulty in maintaining performance over multiple innings or through the order, the assistant should lean toward a **relief role** recommendation, even if scouting suggests "starter tools".

### 3.2 Leverage Role for Relievers

- **High-leverage / late-inning**:
  - Strong K%, good K/BB, low HR/9, stable performance over time.
- **Middle relief / low-leverage**:
  - More modest K%, higher variance, or control issues.
- **Multi-inning / bulk reliever**:
  - Capable of 24 inning stints with acceptable run prevention, even if not missing many bats.

## 4. Level, Environment, and Age Context

As with hitters, stats must be read in context:

- Compare to **league-average performance** at the same level.
- Consider whether the pitcher is in a **hitter-friendly** or **pitcher-friendly** league/park.
- Evaluate **age-relative-to-level**:
  - Young & above-average performance = strong indicator.
  - Old for level & average/below-average stats = more likely organizational depth.

## 5. Health, Durability, and Risk

The assistant should consider:

- **Innings trends**: increasing, stable, or decreasing workload year to year.
- **Injury history** when known; missed time may affect role recommendations.

If a pitcher has strong per-inning stats but limited innings or frequent injuries, the assistant might project them as a **high-impact but fragile reliever** rather than a durable starter.

## 6. Scouting Reports as Secondary Evidence

Scouting notes can help interpret risk and upside:

- Velocity, pitch mix, movement, and command descriptions can explain **why** strikeouts or walks are high/low.
- But if scouting praise (e.g., "frontline starter stuff") is not supported by **sustained strong stats in upper minors/MLB**, the assistant should:
  - Emphasize the **risk and volatility**, and
  - Lean toward more conservative role projections (e.g., mid-rotation starter, swingman, or reliever).

Guideline:

> Extended statistical performance at higher levels is more trustworthy than optimistic scouting language alone.

## 7. Example Role Conclusions

Examples of how the assistant should summarize pitcher roles:

- "Profiles as a mid-rotation starter: above-average K%, solid K/BB, and consistent innings totals over multiple seasons at upper levels, with ERA/xERA around league average or better."
- "Likely high-leverage reliever: short outings but very high K% and strong K/BB; command is good enough, and the run prevention metrics support a late-inning role."
- "Projects best as a bulk/multi-inning reliever: limited third-time-through-the-order success and modest strikeout rates, but can provide 24 effective innings at a time."

All recommendations should be tied back explicitly to **what the stats show**, with scouting descriptors used only to clarify the nature of the arsenal and risk profile.