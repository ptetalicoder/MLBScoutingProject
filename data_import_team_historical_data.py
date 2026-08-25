import requests
import sqlite3
import time
from decimal import Decimal

from db import create_db_connection

# --- Configuration ---
# Kept for potential future API use; not used in current logic.
API_BASE_URL = "http://statsapi.mlb.com/api/v1"

# Seasons to import historical data for
SEASONS = ["2021", "2022", "2023", "2024"]
# The league ID for MLB
MLB_LEAGUE_ID = 103 # American League
MLB_LEAGUE_ID_2 = 104 # National League

def get_standings_from_api(season):
    """
    Fetches standings data for a given season for all MLB teams.
    """
    all_records = []
    # We need to check both AL and NL
    for league_id in [MLB_LEAGUE_ID, MLB_LEAGUE_ID_2]:
        url = f"{API_BASE_URL}/standings?leagueId={league_id}&season={season}"
        print(f"Fetching standings from API for season {season}, league {league_id}...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json().get("records", [])
            for division in data:
                all_records.extend(division.get("teamRecords", []))
        except requests.exceptions.RequestException as e:
            print(f"Error fetching standings for season {season}, league {league_id}: {e}")
    return all_records


def compute_team_stats(conn, season):
    """Compute per-team, per-season aggregate stats from HitterStats/PitcherStats.

    Returns a dict keyed by TeamID with values containing the metrics needed
    for TeamHistoricalData's new columns.
    """
    cursor = conn.cursor()

    # Hitting aggregates from HitterStats (Season column in schema)
    hitting_sql = """
        SELECT
            TeamID,
            SUM(Runs) AS RunsScored,
            SUM(Hits) AS Hits,
            SUM(HomeRuns) AS HomeRuns,
            SUM(RBI) AS RBI,
            SUM(StolenBases) AS StolenBases,
            SUM(PlateAppearances) AS PA,
            SUM(AtBats) AS AB,
            SUM(Walks) AS BB,
            0 AS HBP
        FROM HitterStats
        WHERE Season = ?
        GROUP BY TeamID
    """

    # Pitching aggregates from PitcherStats (Season/InningsPitched columns in schema)
    pitching_sql = """
        SELECT
            TeamID,
            SUM(InningsPitched) * 3 AS IP_outs,
            SUM(EarnedRuns) AS ER,
            SUM(HitsAllowed) AS HitsAllowed,
            SUM(Strikeouts) AS SO,
            SUM(WalksAllowed) AS BBAllowed
        FROM PitcherStats
        WHERE Season = ?
        GROUP BY TeamID
    """

    cursor.execute(hitting_sql, (season,))
    hitting_rows = cursor.fetchall()

    cursor.execute(pitching_sql, (season,))
    pitching_rows = cursor.fetchall()

    stats_by_team = {}

    # Helper to safely compute rates
    def safe_div(numer, denom):
        if numer is None or denom in (0, None):
            return None
        # Normalize to float to avoid Decimal/float type errors
        return float(numer) / float(denom)

    # Load hitting aggregates
    for row in hitting_rows:
        team_id = row["TeamID"]
        runs_scored = row["RunsScored"] or 0
        hits = row["Hits"] or 0
        hr = row["HomeRuns"] or 0
        rbi = row["RBI"] or 0
        sb = row["StolenBases"] or 0
        pa = row["PA"] or 0
        ab = row["AB"] or 0
        bb = row["BB"] or 0
        hbp = row["HBP"] or 0

        ba = safe_div(hits, ab) if ab else None
        obp = safe_div(hits + bb + hbp, pa) if pa else None
        # We do not have total bases here; slugging will be left as None
        slg = None
        ops = None if obp is None or slg is None else obp + slg

        stats_by_team.setdefault(team_id, {})
        stats_by_team[team_id].update({
            "RunsScored": runs_scored,
            "Hits": hits,
            "HomeRuns": hr,
            "RBI": rbi,
            "StolenBases": sb,
            "BA": ba,
            "OBP": obp,
            "SLG": slg,
            "OPS": ops,
        })

    # Load pitching aggregates
    for row in pitching_rows:
        team_id = row["TeamID"]
        ip_outs = row["IP_outs"] or 0
        er = row["ER"] or 0
        hits_allowed = row["HitsAllowed"] or 0
        so = row["SO"] or 0
        bb_allowed = row["BBAllowed"] or 0

        ip = safe_div(ip_outs, 3.0) if ip_outs else 0
        era = safe_div(float(er) * 9.0, ip) if ip else None
        whip = safe_div(hits_allowed + bb_allowed, ip) if ip else None

        stats_by_team.setdefault(team_id, {})
        stats_by_team[team_id].update({
            "RunsAllowed": er,  # proxy using ER if we do not track total runs
            "ERA": era,
            "WHIP": whip,
            "SO": so,
            "BBAllowed": bb_allowed,
        })

    # Add run differential now that we have both sides
    for team_id, vals in stats_by_team.items():
        rs = vals.get("RunsScored")
        ra = vals.get("RunsAllowed")
        vals["RunDiff"] = None if rs is None or ra is None else rs - ra

    return stats_by_team

def insert_historical_data_into_db(conn, historical_data):
    """
    Inserts or updates team historical data into the TeamHistoricalData table.
    """
    if not historical_data:
        print("No historical data to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT INTO TeamHistoricalData (
        TeamID, Year, Wins, Losses, PlayoffAppearance, WorldSeriesWin,
        RunsScored, RunsAllowed, RunDifferential,
        TeamBattingAverage, TeamOnBasePercentage, TeamSluggingPercentage, TeamOnBasePlusSlugging,
        TeamHomeRuns, TeamHits, TeamRBI, TeamStolenBases,
        TeamEarnedRunAverage, TeamWHIP, TeamStrikeoutsPitching, TeamWalksAllowed
    ) VALUES (
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?
    )
    ON CONFLICT(TeamID, Year) DO UPDATE SET
        Wins = excluded.Wins,
        Losses = excluded.Losses,
        PlayoffAppearance = excluded.PlayoffAppearance,
        WorldSeriesWin = excluded.WorldSeriesWin,
        RunsScored = excluded.RunsScored,
        RunsAllowed = excluded.RunsAllowed,
        RunDifferential = excluded.RunDifferential,
        TeamBattingAverage = excluded.TeamBattingAverage,
        TeamOnBasePercentage = excluded.TeamOnBasePercentage,
        TeamSluggingPercentage = excluded.TeamSluggingPercentage,
        TeamOnBasePlusSlugging = excluded.TeamOnBasePlusSlugging,
        TeamHomeRuns = excluded.TeamHomeRuns,
        TeamHits = excluded.TeamHits,
        TeamRBI = excluded.TeamRBI,
        TeamStolenBases = excluded.TeamStolenBases,
        TeamEarnedRunAverage = excluded.TeamEarnedRunAverage,
        TeamWHIP = excluded.TeamWHIP,
        TeamStrikeoutsPitching = excluded.TeamStrikeoutsPitching,
        TeamWalksAllowed = excluded.TeamWalksAllowed;
    """
    
    try:
        print(f"Inserting/updating {len(historical_data)} team historical records...")
        cursor.executemany(sql, historical_data)
        conn.commit()
        print(f"Successfully processed {cursor.rowcount} historical records.")
    except sqlite3.Error as e:
        print(f"Database error during historical data insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to run the data import process for team historical data.
    """
    print("--- Starting Team Historical Data Import ---")
    
    conn = create_db_connection()
    if not conn:
        print("--- Data Import Process Finished (due to connection error) ---")
        return

    all_seasons_data = []
    for season in SEASONS:
        print(f"Fetching standings for season {season}...")
        team_records = get_standings_from_api(season)
        time.sleep(1)

        if not team_records:
            print(f"No standings records found for season {season}.")
            continue

        print(f"Computing team stats from local tables for season {season}...")
        team_stats = compute_team_stats(conn, season)

        for record in team_records:
            team_id = record.get("team", {}).get("id")
            wins = record.get("wins")
            losses = record.get("losses")
            playoff_appearance = 1 if record.get("clinched", False) else 0
            world_series_win = 0

            stats = team_stats.get(team_id, {}) if team_stats else {}

            runs_scored = stats.get("RunsScored")
            runs_allowed = stats.get("RunsAllowed")
            run_diff = stats.get("RunDiff")

            team_ba = stats.get("BA")
            team_obp = stats.get("OBP")
            team_slg = stats.get("SLG")
            team_ops = stats.get("OPS")
            team_hr = stats.get("HomeRuns")
            team_hits = stats.get("Hits")
            team_rbi = stats.get("RBI")
            team_sb = stats.get("StolenBases")

            team_era = stats.get("ERA")
            team_whip = stats.get("WHIP")
            team_k = stats.get("SO")
            team_bb_allowed = stats.get("BBAllowed")

            historical_tuple = (
                team_id,
                season,
                wins,
                losses,
                playoff_appearance,
                world_series_win,
                runs_scored,
                runs_allowed,
                run_diff,
                team_ba,
                team_obp,
                team_slg,
                team_ops,
                team_hr,
                team_hits,
                team_rbi,
                team_sb,
                team_era,
                team_whip,
                team_k,
                team_bb_allowed,
            )
            all_seasons_data.append(historical_tuple)

    if all_seasons_data:
        insert_historical_data_into_db(conn, all_seasons_data)

    conn.close()
    print("Database connection closed.")
    print("--- Data Import Process Finished ---")

def update_world_series_winners_manually(conn):
    """
    Manually updates the World Series winners for specific years using their TeamID.
    """
    print("--- Manually Updating World Series Winners ---")
    winners = [
        (119, 2024), # Los Angeles Dodgers
        (140, 2023), # Texas Rangers
        (117, 2022), # Houston Astros
        (144, 2021)  # Atlanta Braves
    ]

    cursor = conn.cursor()
    update_sql = "UPDATE TeamHistoricalData SET WorldSeriesWin = 1 WHERE TeamID = ? AND Year = ?"
    updated_count = 0

    for team_id, year in winners:
        try:
            cursor.execute(update_sql, (team_id, year))
            if cursor.rowcount > 0:
                print(f"Successfully set TeamID {team_id} as World Series winner for {year}.")
                updated_count += cursor.rowcount
        except sqlite3.Error as e:
            print(f"Database error updating winner for {year} (TeamID {team_id}): {e}")

    conn.commit()
    print(f"--- Finished Manual Update: {updated_count} records updated. ---")


if __name__ == "__main__":
    main()
    # After the main import, connect again to run the manual updates
    conn = create_db_connection()
    if conn:
        update_world_series_winners_manually(conn)
        conn.close()
        print("Database connection closed after manual update.")
