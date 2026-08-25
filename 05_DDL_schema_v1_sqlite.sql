-- DDL Script for MLB Scout and Roster Manager Database
-- Target Database: SQLite
--
-- Translated from 05_DDL_schema_v1.sql (the original MySQL schema) for the
-- Phase 1 public-demo build. Differences from the MySQL version:
--   * INT PRIMARY KEY AUTO_INCREMENT -> INTEGER PRIMARY KEY AUTOINCREMENT
--     (SQLite's rowid-alias autoincrement requires the column type to be
--     spelled exactly "INTEGER")
--   * No storage-engine pragma; SQLite has one engine
--   * Foreign key enforcement is a per-connection PRAGMA rather than a
--     table option, so it's set by db.py's create_db_connection(), not here
--
-- Column types, NOT NULL, UNIQUE, and FOREIGN KEY clauses are otherwise
-- unchanged from the MySQL original.

-- Table: Player
-- Stores information about individual players at all levels.
CREATE TABLE Player (
    PlayerID INTEGER PRIMARY KEY AUTOINCREMENT,
    FirstName VARCHAR(100) NOT NULL,
    LastName VARCHAR(100) NOT NULL,
    DateOfBirth DATE,
    Position VARCHAR(50),
    Height INT,
    Weight INT,
    Throws VARCHAR(5),
    Bats VARCHAR(5),
    PlayerLevel VARCHAR(50) -- e.g., MLB, MiLB, College
);

-- Table: League
-- Defines the different leagues.
CREATE TABLE League (
    LeagueID INTEGER PRIMARY KEY AUTOINCREMENT,
    LeagueName VARCHAR(255) NOT NULL UNIQUE,
    LeagueLevel VARCHAR(50) NOT NULL
);

-- Table: Team
-- Stores information about each team, including its league and MLB affiliate.
CREATE TABLE Team (
    TeamID INTEGER PRIMARY KEY AUTOINCREMENT,
    TeamName VARCHAR(255) NOT NULL,
    City VARCHAR(100),
    LeagueID INT,
    MLBAffiliateID INT, -- Self-referencing FK to model parent team
    FOREIGN KEY (LeagueID) REFERENCES League(LeagueID),
    FOREIGN KEY (MLBAffiliateID) REFERENCES Team(TeamID)
);

-- Table: Contract
-- Manages player contracts.
CREATE TABLE Contract (
    ContractID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlayerID INT NOT NULL,
    TeamID INT NOT NULL,
    Year INT NOT NULL,
    Salary DECIMAL(15, 2),
    SigningBonus DECIMAL(15, 2),
    Experience FLOAT,
    ContractYears INT,
    Options TEXT,
    FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID),
    FOREIGN KEY (TeamID) REFERENCES Team(TeamID),
    UNIQUE (PlayerID, TeamID, Year) -- A player can only have one contract with a team per year
);

-- Table: HitterStats
-- Contains player hitting statistics for each season.
CREATE TABLE HitterStats (
    HitterStatsID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlayerID INT NOT NULL,
    TeamID INT NOT NULL,
    Season INT NOT NULL,
    GamesPlayed INT,
    PlateAppearances INT,
    AtBats INT,
    Runs INT,
    Hits INT,
    Doubles INT,
    Triples INT,
    HomeRuns INT,
    RBI INT,
    Walks INT,
    Strikeouts INT,
    StolenBases INT,
    CaughtStealing INT,
    BattingAverage DECIMAL(4, 3),
    OnBasePercentage DECIMAL(4, 3),
    SluggingPercentage DECIMAL(4, 3),
    OnBasePlusSlugging DECIMAL(4, 3),
    IsolatedPower DECIMAL(4, 3),
    HardHitPercentage DECIMAL(4, 1),
    WinsAboveReplacement DECIMAL(3, 1),
    WeightedOnBaseAverage DECIMAL(4, 3),
    WeightedRunsCreatedPlus INT,
    FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID),
    FOREIGN KEY (TeamID) REFERENCES Team(TeamID),
    UNIQUE (PlayerID, TeamID, Season)
);

