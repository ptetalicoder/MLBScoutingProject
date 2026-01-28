-- Active: 1761668259379@@db-mysql-itom-do-user-28250611-0.j.db.ondigitalocean.com@25060@group01
-- DDL Script for MLB Scout and Roster Manager Database
-- Target Database: MySQL

-- Set storage engine for foreign key support
SET default_storage_engine=InnoDB;

-- Table: Player
-- Stores information about individual players at all levels.
CREATE TABLE Player (
    PlayerID INT PRIMARY KEY AUTO_INCREMENT,
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
    LeagueID INT PRIMARY KEY AUTO_INCREMENT,
    LeagueName VARCHAR(255) NOT NULL UNIQUE,
    LeagueLevel VARCHAR(50) NOT NULL
);

-- Table: Team
-- Stores information about each team, including its league and MLB affiliate.
CREATE TABLE Team (
    TeamID INT PRIMARY KEY AUTO_INCREMENT,
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
    ContractID INT PRIMARY KEY AUTO_INCREMENT,
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
    HitterStatsID INT PRIMARY KEY AUTO_INCREMENT,
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
    PitcherStatsID INT PRIMARY KEY AUTO_INCREMENT,
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
    ReportID INT PRIMARY KEY AUTO_INCREMENT,
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
    TradeID INT PRIMARY KEY AUTO_INCREMENT,
    TradeDate DATE NOT NULL
);

-- Table: TradeDetails
-- A junction table to capture the many-to-many details of a trade.
CREATE TABLE TradeDetails (
    TradeDetailID INT PRIMARY KEY AUTO_INCREMENT,
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
    RecordID INT PRIMARY KEY AUTO_INCREMENT,
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
