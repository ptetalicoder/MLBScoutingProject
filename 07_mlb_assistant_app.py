import streamlit as st
import pandas as pd
import re
import sqlite3
from openai import OpenAI
from dotenv import load_dotenv
import altair as alt
import os
import textwrap
import chromadb
from chromadb.utils import embedding_functions

from db import create_readonly_connection, create_sandbox_connection, dict_row_factory


# --- Team Colors (basic mapping, extend as needed) ---
TEAM_COLORS = {
    # American League East
    "Baltimore Orioles": "#DF4601",
    "Boston Red Sox": "#BD3039",
    "New York Yankees": "#003087",
    "Tampa Bay Rays": "#092C5C",
    "Toronto Blue Jays": "#134A8E",

    # American League Central
    "Chicago White Sox": "#27251F",
    "Cleveland Guardians": "#0C2340",
    "Detroit Tigers": "#0C2340",
    "Kansas City Royals": "#004687",
    "Minnesota Twins": "#002B5C",

    # American League West
    "Houston Astros": "#002D62",
    "Los Angeles Angels": "#BA0021",
    "Oakland Athletics": "#003831",
    "Seattle Mariners": "#0C2C56",
    "Texas Rangers": "#003278",

    # National League East
    "Atlanta Braves": "#13274F",
    "Miami Marlins": "#00A3E0",
    "New York Mets": "#002D72",
    "Philadelphia Phillies": "#E81828",
    "Washington Nationals": "#AB0003",

    # National League Central
    "Chicago Cubs": "#0E3386",
    "Cincinnati Reds": "#C6011F",
    "Milwaukee Brewers": "#12284B",
    "Pittsburgh Pirates": "#FDB827",
    "St. Louis Cardinals": "#C41E3A",

    # National League West
    "Arizona Diamondbacks": "#A71930",
    "Colorado Rockies": "#33006F",
    "Los Angeles Dodgers": "#005A9C",
    "San Diego Padres": "#2F241D",
    "San Francisco Giants": "#FD5A1E",
}
DEFAULT_TEAM_COLOR = "#888888"


# --- Position code to full-name mapping (adjust to match your data) ---
POSITION_CODE_TO_FULL = {
    # Hitters
    "C": "Catcher",
    "1B": "First Base",
    "2B": "Second Base",
    "3B": "Third Base",
    "SS": "Shortstop",
    "LF": "Left Field",
    "CF": "Center Field",
    "RF": "Right Field",
    "DH": "Designated Hitter",
    "UT": "Utility",
    # Pitchers
    "P": "Pitcher",
    "SP": "Starting Pitcher",
    "RP": "Relief Pitcher",
    "CP": "Closer",
}


# --- Rate-stat qualifying thresholds ---
# Sorting/ranking by a rate stat with no minimum sample size lets a single
# at-bat (1.000 AVG) or a single scoreless inning (0.00 ERA) look like a
# leader. These mirror the same rule given to the SQL Chat LLM in
# schema_notes.md, applied here to the dashboard's own hardcoded queries.
RATE_STAT_COLUMNS = {
    "BattingAverage",
    "OnBasePercentage",
    "SluggingPercentage",
    "EarnedRunAverage",
    "FieldingIndependentPitching",
}
MIN_AT_BATS_FOR_RATE_STATS = 100
MIN_INNINGS_PITCHED_FOR_RATE_STATS = 20


def qualifying_where_clause(metric_columns, stats_alias, player_type):
    """Return an extra WHERE clause guarding against tiny-sample rate-stat
    outliers, if any of `metric_columns` is a rate stat -- else None."""
    if not any(col in RATE_STAT_COLUMNS for col in metric_columns):
        return None
    if player_type == "Hitter":
        return f"{stats_alias}.AtBats >= {MIN_AT_BATS_FOR_RATE_STATS}"
    return f"{stats_alias}.InningsPitched >= {MIN_INNINGS_PITCHED_FOR_RATE_STATS}"


# --- Page Configuration ---
st.set_page_config(
    page_title="MLB Scouting & Roster Assistant",
    page_icon="⚾",
    layout="wide"
)

# --- Load environment variables ---
load_dotenv()


def _get_openai_api_key() -> str | None:
    """Read the OpenAI key from Streamlit secrets first, then the environment.

    st.secrets is how the key is configured on Streamlit Community Cloud;
    os.getenv (via .env / load_dotenv above) is the local-dev fallback.
    st.secrets raises if no secrets.toml exists at all (as it won't for
    local runs), so that has to be caught rather than treated as "no key".
    """
    try:
        key = st.secrets.get("OPENAI_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY")


OPENAI_API_KEY = _get_openai_api_key()
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# --- Demo safety: cap paid LLM calls per browser session ---
MAX_LLM_CALLS_PER_SESSION = 8


def _llm_calls_remaining() -> int:
    return max(0, MAX_LLM_CALLS_PER_SESSION - st.session_state.get("llm_calls_used", 0))


def _record_llm_call():
    st.session_state["llm_calls_used"] = st.session_state.get("llm_calls_used", 0) + 1


class PlayerCRUD:
    """Handles all CRUD operations for the Player table."""

    def __init__(self, conn):
        """Initialize with a database connection."""
        self.conn = conn

    def create_player(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: str | None,
        position: str | None,
        height: int | None,
        weight: int | None,
        throws: str | None,
        bats: str | None,
        player_level: str | None,
    ) -> int:
        """Create a new player record and return its PlayerID."""
        try:
            cursor = self.conn.cursor()
            query = """
                INSERT INTO Player
                    (FirstName, LastName, DateOfBirth, Position, Height, Weight, Throws, Bats, PlayerLevel)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            values = (
                first_name,
                last_name,
                date_of_birth,
                position,
                height,
                weight,
                throws,
                bats,
                player_level,
            )
            cursor.execute(query, values)
            self.conn.commit()
            player_id = cursor.lastrowid
            cursor.close()
            return player_id
        except sqlite3.Error as e:
            st.error(f"Database error creating player: {e}")
            raise
        except Exception as e:
            st.error(f"Error creating player: {e}")
            raise

    def read_player(self, player_id: int):
        """Retrieve a single player by PlayerID, or None if not found."""
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory
            cursor.execute("SELECT * FROM Player WHERE PlayerID = ?", (player_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except sqlite3.Error as e:
            st.error(f"Database error reading player: {e}")
            return None
        except Exception as e:
            st.error(f"Error reading player: {e}")
            return None

    def read_all_players(self, limit: int = 100, offset: int = 0):
        """Retrieve all players with pagination."""
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory
            cursor.execute(
                "SELECT * FROM Player ORDER BY LastName, FirstName LIMIT ? OFFSET ?",
                (limit, offset),
            )
            results = cursor.fetchall()
            cursor.close()
            return results
        except sqlite3.Error as e:
            st.error(f"Database error reading players: {e}")
            return []
        except Exception as e:
            st.error(f"Error reading players: {e}")
            return []

    def search_players(self, search_term: str):
        """Search for players by name or PlayerID."""
        try:
            cursor = self.conn.cursor()
            cursor.row_factory = dict_row_factory

            # Try numeric PlayerID search first
            try:
                player_id = int(search_term)
                cursor.execute("SELECT * FROM Player WHERE PlayerID = ?", (player_id,))
                results = cursor.fetchall()
                if results:
                    cursor.close()
                    return results
            except (ValueError, TypeError):
                pass

            search_pattern = f"%{search_term}%"
            # Full name search
            cursor.execute(
                """
                SELECT * FROM Player
                WHERE (FirstName || ' ' || LastName) LIKE ?
                ORDER BY LastName, FirstName
                """,
                (search_pattern,),
            )
            results = cursor.fetchall()

            if not results:
                # Individual first/last name search
                cursor.execute(
                    """
                    SELECT * FROM Player
                    WHERE FirstName LIKE ? OR LastName LIKE ?
                    ORDER BY LastName, FirstName
                    """,
                    (search_pattern, search_pattern),
                )
                results = cursor.fetchall()

            cursor.close()
            return results
        except sqlite3.Error as e:
            st.error(f"Database error searching players: {e}")
            return []
        except Exception as e:
            st.error(f"Error searching players: {e}")
            return []

    def update_player(self, player_id: int, **kwargs) -> bool:
        """Update a player's information using keyword args."""
        field_mapping = {
            "first_name": "FirstName",
            "last_name": "LastName",
            "date_of_birth": "DateOfBirth",
            "position": "Position",
            "height": "Height",
            "weight": "Weight",
            "throws": "Throws",
            "bats": "Bats",
            "player_level": "PlayerLevel",
        }

        if not kwargs:
            st.warning("No fields to update")
            return False

        try:
            cursor = self.conn.cursor()
            set_clauses = []
            values = []

            for key, value in kwargs.items():
                if key in field_mapping:
                    set_clauses.append(f"{field_mapping[key]} = ?")
                    values.append(value)
                else:
                    st.warning(f"Unknown field: {key}")

            if not set_clauses:
                st.error("No valid fields to update")
                return False

            values.append(player_id)
            set_sql = ", ".join(set_clauses)
            query = f"UPDATE Player SET {set_sql} WHERE PlayerID = ?"
            cursor.execute(query, values)
            self.conn.commit()

            if cursor.rowcount > 0:
                return True
            else:
                st.warning(f"No player found with ID {player_id}")
                return False
        except sqlite3.Error as e:
            st.error(f"Database error updating player: {e}")
            return False
        except Exception as e:
            st.error(f"Error updating player: {e}")
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()

    def delete_player(self, player_id: int) -> bool:
        """Delete a player record by PlayerID."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT PlayerID FROM Player WHERE PlayerID = ?", (player_id,))
            if not cursor.fetchone():
                st.error(f"No player found with ID {player_id}")
                return False

            cursor.execute("DELETE FROM Player WHERE PlayerID = ?", (player_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            st.error(f"Database error deleting player: {e}")
            return False
        except Exception as e:
            st.error(f"Error deleting player: {e}")
            return False
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()

    def get_player_count(self) -> int:
        """Return total number of players in the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM Player")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            st.error(f"Error counting players: {e}")
            return 0

