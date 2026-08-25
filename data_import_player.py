import requests
import sqlite3
import time

from db import create_db_connection

# --- Configuration ---
# The base URL for the MLB Stats API
API_BASE_URL = "http://statsapi.mlb.com/api/v1"

# The season you want to import players from
SEASON = "2024"
# Sport IDs for all professional baseball levels
SPORT_IDS = [1, 11, 12, 13, 14] # MLB, AAA, AA, A+, A

def get_all_teams_from_api(season, sport_ids):
    """
    Fetches a list of all teams for a given season across multiple sport IDs.
    """
    all_teams = []
    seen_team_ids = set()
    for sport_id in sport_ids:
        url = f"{API_BASE_URL}/teams?sportId={sport_id}&season={season}"
        print(f"Fetching teams from API for sportId: {sport_id}...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            teams = response.json().get("teams", [])
            for team in teams:
                if team['id'] not in seen_team_ids:
                    all_teams.append(team)
                    seen_team_ids.add(team['id'])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for sportId {sport_id}: {e}")
    print(f"Total unique teams fetched: {len(all_teams)}")
    return all_teams

def get_all_players_from_api(teams, season):
    """
    Fetches all players by iterating through each team's roster.
    
    Args:
        teams (list): A list of team data dictionaries.
        season (str): The year of the season to fetch rosters for.
        
    Returns:
        list: A consolidated list of unique player data dictionaries.
    """
    all_players = []
    seen_player_ids = set()

    for team in teams:
        team_id = team.get("id")
        team_level = team.get("sport", {}).get("name", "Unknown")
        url = f"{API_BASE_URL}/teams/{team_id}/roster?season={season}"
        print(f"Fetching roster for teamId: {team_id} ({team.get('name')})...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            roster = response.json().get("roster", [])
            
            for item in roster:
                player = item.get("person")
                if player and player['id'] not in seen_player_ids:
                    # Add team_level and position to player dict for later use
                    player['team_level'] = team_level
                    player['position_name'] = item.get("position", {}).get("name")
                    all_players.append(player)
                    seen_player_ids.add(player['id'])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching roster for teamId {team_id}: {e}")
            
    print(f"Total unique players fetched: {len(all_players)}")
    return all_players

def get_player_details(player_id):
    """
    Fetches detailed information for a single player.
    
    Args:
        player_id (int): The ID of the player to fetch.
        
    Returns:
        dict: A dictionary with the player's detailed info, or an empty dict if an error occurs.
    """
    url = f"{API_BASE_URL}/people/{player_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get("people", [{}])[0]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for playerId {player_id}: {e}")
        return {}

def insert_players_into_db(conn, players):
    """
    Inserts or updates player data into the Player table after enriching it with details.
    """
    if not players:
        print("No players to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT INTO Player (
        PlayerID, FirstName, LastName, DateOfBirth, Position,
        Height, Weight, Throws, Bats, PlayerLevel
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(PlayerID) DO UPDATE SET
        FirstName = excluded.FirstName,
        LastName = excluded.LastName,
        DateOfBirth = excluded.DateOfBirth,
        Position = excluded.Position,
        Height = excluded.Height,
        Weight = excluded.Weight,
        Throws = excluded.Throws,
        Bats = excluded.Bats,
        PlayerLevel = excluded.PlayerLevel;
    """
    
    players_to_insert = []
    for i, player in enumerate(players):
        player_id = player.get("id")
        print(f"Processing player {i + 1}/{len(players)}: ID {player_id}")
        
        # Fetch detailed player info
        details = get_player_details(player_id)
        time.sleep(0.1) # Be respectful to the API, avoid getting blocked

        # Convert height to inches
        height_inches = None
        if "height" in details and details["height"]:
            try:
                feet, inches = details["height"].replace('"', '').split("' ")
                height_inches = int(feet) * 12 + int(inches)
            except (ValueError, TypeError):
                height_inches = None

        players_to_insert.append((
            player_id,
            details.get("firstName", player.get("fullName", "").split(" ")[0]),
            details.get("lastName", " ".join(player.get("fullName", "").split(" ")[1:])),
            details.get("birthDate"),
            player.get('position_name'),
            height_inches,
            details.get("weight"),
            details.get("pitchHand", {}).get("code"),
            details.get("batSide", {}).get("code"),
            player.get('team_level', 'Unknown')
        ))
        
    try:
        print(f"Inserting/updating {len(players_to_insert)} players into the database...")
        cursor.executemany(sql, players_to_insert)
        conn.commit()
        print(f"Successfully inserted/updated {cursor.rowcount} players.")
    except sqlite3.Error as e:
        print(f"Database error during insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to run the data import process.
    """
    print("--- Starting MLB Player Data Import ---")
    
    # Step 1: Fetch all teams from all league levels
    teams = get_all_teams_from_api(SEASON, SPORT_IDS)

    if teams:
        # Step 2: Fetch all players from the rosters of those teams
        players = get_all_players_from_api(teams, SEASON)
        
        if players:
            # Step 3: Connect to the database
            conn = create_db_connection()
            
            if conn:
                # Step 4: Insert players into the database
                insert_players_into_db(conn, players)
                
                # Step 5: Close the connection
                conn.close()
                print("Database connection closed.")
    
    print("--- Data Import Process Finished ---")

if __name__ == "__main__":
    main()
