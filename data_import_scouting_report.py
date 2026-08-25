import sqlite3
import random
from datetime import datetime

from db import create_db_connection

def get_players(conn):
    """Fetches all players from the Player table."""
    cursor = conn.cursor()
    cursor.execute("SELECT PlayerID, Position FROM Player")
    return cursor.fetchall()

def get_hitter_stats(conn, player_id):
    """Fetches aggregated hitter stats for a player."""
    cursor = conn.cursor()
    query = """
    SELECT
        AVG(BattingAverage) as avg_avg,
        AVG(HomeRuns) as avg_hr,
        AVG(StolenBases) as avg_sb
    FROM HitterStats
    WHERE PlayerID = ? AND Season BETWEEN 2021 AND 2024
    """
    cursor.execute(query, (player_id,))
    return cursor.fetchone()

def get_pitcher_stats(conn, player_id):
    """Fetches aggregated pitcher stats for a player."""
    cursor = conn.cursor()
    query = """
    SELECT
        AVG(EarnedRunAverage) as avg_era,
        AVG(Strikeouts) as avg_so,
        AVG(WalksAllowed) as avg_bb
    FROM PitcherStats
    WHERE PlayerID = ? AND Season BETWEEN 2021 AND 2024
    """
    cursor.execute(query, (player_id,))
    return cursor.fetchone()

def generate_hitter_report(stats):
    """Generates a scouting report for a hitter based on stats."""
    avg_avg = float(stats['avg_avg'] or 0.250)
    avg_hr = float(stats['avg_hr'] or 10)
    avg_sb = float(stats['avg_sb'] or 5)

    contact = int(min(10, avg_avg * 30 + random.uniform(-1, 1)))
    power = int(min(10, avg_hr * 0.4 + random.uniform(-1, 1)))
    running = int(min(10, avg_sb * 0.5 + random.uniform(-1, 1)))
    fielding = random.randint(4, 8)
    arm = random.randint(5, 9)
    
    overall = contact + power + running + fielding + arm
    
    summary = f"Promising hitter with solid potential. Contact grade of {contact} is backed by a respectable batting average. Power grade of {power} shows room for growth. Speed ({running}) is a key asset."
    
    return contact, power, running, fielding, arm, 0, 0, 0, 0, overall, summary

def generate_pitcher_report(stats):
    """Generates a scouting report for a pitcher based on stats."""
    avg_bb = float(stats['avg_bb'] or 30)

    velocity = random.randint(6, 10) 
    accuracy = int(min(10, 10 - avg_bb * 0.1 + random.uniform(-1, 1)))
    spin_rate = random.randint(5, 10)
    breaking_ball = random.randint(5, 9)
    
    overall = velocity + accuracy + spin_rate + breaking_ball
    
    summary = f"This pitcher shows a strong arm with a velocity grade of {velocity}. Accuracy ({accuracy}) is solid, keeping walks down. Spin rate ({spin_rate}) on pitches is a significant weapon."

    return 0, 0, 0, 0, 0, velocity, accuracy, spin_rate, breaking_ball, overall, summary

def insert_scouting_reports(conn, reports):
    """Inserts scouting reports into the database.

    ScoutingReport has no unique constraint besides its auto-generated
    ReportID (which isn't part of this insert), so every run always appends
    fresh rows rather than upserting existing ones — this matches the
    original MySQL behavior, where the ON DUPLICATE KEY UPDATE clause could
    never actually trigger for the same reason.
    """
    cursor = conn.cursor()
    sql = """
    INSERT INTO ScoutingReport (
        PlayerID, ReportDate, Position, ContactGrade, PowerGrade, RunningGrade,
        FieldingGrade, ArmGrade, PitchingVelocity, PitchingAccuracy,
        SpinRateGrade, BreakingBallGrade, OverallPotential, Summary
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    try:
        cursor.executemany(sql, reports)
        conn.commit()
        print(f"Successfully inserted/updated {cursor.rowcount} scouting reports.")
    except sqlite3.Error as e:
        print(f"Database error during insertion: {e}")
        conn.rollback()

def main():
    """Main function to generate and import scouting reports."""
    print("--- Starting Scouting Report Generation ---")
    conn = create_db_connection()
    if not conn:
        return

    players = get_players(conn)
    reports_to_insert = []
    report_date = datetime.now().date().isoformat()

    for i, player in enumerate(players):
        player_id = player['PlayerID']
        position = player['Position']
        
        print(f"Generating report for player {i + 1}/{len(players)}: ID {player_id}")
        
        if position == 'Pitcher':
            stats = get_pitcher_stats(conn, player_id)
            if stats:
                grades = generate_pitcher_report(stats)
                reports_to_insert.append((player_id, report_date, position) + grades)
        else:
            stats = get_hitter_stats(conn, player_id)
            if stats:
                grades = generate_hitter_report(stats)
                reports_to_insert.append((player_id, report_date, position) + grades)

    if reports_to_insert:
        insert_scouting_reports(conn, reports_to_insert)

    conn.close()
    print("\n--- Scouting Report Import Finished ---")

if __name__ == "__main__":
    main()
