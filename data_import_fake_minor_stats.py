import random
import math

from db import create_db_connection

# Target seasons for fake stats (inclusive range)
START_SEASON = 2021
END_SEASON = 2024

# League levels we want to treat as minors
MINOR_LEVELS = ["Single-A", "Double-A", "Triple-A", "High-A"]


def get_minor_league_players(conn):
    """Return list of minor-league players by level (one row per player).

    We treat Player.PlayerLevel as the source of the minor-league level
    (Single-A, Double-A, etc.). We do not join to League here to avoid
    duplicating players if multiple leagues share the same LeagueLevel.
    Teams will be assigned later based on this level.
    """
    cursor = conn.cursor()

    query = f"""
        SELECT DISTINCT
            p.PlayerID,
            p.Position,
            p.PlayerLevel
        FROM Player p
        WHERE p.PlayerLevel IN ({",".join(["?"] * len(MINOR_LEVELS))})
    """

    params = MINOR_LEVELS
    cursor.execute(query, params)
    rows = cursor.fetchall()

    players = []
    for player_id, position, player_level in rows:
        players.append({
            "PlayerID": player_id,
            "Position": (position or "").strip(),
            "LeagueLevel": player_level,
        })

    return players


def get_minor_league_teams_by_level(conn):
    """Return mapping of LeagueLevel -> ordered list of TeamIDs for minor leagues."""
    cursor = conn.cursor()
    query = f"""
        SELECT t.TeamID, l.LeagueLevel
        FROM Team t
        JOIN League l ON t.LeagueID = l.LeagueID
        WHERE l.LeagueLevel IN ({",".join(["?"] * len(MINOR_LEVELS))})
        ORDER BY t.TeamID
    """
    params = MINOR_LEVELS
    cursor.execute(query, params)
    rows = cursor.fetchall()

    teams_by_level = {}
    for team_id, league_level in rows:
        teams_by_level.setdefault(league_level, []).append(team_id)

    return teams_by_level


def assign_players_to_teams_round_robin(players, teams_by_level):
    """Assign each minor-league player to a team for their level.

    Within each level (Single-A, Double-A, etc.) and broad position group
    (pitcher vs hitter), players are assigned in round-robin order across
    that level's teams. This guarantees at most one team per player per
    level within a run.
    """
    # Track next index per (league_level, is_pitcher)
    next_index = {}

    assigned = []
    for p in players:
        level = p["LeagueLevel"]
        teams = teams_by_level.get(level)
        if not teams:
            # No teams known for this level; skip assigning a team
            continue

        pos_upper = (p["Position"] or "").upper()
        is_pitcher = pos_upper in ("P", "SP", "RP", "CP", "PITCHER", "STARTING PITCHER", "RELIEF PITCHER")

        key = (level, is_pitcher)
        idx = next_index.get(key, 0)
        team_id = teams[idx % len(teams)]
        next_index[key] = idx + 1

        assigned.append({
            "PlayerID": p["PlayerID"],
            "Position": p["Position"],
            "LeagueLevel": level,
            "TeamID": team_id,
        })

    return assigned


def split_pitchers_hitters(players):
    pitchers = []
    hitters = []

    for p in players:
        pos = p["Position"].upper()
        # Simple heuristic: anything with "P" is pitcher; others hitter
        if pos in ("P", "SP", "RP", "CP", "PITCHER", "STARTING PITCHER", "RELIEF PITCHER"):
            pitchers.append(p)
        else:
            hitters.append(p)

    return hitters, pitchers


def random_int_clamped(mean, std_dev, min_val, max_val):
    value = int(random.gauss(mean, std_dev))
    return max(min_val, min(max_val, value))


def random_float_clamped(mean, std_dev, min_val, max_val, decimals=3):
    value = random.gauss(mean, std_dev)
    value = max(min_val, min(max_val, value))
    return round(value, decimals)


