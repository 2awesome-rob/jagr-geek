"""Reusable streamlit rendering helpers for the plots dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from app.utils.helpers import ( merge_team_stats, active_rows )

def plot_game_log(game_log_df: pd.DataFrame, df_games: pd.DataFrame) -> None:
	frame = active_rows(game_log_df).merge(
		df_games.reset_index(drop=True),
		on="game_id",
		how="left",
		suffixes=("", "_game"),
	)
	frame = frame.sort_values("game_date", ascending=False)
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date

	if "shots_on" in frame.columns:
		frame["Save %"] = np.where(frame["shots_on"] > 0, frame["saves"] / frame["shots_on"], np.nan)
		st.line_chart(frame, x="game_date", y="Save %", height=120)
	else:
		st.line_chart(frame, x="game_date", y=["assists", "points"], height=200)


def plot_assist_point_ratio(df_players: pd.DataFrame, df_games: pd.DataFrame, df_rosters: pd.DataFrame, team_id: int) -> None:
	frame = merge_team_stats(df_players, df_games, df_rosters, team_id)
	if frame.empty:
		st.info("No stats available for assist/point ratio.")
		return

	summary = frame.groupby("player_first_name", as_index=False).agg(
		goals=("goals", "sum"),
		assists=("assists", "sum"),
		points=("points", "sum"),
	)
	summary = summary[summary["points"] > 0]
	summary["assist_ratio"] = (summary["assists"] / summary["points"] * 100).round(1)

	figure = px.bar(
		summary.sort_values("assist_ratio", ascending=False),
		x="player_first_name",
		y="assist_ratio",
		title="Assist-to-Point Ratio by Player (%)",
		labels={"assist_ratio": "Assist %", "player_first_name": "Player"},
		color="assist_ratio",
		color_continuous_scale="blues",
		text="assist_ratio",
	)
	figure.update_traces(textposition="outside")
	st.plotly_chart(figure)


def plot_season_stats(df_players: pd.DataFrame, df_games: pd.DataFrame, df_rosters: pd.DataFrame, team_id: int, stat: str) -> None:
	if stat not in {"goals", "assists", "points", "penalty_min"}:
		st.warning("Invalid stat for plotting.")
		return

	frame = merge_team_stats(df_players, df_games, df_rosters, team_id)
	if frame.empty:
		st.info("No stats available for plotting.")
		return

	frame = frame[~frame["player_first_name"].str.contains("Guest", na=False)].copy()
	frame[stat] = pd.to_numeric(frame[stat], errors="coerce").fillna(0)
	frame["total_stat"] = frame.groupby("player_first_name")[stat].transform("sum")

	st.plotly_chart(
		px.treemap(
			frame,
			path=["player_first_name"],
			values="total_stat",
			title=f"Total {stat.title()} by Player",
			color="total_stat",
			color_continuous_scale=[(0, "black"), (0.5, "#36D6DB"), (1, "white")],
		)
	)

	wide = (
		frame.set_index(["player_first_name", "game_id"])[stat]
		.unstack("game_id")
		.sort_index(axis=1, level=0)
	)
	figure = px.imshow(
		wide,
		title=f"Player {stat.title()} by Game",
		color_continuous_scale=[(0, "black"), (0.5, "#36D6DB"), (1, "white")],
		labels={"x": "Game #", "y": "Player", "color": stat.title()},
	)
	figure.update_xaxes(showticklabels=False)
	st.plotly_chart(figure)
