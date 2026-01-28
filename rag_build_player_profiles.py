import os
from datetime import datetime

import mysql.connector
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions


load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "port": int(os.getenv("DB_PORT", "25060")),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
}


def create_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return None


# ---------- FETCH DATA ----------


def fetch_hitter_seasons(conn, start_season=2021, end_season=2024):
    """One row per (PlayerID, Season) for hitters, joined with Player, Team, League, Contract.

    Contract is LEFT JOINed because many minor-league players will not have
    a row in the Contract table.
    """
    sql = f"""
        SELECT
            hs.PlayerID,
            hs.Season,
            p.FirstName,
            p.LastName,
            p.Position,
            p.PlayerLevel,
            t.TeamID,
            t.TeamName,
            l.LeagueName,
            l.LeagueLevel,
            parent.TeamID AS ParentMLBTeamID,
            parent.TeamName AS ParentMLBTeamName,
            c.TeamID AS ContractTeamID,
            c.Year AS ContractYear,
            c.Salary AS ContractSalary,
            c.SigningBonus AS ContractSigningBonus,
            c.Experience AS ContractExperience,
            hs.GamesPlayed,
            hs.PlateAppearances,
            hs.AtBats,
            hs.Runs,
            hs.Hits,
            hs.Doubles,
            hs.Triples,
            hs.HomeRuns,
            hs.RBI,
            hs.Walks,
            hs.Strikeouts,
            hs.StolenBases,
            hs.CaughtStealing,
            hs.BattingAverage,
            hs.OnBasePercentage,
            hs.SluggingPercentage,
            hs.OnBasePlusSlugging,
            hs.IsolatedPower,
            hs.HardHitPercentage,
            hs.WinsAboveReplacement,
            hs.WeightedOnBaseAverage,
            hs.WeightedRunsCreatedPlus
        FROM HitterStats hs
        JOIN Player p ON hs.PlayerID = p.PlayerID
        JOIN Team t ON hs.TeamID = t.TeamID
        JOIN League l ON t.LeagueID = l.LeagueID
        LEFT JOIN Team parent ON t.MLBAffiliateID = parent.TeamID
        LEFT JOIN Contract c
            ON c.PlayerID = hs.PlayerID AND c.Year = hs.Season
        WHERE hs.Season BETWEEN %s AND %s
        ORDER BY hs.PlayerID, hs.Season;
    """
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, (start_season, end_season))
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_pitcher_seasons(conn, start_season=2021, end_season=2024):
    """One row per (PlayerID, Season) for pitchers, joined with Player, Team, League, Contract.

    Contract is LEFT JOINed because many minor-league players will not have
    a row in the Contract table.
    """
    sql = f"""
        SELECT
            ps.PlayerID,
            ps.Season,
            p.FirstName,
            p.LastName,
            p.Position,
            p.PlayerLevel,
            t.TeamID,
            t.TeamName,
            l.LeagueName,
            l.LeagueLevel,
            parent.TeamID AS ParentMLBTeamID,
            parent.TeamName AS ParentMLBTeamName,
            c.TeamID AS ContractTeamID,
            c.Year AS ContractYear,
            c.Salary AS ContractSalary,
            c.SigningBonus AS ContractSigningBonus,
            c.Experience AS ContractExperience,
            ps.Wins,
            ps.Losses,
            ps.GamesPitched,
            ps.GamesStarted,
            ps.Saves,
            ps.Holds,
            ps.InningsPitched,
            ps.HitsAllowed,
            ps.RunsAllowed,
            ps.EarnedRuns,
            ps.HomeRunsAllowed,
            ps.WalksAllowed,
            ps.Strikeouts,
            ps.EarnedRunAverage,
            ps.FieldingIndependentPitching,
            ps.ExpectedERA,
            ps.WalksAndHitsPerInningPitched,
            ps.WhiffPercentage
        FROM PitcherStats ps
        JOIN Player p ON ps.PlayerID = p.PlayerID
        JOIN Team t ON ps.TeamID = t.TeamID
        JOIN League l ON t.LeagueID = l.LeagueID
        LEFT JOIN Team parent ON t.MLBAffiliateID = parent.TeamID
        LEFT JOIN Contract c
            ON c.PlayerID = ps.PlayerID AND c.Year = ps.Season
        WHERE ps.Season BETWEEN %s AND %s
        ORDER BY ps.PlayerID, ps.Season;
    """
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, (start_season, end_season))
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------- DOCUMENT BUILDERS ----------


