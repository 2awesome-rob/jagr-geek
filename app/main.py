"""Reusable statistics and Streamlit rendering helpers for the dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


def summarize_team_games(df_games: pd.DataFrame, team_id: int) -> pd.DataFrame:
	"""Add team-relative scores and results to the selected team's games."""
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
	frame = df_games.copy()
	frame["home_team"] = frame["home_team_id"].map(team_map).fillna(frame["home_team_id"])
	frame["visiting_team"] = frame["away_team_id"].map(team_map).fillna(frame["away_team_id"])
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
	frame = frame[["game_date", "result_for_team", "away_score", "visiting_team", "home_team", "home_score"]]
	frame = frame.rename(columns={
		"game_date": "Date", "result_for_team": "Result", "away_score": "Score",
		"visiting_team": "Visitor", "home_team": "at Home", "home_score": "Home score",
	})

	def color_result(value: str) -> str:
		return {"W": "color: green", "L": "color: red", "T": "color: blue"}.get(value, "")

	st.dataframe(frame.style.map(color_result, subset=["Result"]), hide_index=True)


def _merge_team_stats(stats: pd.DataFrame, games: pd.DataFrame, rosters: pd.DataFrame, team_id: int) -> pd.DataFrame:
	frame = stats.reset_index(drop=True).merge(games[["game_id"]], on="game_id")
	frame = frame.merge(rosters[["player_id", "team_id", "player_first_name"]], on="player_id")
	return frame[frame["team_id"] == team_id]


def display_season_total_stats(stats: pd.DataFrame, games: pd.DataFrame, rosters: pd.DataFrame, team_id: int) -> None:
	"""Render season totals for skaters or goalies."""
	frame = _merge_team_stats(stats, games, rosters, team_id)
	if frame.empty:
		st.info("No season statistics available.")
		return
	frame = frame[frame["active"].astype(bool)]
	if "shots_on" in frame:
		totals = frame.groupby("player_first_name", as_index=False).agg(
			Games=("active", "sum"), W=("is_win", "sum"), L=("is_loss", "sum"),
			SOG=("shots_on", "sum"), Saves=("saves", "sum"), Goals=("goals_against", "sum"),
		)
		totals["Save %"] = np.where(totals["SOG"] > 0, totals["Saves"] / totals["SOG"], np.nan)
		st.dataframe(totals.rename(columns={"player_first_name": "Goalie"}).sort_values("W", ascending=False), hide_index=True)
	else:
		totals = frame.groupby("player_first_name", as_index=False).agg(
			Games=("active", "sum"), Goals=("goals", "sum"), Assists=("assists", "sum"),
			Points=("points", "sum"), PIM=("penalty_min", "sum"),
		)
		st.dataframe(totals.rename(columns={"player_first_name": "Player"}).sort_values("Points", ascending=False), hide_index=True)


def _active_rows(frame: pd.DataFrame) -> pd.DataFrame:
	if "active" not in frame:
		return frame
	values = frame["active"]
	if values.dtype == bool:
		return frame[values.fillna(False)]
	return frame[pd.to_numeric(values, errors="coerce").fillna(0) != 0]


def display_summary_stats(stats_df: pd.DataFrame, full_df: pd.DataFrame) -> None:
	"""Render aggregate metrics for one player."""
	frame = _active_rows(stats_df.copy())
	if frame.empty:
		st.info("No active statistics available.")
		return
	if "shots_on" in frame:
		shots = int(frame["shots_on"].sum())
		saves = int(frame["saves"].sum())
		result = frame["result"].astype(str).str.upper()
		values = (int((result == "W").sum()), int((result == "L").sum()), shots, saves)
		columns = st.columns(5)
		for column, label, value in zip(columns, ("Wins", "Losses", "Shots On", "Saves"), values):
			column.metric(label, value)
		columns[4].metric("Save %", f"{saves / shots * 100:.1f}%" if shots else "N/A")
		return
	games = frame["game_id"].nunique()
	goals = int(frame["goals"].sum())
	assists = int(frame["assists"].sum())
	points = int(frame["points"].sum())
	columns = st.columns(5)
	for column, label, value in zip(columns, ("Games", "Goals", "Assists", "Points", "PIM"), (games, goals, assists, points, int(frame["penalty_min"].sum()))):
		column.metric(label, value)


