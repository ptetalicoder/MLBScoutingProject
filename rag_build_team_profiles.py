from decimal import Decimal

import chromadb
from chromadb.utils import embedding_functions

from db import create_db_connection, dict_row_factory


SEASONS = [2021, 2022, 2023, 2024]


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_team_seasons(conn):
    """Fetch team + league + TeamHistoricalData rows for target seasons.

    Also joins back to the parent MLB club (if this is a minor league affiliate)
    via Team.MLBAffiliateID, so we can store organization-level metadata
    for RAG.
    """
    sql = """
        SELECT
            t.TeamID,
            t.TeamName,
            t.City,
            l.LeagueName,
            l.LeagueLevel,
            thd.Year,
            thd.Wins,
            thd.Losses,
            thd.PlayoffAppearance,
            thd.WorldSeriesWin,
            thd.RunsScored,
            thd.RunsAllowed,
            thd.RunDifferential,
            thd.TeamBattingAverage,
            thd.TeamOnBasePercentage,
            thd.TeamSluggingPercentage,
            thd.TeamOnBasePlusSlugging,
            thd.TeamHomeRuns,
            thd.TeamHits,
            thd.TeamRBI,
            thd.TeamStolenBases,
            thd.TeamEarnedRunAverage,
            thd.TeamWHIP,
            thd.TeamStrikeoutsPitching,
            thd.TeamWalksAllowed,
            parent.TeamID AS ParentMLBTeamID,
            parent.TeamName AS ParentMLBTeamName
        FROM TeamHistoricalData thd
        JOIN Team t ON thd.TeamID = t.TeamID
        LEFT JOIN League l ON t.LeagueID = l.LeagueID
        LEFT JOIN Team parent ON t.MLBAffiliateID = parent.TeamID
        WHERE thd.Year IN (?, ?, ?, ?)
        ORDER BY thd.Year, t.TeamID
    """

    cursor = conn.cursor()
    cursor.row_factory = dict_row_factory
    cursor.execute(sql, tuple(SEASONS))
    rows = cursor.fetchall()
    cursor.close()
    return rows


def build_team_season_doc(row):
    """Build a natural-language description of a team-season."""
    team_name = row.get("TeamName") or "Unknown Team"
    city = row.get("City") or "Unknown City"
    league = row.get("LeagueName") or "Unknown League"
    level = row.get("LeagueLevel") or "Unknown Level"
    parent_mlb_name = row.get("ParentMLBTeamName")
    year = row.get("Year")

    wins = row.get("Wins")
    losses = row.get("Losses")
    playoff = row.get("PlayoffAppearance")
    ws_win = row.get("WorldSeriesWin")

    runs_scored = row.get("RunsScored")
    runs_allowed = row.get("RunsAllowed")
    run_diff = row.get("RunDifferential")

    ba = _to_float(row.get("TeamBattingAverage"))
    obp = _to_float(row.get("TeamOnBasePercentage"))
    slg = _to_float(row.get("TeamSluggingPercentage"))
    ops = _to_float(row.get("TeamOnBasePlusSlugging"))

    hr = row.get("TeamHomeRuns")
    hits = row.get("TeamHits")
    rbi = row.get("TeamRBI")
    sb = row.get("TeamStolenBases")

    era = _to_float(row.get("TeamEarnedRunAverage"))
    whip = _to_float(row.get("TeamWHIP"))
    k_pitch = row.get("TeamStrikeoutsPitching")
    bb_allowed = row.get("TeamWalksAllowed")

    playoff_text = "made the playoffs" if playoff else "did not make the playoffs"
    ws_text = "and won the World Series" if ws_win else "and did not win the World Series"

    parts = []
    parts.append(
        f"In {year}, the {city} {team_name} played in the {league} ({level})."
    )

    if parent_mlb_name:
        parts.append(
            f"They are an affiliate of the {parent_mlb_name} organization."
        )

    if wins is not None and losses is not None:
        parts.append(
            f"They finished with a record of {wins}-{losses}, {playoff_text} {ws_text}."
        )

    if runs_scored is not None and runs_allowed is not None:
        diff_str = (
            f"a run differential of {run_diff}" if run_diff is not None else "an unknown run differential"
        )
        parts.append(
            f"They scored {runs_scored} runs and allowed {runs_allowed} runs, for {diff_str}."
        )

    # Offense summary
    off_pieces = []
    if ba is not None:
        off_pieces.append(f"team batting average of {ba:.3f}")
    if obp is not None:
        off_pieces.append(f"on-base percentage of {obp:.3f}")
    if slg is not None:
        off_pieces.append(f"slugging percentage of {slg:.3f}")
    if ops is not None:
        off_pieces.append(f"OPS of {ops:.3f}")

    if off_pieces or any(v is not None for v in [hr, hits, rbi, sb]):
        line = "Offensively, they had "
        pieces_text = []
        if off_pieces:
            pieces_text.append(", ".join(off_pieces))
        if hr is not None:
            pieces_text.append(f"{hr} home runs")
        if hits is not None:
            pieces_text.append(f"{hits} hits")
        if rbi is not None:
            pieces_text.append(f"{rbi} runs batted in")
        if sb is not None:
            pieces_text.append(f"{sb} stolen bases")
        line += ", ".join(pieces_text) + "."
        parts.append(line)

    # Pitching summary
    pitch_pieces = []
    if era is not None:
        pitch_pieces.append(f"team ERA of {era:.2f}")
    if whip is not None:
        pitch_pieces.append(f"WHIP of {whip:.2f}")
    if k_pitch is not None:
        pitch_pieces.append(f"{k_pitch} strikeouts")
    if bb_allowed is not None:
        pitch_pieces.append(f"{bb_allowed} walks allowed")

    if pitch_pieces:
        parts.append("On the mound, they posted " + ", ".join(pitch_pieces) + ".")

    return " " .join(parts)