def _get_float(row: dict, key: str, default: float = 0.0) -> float:
    value = row.get(key)
    return float(value) if value is not None else default


def build_hitter_season_doc(row: dict) -> str:
    """Turn a hitter season row into a natural-language document."""
    full_name = f"{row['FirstName']} {row['LastName']}"
    season = row["Season"]
    position = row.get("Position") or "Unknown"
    level = row.get("PlayerLevel") or "Unknown"
    team = row.get("TeamName") or "Unknown Team"
    parent_mlb = row.get("ParentMLBTeamName")
    league_name = row.get("LeagueName") or "Unknown League"
    league_level = row.get("LeagueLevel") or "Unknown Level"

    contract_year = row.get("ContractYear")
    contract_team_id = row.get("ContractTeamID")
    contract_salary = row.get("ContractSalary")
    contract_signing_bonus = row.get("ContractSigningBonus")
    contract_experience = row.get("ContractExperience")

    doc = (
        f"Player season profile (Hitter):\n"
        f"Name: {full_name}\n"
        f"PlayerID: {row['PlayerID']}\n"
        f"Season: {season}\n"
        f"Position: {position}\n"
        f"Player level: {level}\n"
        f"Team: {team}\n"
        f"League: {league_name}\n"
        f"League level: {league_level}\n"
        f"Parent MLB organization: {parent_mlb if parent_mlb is not None else 'N/A'}\n"
        f"\n"
        f"Contract information (if present):\n"
        f"Contract year: {contract_year if contract_year is not None else 'No MLB contract for this season'}\n"
        f"Contract team ID: {contract_team_id if contract_team_id is not None else 'N/A'}\n"
        f"Contract salary: {contract_salary if contract_salary is not None else 'N/A'}\n"
        f"Contract signing bonus: {contract_signing_bonus if contract_signing_bonus is not None else 'N/A'}\n"
        f"Years of experience at contract time: {contract_experience if contract_experience is not None else 'N/A'}\n"
        f"\n"
        f"Basic counting stats:\n"
        f"Games played: {row.get('GamesPlayed')}\n"
        f"Plate appearances: {row.get('PlateAppearances')}\n"
        f"At-bats: {row.get('AtBats')}\n"
        f"Runs: {row.get('Runs')}\n"
        f"Hits: {row.get('Hits')}\n"
        f"Doubles: {row.get('Doubles')}\n"
        f"Triples: {row.get('Triples')}\n"
        f"Home runs: {row.get('HomeRuns')}\n"
        f"Runs batted in (RBI): {row.get('RBI')}\n"
        f"Walks: {row.get('Walks')}\n"
        f"Strikeouts: {row.get('Strikeouts')}\n"
        f"Stolen bases: {row.get('StolenBases')}\n"
        f"Caught stealing: {row.get('CaughtStealing')}\n"
        f"\n"
        f"Rate stats:\n"
        f"Batting average (AVG): {_get_float(row, 'BattingAverage'):.3f}\n"
        f"On-base percentage (OBP): {_get_float(row, 'OnBasePercentage'):.3f}\n"
        f"Slugging percentage (SLG): {_get_float(row, 'SluggingPercentage'):.3f}\n"
        f"On-base plus slugging (OPS): {_get_float(row, 'OnBasePlusSlugging'):.3f}\n"
        f"Isolated power (ISO): {_get_float(row, 'IsolatedPower'):.3f}\n"
        f"Hard-hit percentage: {_get_float(row, 'HardHitPercentage'):.1f}\n"
        f"\n"
        f"Advanced value metrics:\n"
        f"Wins Above Replacement (WAR): {_get_float(row, 'WinsAboveReplacement'):.2f}\n"
        f"Weighted On-Base Average (wOBA): {_get_float(row, 'WeightedOnBaseAverage'):.3f}\n"
        f"Weighted Runs Created Plus (wRC+): {_get_float(row, 'WeightedRunsCreatedPlus'):.1f}\n"
        f"\n"
        f"Use this document to evaluate how this hitter performed in this specific season "
        f"relative to other players and levels.\n"
    )
    return doc


