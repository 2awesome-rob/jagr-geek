"""Reusable statistics and Streamlit rendering helpers for the team dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

def summarize_team_games(df_games: pd.DataFrame, team_id: int) -> pd.DataFrame:
	"""Add team-relative scores and results to the selected team's games."""
	df_games = df_games.reset_index(drop=True)
	is_home = df_games["home_team_id"] == team_id
	is_away = df_games["away_team_id"] == team_id
	games = df_games[is_home | is_away].copy()
	if games.empty:
		return games
	games["team_score"] = np.where(is_home[games.index], games["home_score"], games["away_score"])
	games["opp_score"] = np.where(is_home[games.index], games["away_score"], games["home_score"])
	games["result_for_team"] = np.select(
		[games["team_score"] > games["opp_score"], games["team_score"] < games["opp_score"]],
		["W", "L"],
		default="T",
	)
	return games.sort_values("game_date", ascending=False)

def display_team_record(team_games: pd.DataFrame) -> None:
	"""Render the selected team's record and scoring totals."""
	team_games = team_games.reset_index(drop=True)
	record = team_games["result_for_team"].value_counts()
	points_for = pd.to_numeric(team_games["team_score"], errors="coerce").fillna(0).sum()
	points_against = pd.to_numeric(team_games["opp_score"], errors="coerce").fillna(0).sum()
	columns = st.columns(6)
	for column, label, value in zip(
		columns,
		("Wins", "Losses", "Ties", "PF", "PA", "SD"),
		(record.get("W", 0), record.get("L", 0), record.get("T", 0), points_for, points_against, points_for - points_against),
	):
		column.metric(label, int(value))

def display_game_table(df_games: pd.DataFrame, team_map: dict[int, str]) -> None:
	"""Render a compact game log with team names and result colors."""
	frame = df_games.reset_index(drop=True).copy()
	frame["home_team"] = frame["home_team_id"].map(team_map).fillna(frame["home_team_id"])
	frame["visiting_team"] = frame["away_team_id"].map(team_map).fillna(frame["away_team_id"])
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
	frame = frame[["game_date", "result_for_team", "away_score", "visiting_team", "home_team", "home_score"]]
	frame = frame.rename(columns={
		"game_date": "Date", "result_for_team": "Result", "away_score": "Away Score",
		"visiting_team": "Visitor", "home_team": "at Home", "home_score": "Home Score",
	})

	def color_result(value: str) -> str:
		return {"W": "color: green", "L": "color: red", "T": "color: blue"}.get(value, "")

	st.dataframe(frame.style.map(color_result, subset=["Result"]), hide_index=True)