def build_team_profiles():
    print("--- Starting Team Team-Season Profile Build ---")

    conn = create_db_connection()
    if not conn:
        print("--- Aborting: could not connect to database ---")
        return

    rows = fetch_team_seasons(conn)
    print(f"Fetched {len(rows)} team-season rows.")

    if not rows:
        conn.close()
        print("No data found; exiting.")
        return

    # Set up persistent Chroma client + local ONNX embedding function (free, offline)
    client = chromadb.PersistentClient(path=".chromadb")

    embedding_function = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="team_season_profiles",
        embedding_function=embedding_function,
    )

    ids = []
    documents = []
    metadatas = []

    for row in rows:
        team_id = row.get("TeamID")
        year = row.get("Year")
        base_id = f"team_{team_id}_{year}"

        doc = build_team_season_doc(row)

        metadata = {
            "TeamID": int(team_id) if team_id is not None else 0,
            "TeamName": row.get("TeamName") or "",
            "City": row.get("City") or "",
            "LeagueName": row.get("LeagueName") or "",
            "LeagueLevel": row.get("LeagueLevel") or "",
            "Year": int(year) if year is not None else 0,
            "Wins": int(row.get("Wins") or 0),
            "Losses": int(row.get("Losses") or 0),
            "PlayoffAppearance": int(row.get("PlayoffAppearance") or 0),
            "WorldSeriesWin": int(row.get("WorldSeriesWin") or 0),
            # MLB affiliation fields used by the app's RAG filters
            "ParentMLBTeamID": int(row.get("ParentMLBTeamID") or 0),
            "ParentMLBTeamName": row.get("ParentMLBTeamName") or "",
            # Convenience lower‑case keys to match downstream metadata lookups
            "parent_mlb_team_id": int(row.get("ParentMLBTeamID") or 0),
            "parent_mlb_team_name": row.get("ParentMLBTeamName") or "",
        }

        ids.append(base_id)
        documents.append(doc)
        metadatas.append(metadata)

    # Batch insert to stay under token limits
    batch_size = 500
    total = len(ids)
    print(f"Adding {total} documents to Chroma in batches of {batch_size}...")

    for start in range(0, total, batch_size):
        end = start + batch_size
        batch_ids = ids[start:end]
        batch_docs = documents[start:end]
        batch_metas = metadatas[start:end]
        print(f"Adding documents {start} to {end - 1}...")
        collection.add(ids=batch_ids, documents=batch_docs, metadatas=batch_metas)

    conn.close()
    print("Database connection closed.")
    print("--- Finished building team-season profiles ---")


if __name__ == "__main__":
    build_team_profiles()
