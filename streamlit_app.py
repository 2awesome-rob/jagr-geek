"""Streamlit entry point for the Jagr hockey statistics dashboard."""

import pandas as pd
import streamlit as st

from app.main import (
	display_game_log,
	display_game_table,
	display_season_total_stats,
	display_summary_stats,
	display_team_record,
	plot_assist_point_ratio,
	plot_game_log,
	plot_season_stats,
	summarize_team_games,
)
from app.database.api import load_dfs_from_database


st.set_page_config(page_title="SimpleHockeyStat", page_icon="🏒")


@st.cache_data
def load_dashboard_data(season: int):
	"""Cache the database read while allowing DATABASE_URL to select the backend."""
	return load_dfs_from_database(season)


st.title("🏒 HockeyStat Dashboard", help="Hockey Team and Player Statistics Tracker")
selected_season = 2026
st.session_state.season = selected_season

try:
	df_teams, df_rosters, df_games, df_players, df_goalies = load_dashboard_data(selected_season)
except Exception as error:
	st.error(f"Unable to load hockey data: {error}")
	st.stop()

col01, col02 = st.columns(2)
team_map: dict[int, str] = {}
selected_team_id: int | None = None

if df_teams.empty or df_rosters.empty:
	st.info("No teams found for the selected season")
	df_selected_games = df_games
	selected_game_ids = df_selected_games["game_id"].unique() if "game_id" in df_selected_games else []
else:
	team_map = df_teams.set_index("team_id")["team_name"].to_dict()
	#team_options = sorted(df_teams["team_name"].dropna().unique().tolist(), reverse=True)
	team_options = df_teams["team_name"].dropna().tolist()
	with col01:
		selected_team_name = st.selectbox("Selected Team", team_options, index=1, disabled=True)
	selected_team_id = int(df_teams.loc[df_teams["team_name"] == selected_team_name, "team_id"].iloc[0])
	st.session_state.team_name = selected_team_name
	st.session_state.team_id = selected_team_id

	with col02:
		selected_league_plays = st.pills(
			"League Play",
			["League", "Tournament", "PostSeason", "PreSeason"],
			selection_mode="multi",
			default=["League", "Tournament", "PostSeason", "PreSeason"],
		)
	st.session_state.league_play = selected_league_plays
	game_type_map = {"League": 1, "Tournament": 2, "PreSeason": 4, "PostSeason": 3}
	selected_game_types = [game_type_map[label] for label in selected_league_plays]
	df_selected_games = df_games[df_games["game_type_id"].isin(selected_game_types)] if selected_game_types else df_games.iloc[0:0]
	selected_game_ids = df_selected_games["game_id"].unique()

team_games = pd.DataFrame()
if selected_team_id is not None and not df_selected_games.empty:
	team_games = summarize_team_games(df_selected_games, selected_team_id)

tabs = st.tabs(["Team", "Players", "Plots", "About"])

with tabs[0]:
	if selected_team_id is None:
		st.info("Select a team to view its dashboard.")
	else:
		st.subheader(f"{st.session_state.team_name} Overview", divider="red")
		if team_games.empty:
			st.info("No games found for this season.")
		else:
			st.badge("Team Record", color="red")
			display_team_record(team_games)
			st.badge("Goalie Stats", color="red")
			display_season_total_stats(df_goalies, team_games, df_rosters, selected_team_id)
			st.badge("Skater Stats", color="red")
			display_season_total_stats(df_players, team_games, df_rosters, selected_team_id)
			st.badge("Games Log", color="red")
			display_game_table(team_games.head(20), team_map)

with tabs[1]:
	if selected_team_id is None:
		st.info("Select a team to view players.")
	else:
		team_players = df_rosters[df_rosters["team_id"] == selected_team_id]
		player_options = sorted([name for name in team_players["player_first_name"].dropna() if "Guest" not in name], reverse=True)
		if not player_options:
			st.info("No roster data available.")
		else:
			selected_player_name = st.selectbox("Select player", player_options)
			player = team_players[team_players["player_first_name"] == selected_player_name].iloc[0]
			selected_player_id = int(player["player_id"])
			st.subheader(f"#{int(player['player_jersey'])}   {selected_player_name} ({player['position']})", divider="red")

			goalie_stats = df_goalies[(df_goalies["player_id"] == selected_player_id) & df_goalies["game_id"].isin(selected_game_ids)]
			if not goalie_stats.empty:
				display_summary_stats(goalie_stats, df_goalies)
				display_game_log(goalie_stats, df_selected_games)
				if len(goalie_stats) > 3:
					plot_game_log(goalie_stats, df_selected_games)

			player_stats = df_players[(df_players["player_id"] == selected_player_id) & df_players["game_id"].isin(selected_game_ids)]
			if player_stats.empty:
				st.info("No skater game stats available for this player.")
			else:
				display_summary_stats(player_stats, df_players)
				display_game_log(player_stats, df_selected_games)
				if len(player_stats) > 3:
					plot_game_log(player_stats, df_selected_games)

with tabs[2]:
	if selected_team_id is None or df_players.empty or team_games.empty:
		st.info("No stats available for plotting.")
	else:
		stat = st.radio("Select Statistic", ["goals", "assists", "points", "penalty_min"], index=1, label_visibility="collapsed", horizontal=True)
		plot_season_stats(df_players, team_games, df_rosters, selected_team_id, stat)
		if stat in {"assists", "points"}:
			st.badge("Assist-to-Point Ratio", color="blue")
			plot_assist_point_ratio(df_players, team_games, df_rosters, selected_team_id)

with tabs[3]:
	st.write("League Standing and Schedule:")
	st.link_button("🏙️ PNAHA", "https://stats.pnaha.timetoscore.com//display-stats.php?league=1")
	st.markdown("---")
	st.header("12U A2 Rocket Systems 🐶 🦊 🦅")
	col31, col32, col33 = st.columns(3)
	with col31:
		st.link_button("✏️ 1-2-2 Forecheck", "https://www.youtube.com/watch?app=desktop&v=cOR--Fi5KoU&ra=m")
		st.link_button("📽️ 1-2-2 Forecheck", "https://www.youtube.com/watch?app=desktop&v=8URiYylC7lc&ra=m")
	with col32:
		st.link_button("✏️ Breakout", "https://www.youtube.com/watch?v=Lb5OfNvu3FM")
		st.link_button("✏️ Breakout", "https://www.youtube.com/watch?v=Tnwe87WvCpc")
	with col33:
		st.link_button("📽️ Breakout", "https://www.youtube.com/watch?v=4sMlLFmDd1Q")
		st.link_button("📽️ Breakout", "https://www.youtube.com/watch?v=-CvoplULOZw")
	
	st.markdown("---")
	st.write("Other Hockey Links:")
	st.link_button("🏒 Strategy", "https://blueseatblogs.com/hockey-systems-strategy/")
	st.link_button("🧩 Drills and Practice", "https://www.icehockeysystems.com/hockey-drills/drill-category/small-area-games")
	st.link_button("📘 Playbook", "https://www.jes-hockey.com/")
	st.markdown("---")
	st.write("Rob's simple Streamlit app used to query and display team and player statistics from a database.")
	st.write("Apache License Version 2.0, January 2004")
