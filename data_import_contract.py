import pandas as pd
import mysql.connector
import os
import re
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- Configuration ---
# Database Connection Details from environment
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'port': int(os.getenv("DB_PORT", "25060")),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME"),
}
# The name of the CSV file in the same directory
CSV_FILE = 'SalaryData2024.csv'
# The year for the contract data
CONTRACT_YEAR = 2024

def create_db_connection():
    """
    Creates a connection to the MySQL database.
    """
    conn = None
    try:
        print(f"Connecting to database at: {DB_CONFIG['host']}...")
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Database connection successful.")
    except mysql.connector.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def get_player_map_from_db(conn):
    """
    Fetches all players from the DB and creates a map of 
    'lowercase fullname' -> PlayerID for efficient lookup.
    """
    player_map = {}
    try:
        cursor = conn.cursor(dictionary=True)
        print("Fetching all players from database to create a name map...")
        cursor.execute("SELECT PlayerID, FirstName, LastName FROM Player;")
        players = cursor.fetchall()
        for player in players:
            # Normalize the name to lowercase for matching
            full_name = f"{player['FirstName']} {player['LastName']}".lower()
            player_map[full_name] = player['PlayerID']
        print(f"Created a map for {len(players)} players.")
    except mysql.connector.Error as e:
        print(f"Database error while fetching players: {e}")
    return player_map

def get_team_map_from_db(conn):
    """
    Fetches all teams from the DB and creates a map of 
    'lowercase teamname' -> TeamID for efficient lookup.
    """
    team_map = {}
    try:
        cursor = conn.cursor(dictionary=True)
        print("Fetching all teams from database to create a name map...")
        cursor.execute("SELECT TeamID, TeamName FROM Team;")
        teams = cursor.fetchall()
        for team in teams:
            # Normalize the name to lowercase for matching
            team_name = team['TeamName'].lower()
            team_map[team_name] = team['TeamID']
        print(f"Created a map for {len(teams)} teams.")
    except mysql.connector.Error as e:
        print(f"Database error while fetching teams: {e}")
    return team_map

def parse_excel_player_name(name_string):
    """
    Parses the complex player name string from the Excel file.
    Example: "Abreu, J         Abreu, Jose" -> "Abreu, Jose"
    Example: "Betts         Betts, Mookie" -> "Betts, Mookie"
    Returns the cleaned full name.
    """
    if not isinstance(name_string, str):
        return None
    # Split the string by two or more spaces
    parts = re.split(r'\s{2,}', name_string.strip())
    # The full name is usually the last part
    if parts:
        return parts[-1].strip()
    return None

def clean_nan(value):
    """Converts numpy.nan to None, which is SQL-compatible for NULL."""
    if pd.isna(value):
        return None
    return value

def clean_currency(value):
    """
    Cleans a currency string by removing '$', ',', handling '-', and converting to a numeric type.
    Returns None if the value is empty, NaN, or cannot be converted.
    """
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned_value = value.strip()
        if cleaned_value == '-':
            return None
        try:
            # Remove currency symbols and commas
            cleaned_value = cleaned_value.replace('$', '').replace(',', '')
            if cleaned_value:
                return float(cleaned_value)
        except (ValueError, TypeError):
            # Return None if conversion fails
            return None
    return None

def insert_contracts_into_db(conn, contracts_to_insert):
    """
    Inserts or updates contract data into the Contract table.
    """
    if not contracts_to_insert:
        print("No valid contract data to insert.")
        return

    cursor = conn.cursor()
    sql = """
    INSERT INTO Contract (
        PlayerID, TeamID, Year, Salary, SigningBonus, Experience
    ) VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        Salary = VALUES(Salary),
        SigningBonus = VALUES(SigningBonus),
        Experience = VALUES(Experience);
    """
    
    try:
        print(f"Inserting/updating {len(contracts_to_insert)} contracts into the database...")
        cursor.executemany(sql, contracts_to_insert)
        conn.commit()
        print(f"Successfully processed {cursor.rowcount} contract records.")
    except mysql.connector.Error as e:
        print(f"Database error during contract insertion: {e}")
        conn.rollback()

def main():
    """
    Main function to read contract data from Excel and import it into the database.
    """
    print("--- Starting Contract Data Import ---")

    # Check if the CSV file exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: The file '{CSV_FILE}' was not found in the project folder.")
        print("--- Data Import Process Finished (with error) ---")
        return

    conn = create_db_connection()
    if not conn:
        print("--- Data Import Process Finished (due to connection error) ---")
        return

    # Step 1: Get lookup maps from the database
    player_map = get_player_map_from_db(conn)
    team_map = get_team_map_from_db(conn)
    
    # Step 2: Read the CSV file
    print(f"Reading data from '{CSV_FILE}'...")
    try:
        df = pd.read_csv(CSV_FILE)
        # Standardize column names: remove whitespace, convert to lowercase
        df.columns = df.columns.str.strip().str.lower()
        print("CSV file read successfully.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        conn.close()
        return

    contracts_to_insert = []
    unmatched_names = []
    unmatched_teams = set()

    # Step 3: Process each row in the DataFrame
    for index, row in df.iterrows():
        raw_name = row.get('player')
        team_name = row.get('teamname')
        
        # Parse the player name
        parsed_name = parse_excel_player_name(raw_name)
        if not parsed_name:
            continue

        # Normalize for matching
        normalized_name = parsed_name.lower()
        
        # Find the PlayerID from our map
        player_id = player_map.get(normalized_name)
        
        # Find the TeamID from our map
        team_id = None
        if isinstance(team_name, str):
            team_id = team_map.get(team_name.lower())

        if player_id and team_id:
            # We have a match for both, prepare the data for insertion
            contract_tuple = (
                player_id,
                team_id,
                CONTRACT_YEAR,
                clean_currency(row.get('payroll salary')),
                clean_currency(row.get('signing bonus')),
                clean_nan(row.get('exp'))
            )
            contracts_to_insert.append(contract_tuple)
        else:
            if not player_id:
                unmatched_names.append(raw_name)
            if not team_id and isinstance(team_name, str):
                unmatched_teams.add(team_name)

    # Step 4: Insert the matched data into the database
    insert_contracts_into_db(conn, contracts_to_insert)

    # Step 5: Report any names that couldn't be matched
    if unmatched_names:
        print("\n--- Warning: Could not match the following players ---")
        for name in unmatched_names:
            print(f" - {name}")
        print("These players were not added to the Contract table.")

    if unmatched_teams:
        print("\n--- Warning: Could not match the following teams ---")
        for name in sorted(list(unmatched_teams)):
            print(f" - {name}")
        print("Contracts for these teams were not added. Check for spelling differences.")

    # Step 6: Close the connection
    conn.close()
    print("\n--- Data Import Process Finished ---")

if __name__ == "__main__":
    main()