def generate_fake_hitter_stats_row(player, season):
    """Generate a dict of fake but reasonable hitter stats for a single player-season."""
    # Games and PA based on rough full/partial season
    games = random_int_clamped(115, 25, 40, 145)
    plate_appearances = random_int_clamped(games * 4.4, 60, 150, 750)

    # Batting average and OBP/SLG – slightly wider range to allow stars/strugglers
    batting_avg = random_float_clamped(0.245, 0.045, 0.150, 0.380, 3)
    obp = random_float_clamped(batting_avg + 0.055, 0.020, 0.230, 0.470, 3)
    slg = random_float_clamped(batting_avg + 0.150, 0.060, 0.280, 0.750, 3)
    ops = round(obp + slg, 3)

    hits = int(batting_avg * plate_appearances * 0.9)
    at_bats = max(hits + random_int_clamped(40, 30, 20, plate_appearances), hits + 1)

    doubles = random_int_clamped(hits * 0.20, 5, 3, max(10, hits // 3))
    triples = random_int_clamped(hits * 0.03, 2, 0, max(5, hits // 15))
    home_runs = random_int_clamped(hits * 0.07, 5, 0, max(40, hits // 2))

    singles = max(hits - doubles - triples - home_runs, 0)

    runs = random_int_clamped(plate_appearances * 0.15, 15, 5, 150)
    rbi = random_int_clamped(plate_appearances * 0.17, 15, 5, 160)

    walks = random_int_clamped(plate_appearances * 0.11, 7, 0, 140)
    strikeouts = random_int_clamped(plate_appearances * 0.24, 15, 10, 210)

    stolen_bases = random_int_clamped(plate_appearances * 0.05, 5, 0, 70)
    caught_stealing = random_int_clamped(stolen_bases * 0.35, 3, 0, 20)

    iso = round(slg - batting_avg, 3)
    hard_hit_pct = random_float_clamped(32.0, 10.0, 5.0, 70.0, 1)
    war = random_float_clamped(1.5, 1.5, -2.0, 8.0, 1)
    woba = random_float_clamped(0.325, 0.035, 0.230, 0.430, 3)
    wrc_plus = random_int_clamped(100, 30, 40, 190)

    return {
        "PlayerID": player["PlayerID"],
        "TeamID": player["TeamID"],
        "Season": season,
        "GamesPlayed": games,
        "PlateAppearances": plate_appearances,
        "AtBats": at_bats,
        "Runs": runs,
        "Hits": hits,
        "Doubles": doubles,
        "Triples": triples,
        "HomeRuns": home_runs,
        "RBI": rbi,
        "Walks": walks,
        "Strikeouts": strikeouts,
        "StolenBases": stolen_bases,
        "CaughtStealing": caught_stealing,
        "BattingAverage": batting_avg,
        "OnBasePercentage": obp,
        "SluggingPercentage": slg,
        "OnBasePlusSlugging": ops,
        "IsolatedPower": iso,
        "HardHitPercentage": hard_hit_pct,
        "WinsAboveReplacement": war,
        "WeightedOnBaseAverage": woba,
        "WeightedRunsCreatedPlus": wrc_plus,
    }


def generate_fake_pitcher_stats_row(player, season):
    """Generate a dict of fake but reasonable pitcher stats for a single player-season."""
    games_pitched = random_int_clamped(48, 18, 10, 80)
    games_started = random_int_clamped(18, 10, 0, games_pitched)

    innings_pitched = random_float_clamped(95.0, 35.0, 15.0, 220.0, 1)

    strikeouts = random_int_clamped(innings_pitched * 1.1, 25, 20, 320)
    walks_allowed = random_int_clamped(innings_pitched * 0.40, 12, 5, 120)

    hits_allowed = random_int_clamped(innings_pitched * 1.05, 20, 25, 280)
    home_runs_allowed = random_int_clamped(innings_pitched * 0.15, 4, 0, 50)

    era = random_float_clamped(3.90, 1.10, 1.20, 9.50, 2)
    earned_runs = int(era * innings_pitched / 9)

    runs_allowed = earned_runs + random_int_clamped(7, 4, 0, 40)

    wins = random_int_clamped(11, 5, 0, 22)
    losses = random_int_clamped(9, 5, 0, 20)
    saves = random_int_clamped(7, 6, 0, 45)
    holds = random_int_clamped(7, 6, 0, 35)

    fip = random_float_clamped(era, 0.60, 1.20, 9.50, 2)
    expected_era = random_float_clamped(era, 0.55, 1.20, 9.50, 2)
    whip = random_float_clamped(1.27, 0.30, 0.70, 2.10, 2)
    whiff_pct = random_float_clamped(29.0, 9.0, 5.0, 52.0, 1)

    return {
        "PlayerID": player["PlayerID"],
        "TeamID": player["TeamID"],
        "Season": season,
        "Wins": wins,
        "Losses": losses,
        "GamesPitched": games_pitched,
        "GamesStarted": games_started,
        "Saves": saves,
        "Holds": holds,
        "InningsPitched": innings_pitched,
        "HitsAllowed": hits_allowed,
        "RunsAllowed": runs_allowed,
        "EarnedRuns": earned_runs,
        "HomeRunsAllowed": home_runs_allowed,
        "WalksAllowed": walks_allowed,
        "Strikeouts": strikeouts,
        "EarnedRunAverage": era,
        "FieldingIndependentPitching": fip,
        "ExpectedERA": expected_era,
        "WalksAndHitsPerInningPitched": whip,
        "WhiffPercentage": whiff_pct,
    }


def insert_fake_hitter_stats(conn, hitter_rows):
    if not hitter_rows:
        return

    cursor = conn.cursor()
    sql = """
        INSERT INTO HitterStats (
            PlayerID, TeamID, Season,
            GamesPlayed, PlateAppearances, AtBats,
            Runs, Hits, Doubles, Triples, HomeRuns, RBI,
            Walks, Strikeouts, StolenBases, CaughtStealing,
            BattingAverage, OnBasePercentage, SluggingPercentage,
            OnBasePlusSlugging, IsolatedPower,
            HardHitPercentage, WinsAboveReplacement,
            WeightedOnBaseAverage, WeightedRunsCreatedPlus
        ) VALUES (
            :PlayerID, :TeamID, :Season,
            :GamesPlayed, :PlateAppearances, :AtBats,
            :Runs, :Hits, :Doubles, :Triples, :HomeRuns, :RBI,
            :Walks, :Strikeouts, :StolenBases, :CaughtStealing,
            :BattingAverage, :OnBasePercentage, :SluggingPercentage,
            :OnBasePlusSlugging, :IsolatedPower,
            :HardHitPercentage, :WinsAboveReplacement,
            :WeightedOnBaseAverage, :WeightedRunsCreatedPlus
        )
        ON CONFLICT(PlayerID, TeamID, Season) DO UPDATE SET
            GamesPlayed = excluded.GamesPlayed,
            PlateAppearances = excluded.PlateAppearances,
            AtBats = excluded.AtBats,
            Runs = excluded.Runs,
            Hits = excluded.Hits,
            Doubles = excluded.Doubles,
            Triples = excluded.Triples,
            HomeRuns = excluded.HomeRuns,
            RBI = excluded.RBI,
            Walks = excluded.Walks,
            Strikeouts = excluded.Strikeouts,
            StolenBases = excluded.StolenBases,
            CaughtStealing = excluded.CaughtStealing,
            BattingAverage = excluded.BattingAverage,
            OnBasePercentage = excluded.OnBasePercentage,
            SluggingPercentage = excluded.SluggingPercentage,
            OnBasePlusSlugging = excluded.OnBasePlusSlugging,
            IsolatedPower = excluded.IsolatedPower,
            HardHitPercentage = excluded.HardHitPercentage,
            WinsAboveReplacement = excluded.WinsAboveReplacement,
            WeightedOnBaseAverage = excluded.WeightedOnBaseAverage,
            WeightedRunsCreatedPlus = excluded.WeightedRunsCreatedPlus;
    """

    cursor.executemany(sql, hitter_rows)
    conn.commit()


def insert_fake_pitcher_stats(conn, pitcher_rows):
    if not pitcher_rows:
        return

    cursor = conn.cursor()
    sql = """
        INSERT INTO PitcherStats (
            PlayerID, TeamID, Season,
            Wins, Losses, GamesPitched, GamesStarted,
            Saves, Holds,
            InningsPitched, HitsAllowed, RunsAllowed, EarnedRuns,
            HomeRunsAllowed, WalksAllowed, Strikeouts,
            EarnedRunAverage, FieldingIndependentPitching, ExpectedERA,
            WalksAndHitsPerInningPitched, WhiffPercentage
        ) VALUES (
            :PlayerID, :TeamID, :Season,
            :Wins, :Losses, :GamesPitched, :GamesStarted,
            :Saves, :Holds,
            :InningsPitched, :HitsAllowed, :RunsAllowed, :EarnedRuns,
            :HomeRunsAllowed, :WalksAllowed, :Strikeouts,
            :EarnedRunAverage, :FieldingIndependentPitching, :ExpectedERA,
            :WalksAndHitsPerInningPitched, :WhiffPercentage
        )
        ON CONFLICT(PlayerID, TeamID, Season) DO UPDATE SET
            Wins = excluded.Wins,
            Losses = excluded.Losses,
            GamesPitched = excluded.GamesPitched,
            GamesStarted = excluded.GamesStarted,
            Saves = excluded.Saves,
            Holds = excluded.Holds,
            InningsPitched = excluded.InningsPitched,
            HitsAllowed = excluded.HitsAllowed,
            RunsAllowed = excluded.RunsAllowed,
            EarnedRuns = excluded.EarnedRuns,
            HomeRunsAllowed = excluded.HomeRunsAllowed,
            WalksAllowed = excluded.WalksAllowed,
            Strikeouts = excluded.Strikeouts,
            EarnedRunAverage = excluded.EarnedRunAverage,
            FieldingIndependentPitching = excluded.FieldingIndependentPitching,
            ExpectedERA = excluded.ExpectedERA,
            WalksAndHitsPerInningPitched = excluded.WalksAndHitsPerInningPitched,
            WhiffPercentage = excluded.WhiffPercentage;
    """

    cursor.executemany(sql, pitcher_rows)
    conn.commit()


def main():
    print("--- Starting fake minor league stats generation ---")
    conn = create_db_connection()
    if not conn:
        return

    # Get all minor-league players and available teams by level
    raw_players = get_minor_league_players(conn)
    teams_by_level = get_minor_league_teams_by_level(conn)

    players = assign_players_to_teams_round_robin(raw_players, teams_by_level)
    total_players = len(players)
    print(f"Found {total_players} minor-league players to assign to teams.")

    hitters, pitchers = split_pitchers_hitters(players)
    print(f"Classified {len(hitters)} hitters and {len(pitchers)} pitchers.")

    for season in range(START_SEASON, END_SEASON + 1):
        print(f"--- Generating fake minor league stats for season {season} ---")

        # Generate hitter stats with progress updates
        hitter_rows = []
        if hitters:
            print("Generating fake hitter stats...")
            for idx, p in enumerate(hitters, start=1):
                hitter_rows.append(generate_fake_hitter_stats_row(p, season))
                if idx % 50 == 0 or idx == len(hitters):
                    print(f"  [{season}] Generated hitter stats for {idx}/{len(hitters)} hitters")

        # Generate pitcher stats with progress updates
        pitcher_rows = []
        if pitchers:
            print("Generating fake pitcher stats...")
            for idx, p in enumerate(pitchers, start=1):
                pitcher_rows.append(generate_fake_pitcher_stats_row(p, season))
                if idx % 50 == 0 or idx == len(pitchers):
                    print(f"  [{season}] Generated pitcher stats for {idx}/{len(pitchers)} pitchers")

        print("Inserting hitter stats into HitterStats...")
        insert_fake_hitter_stats(conn, hitter_rows)
        print(f"  [{season}] Insert attempted for {len(hitter_rows)} hitter rows.")

        print("Inserting pitcher stats into PitcherStats...")
        insert_fake_pitcher_stats(conn, pitcher_rows)
        print(f"  [{season}] Insert attempted for {len(pitcher_rows)} pitcher rows.")

    conn.close()
    print("--- Fake minor league stats generation complete ---")


if __name__ == "__main__":
    main()