-- Table: PitcherStats
-- Contains player pitching statistics for each season.
CREATE TABLE PitcherStats (
    PitcherStatsID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlayerID INT NOT NULL,
    TeamID INT NOT NULL,
    Season INT NOT NULL,
    Wins INT,
    Losses INT,
    GamesPitched INT,
    GamesStarted INT,
    Saves INT,
    Holds INT,
    InningsPitched DECIMAL(5, 1),
    HitsAllowed INT,
    RunsAllowed INT,
    EarnedRuns INT,
    HomeRunsAllowed INT,
    WalksAllowed INT,
    Strikeouts INT,
    EarnedRunAverage DECIMAL(6, 2),
    FieldingIndependentPitching DECIMAL(6, 2),
    ExpectedERA DECIMAL(6, 2),
    WalksAndHitsPerInningPitched DECIMAL(4, 2),
    WhiffPercentage DECIMAL(4, 1),
    FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID),
    FOREIGN KEY (TeamID) REFERENCES Team(TeamID),
    UNIQUE (PlayerID, TeamID, Season)
);

-- Table: ScoutingReport
-- Contains scouting information and grades for players.
CREATE TABLE ScoutingReport (
    ReportID INTEGER PRIMARY KEY AUTOINCREMENT,
    PlayerID INT NOT NULL,
    ReportDate DATE,
    Position VARCHAR(50),
    ContactGrade INT,
    PowerGrade INT,
    RunningGrade INT,
    FieldingGrade INT,
    ArmGrade INT,
    PitchingVelocity INT,
    PitchingAccuracy INT,
    SpinRateGrade INT,
    BreakingBallGrade INT,
    OverallPotential INT,
    Summary TEXT,
    FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID)
);

-- Table: Trade
-- Represents a trade event.
CREATE TABLE Trade (
    TradeID INTEGER PRIMARY KEY AUTOINCREMENT,
    TradeDate DATE NOT NULL
);

-- Table: TradeDetails
-- A junction table to capture the many-to-many details of a trade.
CREATE TABLE TradeDetails (
    TradeDetailID INTEGER PRIMARY KEY AUTOINCREMENT,
    TradeID INT NOT NULL,
    PlayerID INT NOT NULL,
    OriginalTeamID INT NOT NULL,
    NewTeamID INT NOT NULL,
    FOREIGN KEY (TradeID) REFERENCES Trade(TradeID),
    FOREIGN KEY (PlayerID) REFERENCES Player(PlayerID),
    FOREIGN KEY (OriginalTeamID) REFERENCES Team(TeamID),
    FOREIGN KEY (NewTeamID) REFERENCES Team(TeamID)
);

-- Table: TeamHistoricalData
-- Stores historical performance data for teams.
CREATE TABLE TeamHistoricalData (
    RecordID INTEGER PRIMARY KEY AUTOINCREMENT,
    TeamID INT NOT NULL,
    Year INT NOT NULL,
    Wins INT,
    Losses INT,
    PlayoffAppearance BOOLEAN, -- Using BOOLEAN for true/false
    WorldSeriesWin BOOLEAN,    -- Using BOOLEAN for true/false
    RunsScored INT,
    RunsAllowed INT,
    RunDifferential INT,
    TeamBattingAverage DECIMAL(4, 3),
    TeamOnBasePercentage DECIMAL(4, 3),
    TeamSluggingPercentage DECIMAL(4, 3),
    TeamOnBasePlusSlugging DECIMAL(4, 3),
    TeamHomeRuns INT,
    TeamHits INT,
    TeamRBI INT,
    TeamStolenBases INT,
    TeamEarnedRunAverage DECIMAL(6, 2),
    TeamWHIP DECIMAL(4, 2),
    TeamStrikeoutsPitching INT,
    TeamWalksAllowed INT,
    FOREIGN KEY (TeamID) REFERENCES Team(TeamID),
    UNIQUE (TeamID, Year)
);