def display_game_log(game_log_df: pd.DataFrame, df_games: pd.DataFrame) -> None:
	frame = _active_rows(game_log_df).merge(df_games, on="game_id", how="left", suffixes=("", "_game"))
	frame = frame.sort_values("game_date", ascending=False)
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
	if "shots_on" in frame:
		columns = ["game_date", "result", "shots_on", "saves", "goals_against"]
		names = {"game_date": "Date", "result": "W/L", "shots_on": "SOG", "goals_against": "Goals"}
	else:
		columns = ["game_date", "goals", "assists", "points", "penalty_min"]
		names = {"game_date": "Date", "goals": "Goals", "assists": "Assists", "points": "Points", "penalty_min": "PIM"}
	st.dataframe(frame.head(3)[columns].rename(columns=names), hide_index=True)


def plot_game_log(game_log_df: pd.DataFrame, df_games: pd.DataFrame) -> None:
	frame = _active_rows(game_log_df).merge(df_games, on="game_id", how="left", suffixes=("", "_game"))
	frame = frame.sort_values("game_date", ascending=False)
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date
	if "shots_on" in frame:
		frame["Save %"] = np.where(frame["shots_on"] > 0, frame["saves"] / frame["shots_on"], np.nan)
		st.line_chart(frame, x="game_date", y="Save %", height=120)
	else:
		st.line_chart(frame, x="game_date", y=["assists", "points"], height=200)


def plot_assist_point_ratio(df_players: pd.DataFrame, df_games: pd.DataFrame, df_rosters: pd.DataFrame, team_id: int) -> None:
	frame = _merge_team_stats(df_players, df_games, df_rosters, team_id)
	summary = frame.groupby("player_first_name", as_index=False).agg(goals=("goals", "sum"), assists=("assists", "sum"), points=("points", "sum"))
	summary = summary[summary["points"] > 0]
	summary["assist_ratio"] = (summary["assists"] / summary["points"] * 100).round(1)
	figure = px.bar(summary.sort_values("assist_ratio", ascending=False), x="player_first_name", y="assist_ratio", title="Assist-to-Point Ratio by Player (%)", labels={"assist_ratio": "Assist %", "player_first_name": "Player"}, color="assist_ratio", color_continuous_scale="blues", text="assist_ratio")
	figure.update_traces(textposition="outside")
	st.plotly_chart(figure)


def plot_season_stats(df_players: pd.DataFrame, df_games: pd.DataFrame, df_rosters: pd.DataFrame, team_id: int, stat: str) -> None:
	if stat not in {"goals", "assists", "points", "penalty_min"}:
		st.warning("Invalid stat for plotting.")
		return
	frame = _merge_team_stats(df_players, df_games, df_rosters, team_id)
	frame = frame[~frame["player_first_name"].str.contains("Guest", na=False)].copy()
	frame[stat] = pd.to_numeric(frame[stat], errors="coerce").fillna(0)
	frame["total_stat"] = frame.groupby("player_first_name")[stat].transform("sum")
	st.plotly_chart(px.treemap(frame, path=["player_first_name"], values="total_stat", title=f"Total {stat.title()} by Player", color="total_stat", color_continuous_scale="reds_r"))
	wide = frame.set_index(["player_first_name", "game_id"])[stat].unstack("game_id").sort_index(axis=1, level=1)
	figure = px.imshow(wide, title=f"Player {stat.title()} by Game", color_continuous_scale=[(0, "black"), (0.7, "#A54848"), (1, "white")], labels={"x": "Game #", "y": "Player", "color": stat.title()})
	figure.update_xaxes(showticklabels=False)
	st.plotly_chart(figure)