# --- Helper Functions ---
@st.cache_resource
def get_readonly_connection():
    """Cached, shared read-only connection for SQL Chat and the Analytics Dashboard.

    Shared across all sessions -- safe because it's read-only, so there's no
    write contention or risk of one visitor's session affecting another's.
    """
    return create_readonly_connection()


def get_crud_connection():
    """Per-session writable sandbox connection for Player Management (CRUD).

    Created once per browser session (cached on st.session_state) as a
    private copy of mlb_scouting.db, so CRUD writes never touch the
    committed database and each visitor's edits reset on refresh.
    """
    if "crud_conn" not in st.session_state:
        st.session_state["crud_conn"] = create_sandbox_connection()
    return st.session_state["crud_conn"]

def get_db_schema(conn):
    """
    Fetches the schema of the database to provide context to the LLM.
    Returns a human-readable list of tables and their columns.
    """
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    schema_lines = ["Database Schema (tables and columns):"]

    # For each table, get its columns
    for table_name in tables:
        cursor.execute(f'PRAGMA table_info("{table_name}");')
        columns = cursor.fetchall()
        schema_lines.append(f"Table `{table_name}`:")
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            schema_lines.append(f"  - {col_name} {col_type}")

    # Optionally include example rows for key lookup/enum tables so the model
    # sees real categorical values (e.g., LeagueLevel, Position, etc.).
    important_tables = ["League", "Team", "Player"]
    for table_name in important_tables:
        try:
            cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 10;')
            rows = cursor.fetchall()
            if rows:
                col_names = [desc[0] for desc in cursor.description]
                schema_lines.append(f"Example rows from `{table_name}`:")
                for row in rows:
                    row_repr = ", ".join(f"{col}={val}" for col, val in zip(col_names, row))
                    schema_lines.append(f"  - {row_repr}")
        except sqlite3.Error:
            # If the table doesn't exist or another error occurs, just skip it.
            continue

    return "\n".join(schema_lines)


def load_additional_schema_knowledge():
    """Load extra schema/domain notes from a markdown file if present.

    This lets you maintain hand-written guidance like valid categorical
    values (e.g., LeagueLevel = "Major League Baseball") in a separate
    `schema_notes.md` file that is appended to the LLM system prompt.
    """
    notes_path = os.path.join(os.path.dirname(__file__), "schema_notes.md")
    if os.path.exists(notes_path):
        try:
            with open(notes_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    return ""

def generate_sql_from_prompt(prompt, schema):
    """Uses an LLM to generate a SQL query from a natural language prompt."""

    # If no API key / client is configured, fall back to simple heuristics.
    if client is None:
        st.warning("OPENAI_API_KEY not set. Using placeholder SQL instead of LLM.")
        if "top 5 pitchers by era" in prompt.lower():
            return "SELECT (p.FirstName || ' ' || p.LastName) AS FullName, ps.Season, ps.EarnedRunAverage FROM PitcherStats ps JOIN Player p ON ps.PlayerID = p.PlayerID WHERE ps.InningsPitched >= 20 ORDER BY ps.EarnedRunAverage ASC LIMIT 5;"
        elif "highest batting average" in prompt.lower():
            return "SELECT (p.FirstName || ' ' || p.LastName) AS FullName, hs.Season, hs.BattingAverage FROM HitterStats hs JOIN Player p ON hs.PlayerID = p.PlayerID WHERE hs.AtBats >= 100 ORDER BY hs.BattingAverage DESC LIMIT 10;"
        else:
            return "SELECT PlayerID, FirstName, LastName, Position, PlayerLevel FROM Player LIMIT 10;"

    if _llm_calls_remaining() <= 0:
        st.warning(
            f"This demo caps LLM-generated queries at {MAX_LLM_CALLS_PER_SESSION} per "
            "session to keep hosting costs bounded. Showing an example query instead — "
            "refresh the page to reset your limit."
        )
        return "SELECT (p.FirstName || ' ' || p.LastName) AS FullName, ps.Season, ps.EarnedRunAverage FROM PitcherStats ps JOIN Player p ON ps.PlayerID = p.PlayerID WHERE ps.InningsPitched >= 20 ORDER BY ps.EarnedRunAverage ASC LIMIT 5;"

    try:
        # Load any hand-written domain notes (e.g., valid LeagueLevel values).
        extra_notes = load_additional_schema_knowledge()

        # Put schema and any extra notes into the system message so they are
        # pre-loaded context.
        system_content = (
            "You are a SQLite SQL assistant for an MLB scouting database. "
            "You are given the exact database schema and a natural language request.\n"
            "- Use ONLY tables and columns that appear in the schema below.\n"
            "- Use the column and table names exactly as written in the schema "
            "(for example, use PlayerID and FirstName, NOT player_id or first_name).\n"
            "- Do not invent new columns or rename them.\n"
            "- Prefer using backticks around identifiers (e.g., `Player`, `PlayerID`).\n"
            "- When filtering on categorical columns (like LeagueLevel or Position), "
            "prefer the example values shown in the schema or notes below; do not "
            "invent abbreviations like 'MLB' if the examples show 'Major League Baseball'.\n"
            "- Return a single valid SQL SELECT query only, with no explanation.\n\n"
            f"Schema:\n{schema}\n\n"
            f"Additional domain notes (if any):\n{extra_notes}"
        )

        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_content},
                {
                    "role": "user",
                    "content": (
                        "Remember: use column names exactly as in the schema; "
                        "do not convert them to snake_case or invent new ones.\n\n"
                        f"Request: {prompt}"
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.1,
        )
        _record_llm_call()
        sql_query = response.choices[0].message.content.strip()
        return sql_query
    except Exception as e:
        st.error(f"Error calling SQL LLM: {e}")
        # Fallback if the API call fails
        return "SELECT PlayerID, FirstName, LastName, Position, PlayerLevel FROM Player LIMIT 10;"


_FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"(?is)\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|"
    r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b"
)


def is_safe_select_query(sql: str) -> bool:
    """True if `sql` is a single, read-only SELECT statement.

    This app runs LLM-generated SQL directly, so on a public demo a
    non-SELECT statement is a DROP TABLE waiting to happen. The read-only
    connection (see db.create_readonly_connection) is the real backstop,
    but rejecting anything that isn't a plain SELECT here means a bad query
    never even reaches the database.
    """
    if not sql:
        return False
    stripped = sql.strip().rstrip(";").strip()
    if not stripped or ";" in stripped:
        return False  # empty, or multiple stacked statements
    if not re.match(r"(?is)^SELECT\b", stripped):
        return False
    if _FORBIDDEN_SQL_KEYWORDS.search(stripped):
        return False
    return True


def run_sql_query(conn, sql_query):
    """Executes a SQL query and returns the result as a DataFrame."""
    if not conn or not sql_query:
        return pd.DataFrame()
    if not is_safe_select_query(sql_query):
        st.error("Query rejected: only a single SELECT statement is allowed on this demo.")
        return pd.DataFrame()
    try:
        df = pd.read_sql(sql_query, conn)
        return df
    except Exception as e:
        st.error(f"Error executing query: {e}")
        return pd.DataFrame()


# --- Chroma / RAG Setup ---

