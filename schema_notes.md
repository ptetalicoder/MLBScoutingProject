# Schema Notes for MLB Scouting Database

This file highlights key columns that are most likely to be used
in JOIN conditions and WHERE filters for each table.

## Player
- **Join keys**:
  - `Player.PlayerID` — primary key; used to join from `HitterStats`, `PitcherStats`, `Contract`, `ScoutingReport`, `TradeDetails`.
- **Common filters**:
  - `Player.FirstName`, `Player.LastName` — search/filter by player name.
  - `Player.Position` — filter by fielding position (e.g., "C", "1B", "SS", "OF").
  - `Player.PlayerLevel` — values like "Major League Baseball", "Triple-A", "Double-A", "College".
  - `Player.Bats` — e.g., "R", "L", "S".
  - `Player.Throws` — e.g., "R", "L".
  - `Player.DateOfBirth` — filter by age ranges.

## League
- **Join keys**:
  - `League.LeagueID` — primary key; joined from `Team.LeagueID`.
- **Common filters**:
  - `League.LeagueName` — e.g., "American League", "National League".
  - `League.LeagueLevel` — e.g., "Major League Baseball", "Minor League", "College".

## Team
- **Join keys**:
  - `Team.TeamID` — primary key; joined from `HitterStats.TeamID`, `PitcherStats.TeamID`, `Contract.TeamID`, `TradeDetails.OriginalTeamID`, `TradeDetails.NewTeamID`, `TeamHistoricalData.TeamID`.
  - `Team.LeagueID` — foreign key to `League.LeagueID`.
  - `Team.MLBAffiliateID` — self-reference to `Team.TeamID` (minor league → MLB affiliate).
- **Common filters**:
  - `Team.TeamName` — filter by team.
  - `Team.City` — filter by city/market.
  - `Team.LeagueID` / `League.LeagueName` / `League.LeagueLevel` via join to `League`.

## Contract
- **Join keys**:
  - `Contract.PlayerID` — join to `Player.PlayerID`.
  - `Contract.TeamID` — join to `Team.TeamID`.
- **Natural keys / uniqueness**:
  - `(Contract.PlayerID, Contract.TeamID, Contract.Year)` — unique contract per player/team/year.
- **Common filters**:
  - `Contract.Year` — filter by season/year of contract.
  - `Contract.Salary` — filter/sort by salary.
  - `Contract.SigningBonus` — filter by signing bonus.
  - `Contract.Experience` — filter by years of service.

## HitterStats
- **Join keys**:
  - `HitterStats.PlayerID` — join to `Player.PlayerID`.
  - `HitterStats.TeamID` — join to `Team.TeamID`.
- **Natural keys / uniqueness**:
  - `(HitterStats.PlayerID, HitterStats.TeamID, HitterStats.Season)` — unique row per player/team/season.
- **Common filters**:
  - `HitterStats.Season` — season/year filter.
  - `HitterStats.GamesPlayed` — minimum playing time filters.
  - `HitterStats.HomeRuns`, `HitterStats.RBI`, `HitterStats.Hits` — performance filters and sorting.
  - `HitterStats.BattingAverage`, `HitterStats.OnBasePercentage`, `HitterStats.SluggingPercentage`,
    `HitterStats.OnBasePlusSlugging`, `HitterStats.IsolatedPower` — rate stats filters.
  - Advanced metrics such as `HitterStats.WinsAboveReplacement`, `HitterStats.WeightedOnBaseAverage`,
    `HitterStats.WeightedRunsCreatedPlus` for sabermetric queries.

## PitcherStats
- **Join keys**:
  - `PitcherStats.PlayerID` — join to `Player.PlayerID`.
  - `PitcherStats.TeamID` — join to `Team.TeamID`.
- **Natural keys / uniqueness**:
  - `(PitcherStats.PlayerID, PitcherStats.TeamID, PitcherStats.Season)` — unique row per player/team/season.
