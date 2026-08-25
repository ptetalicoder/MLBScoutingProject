import requests
import sqlite3
import time

from db import create_db_connection

# --- Configuration ---
API_BASE_URL = "http://statsapi.mlb.com/api/v1"

SEASONS = ["2021", "2022", "2023", "2024"]
STAT_GROUP = "pitching"

def get_all_players_from_db(conn):
    """
    Fetches all PlayerIDs for pitchers from the database.
    """
    players = []
    try:
        cursor = conn.cursor()
        print("Fetching all pitchers from the database...")
        # Fetching only pitchers
        cursor.execute("SELECT PlayerID, Position FROM Player WHERE Position = 'Pitcher';")
        players = cursor.fetchall()
        print(f"Found {len(players)} pitcher players in the database.")
    except sqlite3.Error as e:
        print(f"Database error while fetching players: {e}")
    return players

def get_player_stats_from_api(player_id, season, stat_group):
    """
    Fetches season statistics for a single player for a specific stat group.
    """
    url = f"{API_BASE_URL}/people/{player_id}/stats?stats=season&season={season}&group={stat_group}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        stats = response.json().get("stats", [])
        # We only care about the pitching stats
        for stat_type in stats:
            if stat_type.get('group', {}).get('displayName') == stat_group:
                return stat_type.get('splits', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stats for playerId {player_id}: {e}")
    return []

def insert_pitcher_stats_into_db(conn, all_stats_to_insert):
    """
    Inserts or updates pitcher stats into the PitcherStats table.
    """
    if not all_stats_to_insert:
        print("No pitcher stats to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT INTO PitcherStats (
        PlayerID, TeamID, Season, Wins, Losses, GamesPitched, GamesStarted, Saves, Holds,
        InningsPitched, HitsAllowed, RunsAllowed, EarnedRuns, HomeRunsAllowed, WalksAllowed,
        Strikeouts, EarnedRunAverage, WalksAndHitsPerInningPitched
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(PlayerID, TeamID, Season) DO UPDATE SET
        Wins = excluded.Wins, Losses = excluded.Losses, GamesPitched = excluded.GamesPitched,
        GamesStarted = excluded.GamesStarted, Saves = excluded.Saves, Holds = excluded.Holds,
        InningsPitched = excluded.InningsPitched, HitsAllowed = excluded.HitsAllowed,
        RunsAllowed = excluded.RunsAllowed, EarnedRuns = excluded.EarnedRuns,
        HomeRunsAllowed = excluded.HomeRunsAllowed, WalksAllowed = excluded.WalksAllowed,
        Strikeouts = excluded.Strikeouts, EarnedRunAverage = excluded.EarnedRunAverage,
        WalksAndHitsPerInningPitched = excluded.WalksAndHitsPerInningPitched;
    """
    
    try:
        print(f"Inserting/updating stats for {len(all_stats_to_insert)} pitchers...")
        cursor.executemany(sql, all_stats_to_insert)
        conn.commit()
        print(f"Successfully processed {cursor.rowcount} pitcher stat records.")
    except sqlite3.Error as e:
        print(f"Database error during pitcher stats insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to run the data import process for pitcher stats.
    """
    print("--- Starting MLB Pitcher Stats Data Import for Seasons: " + ", ".join(SEASONS) + " ---")
    
    conn = create_db_connection()
    if not conn:
        print("--- Data Import Process Finished (due to connection error) ---")
        return

    # Step 1: Get all pitcher players from our database
    players = get_all_players_from_db(conn)
    
    if players:
        all_stats_to_insert = []
        # Loop through each season
        for season in SEASONS:
            print(f"\n--- Processing Season: {season} ---")
            # Step 2: Iterate through each player and fetch their stats for the current season
            for i, player in enumerate(players):
                player_id = player['PlayerID']
                # TeamID will be determined from the stats API response
                team_id = None 
                
                print(f"Processing pitcher {i + 1}/{len(players)} for {season}: ID {player_id}")
                
                stat_splits = get_player_stats_from_api(player_id, season, STAT_GROUP)
                time.sleep(0.1) # API rate limiting

                if not stat_splits:
                    continue

                # Aggregate stats if player played for multiple teams in a season
                agg_stats = {}
                for split in stat_splits:
                    team_id = split.get('team', {}).get('id', team_id)
                    stats = split.get('stat', {})
                    for key, value in stats.items():
                        try:
                            numeric_value = float(value) if '.' in str(value) else int(value)
                            agg_stats[key] = agg_stats.get(key, 0) + numeric_value
                        except (ValueError, TypeError):
                            agg_stats[key] = value

                if team_id is None:
                    # This is common for players who didn't play in a given year, so we won't print a message
                    continue

                # Rate stats (ERA/WHIP) must be recomputed from the aggregated
                # counting stats, not summed across splits — summing e.g. two
                # teams' ERA values produces impossible numbers for pitchers
                # traded mid-season.
                innings_pitched = agg_stats.get('inningsPitched') or 0
                earned_runs = agg_stats.get('earnedRuns') or 0
                hits_allowed = agg_stats.get('hits') or 0
                walks_allowed = agg_stats.get('baseOnBalls') or 0

                era = round(9 * earned_runs / innings_pitched, 2) if innings_pitched else None
                whip = round((hits_allowed + walks_allowed) / innings_pitched, 2) if innings_pitched else None

                # Step 3: Prepare the data tuple for insertion
                # Note: Advanced stats like FIP, xERA, Whiff% are not available from this endpoint.

                stat_tuple = (
                    player_id,
                    team_id,
                    season,
                    agg_stats.get('wins'),
                    agg_stats.get('losses'),
                    agg_stats.get('gamesPitched'),
                    agg_stats.get('gamesStarted'),
                    agg_stats.get('saves'),
                    agg_stats.get('holds'),
                    agg_stats.get('inningsPitched'),
                    agg_stats.get('hits'), # Hits Allowed
                    agg_stats.get('runs'), # Runs Allowed
                    agg_stats.get('earnedRuns'),
                    agg_stats.get('homeRuns'), # Home Runs Allowed
                    agg_stats.get('baseOnBalls'), # Walks Allowed
                    agg_stats.get('strikeOuts'), # Strikeouts
                    era,
                    whip
                )
                all_stats_to_insert.append(stat_tuple)

        # Step 4: Insert all collected stats into the database
        if all_stats_to_insert:
            insert_pitcher_stats_into_db(conn, all_stats_to_insert)
        else:
            print("No new stats found for any player in the specified seasons.")

    # Step 5: Close the connection
    conn.close()
    print("\n--- Data Import Process Finished ---")

if __name__ == "__main__":
    main()
