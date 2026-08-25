import requests
import sqlite3
import time

from db import create_db_connection

# --- Configuration ---
API_BASE_URL = "http://statsapi.mlb.com/api/v1"

SEASONS = ["2021", "2022", "2023", "2024"]
STAT_GROUP = "hitting"

def get_all_players_from_db(conn):
    """
    Fetches all PlayerIDs and their primary position from the database.
    """
    players = []
    try:
        cursor = conn.cursor()
        print("Fetching all players from the database...")
        # Fetching only non-pitchers
        cursor.execute("SELECT PlayerID, Position FROM Player WHERE Position != 'Pitcher';")
        players = cursor.fetchall()
        print(f"Found {len(players)} non-pitcher players in the database.")
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
        # We only care about the hitting stats
        for stat_type in stats:
            if stat_type.get('group', {}).get('displayName') == stat_group:
                return stat_type.get('splits', [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching stats for playerId {player_id}: {e}")
    return []

def insert_hitter_stats_into_db(conn, all_stats_to_insert):
    """
    Inserts or updates hitter stats into the HitterStats table.
    """
    if not all_stats_to_insert:
        print("No hitter stats to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT INTO HitterStats (
        PlayerID, TeamID, Season, GamesPlayed, PlateAppearances, AtBats, Runs, Hits,
        Doubles, Triples, HomeRuns, RBI, Walks, Strikeouts, StolenBases, CaughtStealing,
        BattingAverage, OnBasePercentage, SluggingPercentage, OnBasePlusSlugging, IsolatedPower
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(PlayerID, TeamID, Season) DO UPDATE SET
        GamesPlayed = excluded.GamesPlayed, PlateAppearances = excluded.PlateAppearances,
        AtBats = excluded.AtBats, Runs = excluded.Runs, Hits = excluded.Hits,
        Doubles = excluded.Doubles, Triples = excluded.Triples, HomeRuns = excluded.HomeRuns,
        RBI = excluded.RBI, Walks = excluded.Walks, Strikeouts = excluded.Strikeouts,
        StolenBases = excluded.StolenBases, CaughtStealing = excluded.CaughtStealing,
        BattingAverage = excluded.BattingAverage, OnBasePercentage = excluded.OnBasePercentage,
        SluggingPercentage = excluded.SluggingPercentage, OnBasePlusSlugging = excluded.OnBasePlusSlugging,
        IsolatedPower = excluded.IsolatedPower;
    """
    
    try:
        print(f"Inserting/updating stats for {len(all_stats_to_insert)} hitters...")
        cursor.executemany(sql, all_stats_to_insert)
        conn.commit()
        print(f"Successfully processed {cursor.rowcount} hitter stat records.")
    except sqlite3.Error as e:
        print(f"Database error during hitter stats insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to run the data import process for hitter stats.
    """
    print("--- Starting MLB Hitter Stats Data Import for Seasons: " + ", ".join(SEASONS) + " ---")
    
    conn = create_db_connection()
    if not conn:
        print("--- Data Import Process Finished (due to connection error) ---")
        return

    # Step 1: Get all non-pitcher players from our database
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
                
                print(f"Processing hitter {i + 1}/{len(players)} for {season}: ID {player_id}")
                
                # The API returns a list of stat objects if they played for multiple teams
                stat_splits = get_player_stats_from_api(player_id, season, STAT_GROUP)
                time.sleep(0.1) # API rate limiting

                if not stat_splits:
                    continue

                # Aggregate stats if player played for multiple teams in a season
                agg_stats = {}
                for split in stat_splits:
                    # Update team_id to the last team they played for in the season
                    team_id = split.get('team', {}).get('id', team_id)
                    stats = split.get('stat', {})
                    for key, value in stats.items():
                        # Convert numeric strings to numbers
                        try:
                            numeric_value = float(value) if '.' in str(value) else int(value)
                            agg_stats[key] = agg_stats.get(key, 0) + numeric_value
                        except (ValueError, TypeError):
                            agg_stats[key] = value # Keep as string if not numeric (e.g., avg)

                # If after all splits, team_id is still None, we cannot proceed with this record
                if team_id is None:
                    # This is common for players who didn't play in a given year, so we won't print a message
                    continue

                # Rate stats (avg/obp/slg/ops/iso) must be recomputed from the
                # aggregated counting stats, not summed across splits — summing
                # e.g. two teams' BattingAverage double-counts and produces
                # impossible values (>1.000) for players traded mid-season.
                at_bats = agg_stats.get('atBats') or 0
                hits = agg_stats.get('hits') or 0
                walks = agg_stats.get('baseOnBalls') or 0
                plate_appearances = agg_stats.get('plateAppearances') or 0
                doubles = agg_stats.get('doubles') or 0
                triples = agg_stats.get('triples') or 0
                home_runs = agg_stats.get('homeRuns') or 0
                singles = max(hits - doubles - triples - home_runs, 0)
                total_bases = singles + 2 * doubles + 3 * triples + 4 * home_runs

                avg = round(hits / at_bats, 3) if at_bats else None
                obp = round((hits + walks) / plate_appearances, 3) if plate_appearances else None
                slg = round(total_bases / at_bats, 3) if at_bats else None
                ops = round(obp + slg, 3) if obp is not None and slg is not None else None
                iso = round(slg - avg, 3) if slg is not None and avg is not None else None

                # Step 3: Prepare the data tuple for insertion
                # Note: Advanced stats like WAR, wOBA, wRC+ are not available from this endpoint
                # and will be left as NULL in the database.
                stat_tuple = (
                    player_id,
                    team_id,
                    season,
                    agg_stats.get('gamesPlayed'),
                    agg_stats.get('plateAppearances'),
                    agg_stats.get('atBats'),
                    agg_stats.get('runs'),
                    agg_stats.get('hits'),
                    agg_stats.get('doubles'),
                    agg_stats.get('triples'),
                    agg_stats.get('homeRuns'),
                    agg_stats.get('rbi'),
                    agg_stats.get('baseOnBalls'), # Walks
                    agg_stats.get('strikeOuts'), # Strikeouts
                    agg_stats.get('stolenBases'),
                    agg_stats.get('caughtStealing'),
                    avg,
                    obp,
                    slg,
                    ops,
                    iso
                )
                all_stats_to_insert.append(stat_tuple)

        # Step 4: Insert all collected stats into the database after processing all seasons
        if all_stats_to_insert:
            insert_hitter_stats_into_db(conn, all_stats_to_insert)
        else:
            print("No new stats found for any player in the specified seasons.")

    # Step 5: Close the connection
    conn.close()
    print("\n--- Data Import Process Finished ---")

if __name__ == "__main__":
    main()
