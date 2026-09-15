
import streamlit as st
import pandas as pd

def merge_team_stats(stats: pd.DataFrame, games: pd.DataFrame, rosters: pd.DataFrame, team_id: int) -> pd.DataFrame:
	"""Merge stats with games and rosters for a given team, using flat, normalized frames."""
	stats = stats.reset_index(drop=True).copy()
	games = games.reset_index(drop=True).copy()
	rosters = rosters.reset_index(drop=True).copy()

	# Ensure required columns exist
	for df, name, cols in (
		(stats, "stats", ["game_id", "player_id"]),
		(games, "games", ["game_id"]),
		(rosters, "rosters", ["player_id", "team_id", "player_first_name"]),
	):
		missing = [c for c in cols if c not in df.columns]
		if missing:
			st.warning(f"Missing columns in {name} DataFrame: {missing}")
			return stats.iloc[0:0]

	# Merge stats with games on game_id
	frame = stats.merge(
		games[["game_id"]],
		on="game_id",
		how="inner",
	)

	# Merge with roster info on player_id
	frame = frame.merge(
		rosters[["player_id", "team_id", "player_first_name"]],
		on="player_id",
		how="left",
	)

	# Filter for the selected team
	return frame[frame["team_id"] == team_id].reset_index(drop=True)



def active_rows(frame: pd.DataFrame) -> pd.DataFrame:
	frame = frame.reset_index(drop=True)
	if "active" not in frame.columns:
		return frame
	values = frame["active"]
	if values.dtype == bool:
		return frame[values.fillna(False)]
	return frame[pd.to_numeric(values, errors="coerce").fillna(0) != 0]