@st.cache_resource
def get_chroma_client_and_collections():
    client_chroma = chromadb.PersistentClient(path=".chromadb")
    # Local ONNX embedder (chromadb's bundled all-MiniLM-L6-v2) -- retrieval is
    # free and offline, leaving exactly one paid OpenAI call per question (the
    # scouting LLM generation itself, not embedding).
    ef = embedding_functions.DefaultEmbeddingFunction()
    player_col = client_chroma.get_collection(
        name="player_season_profiles",
        embedding_function=ef,
    )
    team_col = client_chroma.get_collection(
        name="team_season_profiles",
        embedding_function=ef,
    )
    return client_chroma, player_col, team_col


def load_guideline_markdown():
    """Load behavior / domain guideline markdown files into one string."""
    base_dir = os.path.dirname(__file__)
    md_files = [
        "01_roster_evaluation.md",
        "02_calling_up_minor_leaguers.md",
        "03_trades_guidelines.md",
        "04_hitter_scouting_and_roles.md",
        "05_pitcher_scouting_and_roles.md",
        "07_competitive_window_and_strategy.md",
        "08_player_development_philosophy.md",
        "10_salary_and_budget_considerations.md",
        "11_answer_style_and_explanation_guidelines.md",
        "12_example_scouting_reports_and_recommendations.md",
    ]
    parts = []
    for name in md_files:
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    parts.append(f"\n\n# {name}\n\n" + f.read())
            except OSError:
                continue
    return "\n".join(parts)


def load_query_enricher_markdown():
    """Load the RAG query enricher instructions (for documentation/maintenance)."""
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "rag_query_enricher.md")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""
    return ""


def enrich_rag_query(user_query: str) -> str:
    """Heuristically enrich the user's query with structured hints for retrieval.

    The logic here is guided by rag_query_enricher.md but runs locally without
    calling any LLM. It returns a hint string like:

        "[HINTS] team=Baltimore Orioles; positions=CF,OF; levels=AAA,AA; intent=CALL_UP_DECISION; ..."

    which is appended to the query text used for Chroma retrieval.
    """
    text = user_query.lower()

    # --- Team / organization hints (small alias mapping) ---
    team_aliases = {
        "orioles": "Baltimore Orioles",
        "o's": "Baltimore Orioles",
        "yankees": "New York Yankees",
        "red sox": "Boston Red Sox",
        "dodgers": "Los Angeles Dodgers",
        "cubs": "Chicago Cubs",
        "giants": "San Francisco Giants",
        "astros": "Houston Astros",
        "braves": "Atlanta Braves",
        "mets": "New York Mets",
        "phillies": "Philadelphia Phillies",
        "cardinals": "St. Louis Cardinals",
    }
    team_hint = None
    for alias, full_name in team_aliases.items():
        if alias in text:
            team_hint = full_name
            break

    # --- Position / role hints ---
    positions = set()
    roles = set()

    if "catcher" in text:
        positions.add("C")
    if "first base" in text or " 1b" in text:
        positions.add("1B")
    if "second base" in text or " 2b" in text:
        positions.add("2B")
    if "third base" in text or " 3b" in text:
        positions.add("3B")
    if "shortstop" in text or "short stop" in text or " ss" in text:
        positions.add("SS")
    if "left field" in text or "left fielder" in text or " lf" in text:
        positions.add("LF")
    if "center field" in text or "center fielder" in text or " cf" in text:
        positions.add("CF")
    if "right field" in text or "right fielder" in text or " rf" in text:
        positions.add("RF")
    if "outfield" in text or "outfielder" in text:
        positions.update(["LF", "CF", "RF"])
    if "utility" in text or "super-utility" in text:
        positions.add("UT")
    if "designated hitter" in text or " dh" in text:
        positions.add("DH")

    if "starting pitcher" in text or "starter" in text or "in the rotation" in text:
        roles.add("SP")
    if "reliever" in text or "relief pitcher" in text:
        roles.add("RP")
    if "closer" in text or "ninth-inning" in text:
        roles.add("CP")
    if "high-leverage" in text or "setup man" in text:
        roles.add("RP_high_leverage")

    # --- Level / development hints ---
    levels = set()
    if "mlb" in text or "big leagues" in text or "majors" in text:
        levels.add("MLB")
    if "triple-a" in text or "triple a" in text or " aaa" in text:
        levels.add("AAA")
    if "double-a" in text or "double a" in text or " aa" in text:
        levels.add("AA")
    if "high-a" in text:
        levels.add("High-A")
    if "low-a" in text or "a-ball" in text or "a ball" in text:
        levels.add("A")
    if "rookie ball" in text or "complex league" in text:
        levels.add("Rookie")
    if "college" in text:
        levels.add("College")

    # Call-up questions: bias to AAA/AA if not already present
    is_callup = any(
        kw in text
        for kw in [
            "call up",
            "call-up",
            "promote",
            "promotion",
            "bring him up",
            "bring her up",
            "ready for the majors",
        ]
    )
    if is_callup and not levels:
        levels.update(["AAA", "AA"])

    # --- Timeframe / seasons ---
    years = set()
    for yr in ["2021", "2022", "2023", "2024"]:
        if yr in text:
            years.add(yr)

    if "this year" in text or "this season" in text or "current season" in text:
        years.add("2024")
    if "last year" in text or "last season" in text:
        years.add("2023")
    if "over the last three years" in text or "last three seasons" in text:
        years.update(["2022", "2023", "2024"])

    # --- Decision type / intent ---
    intent = []
    if is_callup:
        intent.append("CALL_UP_DECISION")
    if any(kw in text for kw in ["trade", "swap", "deal", "package", "deadline move", "sell high", "buy low"]):
        intent.append("TRADE_EVALUATION")
    if any(kw in text for kw in ["roster construction", "depth chart", "platoon", "bench role", "starting job", "move him to", "move her to"]):
        intent.append("ROSTER_CONSTRUCTION")
    if any(kw in text for kw in ["extension", "contract", "arbitration", "arb", "club control", "team control", "free agency", "free agent", "non-tender", "option year"]):
        intent.append("CONTRACT_DECISION")

    # --- Constraints / preferences ---
    competitive_window = None
    if "rebuilding" in text or "rebuild" in text:
        competitive_window = "REBUILD"
    elif "contending" in text or "title window" in text or "world series or bust" in text:
        competitive_window = "CONTEND"
    elif any(kw in text for kw in ["fringe playoff", "wild card race", "wildcard race", "on the bubble"]):
        competitive_window = "FRINGE_CONTENDER"

    risk_tolerance = None
    if "conservative" in text or "minimize risk" in text:
        risk_tolerance = "LOW"
    elif any(kw in text for kw in ["willing to gamble", "high-upside", "aggressive"]):
        risk_tolerance = "HIGH"

    time_horizon = None
    if any(kw in text for kw in ["this year only", "rest of this season", "short term"]):
        time_horizon = "SHORT_TERM"
    elif any(kw in text for kw in ["next 3-5 years", "next three to five years", "long-term core", "multi-year window"]):
        time_horizon = "LONG_TERM"

    # --- Build hint string ---
    parts = []

    if team_hint:
        parts.append(f"team={team_hint}")
    if positions:
        parts.append("positions=" + ",".join(sorted(positions)))
    if roles:
        parts.append("roles=" + ",".join(sorted(roles)))
    if levels:
        parts.append("levels=" + ",".join(sorted(levels)))
    if years:
        parts.append("years=" + ",".join(sorted(years)))
    if intent:
        parts.append("intent=" + ",".join(intent))
    if competitive_window:
        parts.append(f"competitive_window={competitive_window}")
    if risk_tolerance:
        parts.append(f"risk_tolerance={risk_tolerance}")
    if time_horizon:
        parts.append(f"time_horizon={time_horizon}")

    if not parts:
        return ""  # no enrichment; just use the original query

    return "[HINTS] " + "; ".join(parts)


def _parse_team_and_intent_from_hints(hint_str: str):
    """Return (team_name, intents) parsed from the enricher hint string.

    - team_name: canonical team name from a `team=` segment, or None
    - intents: list of raw intent tags from an `intent=` segment
    """
    if not hint_str:
        return None, []

    team_name = None
    intents = []

    raw = hint_str.replace("[HINTS]", "").strip()
    for segment in raw.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        lower = segment.lower()
        if lower.startswith("team="):
            team_name = segment.split("=", 1)[1].strip()
        elif lower.startswith("intent="):
            intent_vals = segment.split("=", 1)[1].strip()
            for v in intent_vals.split(","):
                v = v.strip()
                if v:
                    intents.append(v)

    return team_name, intents


def _parse_positions_from_hints(hint_str: str):
    """Extract position codes from a `positions=` segment in the hints string."""
    if not hint_str:
        return []
    positions = []
    raw = hint_str.replace("[HINTS]", "").strip()
    for segment in raw.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        lower = segment.lower()
        if lower.startswith("positions="):
            vals = segment.split("=", 1)[1].strip()
            for v in vals.split(","):
                v = v.strip()
                if v:
                    positions.append(v)
    return positions


