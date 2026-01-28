# Core MVP Entities and Attributes

### Player
- PlayerID (PK)
- FirstName
- LastName
- DateOfBirth
- Position
- Height
- Weight
- Throws
- Bats
- PlayerLevel (e.g., MLB, MiLB, College)

### Team
- TeamID (PK)
- TeamName
- City
- LeagueID (FK to League.LeagueID)
- MLBAffiliateID (FK to Team.TeamID)

### Contract
- ContractID (PK)
- PlayerID (FK to Player.PlayerID)
- TeamID (FK to Team.TeamID)
- Year
- Salary
- SigningBonus
- Experience
- ContractYears
- Options

### HitterStats
- HitterStatsID (PK)
- PlayerID (FK to Player.PlayerID)
- TeamID (FK to Team.TeamID)
- Season
- GamesPlayed
- PlateAppearances
- AtBats
- Runs
- Hits
- Doubles
- Triples
- HomeRuns
- RBI
- Walks (BB)
- Strikeouts (SO)
- StolenBases (SB)
- CaughtStealing (CS)
- BattingAverage (AVG)
- OnBasePercentage (OBP)
- SluggingPercentage (SLG)
- OnBasePlusSlugging (OPS)
- IsolatedPower (ISO)
- HardHitPercentage
- WinsAboveReplacement (WAR)
- WeightedOnBaseAverage (wOBA)
- WeightedRunsCreatedPlus (wRC+)

### PitcherStats
- PitcherStatsID (PK)
- PlayerID (FK to Player.PlayerID)
- TeamID (FK to Team.TeamID)
- Season
- Wins
- Losses
- GamesPitched
- GamesStarted
- Saves
- Holds
- InningsPitched
- HitsAllowed
- RunsAllowed
- EarnedRuns
- HomeRunsAllowed
- WalksAllowed
- Strikeouts
- EarnedRunAverage (ERA)
- FieldingIndependentPitching (FIP)
- ExpectedERA (xERA)
- WalksAndHitsPerInningPitched (WHIP)
- WhiffPercentage

### ScoutingReport
- ReportID (PK)
- PlayerID (FK to Player.PlayerID)
- ReportDate
- Position
- ContactGrade
- PowerGrade
- RunningGrade
- FieldingGrade
- ArmGrade
- PitchingVelocity
- PitchingAccuracy
- SpinRateGrade
- BreakingBallGrade
- OverallPotential
- Summary

### League
- LeagueID (PK)
- LeagueName
- LeagueLevel

### Trade
- TradeID (PK)
- TradeDate

### TradeDetails
- TradeDetailID (PK)
- TradeID (FK to Trade.TradeID)
- PlayerID (FK to Player.PlayerID)
- OriginalTeamID (FK to Team.TeamID)
- NewTeamID (FK to Team.TeamID)

### TeamHistoricalData
- RecordID (PK)
- TeamID (FK to Team.TeamID)
- Year
- Wins
- Losses
- PlayoffAppearance
- WorldSeriesWin
- RunsScored
- RunsAllowed
- RunDifferential
- TeamBattingAverage
- TeamOnBasePercentage
- TeamSluggingPercentage
- TeamOnBasePlusSlugging
- TeamHomeRuns
- TeamHits
- TeamRBI
- TeamStolenBases
- TeamEarnedRunAverage
- TeamWHIP
- TeamStrikeoutsPitching
- TeamWalksAllowed
