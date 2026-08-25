import requests
import sqlite3

from db import create_db_connection

# --- Configuration ---
API_BASE_URL = "http://statsapi.mlb.com/api/v1"

SEASON = "2024"
# Sport IDs for all professional baseball levels
SPORT_IDS = [1, 11, 12, 13, 14] # MLB, AAA, AA, A+, A

def get_all_teams_from_api(season, sport_ids):
    """
    Fetches a list of all teams for a given season across multiple sport IDs.
    
    Args:
        season (str): The year of the season to fetch.
        sport_ids (list): A list of sport IDs for different league levels.
        
    Returns:
        list: A consolidated list of team data dictionaries, or an empty list if the request fails.
    """
    all_teams = []
    # Use a set to keep track of team IDs to avoid duplicates
    seen_team_ids = set()

    for sport_id in sport_ids:
        url = f"{API_BASE_URL}/teams?sportId={sport_id}&season={season}"
        print(f"Fetching teams and leagues from API for sportId: {sport_id}...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            teams = response.json().get("teams", [])
            
            for team in teams:
                if team['id'] not in seen_team_ids:
                    all_teams.append(team)
                    seen_team_ids.add(team['id'])

            print(f"Successfully fetched {len(teams)} teams for sportId: {sport_id}.")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for sportId {sport_id}: {e}")
    
    print(f"Total unique teams fetched: {len(all_teams)}")
    return all_teams

def insert_leagues_into_db(conn, teams):
    """
    Extracts unique leagues from the team data and inserts them into the League table.
    
    Args:
        conn (sqlite3.Connection): The database connection object.
        teams (list): A list of team data dictionaries from the API.
    """
    if not teams:
        print("No team data provided to extract leagues.")
        return

    cursor = conn.cursor()
    sql = "INSERT OR IGNORE INTO League (LeagueID, LeagueName, LeagueLevel) VALUES (?, ?, ?);"
    
    leagues_to_insert = set()
    for team in teams:
        if "league" in team and "name" in team["league"]:
            league_id = team["league"].get("id")
            league_name = team["league"].get("name")
            # The 'sport' object often contains the level (e.g., Major League Baseball)
            league_level = team.get("sport", {}).get("name", "Unknown")
            leagues_to_insert.add((league_id, league_name, league_level))
            
    try:
        print(f"Inserting/updating {len(leagues_to_insert)} leagues into the database...")
        cursor.executemany(sql, list(leagues_to_insert))
        conn.commit()
        print(f"Successfully inserted/updated {cursor.rowcount} leagues.")
    except sqlite3.Error as e:
        print(f"Database error during league insertion: {e}")
        conn.rollback()

def insert_teams_into_db(conn, teams):
    """
    Inserts team data into the Team table.
    
    Args:
        conn (sqlite3.Connection): The database connection object.
        teams (list): A list of team data dictionaries from the API.
    """
    if not teams:
        print("No teams to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT OR IGNORE INTO Team (
        TeamID, TeamName, City, LeagueID, MLBAffiliateID
    ) VALUES (?, ?, ?, ?, ?);
    """
    
    teams_to_insert = []
    for team in teams:
        teams_to_insert.append((
            team.get("id"),
            team.get("name"),
            team.get("locationName"),
            team.get("league", {}).get("id"),
            team.get("parentOrgId") # This is the affiliate ID for MiLB teams
        ))
        
    try:
        print(f"Inserting/updating {len(teams_to_insert)} teams into the database...")
        cursor.executemany(sql, teams_to_insert)
        conn.commit()
        print(f"Successfully inserted/updated {cursor.rowcount} teams.")
    except sqlite3.Error as e:
        print(f"Database error during team insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to run the data import process for leagues and teams.
    """
    print("--- Starting MLB League and Team Data Import ---")
    
    # Step 1: Fetch team data from the API
    teams = get_all_teams_from_api(SEASON, SPORT_IDS)
    
    if teams:
        # Step 2: Connect to the database
        conn = create_db_connection()
        
        if conn:
            # Step 3: Insert leagues first to satisfy foreign key constraints
            insert_leagues_into_db(conn, teams)
            
            # Step 4: Insert teams
            insert_teams_into_db(conn, teams)
            
            # Step 5: Close the connection
            conn.close()
            print("Database connection closed.")
    
    print("--- Data Import Process Finished ---")

if __name__ == "__main__":
    main()