def _parse_levels_from_hints(hint_str: str):
    """Extract level codes (MLB, AAA, AA, ...) from a `levels=` segment in the hints string."""
    if not hint_str:
        return []
    levels = []
    raw = hint_str.replace("[HINTS]", "").strip()
    for segment in raw.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        lower = segment.lower()
        if lower.startswith("levels="):
            vals = segment.split("=", 1)[1].strip()
            for v in vals.split(","):
                v = v.strip()
                if v:
                    levels.append(v)
    return levels


def _chroma_where(conditions: list[dict | None]) -> dict | None:
    """Combine field conditions into a single Chroma `where` filter, or None."""
    conditions = [c for c in conditions if c]
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _query_players_with_fallback(player_col, query_text, n_players, org_team_name, level_codes, position_full_names):
    """Query player docs, progressively relaxing metadata filters until something matches.

    A fully-specified filter (org + level + position) can easily match zero
    documents for a narrow roster slice -- e.g. "Yankees AAA catchers" may be
    0-2 real players in a single-season store. Rather than silently
    returning nothing, relax the least important constraint first
    (position, then level) and hold onto the org filter the longest, since
    "which organization" is usually the most important thing to get right
    for grounding a call-up/trade answer.
    """
    org_cond = {"org_team_name": {"$eq": org_team_name}} if org_team_name else None
    level_cond = {"league_level_short": {"$in": level_codes}} if level_codes else None
    position_cond = {"position": {"$in": position_full_names}} if position_full_names else None

    attempts = [
        _chroma_where([org_cond, level_cond, position_cond]),
        _chroma_where([org_cond, level_cond]),
        _chroma_where([org_cond]),
        None,
    ]
    tried = set()
    for where in attempts:
        key = str(where)
        if key in tried:
            continue
        tried.add(key)
        try:
            res = (
                player_col.query(query_texts=[query_text], n_results=n_players, where=where)
                if where
                else player_col.query(query_texts=[query_text], n_results=n_players)
            )
        except Exception as e:
            st.warning(f"Player RAG retrieval error: {e}")
            continue
        if res.get("ids", [[]])[0]:
            return res
    return {"ids": [[]], "documents": [[]], "metadatas": [[]]}


def retrieve_rag_context(
    player_col,
    team_col,
    user_query,
    n_players=8,
    n_teams=5,
    org_team_name_override: str | None = None,
):
    """Retrieve top player and team docs from Chroma for a given query.

    Uses the enricher hints both for text steering and for metadata filters
    (limiting to a single MLB organization, level, and/or position when the
    query or the org dropdown implies one) via
    ``_query_players_with_fallback``, which relaxes those filters rather
    than returning nothing when a narrow combination has no matches.

    If ``org_team_name_override`` is provided (from the dropdown), it takes
    precedence over any team parsed from the hints.
    """
    player_docs = []
    team_docs = []

    # Enrich the query with structured hints
    hint_str = enrich_rag_query(user_query)
    if hint_str:
        query_text = f"{user_query}\n\n{hint_str}"
    else:
        query_text = user_query

    # Parse org + positions + levels from hints (org can be overridden)
    org_team_name_hints, _intents = _parse_team_and_intent_from_hints(hint_str) if hint_str else (None, [])
    org_team_name = org_team_name_override or org_team_name_hints
    position_codes = _parse_positions_from_hints(hint_str)
    level_codes = _parse_levels_from_hints(hint_str)
    position_full_names = [POSITION_CODE_TO_FULL.get(code, code) for code in position_codes]

    res = _query_players_with_fallback(
        player_col, query_text, n_players, org_team_name, level_codes, position_full_names
    )
    for i in range(len(res.get("ids", [[]])[0])):
        player_docs.append({
            "id": res["ids"][0][i],
            "doc": res["documents"][0][i],
            "meta": res["metadatas"][0][i],
        })

    # Team docs: still a single pass, unfiltered
    try:
        team_res = team_col.query(
            query_texts=[query_text],
            n_results=n_teams,
        )
        for i in range(len(team_res.get("ids", [[]])[0])):
            team_docs.append({
                "id": team_res["ids"][0][i],
                "doc": team_res["documents"][0][i],
                "meta": team_res["metadatas"][0][i],
            })
    except Exception as e:
        st.warning(f"Team RAG retrieval error: {e}")

    return player_docs, team_docs


def format_rag_context_for_llm(player_docs, team_docs):
    """Turn retrieved docs into a compact context string for the LLM."""
    lines = []

    if team_docs:
        lines.append("## Retrieved Team Context")
        for t in team_docs:
            m = t["meta"] or {}
            team_name = m.get("TeamName") or m.get("team_name") or m.get("team") or ""
            year = m.get("Year") or m.get("season") or ""
            lines.append(f"- [TEAM] {team_name} ({year}) | id={t['id']}")
            lines.append(textwrap.shorten(t["doc"], width=600, placeholder=" ..."))
            lines.append("")

    if player_docs:
        lines.append("## Retrieved Player Context")
        for p in player_docs:
            m = p["meta"] or {}
            role = m.get("role", "")
            pid = m.get("PlayerID") or m.get("player_id") or ""
            season = m.get("Season") or m.get("season") or ""
            lines.append(f"- [PLAYER] role={role}, player_id={pid}, season={season} | id={p['id']}")
            lines.append(textwrap.shorten(p["doc"], width=600, placeholder=" ..."))
            lines.append("")

    return "\n".join(lines)


EXAMPLE_SCOUTING_ANSWER = """\
*(Example answer — not generated from your question)*

I like the idea of leaning on our AAA depth here. Our incumbent MLB shortstop \
is a league-average bat on an expiring deal, and the AAA option we're looking at \
just posted a 140 wRC+ over a full season with strong contact rates — that's a \
real everyday-caliber season, not a small-sample spike.

**Option A – Call him up now.** Benefits: locks in his service-time clock while \
he's producing, gives our lineup an upgrade immediately. Risks: a jump straight \
from AAA can come with an adjustment period, and it burns a minor-league option year.

**Option B – One more month of seasoning.** Benefits: lets us evaluate his final \
stretch against tougher AAA pitching before committing a roster spot. Risks: we \
delay the upgrade and the incumbent keeps starting.

My honest read: I'd call him up. The offensive profile is strong enough that the \
adjustment risk is worth it, and our incumbent isn't blocking a long-term piece — \
this is a low-risk, high-upside move for us.
"""


def call_scouting_llm(user_query, rag_context, guidelines_text):
    """Call OpenAI for the scouting assistant, using RAG + guidelines."""
    if client is None:
        return "OPENAI_API_KEY is not configured. Unable to call the scouting assistant."

    if _llm_calls_remaining() <= 0:
        return (
            f"**Demo limit reached.** This demo caps scouting analyses at "
            f"{MAX_LLM_CALLS_PER_SESSION} per session to keep hosting costs bounded. "
            "Refresh the page to reset your limit. In the meantime, here's an example "
            "of the kind of answer this assistant gives:\n\n"
            f"{EXAMPLE_SCOUTING_ANSWER}"
        )

    system_prompt = (
        "You are an MLB scouting and roster strategy assistant embedded inside the user's front office.\n"
        "You speak in the first person as if you are a trusted advisor on their staff, "
        "using a conversational, collaborative tone (for example: 'I think', 'I would recommend', 'I see this as').\n"
        "Do NOT write in the third person (avoid phrases like 'the front office should', 'the team might').\n"
        "Always frame your reasoning and recommendations as what *you* would do.\n\n"
        "You must use the provided guidelines and examples as strict instructions for style, structure, and decision-making.\n"
        "You must follow the answer templates described in the guidelines, including:\n"
        "- For decisions (call-ups, trades, roster/contract moves): summary → context → analysis → "
        "bulleted options with Benefits/Risks → final honest recommendation.\n"
        "- For single-player evaluations: summary → context → analysis → positives/negatives bullets "
        "→ final consensus evaluation.\n\n"
        "CRITICAL GROUNDING RULES:\n"
        "- Treat the retrieved player and team context as your scouting database.\n"
        "- When you propose concrete options (Option A/B/C, trade ideas, call-ups, role changes, etc.), "
        "you must base them on specific players and teams that appear in the retrieved context.\n"
        "- Explicitly name the relevant players (for example: 'Option A – call up John Smith from AAA...').\n"
        "- Do NOT invent new player names, teams, or stats that are not present in the retrieved context.\n"
        "- If the context does not provide enough detail to make a specific player-based recommendation, "
        "say so plainly and either request more info or give a more general guideline, but do not fabricate details.\n\n"
        "Tone and honesty:\n"
        "- Be conservative and honest; if the best move is to keep the current situation, say so clearly.\n"
        "- Consider long-term consequences of trades and promotions.\n\n"
        "Below are your internal guidelines (do NOT repeat them verbatim to the user):\n\n"
        f"{guidelines_text}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "You are advising my front office on this question:\n"
                f"{user_query}\n\n"
                "Here is the retrieved context from our internal scouting database (players and teams):\n"
                f"{rag_context}\n\n"
                "Instructions for this answer:\n"
                "- Use ONLY players and teams that appear in the retrieved context when you name concrete options.\n"
                "- When you present options (Option A/B/C, or similar), each option should reference at least one specific player by name "
                "and describe a concrete action (for example, 'Option A – bring up X from AAA as the everyday CF').\n"
                "- Do NOT invent any new player names, team names, or specific stats that are not visible in the context.\n"
                "- Speak in the first person as a trusted advisor ('I think', 'I would').\n"
                "- If the context is thin or missing for some players/teams, say so briefly and reason with what you have, "
                "rather than fabricating details.\n"
            ),
        },
    ]

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            max_tokens=900,
            temperature=0.2,
        )
        _record_llm_call()
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error calling scouting LLM: {e}"