def _normalize_league_level_short(league_level: str | None) -> str | None:
    """Map verbose league levels to short codes (MLB, AAA, AA, etc.)."""
    if not league_level:
        return None
    text = league_level.lower()
    if "major" in text and "league" in text:
        return "MLB"
    if "triple" in text or "aaa" in text:
        return "AAA"
    if "double" in text or "aa" in text:
        return "AA"
    if "high-a" in text or "high a" in text:
        return "High-A"
    if "low-a" in text or "low a" in text or "single-a" in text or "single a" in text:
        return "A"
    if "rookie" in text or "complex" in text:
        return "Rookie"
    if "college" in text:
        return "College"
    return league_level


def build_pitcher_season_doc(row: dict) -> str:
    """Turn a pitcher season row into a natural-language document."""
    full_name = f"{row['FirstName']} {row['LastName']}"
    season = row["Season"]
    position = row.get("Position") or "Pitcher"
    level = row.get("PlayerLevel") or "Unknown"
    team = row.get("TeamName") or "Unknown Team"
    parent_mlb = row.get("ParentMLBTeamName")
    league_name = row.get("LeagueName") or "Unknown League"
    league_level = row.get("LeagueLevel") or "Unknown Level"

    contract_year = row.get("ContractYear")
    contract_team_id = row.get("ContractTeamID")
    contract_salary = row.get("ContractSalary")
    contract_signing_bonus = row.get("ContractSigningBonus")
    contract_experience = row.get("ContractExperience")

    doc = (
        f"Player season profile (Pitcher):\n"
        f"Name: {full_name}\n"
        f"PlayerID: {row['PlayerID']}\n"
        f"Season: {season}\n"
        f"Position: {position}\n"
        f"Player level: {level}\n"
        f"Team: {team}\n"
        f"League: {league_name}\n"
        f"League level: {league_level}\n"
        f"Parent MLB organization: {parent_mlb if parent_mlb is not None else 'N/A'}\n"
        f"\n"
        f"Contract information (if present):\n"
        f"Contract year: {contract_year if contract_year is not None else 'No MLB contract for this season'}\n"
        f"Contract team ID: {contract_team_id if contract_team_id is not None else 'N/A'}\n"
        f"Contract salary: {contract_salary if contract_salary is not None else 'N/A'}\n"
        f"Contract signing bonus: {contract_signing_bonus if contract_signing_bonus is not None else 'N/A'}\n"
        f"Years of experience at contract time: {contract_experience if contract_experience is not None else 'N/A'}\n"
        f"\n"
        f"Basic pitching stats:\n"
        f"Wins: {row.get('Wins')}\n"
        f"Losses: {row.get('Losses')}\n"
        f"Games pitched: {row.get('GamesPitched')}\n"
        f"Games started: {row.get('GamesStarted')}\n"
        f"Saves: {row.get('Saves')}\n"
        f"Holds: {row.get('Holds')}\n"
        f"Innings pitched: {_get_float(row, 'InningsPitched'):.1f}\n"
        f"Hits allowed: {row.get('HitsAllowed')}\n"
        f"Runs allowed: {row.get('RunsAllowed')}\n"
        f"Earned runs: {row.get('EarnedRuns')}\n"
        f"Home runs allowed: {row.get('HomeRunsAllowed')}\n"
        f"Walks allowed: {row.get('WalksAllowed')}\n"
        f"Strikeouts: {row.get('Strikeouts')}\n"
        f"\n"
        f"Rate stats and advanced metrics:\n"
        f"Earned run average (ERA): {_get_float(row, 'EarnedRunAverage'):.2f}\n"
        f"Fielding Independent Pitching (FIP): {_get_float(row, 'FieldingIndependentPitching'):.2f}\n"
        f"Expected ERA (xERA): {_get_float(row, 'ExpectedERA'):.2f}\n"
        f"Walks and hits per inning pitched (WHIP): {_get_float(row, 'WalksAndHitsPerInningPitched'):.2f}\n"
        f"Whiff percentage: {_get_float(row, 'WhiffPercentage'):.1f}\n"
        f"\n"
        f"Use this document to evaluate how this pitcher performed in this specific season "
        f"relative to other players and levels.\n"
    )
    return doc


# ---------- MAIN: BUILD CHROMA COLLECTION ----------


