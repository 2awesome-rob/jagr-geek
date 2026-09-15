"""Database access for the Jagr Streamlit application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'tests' / 'test.db'}"

TEAM_COLUMNS = ["team_id", "club", "team_name", "season"]
ROSTER_COLUMNS = ["player_id", "team_id", "player_jersey", "player_first_name", "position"]
GAME_COLUMNS = [
	"game_id", "game_date", "home_team_id", "home_score", "away_team_id",
	"away_score", "was_overtime", "was_shootout", "game_type_id",
]
PLAYER_COLUMNS = [
	"game_id", "player_id", "goals", "assists", "penalty_min", "toi_sec",
	"shots", "plus", "minus", "active",
]
GOALIE_COLUMNS = [
	"game_id", "player_id", "shots_on", "saves", "goals_against", "is_win",
	"is_loss", "active",
]


def get_database_url() -> str:
	"""Return DATABASE_URL from the process environment or a local .env file."""
	load_dotenv(PROJECT_ROOT / ".env")
	return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip().strip('"').strip("'")


def create_database_engine(database_url: str | None = None) -> Engine:
	"""Create an engine for SQLite or a deployed SQLAlchemy database URL."""
	url = database_url or get_database_url()
	if url.startswith("postgres://"):
		url = "postgresql+psycopg2://" + url.removeprefix("postgres://")
	if url.startswith("sqlite"):
		return create_engine(url, connect_args={"check_same_thread": False})
	return create_engine(url, pool_pre_ping=True)


def _empty_frames() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	return (
		pd.DataFrame(columns=TEAM_COLUMNS),
		pd.DataFrame(columns=ROSTER_COLUMNS),
		pd.DataFrame(columns=GAME_COLUMNS),
		pd.DataFrame(columns=PLAYER_COLUMNS),
		pd.DataFrame(columns=GOALIE_COLUMNS),
	)


def _in_params(prefix: str, values: list[int]) -> tuple[str, Dict[str, int]]:
	names = [f":{prefix}{index}" for index in range(len(values))]
	return ",".join(names), {f"{prefix}{index}": value for index, value in enumerate(values)}


def _normalize_columns(frame: pd.DataFrame, aliases: dict[str, str], defaults: dict[str, object]) -> pd.DataFrame:
	"""Adapt older and newer database column names to the UI contract."""
	frame = frame.rename(columns={source: target for source, target in aliases.items() if source in frame})
	for column, default in defaults.items():
		if column not in frame:
			frame[column] = default
	return frame


def load_dfs_from_database(
	season: int,
	database_url: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	"""Load season teams, rosters, games, skater stats, and goalie stats."""
	df_teams, df_rosters, df_games, df_players, df_goalies = _empty_frames()
	engine = create_database_engine(database_url)

	with engine.connect() as connection:
		df_teams = pd.read_sql_query(
			text("SELECT team_id, club, team_name, season FROM teams WHERE season = :season"),
			connection,
			params={"season": season},
		)
		if df_teams.empty:
			return df_teams, df_rosters, df_games, df_players, df_goalies

		team_ids = df_teams["team_id"].dropna().astype(int).unique().tolist()
		team_params, team_values = _in_params("team", team_ids)
		df_rosters = pd.read_sql_query(
			text(f"""
				SELECT p.player_id, p.team_id, p.player_jersey,
					   ps.player_first_name, dp.code AS position
				FROM players AS p
				INNER JOIN players_static AS ps ON p.player_static_id = ps.player_static_id
				INNER JOIN dict_positions AS dp ON p.position_id = dp.position_id
				WHERE p.team_id IN ({team_params})
			"""),
			connection,
			params=team_values,
		)
		df_games = pd.read_sql_query(
			text(f"""
				SELECT * FROM games
				WHERE home_team_id IN ({team_params})
				   OR away_team_id IN ({team_params})
			"""),
			connection,
			params={**team_values, **{f"team{len(team_ids) + index}": value for index, value in enumerate(team_ids)}},
		)
		if not df_games.empty:
			df_games["game_date"] = pd.to_datetime(df_games["game_date"], errors="coerce")
			df_games = df_games.sort_values("game_date")

		player_ids = df_rosters["player_id"].dropna().astype(int).unique().tolist()
		game_ids = df_games["game_id"].dropna().astype(int).unique().tolist()
		if player_ids and game_ids:
			player_params, player_values = _in_params("player", player_ids)
			game_params, game_values = _in_params("game", game_ids)
			params = {**player_values, **game_values}
			stats_sql = f"""
				WHERE player_id IN ({player_params})
				  AND game_id IN ({game_params})
			"""
			df_players = pd.read_sql_query(text(f"SELECT * FROM lineups {stats_sql}"), connection, params=params)
			df_goalies = pd.read_sql_query(text(f"SELECT * FROM goalies {stats_sql}"), connection, params=params)

	df_players = _normalize_columns(
		df_players,
		{"pim": "penalty_min"},
		{
			"goals": 0, "assists": 0, "penalty_min": 0, "toi_sec": 0,
			"shots": 0, "plus": 0, "minus": 0,
			"active": False,
		},
	)
	if not df_players.empty and "line_id" in df_players:
		df_players["active"] = df_players["line_id"].fillna(0) != 0

	df_goalies = _normalize_columns(
		df_goalies,
		{
			"shots_faced": "shots_on", "goals_allowed": "goals_against",
			"TOI": "toi_sec", "result": "result_code",
		},
		{
			"shots_on": 0, "saves": 0, "goals_against": 0, "toi_sec": 0,
			"is_win": False, "is_loss": False, "active": False,
		},
	)
	if not df_goalies.empty and "result_code" in df_goalies:
		df_goalies["is_win"] = df_goalies["result_code"].astype(str).str.upper().eq("W")
		df_goalies["is_loss"] = df_goalies["result_code"].astype(str).str.upper().eq("L")

	if not df_players.empty:
		df_players["goals"] = pd.to_numeric(df_players["goals"], errors="coerce").fillna(0).astype(int)
		df_players["assists"] = pd.to_numeric(df_players["assists"], errors="coerce").fillna(0).astype(int)
		df_players["points"] = df_players["goals"] + df_players["assists"]
		df_players["penalty_min"] = df_players["penalty_min"].div(60)
		df_players["active"] = ~df_players["active"].isin([0, 5, 6])

	if not df_goalies.empty:
		df_goalies["shots_on"] = pd.to_numeric(df_goalies["shots_on"], errors="coerce").fillna(0).astype(int)
		df_goalies["saves"] = pd.to_numeric(df_goalies["saves"], errors="coerce").fillna(0).astype(int)
		df_goalies["save_pct"] = np.where(
			df_goalies["shots_on"] > 0,
			df_goalies["saves"] / df_goalies["shots_on"],
			np.nan,
		)
		df_goalies["active"] = df_goalies["toi_sec"] > 0
		df_goalies["result"] = np.where(
			df_goalies["is_win"] == 1, "W", np.where(df_goalies["is_loss"] == 1, "L", "-")
		)

	if not df_teams.empty:
		df_teams = df_teams.reset_index(drop=True)

	if not df_rosters.empty:
		df_rosters = df_rosters.reset_index(drop=True)

	if not df_games.empty:
		df_games = df_games.reset_index(drop=True)

	if not df_players.empty:
		df_players = df_players.reset_index(drop=True)

	if not df_goalies.empty:
		df_goalies = df_goalies.reset_index(drop=True)

	return df_teams, df_rosters, df_games, df_players, df_goalies