# --- Main Application ---
st.title("⚾ MLB Scouting & Roster Assistant")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
app_section = st.sidebar.radio(
    "Go to",
    ("SQL Chat", "Analytics Dashboard", "Player Management (CRUD)", "Scouting Assistant (LLM)")
)

# --- Database Connection ---
conn = get_readonly_connection()

# ==============================================================================
# --- Section 1: SQL Chat ---
# ==============================================================================
if app_section == "SQL Chat":
    st.header("Natural Language to SQL Query")
    st.markdown("""
    Ask a question about the MLB data in plain English. The assistant will translate your question into a SQL query, execute it, and display the results.
    **Examples:** 
    - "Show me the top 5 pitchers by ERA"
    - "Which players had the highest batting average in 2023?"
    """)

    if conn:
        col1, col2 = st.columns([2, 3])

        with col1:
            # User input
            user_prompt = st.text_area("Enter your question here:", height=150)
            
            if st.button("Generate and Run Query"):
                if user_prompt:
                    with st.spinner("Generating SQL..."):
                        # In a real app, you'd get the schema to help the LLM
                        # schema = get_db_schema(conn) 
                        schema = get_db_schema(conn) # Using a placeholder for now
                        
                        generated_sql = generate_sql_from_prompt(user_prompt, schema)
                        st.session_state['generated_sql'] = generated_sql
                        
                        # Run the query
                        query_results = run_sql_query(conn, generated_sql)
                        st.session_state['query_results'] = query_results
                else:
                    st.warning("Please enter a question.")

            # Display generated SQL
            st.markdown("---")
            st.subheader("Generated SQL")
            if 'generated_sql' in st.session_state:
                st.code(st.session_state['generated_sql'], language="sql")
            else:
                st.info("SQL will appear here after you run a query.")

        with col2:
            # Display query results
            st.subheader("Query Results")
            if 'query_results' in st.session_state:
                st.dataframe(st.session_state['query_results'])
            else:
                st.info("Results from the database will appear here.")
    else:
        st.error("Database connection failed. Please check the configuration.")


