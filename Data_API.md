# Data Sources and APIs for MLB Scout and Roster Manager

**Version:** 1.0
**Date:** November 9, 2025

---

## 1. Introduction

This document identifies the external APIs and internal data sources required to populate and maintain the database for the MLB Scout and Roster Manager application. The primary source for a significant portion of the professional data will be the **MLB Stats API**, which is the official, albeit undocumented, source for MLB data. For data not available there, such as contract details and amateur scouting, other sources will be necessary.

## 2. API and Data Source Breakdown by Table

### Player Table
*   **Primary Source:** MLB Stats API
*   **Description:** The API provides comprehensive biographical data for players. To get a complete list of all players (MLB and MiLB), it's necessary to first fetch all teams from all league levels and then query the roster for each team. A simpler, but less comprehensive, method is to query the players endpoint for each `sportId`.
*   **Data Points Covered:** PlayerID (can be mapped from API), FirstName, LastName, DateOfBirth, Position, Height, Weight, Throws, Bats.
*   **Note:** `PlayerLevel` will be determined by the league level of the team they play for. College player data will need to be sourced separately.

### Team & League Tables
*   **Primary Source:** MLB Stats API
*   **Description:** To get a complete list of all MLB and MiLB teams, it is necessary to make multiple calls to the `/api/v1/teams` endpoint, iterating through the `sportId` for each level of baseball.
    *   MLB: `sportId=1`
    *   AAA: `sportId=11`
    *   AA: `sportId=12`
    *   High-A: `sportId=13`
    *   Single-A: `sportId=14`
*   **Data Points Covered:**
    *   **Team:** TeamName, City, LeagueID.
    *   **League:** LeagueName, LeagueLevel.
*   **Note:** The affiliate structure (`MLBAffiliateID`) is included in the data returned from these endpoints. `sportId=15` (Rookie) has been excluded as it can be unreliable and is not essential for core prospect tracking.

### Contract Table
*   **Primary Source:** Third-Party Data Provider (e.g., Spotrac, Cot's Baseball Contracts)
*   **Description:** Player contract information is not reliably available via the free MLB Stats API. A specialized sports contract data provider would be the most accurate source. This data would likely be accessed via a paid API subscription or through manual data entry from their public-facing websites.
*   **Data Points Covered:** StartDate, EndDate, Salary, ContractYears, Options.

### PlayerStats Table
*   **Primary Source:** MLB Stats API
*   **Description:** This is the API's greatest strength. It provides extensive and deep statistical data for players at all professional levels, which can be queried by year and team.
*   **Data Points Covered:** All statistical fields, including GamesPlayed, AtBats, Hits, HomeRuns, RBIs, BattingAverage, Wins, Losses, ERA, Strikeouts, and WHIP.

### ScoutingReport Table
*   **Primary Source:** Internal Data + Third-Party Scouting Services
*   **Description:** This data is proprietary and represents the core value of a team's scouting department.
*   **Sources:**
    1.  **Internal Scouting:** Reports and grades entered directly into the application by the team's own scouts.
    2.  **Amateur Scouting Services:** Data for college players could be licensed from services like Baseball America, Perfect Game, or D1Baseball.com. This would likely be delivered via a private API or data file dumps.
*   **Data Points Covered:** All fields in this table are considered internal or licensed data.

### Trade & TradeDetails Tables
*   **Primary Source:** MLB Stats API
*   **Description:** The MLB Stats API has a transactions endpoint that can be monitored for all player movements, including trades, free-agent signings, and assignments.
*   **Data Points Covered:** TradeDate, PlayerID, OriginalTeamID, NewTeamID.
*   **Note:** The application would need a background process to poll this API endpoint regularly, parse the transaction data, and populate the `Trade` and `TradeDetails` tables accordingly.

### TeamHistoricalData Table
*   **Primary Source:** MLB Stats API
*   **Description:** The API provides access to historical standings and team records on a year-by-year basis.
*   **Data Points Covered:** Year, Wins, Losses, PlayoffAppearance, WorldSeriesWin.
*   **Note:** `PlayoffAppearance` and `WorldSeriesWin` can be inferred from the final standings and postseason results available from the API.