def build_player_profiles(start_season: int = 2021, end_season: int = 2024):
    print(f"--- Building player season profiles for {start_season}-{end_season} ---")
    conn = create_db_connection()
    if not conn:
        print("Failed to connect to database. Exiting.")
        return

    print("Fetching hitter season rows...")
    hitter_rows = fetch_hitter_seasons(conn, start_season, end_season)
    print(f"Fetched {len(hitter_rows)} hitter-season rows.")

    print("Fetching pitcher season rows...")
    pitcher_rows = fetch_pitcher_seasons(conn, start_season, end_season)
    print(f"Fetched {len(pitcher_rows)} pitcher-season rows.")

    conn.close()

    # Setup Chroma persistent client + embedding function
    client = chromadb.PersistentClient(path=".chromadb")
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY"),
        model_name="text-embedding-3-small",
    )

    collection = client.get_or_create_collection(
        name="player_season_profiles",
        embedding_function=openai_ef,
    )

    ids = []
    docs = []
    metadatas = []

    # Track how many times we've seen each base ID to ensure uniqueness
    id_counts = {}

    # Build hitter docs
    print("Building hitter documents...")
    for idx, row in enumerate(hitter_rows, start=1):
        doc = build_hitter_season_doc(row)
        pid = int(row["PlayerID"])
        season = int(row["Season"])
        base_id = f"hitter_{pid}_{season}"

        # Ensure unique Chroma ID even if (PlayerID, Season) appears multiple times
        count = id_counts.get(base_id, 0)
        if count == 0:
            doc_id = base_id
        else:
            doc_id = f"{base_id}-{count}"
        id_counts[base_id] = count + 1

        ids.append(doc_id)
        docs.append(doc)
        metadatas.append({
            "role": "hitter",
            "player_id": pid,
            "season": season,
            "position": row.get("Position") or "",
            "player_level": row.get("PlayerLevel") or "",
            "team_id": int(row.get("TeamID") or 0),
            "team": row.get("TeamName") or "",
            "league_level": row.get("LeagueLevel") or "",
            "parent_mlb_team_id": int(row.get("ParentMLBTeamID") or 0),
            "parent_mlb_team_name": row.get("ParentMLBTeamName") or "",
        })

        if idx % 500 == 0:
            print(f"  Processed {idx}/{len(hitter_rows)} hitter-season docs...")

    # Build pitcher docs
    print("Building pitcher documents...")
    for idx, row in enumerate(pitcher_rows, start=1):
        doc = build_pitcher_season_doc(row)
        pid = int(row["PlayerID"])
        season = int(row["Season"])
        base_id = f"pitcher_{pid}_{season}"

        # Ensure unique Chroma ID even if (PlayerID, Season) appears multiple times
        count = id_counts.get(base_id, 0)
        if count == 0:
            doc_id = base_id
        else:
            doc_id = f"{base_id}-{count}"
        id_counts[base_id] = count + 1

        ids.append(doc_id)
        docs.append(doc)
        metadatas.append({
            "role": "pitcher",
            "player_id": pid,
            "season": season,
            "position": row.get("Position") or "P",
            "player_level": row.get("PlayerLevel") or "",
            "team_id": int(row.get("TeamID") or 0),
            "team": row.get("TeamName") or "",
            "league_level": row.get("LeagueLevel") or "",
            # MLB affiliation in both snake_case and CamelCase for flexibility in filters
            "parent_mlb_team_id": int(row.get("ParentMLBTeamID") or 0),
            "parent_mlb_team_name": row.get("ParentMLBTeamName") or "",
            "ParentMLBTeamID": int(row.get("ParentMLBTeamID") or 0),
            "ParentMLBTeamName": row.get("ParentMLBTeamName") or "",
        })

        if idx % 500 == 0:
            print(f"  Processed {idx}/{len(pitcher_rows)} pitcher-season docs...")

    print(f"Adding {len(docs)} total documents to Chroma collection 'player_season_profiles'...")

    # Add documents in batches to avoid exceeding OpenAI token limits
    batch_size = 500  # adjust if needed (e.g., 200–1000)
    for start in range(0, len(docs), batch_size):
        end = min(start + batch_size, len(docs))
        batch_ids = ids[start:end]
        batch_docs = docs[start:end]
        batch_metadatas = metadatas[start:end]
        print(f"  Adding documents {start}–{end - 1}...")
        collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metadatas)

    print("Done.")
    print("--- Player season profiles build complete ---")


if __name__ == "__main__":
    # You can tweak the range here if needed
    build_player_profiles(2021, 2024)