- **Common filters**:
  - `PitcherStats.Season` — season/year filter.
  - `PitcherStats.GamesPitched`, `PitcherStats.GamesStarted`, `PitcherStats.InningsPitched` — workload filters.
  - `PitcherStats.Wins`, `PitcherStats.Losses`, `PitcherStats.Saves`, `PitcherStats.Holds` — role/outcome stats.
  - `PitcherStats.EarnedRunAverage`, `PitcherStats.FieldingIndependentPitching`, `PitcherStats.ExpectedERA`,
    `PitcherStats.WalksAndHitsPerInningPitched`, `PitcherStats.WhiffPercentage` — run prevention & quality filters.

## ScoutingReport
- **Join keys**:
  - `ScoutingReport.PlayerID` — join to `Player.PlayerID`.
- **Common filters**:
  - `ScoutingReport.ReportDate` — latest report per player.
  - `ScoutingReport.Position` — filter by scouting position.
  - `ScoutingReport.ContactGrade`, `ScoutingReport.PowerGrade`, `ScoutingReport.RunningGrade`,
    `ScoutingReport.FieldingGrade`, `ScoutingReport.ArmGrade`, `ScoutingReport.OverallPotential` —
    filter/sort by scouting tools and overall potential.

## Trade
- **Join keys**:
  - `Trade.TradeID` — primary key; joined from `TradeDetails.TradeID`.
- **Common filters**:
  - `Trade.TradeDate` — filter by date range or specific trade windows.

## TradeDetails
- **Join keys**:
  - `TradeDetails.TradeID` — join to `Trade.TradeID`.
  - `TradeDetails.PlayerID` — join to `Player.PlayerID`.
  - `TradeDetails.OriginalTeamID` — join to `Team.TeamID` (team trading the player away).
  - `TradeDetails.NewTeamID` — join to `Team.TeamID` (team acquiring the player).
- **Common filters**:
  - Often filtered indirectly via `Trade.TradeDate` and team/player joins.

## TeamHistoricalData
- **Join keys**:
  - `TeamHistoricalData.TeamID` — join to `Team.TeamID`.
- **Natural keys / uniqueness**:
  - `(TeamHistoricalData.TeamID, TeamHistoricalData.Year)` — unique record per team/year.
- **Common filters**:
  - `TeamHistoricalData.Year` — filter by season/year.
  - `TeamHistoricalData.Wins`, `TeamHistoricalData.Losses` — record filters and sorting.
  - `TeamHistoricalData.PlayoffAppearance` — boolean (0/1) for playoff teams.
  - `TeamHistoricalData.WorldSeriesWin` — boolean (0/1) for World Series champions.

---

### General Guidance for the SQL Assistant
- Prefer JOINs along defined foreign key relationships listed above.
- Use `PlayerID`, `TeamID`, `LeagueID`, `TradeID` as numeric join keys.
- When filtering on text categories (e.g., `LeagueLevel`, `PlayerLevel`, `Position`),
  prefer the examples seen in schema/example rows instead of inventing short codes.
- When ranking or sorting by a *rate* stat (e.g. `BattingAverage`, `OnBasePercentage`,
  `SluggingPercentage`, `OnBasePlusSlugging`, `WeightedOnBaseAverage`,
  `EarnedRunAverage`, `FieldingIndependentPitching`, `WalksAndHitsPerInningPitched`),
  always add a minimum-sample-size qualifier so a one-game or tiny-sample outlier
  doesn't dominate the results: `HitterStats.AtBats >= 100` for hitting rate stats, or
  `PitcherStats.InningsPitched >= 20` for pitching rate stats. Skip this qualifier only
  if the request is about one specific named player, or explicitly asks to include
  small-sample/September call-up performances.
- Counting stats (`HomeRuns`, `RBI`, `Hits`, `Wins`, `Saves`, `Strikeouts`, etc.) do not
  need a sample-size qualifier.