# ==============================================================================
# --- Section 2: Analytics Dashboard ---
# ==============================================================================
elif app_section == "Analytics Dashboard":
    st.header("Analytics Dashboard – Player Comparison")

    if not conn:
        st.error("Database connection failed. Please check the configuration.")
    else:
        # --- High-level controls ---
        st.subheader("Filters")

        col_filters_1, col_filters_2 = st.columns(2)

        with col_filters_1:
            player_type = st.radio(
                "Player type",
                options=["Hitter", "Pitcher"],
                horizontal=True,
            )
            season = st.number_input(
                "Season (Year)",
                min_value=2000,
                max_value=2100,
                value=2024,
                step=1,
            )

        # Base cursor
        cursor = conn.cursor()

        # Fetch all levels first
        cursor.execute("SELECT DISTINCT LeagueLevel FROM League ORDER BY LeagueLevel;")
        all_levels = [row[0] for row in cursor.fetchall()]

        with col_filters_2:
            # Multi-select levels
            selected_levels = st.multiselect(
                "Level (LeagueLevel)",
                options=all_levels,
                default=all_levels,
            )

        # Dynamically fetch teams filtered by selected levels (if any)
        if selected_levels:
            placeholders = ",".join(["?"] * len(selected_levels))
            cursor.execute(
                f"""
                SELECT t.TeamID, t.TeamName, l.LeagueLevel
                FROM Team t
                JOIN League l ON t.LeagueID = l.LeagueID
                WHERE l.LeagueLevel IN ({placeholders})
                ORDER BY t.TeamName;
                """,
                selected_levels,
            )
        else:
            # No level selected -> show all teams
            cursor.execute(
                """
                SELECT t.TeamID, t.TeamName, l.LeagueLevel
                FROM Team t
                JOIN League l ON t.LeagueID = l.LeagueID
                ORDER BY t.TeamName;
                """
            )

        teams = cursor.fetchall()
        team_display = [f"{tname} - {lvl}" for (tid, tname, lvl) in teams]

        with col_filters_2:
            selected_team_labels = st.multiselect(
                "Teams",
                options=team_display,
            )

        # Map selected team labels back to IDs
        selected_team_ids = []
        if selected_team_labels:
            label_to_id = {f"{tname} - {lvl}": tid for (tid, tname, lvl) in teams}
            selected_team_ids = [label_to_id[label] for label in selected_team_labels]

        # Position filter: multi-select, options differ for hitters vs pitchers
        if player_type == "Hitter":
            position_options = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "UT"]
        else:
            # All pitchers are stored as generic "Pitcher" in Player.Position
            position_options = ["P"]

        selected_position_codes = st.multiselect(
            "Position filter (optional)",
            options=position_options,
        )

        # Specific players filter: multi-select of player names, dynamically
        # filtered by selected levels and teams.
        player_where = []
        player_params = []

        if selected_levels:
            placeholders = ",".join(["?"] * len(selected_levels))
            player_where.append(f"l.LeagueLevel IN ({placeholders})")
            player_params.extend(selected_levels)

        if selected_team_ids:
            placeholders = ",".join(["?"] * len(selected_team_ids))
            player_where.append(f"t.TeamID IN ({placeholders})")
            player_params.extend(selected_team_ids)

        player_where_sql = " AND ".join(player_where)
        if player_where_sql:
            player_where_sql = "WHERE " + player_where_sql

        cursor.execute(
            f"""
            SELECT DISTINCT p.PlayerID, p.FirstName, p.LastName, t.TeamName, p.Position
            FROM Player p
            LEFT JOIN HitterStats hs ON hs.PlayerID = p.PlayerID
            LEFT JOIN PitcherStats ps ON ps.PlayerID = p.PlayerID
            LEFT JOIN Team t ON COALESCE(hs.TeamID, ps.TeamID) = t.TeamID
            LEFT JOIN League l ON t.LeagueID = l.LeagueID
            {player_where_sql}
            ORDER BY p.LastName, p.FirstName;
            """,
            tuple(player_params),
        )
        player_rows = cursor.fetchall()
        player_display = [
            f"{fn} {ln} - {tname if tname else 'Unknown Team'} - {pos if pos else 'N/A'}"
            for (pid, fn, ln, tname, pos) in player_rows
        ]
        selected_players = st.multiselect(
            "Specific players (optional)",
            options=player_display,
        )

        # --- Metric selection for bar chart ---
        st.markdown("---")
        st.subheader("Bar Chart – Top Players by Metric")

        if player_type == "Hitter":
            metric_options = {
                "HomeRuns": "HomeRuns",
                "RBI": "RBI",
                "Hits": "Hits",
                "BattingAverage": "BattingAverage",
                "OnBasePercentage": "OnBasePercentage",
                "SluggingPercentage": "SluggingPercentage",
                "WinsAboveReplacement": "WinsAboveReplacement",
            }
            stats_table = "HitterStats"
            stats_alias = "hs"
        else:
            metric_options = {
                "Strikeouts": "Strikeouts",
                "EarnedRunAverage (lower is better)": "EarnedRunAverage",
                "Wins": "Wins",
                "Saves": "Saves",
                "InningsPitched": "InningsPitched",
                "FieldingIndependentPitching (lower is better)": "FieldingIndependentPitching",
            }
            stats_table = "PitcherStats"
            stats_alias = "ps"

        metric_label = st.selectbox("Metric", options=list(metric_options.keys()))
        metric_column = metric_options[metric_label]

        top_n = st.slider("Number of players to show", min_value=5, max_value=50, value=15, step=5)

        # Metric options for scatter plot
        if player_type == "Hitter":
            scatter_metric_options = {
                "BattingAverage": "BattingAverage",
                "OnBasePercentage": "OnBasePercentage",
                "SluggingPercentage": "SluggingPercentage",
                "HomeRuns": "HomeRuns",
                "RBI": "RBI",
                "Hits": "Hits",
                "WinsAboveReplacement": "WinsAboveReplacement",
            }
        else:
            scatter_metric_options = {
                "Strikeouts": "Strikeouts",
                "EarnedRunAverage": "EarnedRunAverage",
                "Wins": "Wins",
                "Saves": "Saves",
                "InningsPitched": "InningsPitched",
                "FieldingIndependentPitching": "FieldingIndependentPitching",
            }

        # --- Build SQL query based on filters ---
        where_clauses = [f"{stats_alias}.Season = ?"]
        params = [season]

        qualifier = qualifying_where_clause([metric_column], stats_alias, player_type)
        if qualifier:
            where_clauses.append(qualifier)

        # Level filter (via League.LeagueLevel) - allow multiple
        if selected_levels:
            placeholders = ",".join(["?"] * len(selected_levels))
            where_clauses.append(f"l.LeagueLevel IN ({placeholders})")
            params.extend(selected_levels)

        # Team filter - allow multiple
        if selected_team_ids:
            placeholders = ",".join(["?"] * len(selected_team_ids))
            where_clauses.append(f"{stats_alias}.TeamID IN ({placeholders})")
            params.extend(selected_team_ids)

        # Position filter (applies via Player.Position) - multi-select
        if selected_position_codes:
            # Map short codes (e.g., 'SS') to full names stored in Player.Position
            selected_positions_full = [
                POSITION_CODE_TO_FULL.get(code, code) for code in selected_position_codes
            ]
            placeholders = ",".join(["?"] * len(selected_positions_full))
            where_clauses.append(f"p.Position IN ({placeholders})")
            params.extend(selected_positions_full)

        # Specific players filter
        if selected_players:
            label_to_pid = {}
            for (pid, fn, ln, tname, pos) in player_rows:
                label = f"{fn} {ln} - {tname if tname else 'Unknown Team'} - {pos if pos else 'N/A'}"
                label_to_pid[label] = pid

            selected_player_ids = [label_to_pid[label] for label in selected_players]
            placeholders = ",".join(["?"] * len(selected_player_ids))
            where_clauses.append(f"{stats_alias}.PlayerID IN ({placeholders})")
            params.extend(selected_player_ids)

        where_sql = " AND ".join(where_clauses)

        # Order direction – most metrics descending, a couple ascending
        if metric_column in ["EarnedRunAverage", "FieldingIndependentPitching"]:
            order_dir = "ASC"
        else:
            order_dir = "DESC"

        sql = f"""
            SELECT 
                p.PlayerID,
                (p.FirstName || ' ' || p.LastName) AS PlayerName,
                t.TeamName,
                {stats_alias}.{metric_column} AS MetricValue
            FROM `{stats_table}` {stats_alias}
            JOIN `Player` p ON {stats_alias}.PlayerID = p.PlayerID
            JOIN `Team` t ON {stats_alias}.TeamID = t.TeamID
            JOIN `League` l ON t.LeagueID = l.LeagueID
            WHERE {where_sql}
            ORDER BY MetricValue {order_dir}
            LIMIT ?;
        """
        params.append(top_n)

        # --- Run query and render bar chart ---
        try:
            df = pd.read_sql(sql, conn, params=params)
            if df.empty:
                st.info("No data found for the selected filters.")
            else:
                # Sort explicitly according to metric
                df_sorted = df.sort_values("MetricValue", ascending=(order_dir == "ASC"))

                # Map team names to colors, fallback to default
                df_sorted["TeamColor"] = df_sorted["TeamName"].map(TEAM_COLORS).fillna(DEFAULT_TEAM_COLOR)

                # Build Altair chart with labels and team colors
                base = alt.Chart(df_sorted).encode(
                    x=alt.X("PlayerName:N", sort=list(df_sorted["PlayerName"]), title="Player"),
                    y=alt.Y("MetricValue:Q", title=metric_label),
                    color=alt.Color(
                        "TeamName:N",
                        legend=alt.Legend(title="Team"),
                    ),
                    tooltip=["PlayerName", "TeamName", "MetricValue"],
                )

                bars = base.mark_bar()

                labels = base.mark_text(
                    align="center",
                    baseline="bottom",
                    dy=-4,
                ).encode(
                    text=alt.Text("MetricValue:Q", format=".2f"),
                )

                chart = (bars + labels).properties(
                    width="container",
                    height=400,
                )

                st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading data for bar chart: {e}")

        # --- Scatter Plot – Compare Two Metrics ---
        st.markdown("---")
        st.subheader("Scatter Plot – Metric vs Metric")

        col_scatter_x, col_scatter_y = st.columns(2)
        with col_scatter_x:
            scatter_x_label = st.selectbox(
                "X-axis metric",
                options=list(scatter_metric_options.keys()),
                key="scatter_x_metric",
            )
        with col_scatter_y:
            scatter_y_label = st.selectbox(
                "Y-axis metric",
                options=list(scatter_metric_options.keys()),
                index=1 if len(scatter_metric_options) > 1 else 0,
                key="scatter_y_metric",
            )

        scatter_x_col = scatter_metric_options[scatter_x_label]
        scatter_y_col = scatter_metric_options[scatter_y_label]

        scatter_top_n = st.slider(
            "Number of players to show (scatter)",
            min_value=5,
            max_value=200,
            value=75,
            step=5,
        )

        # Build WHERE clauses again (top filters apply here too) for season
        scatter_where_clauses = [f"{stats_alias}.Season = ?"]
        scatter_params = [season]

        scatter_qualifier = qualifying_where_clause([scatter_x_col, scatter_y_col], stats_alias, player_type)
        if scatter_qualifier:
            scatter_where_clauses.append(scatter_qualifier)

        if selected_levels:
            placeholders = ",".join(["?"] * len(selected_levels))
            scatter_where_clauses.append(f"l.LeagueLevel IN ({placeholders})")
            scatter_params.extend(selected_levels)

        if selected_team_ids:
            placeholders = ",".join(["?"] * len(selected_team_ids))
            scatter_where_clauses.append(f"{stats_alias}.TeamID IN ({placeholders})")
            scatter_params.extend(selected_team_ids)

        if selected_position_codes:
            selected_positions_full = [
                POSITION_CODE_TO_FULL.get(code, code) for code in selected_position_codes
            ]
            placeholders = ",".join(["?"] * len(selected_positions_full))
            scatter_where_clauses.append(f"p.Position IN ({placeholders})")
            scatter_params.extend(selected_positions_full)

        if selected_players:
            label_to_pid = {}
            for (pid, fn, ln, tname, pos) in player_rows:
                label = f"{fn} {ln} - {tname if tname else 'Unknown Team'} - {pos if pos else 'N/A'}"
                label_to_pid[label] = pid

            selected_player_ids = [label_to_pid[label] for label in selected_players]
            placeholders = ",".join(["?"] * len(selected_player_ids))
            scatter_where_clauses.append(f"{stats_alias}.PlayerID IN ({placeholders})")
            scatter_params.extend(selected_player_ids)

        scatter_where_sql = " AND ".join(scatter_where_clauses)

        # Determine order direction for choosing "top" players by X metric
        if scatter_x_col in ["EarnedRunAverage", "FieldingIndependentPitching"]:
            scatter_order_dir = "ASC"  # lower is better
        else:
            scatter_order_dir = "DESC"  # higher is better

        # First, select top-N players by X-axis metric under current filters
        top_scatter_sql = f"""
            SELECT
                {stats_alias}.PlayerID,
                {stats_alias}.{scatter_x_col} AS XValue
            FROM `{stats_table}` {stats_alias}
            JOIN `Player` p ON {stats_alias}.PlayerID = p.PlayerID
            JOIN `Team` t ON {stats_alias}.TeamID = t.TeamID
            JOIN `League` l ON t.LeagueID = l.LeagueID
            WHERE {scatter_where_sql}
            ORDER BY XValue {scatter_order_dir}
            LIMIT ?;
        """

        try:
            df_top_scatter = pd.read_sql(top_scatter_sql, conn, params=scatter_params + [scatter_top_n])

            if df_top_scatter.empty:
                st.info("No data found for the selected filters (scatter plot).")
            else:
                top_scatter_player_ids = df_top_scatter["PlayerID"].tolist()

                # Now fetch X and Y values for exactly those players
                placeholders_players = ",".join(["?"] * len(top_scatter_player_ids))
                final_scatter_where = f"{stats_alias}.Season = ? AND {stats_alias}.PlayerID IN ({placeholders_players})"
                final_scatter_params = [season] + top_scatter_player_ids

                if selected_team_ids:
                    placeholders = ",".join(["?"] * len(selected_team_ids))
                    final_scatter_where += f" AND {stats_alias}.TeamID IN ({placeholders})"
                    final_scatter_params.extend(selected_team_ids)

                if selected_levels:
                    placeholders = ",".join(["?"] * len(selected_levels))
                    final_scatter_where += f" AND l.LeagueLevel IN ({placeholders})"
                    final_scatter_params.extend(selected_levels)

                if selected_position_codes:
                    selected_positions_full = [
                        POSITION_CODE_TO_FULL.get(code, code) for code in selected_position_codes
                    ]
                    placeholders = ",".join(["?"] * len(selected_positions_full))
                    final_scatter_where += f" AND p.Position IN ({placeholders})"
                    final_scatter_params.extend(selected_positions_full)

                final_scatter_sql = f"""
                    SELECT 
                        p.PlayerID,
                        (p.FirstName || ' ' || p.LastName) AS PlayerName,
                        t.TeamName,
                        {stats_alias}.{scatter_x_col} AS XValue,
                        {stats_alias}.{scatter_y_col} AS YValue
                    FROM `{stats_table}` {stats_alias}
                    JOIN `Player` p ON {stats_alias}.PlayerID = p.PlayerID
                    JOIN `Team` t ON {stats_alias}.TeamID = t.TeamID
                    JOIN `League` l ON t.LeagueID = l.LeagueID
                    WHERE {final_scatter_where};
                """

                df_scatter = pd.read_sql(final_scatter_sql, conn, params=final_scatter_params)
                if df_scatter.empty:
                    st.info("No data found for the selected filters (scatter plot).")
                else:
                    # Map team names to colors, fallback to default
                    df_scatter["TeamColor"] = df_scatter["TeamName"].map(TEAM_COLORS).fillna(DEFAULT_TEAM_COLOR)

                    scatter_chart = (
                        alt.Chart(df_scatter)
                        .mark_circle(size=80, opacity=0.8)
                        .encode(
                            x=alt.X("XValue:Q", title=scatter_x_label),
                            y=alt.Y("YValue:Q", title=scatter_y_label),
                            color=alt.Color("TeamName:N", legend=alt.Legend(title="Team")),
                            tooltip=["PlayerName", "TeamName", "XValue", "YValue"],
                        )
                        .properties(width="container", height=400)
                    )

                    st.altair_chart(scatter_chart, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading data for scatter plot: {e}")

        # --- Line Chart – Metric over Seasons (2021–2024) ---
        st.markdown("---")
        st.subheader("Line Chart – Metric over Seasons (2021–2024)")

        line_metric_options = scatter_metric_options
        line_metric_label = st.selectbox(
            "Y-axis metric (line chart)",
            options=list(line_metric_options.keys()),
            key="line_metric",
        )
        line_metric_col = line_metric_options[line_metric_label]

        line_top_n = st.slider(
            "Number of players to show (line)",
            min_value=5,
            max_value=50,
            value=15,
            step=5,
        )

        # Build filters used to choose top-N players in 2024
        top_where_clauses = [f"{stats_alias}.Season = ?"]
        top_params = [2024]

        line_qualifier = qualifying_where_clause([line_metric_col], stats_alias, player_type)
        if line_qualifier:
            top_where_clauses.append(line_qualifier)

        if selected_levels:
            placeholders = ",".join(["?"] * len(selected_levels))
            top_where_clauses.append(f"l.LeagueLevel IN ({placeholders})")
            top_params.extend(selected_levels)

        if selected_team_ids:
            placeholders = ",".join(["?"] * len(selected_team_ids))
            top_where_clauses.append(f"{stats_alias}.TeamID IN ({placeholders})")
            top_params.extend(selected_team_ids)

        if selected_position_codes:
            selected_positions_full = [
                POSITION_CODE_TO_FULL.get(code, code) for code in selected_position_codes
            ]
            placeholders = ",".join(["?"] * len(selected_positions_full))
            top_where_clauses.append(f"p.Position IN ({placeholders})")
            top_params.extend(selected_positions_full)

        if selected_players:
            label_to_pid = {}
            for (pid, fn, ln, tname, pos) in player_rows:
                label = f"{fn} {ln} - {tname if tname else 'Unknown Team'} - {pos if pos else 'N/A'}"
                label_to_pid[label] = pid

            selected_player_ids = [label_to_pid[label] for label in selected_players]
            placeholders = ",".join(["?"] * len(selected_player_ids))
            top_where_clauses.append(f"{stats_alias}.PlayerID IN ({placeholders})")
            top_params.extend(selected_player_ids)

        top_where_sql = " AND ".join(top_where_clauses)

        # Determine order direction for choosing "top" players
        if line_metric_col in ["EarnedRunAverage", "FieldingIndependentPitching"]:
            line_order_dir = "ASC"  # lower is better
        else:
            line_order_dir = "DESC"  # higher is better

        top_players_sql = f"""
            SELECT
                {stats_alias}.PlayerID,
                {stats_alias}.{line_metric_col} AS MetricValue
            FROM `{stats_table}` {stats_alias}
            JOIN `Player` p ON {stats_alias}.PlayerID = p.PlayerID
            JOIN `Team` t ON {stats_alias}.TeamID = t.TeamID
            JOIN `League` l ON t.LeagueID = l.LeagueID
            WHERE {top_where_sql}
            ORDER BY MetricValue {line_order_dir}
            LIMIT ?;
        """

        try:
            # First, get the top-N players for the chosen metric in 2024
            df_top_players = pd.read_sql(top_players_sql, conn, params=top_params + [line_top_n])

            if df_top_players.empty:
                st.info("No data found for the selected filters (line chart).")
            else:
                top_player_ids = df_top_players["PlayerID"].tolist()

                # Now pull their full 2021–2024 history (still respecting filters)
                history_where_clauses = [
                    f"{stats_alias}.PlayerID IN ({','.join(['?'] * len(top_player_ids))})",
                    f"{stats_alias}.Season BETWEEN ? AND ?",
                ]
                history_params = top_player_ids + [2021, 2024]

                if selected_levels:
                    placeholders = ",".join(["?"] * len(selected_levels))
                    history_where_clauses.append(f"l.LeagueLevel IN ({placeholders})")
                    history_params.extend(selected_levels)

                if selected_team_ids:
                    placeholders = ",".join(["?"] * len(selected_team_ids))
                    history_where_clauses.append(f"{stats_alias}.TeamID IN ({placeholders})")
                    history_params.extend(selected_team_ids)

                if selected_position_codes:
                    selected_positions_full = [
                        POSITION_CODE_TO_FULL.get(code, code) for code in selected_position_codes
                    ]
                    placeholders = ",".join(["?"] * len(selected_positions_full))
                    history_where_clauses.append(f"p.Position IN ({placeholders})")
                    history_params.extend(selected_positions_full)

                history_where_sql = " AND ".join(history_where_clauses)

                line_sql = f"""
                    SELECT
                        p.PlayerID,
                        (p.FirstName || ' ' || p.LastName) AS PlayerName,
                        t.TeamName,
                        {stats_alias}.Season AS Season,
                        {stats_alias}.{line_metric_col} AS MetricValue
                    FROM `{stats_table}` {stats_alias}
                    JOIN `Player` p ON {stats_alias}.PlayerID = p.PlayerID
                    JOIN `Team` t ON {stats_alias}.TeamID = t.TeamID
                    JOIN `League` l ON t.LeagueID = l.LeagueID
                    WHERE {history_where_sql}
                    ORDER BY p.PlayerID, {stats_alias}.Season;
                """

                df_line = pd.read_sql(line_sql, conn, params=history_params)

                if df_line.empty:
                    st.info("No data found for the selected filters (line chart).")
                else:
                    df_line["TeamColor"] = df_line["TeamName"].map(TEAM_COLORS).fillna(DEFAULT_TEAM_COLOR)

                    line_chart = (
                        alt.Chart(df_line)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("Season:Q", title="Season"),
                            y=alt.Y("MetricValue:Q", title=line_metric_label),
                            color=alt.Color("PlayerName:N", legend=alt.Legend(title="Player")),
                            tooltip=["PlayerName", "TeamName", "Season", "MetricValue"],
                        )
                        .properties(width="container", height=400)
                    )

                    st.altair_chart(line_chart, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading data for line chart: {e}")


# ============================================================================
# --- Section 3: Player Management (CRUD) ---
# ============================================================================
elif app_section == "Player Management (CRUD)":
    st.header("Player Management (CRUD)")
    st.caption(
        "You're editing a private, temporary copy of the database. "
        "Changes here never touch the live demo data and reset if you refresh the page."
    )

    crud_conn = get_crud_connection()
    if not crud_conn:
        st.error("Database connection failed. Please check the configuration.")
    else:
        crud = PlayerCRUD(crud_conn)

        crud_mode = st.sidebar.radio(
            "Player Management Mode",
            ("Create", "View", "Search", "Update", "Delete"),
        )

        # --- Create ---
        if crud_mode == "Create":
            st.subheader("Create New Player")
            col1, col2 = st.columns(2)

            with col1:
                first_name = st.text_input("First Name")
                last_name = st.text_input("Last Name")
                date_of_birth = st.date_input("Date of Birth", value=None, format="YYYY-MM-DD")
                position = st.text_input("Position (e.g., SS, C, P)")

            with col2:
                height = st.number_input("Height (inches)", min_value=0, max_value=96, value=0)
                weight = st.number_input("Weight (lbs)", min_value=0, max_value=400, value=0)
                throws = st.selectbox("Throws", options=["", "L", "R"], index=0)
                bats = st.selectbox("Bats", options=["", "L", "R", "S"], index=0)
                player_level = st.text_input("Player Level (e.g., MLB, MiLB, College)")

            if st.button("Create Player"):
                if not first_name or not last_name:
                    st.warning("First and Last Name are required.")
                else:
                    pid = crud.create_player(
                        first_name,
                        last_name,
                        str(date_of_birth) if date_of_birth else None,
                        position or None,
                        int(height) if height else None,
                        int(weight) if weight else None,
                        throws or None,
                        bats or None,
                        player_level or None,
                    )
                    st.success(f"Player created with PlayerID = {pid}")

        # --- View ---
        elif crud_mode == "View":
            st.subheader("View Players")
            total = crud.get_player_count()
            st.write(f"Total players in database: {total}")

            page_size = st.selectbox("Page size", options=[10, 25, 50, 100], index=1)
            page = st.number_input("Page", min_value=1, value=1)
            offset = (page - 1) * page_size

            players = crud.read_all_players(limit=page_size, offset=offset)
            if players:
                st.dataframe(pd.DataFrame(players))
            else:
                st.info("No players found for this page.")

        # --- Search ---
        elif crud_mode == "Search":
            st.subheader("Search Players")
            term = st.text_input("Search by name or PlayerID")
            if st.button("Search") and term:
                results = crud.search_players(term)
                if results:
                    st.dataframe(pd.DataFrame(results))
                else:
                    st.info("No players matched your search.")

        # --- Update ---
        elif crud_mode == "Update":
            st.subheader("Update Player")
            search_id = st.number_input("PlayerID to update", min_value=1, step=1)
            if st.button("Load Player"):
                player = crud.read_player(int(search_id))
                if player:
                    st.session_state["_update_player"] = player
                else:
                    st.warning("Player not found.")

            player = st.session_state.get("_update_player")
            if player:
                st.write(f"Editing PlayerID {player['PlayerID']} - {player['FirstName']} {player['LastName']}")
                col1, col2 = st.columns(2)
                with col1:
                    first_name = st.text_input("First Name", value=player["FirstName"])
                    last_name = st.text_input("Last Name", value=player["LastName"])
                    date_of_birth = st.text_input("Date of Birth (YYYY-MM-DD)", value=str(player.get("DateOfBirth") or ""))
                    position = st.text_input("Position", value=player.get("Position") or "")
                with col2:
                    height = st.number_input("Height (inches)", min_value=0, max_value=96, value=player.get("Height") or 0)
                    weight = st.number_input("Weight (lbs)", min_value=0, max_value=400, value=player.get("Weight") or 0)
                    throws = st.text_input("Throws (L/R)", value=player.get("Throws") or "")
                    bats = st.text_input("Bats (L/R/S)", value=player.get("Bats") or "")
                    player_level = st.text_input("Player Level", value=player.get("PlayerLevel") or "")

                if st.button("Save Changes"):
                    updates = {}
                    if first_name != player["FirstName"]:
                        updates["first_name"] = first_name
                    if last_name != player["LastName"]:
                        updates["last_name"] = last_name
                    if date_of_birth != str(player.get("DateOfBirth") or ""):
                        updates["date_of_birth"] = date_of_birth or None
                    if position != (player.get("Position") or ""):
                        updates["position"] = position or None
                    if height != (player.get("Height") or 0):
                        updates["height"] = int(height) if height else None
                    if weight != (player.get("Weight") or 0):
                        updates["weight"] = int(weight) if weight else None
                    if throws != (player.get("Throws") or ""):
                        updates["throws"] = throws or None
                    if bats != (player.get("Bats") or ""):
                        updates["bats"] = bats or None
                    if player_level != (player.get("PlayerLevel") or ""):
                        updates["player_level"] = player_level or None

                    if not updates:
                        st.info("No changes detected.")
                    else:
                        ok = crud.update_player(int(player["PlayerID"]), **updates)
                        if ok:
                            st.success("Player updated successfully.")
                            # Refresh the cached player so the form reflects latest values
                            st.session_state["_update_player"] = crud.read_player(int(player["PlayerID"]))
                        else:
                            st.error("Update failed.")

        # --- Delete ---
        elif crud_mode == "Delete":
            st.subheader("Delete Player")
            del_id = st.number_input("PlayerID to delete", min_value=1, step=1)
            confirm = st.checkbox("I understand this will permanently delete the player.")
            if st.button("Delete Player"):
                if not confirm:
                    st.warning("Please confirm deletion.")
                else:
                    ok = crud.delete_player(int(del_id))
                    if ok:
                        st.success(f"Player {int(del_id)} deleted.")
                    else:
                        st.error("Deletion failed.")


# ==============================================================================
# --- Section 4: Scouting Assistant (LLM) ---
# ==============================================================================
elif app_section == "Scouting Assistant (LLM)":
    st.header("AI Scouting & Roster Management Assistant")

    # Load/cached RAG resources
    try:
        chroma_client, player_collection, team_collection = get_chroma_client_and_collections()
    except Exception as e:
        st.error(f"Error initializing Chroma client/collections: {e}")
        st.stop()

    guidelines_text = st.session_state.get("guidelines_text")
    if guidelines_text is None:
        guidelines_text = load_guideline_markdown()
        st.session_state["guidelines_text"] = guidelines_text

    st.markdown(
        """
        Use this assistant for:
        - Evaluating whether to call up a minor leaguer
        - Assessing trades (major league or minor league players)
        - Evaluating current roster construction and contracts in context of team goals
        """
    )

    # Optional: select your organization from a dropdown so the assistant
    # and RAG retrieval know which MLB club you are working for.
    team_dropdown_options = ["(Not specified)"] + sorted(TEAM_COLORS.keys())
    selected_team = st.selectbox(
        "Your organization (for context)",
        options=team_dropdown_options,
        index=0,
        help="Choose your MLB organization, or leave as '(Not specified)' if you prefer to state it in the question.",
    )

    user_query = st.text_area(
        "Describe your scenario or question (e.g., call-up decision, trade idea, roster concern):",
        height=160,
        placeholder=(
            "Example: I'm running the Yankees and debating whether to call up our AAA shortstop "
            "who just posted a 140 wRC+ in 2023, or give him more development time. We have a "
            "league-average MLB SS under contract for two more years."
        ),
    )

    col_left, col_right = st.columns([2, 3])

    with col_left:
        n_players = st.slider("Max player documents to retrieve", 5, 100, 25, 5)
        n_teams = st.slider("Max team documents to retrieve", 2, 50, 10, 2)

        if st.button("Run Scouting Analysis"):
            if not user_query.strip():
                st.warning("Please enter a scenario or question.")
            else:
                with st.spinner("Retrieving context and generating analysis..."):
                    # If the user selected a specific team, prepend a short
                    # note so the enricher and downstream logic treat it as
                    # the current organization, even if the user doesn't
                    # explicitly say so in the prompt.
                    effective_query = user_query
                    if selected_team and selected_team != "(Not specified)":
                        effective_query = (
                            f"I am working for the {selected_team} front office. "
                            + user_query
                        )
                    player_docs, team_docs = retrieve_rag_context(
                        player_collection,
                        team_collection,
                        effective_query,
                        n_players=n_players,
                        n_teams=n_teams,
                        org_team_name_override=selected_team if selected_team != "(Not specified)" else None,
                    )
                    rag_context = format_rag_context_for_llm(player_docs, team_docs)
                    st.session_state["rag_context"] = rag_context
                    answer = call_scouting_llm(effective_query, rag_context, guidelines_text)
                    st.session_state["scouting_answer"] = answer

    with col_right:
        st.subheader("Assistant Answer")
        if "scouting_answer" in st.session_state:
            st.markdown(st.session_state["scouting_answer"])
        else:
            st.info("The assistant's answer will appear here after you run an analysis.")

    st.markdown("---")
    st.subheader("Retrieved Context (for transparency)")
    if "rag_context" in st.session_state:
        with st.expander("Show retrieved RAG context"):
            st.text(st.session_state["rag_context"])
    else:
        st.info("Context from Chroma will be shown here after the first query.")
