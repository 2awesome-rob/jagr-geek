"""Reusable Streamlit rendering helpers for the player dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd

import streamlit as st

from app.utils.helpers import (
	merge_team_stats,
	active_rows
)

def display_summary_stats(stats_df: pd.DataFrame, full_df: pd.DataFrame) -> None:
    """Render full player/goalie summary including medals, per-game averages, and special events."""
    frame = active_rows(stats_df.copy()).reset_index(drop=True)
    if frame.empty:
        st.info("No active statistics available.")
        return

    # -----------------------------
    # GOALIE SUMMARY
    # -----------------------------
    if "shots_on" in frame.columns or "shots_faced" in frame.columns:
        # Normalize goalie column names
        shots = int(frame.get("shots_on", frame.get("shots_faced", 0)).sum())
        saves = int(frame.get("saves", 0).sum())
        goals_allowed = int(pd.to_numeric(frame.get("goals_against", 0), errors="coerce").fillna(0).sum())

        result = frame.get("result", pd.Series(dtype=str)).astype(str).str.upper()

        wins = int((result == "W").sum())
        losses = int((result == "L").sum())

        # Shutouts: only count if goalie was the ONLY active goalie in that game
        shutouts = 0
        shutout_games = frame.loc[(result == "W") & (frame.get("goals_against", 0) == 0), "game_id"].unique()
        for gid in shutout_games:
            if full_df.groupby("game_id")["active"].sum().loc[gid] == 1:
                shutouts += 1

        save_pct = round(saves / shots, 3) if shots > 0 else None

        # Leader badges (🥇🥈🥉)
        p_id = frame["player_id"].iloc[0]
        leader_for = []
        if "goalie_leader" in st.session_state:
            for stat_name, leader_id in st.session_state.goalie_leader.items():
                if leader_id == p_id:
                    leader_for.append((stat_name, "🥇"))

        def badge(stat):
            for name, b in leader_for:
                if stat.lower() in name.lower():
                    return b
            return ""

        st.badge("Goalie Stats", color="red")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("W " + badge("win"), wins, delta=f"{shutouts} Shutouts" if shutouts else None)
        c2.metric("L", losses)
        c3.metric("Shots On", shots)
        c4.metric("Saves", saves)
        c5.metric("Save % " + badge("save"), f"{save_pct*100:.1f}%" if save_pct is not None else "N/A")
        return

    # -----------------------------
    # SKATER SUMMARY
    # -----------------------------
    games = frame["game_id"].nunique()
    goals = int(frame["goals"].sum())
    assists = int(frame["assists"].sum())
    points = int(frame.get("points", frame["goals"] + frame["assists"]).sum())
    pim = int(pd.to_numeric(frame.get("penalty_min", 0), errors="coerce").fillna(0).sum())

    # Special events
    hat_tricks = frame[frame["goals"] >= 3].shape[0]
    playmakers = frame[frame["assists"] >= 3].shape[0]

    # Per-game averages
    gpg = round(goals / games, 2) if games else 0.0
    apg = round(assists / games, 2) if games else 0.0
    ppg = round(points / games, 2) if games else 0.0
    pimpg = round(pim / games, 2) if games else 0.0

    # Assist-per-point ratio
    app = round(assists / points, 2) if points > 0 else None

    # Hot/cold streak logic
    fire = 0.0
    great_game = False
    if games > 3:
        last_two = frame["points"].iloc[-2:].mean()
        prev = frame["points"].iloc[:-2].mean()
        fire = last_two - prev

        # Cool down if last game was scoreless
        if frame["points"].iloc[-1] == 0:
            fire = min(0.0, fire)
        # Heat up if last game was strong
        elif frame["points"].iloc[-1] >= prev:
            fire = max(0.0, fire)

        great_game = frame["points"].iloc[-1] > prev + 1

    # Leader medals (🥇🥈🥉)
    p_id = frame["player_id"].iloc[0]
    leader_for = []
    badges = ["🥇", "🥈", "🥉"]
    if "leader" in st.session_state:
        for stat_name, leaders_list in st.session_state.leader.items():
            if isinstance(leaders_list, list):
                for player_id, medal_rank in leaders_list:
                    if player_id == p_id and medal_rank < len(badges):
                        leader_for.append((stat_name, badges[medal_rank]))

    def badge(stat):
        for name, b in leader_for:
            if stat.lower() in name.lower():
                return b
        return ""

    # -----------------------------
    # Render skater metrics
    # -----------------------------
    st.badge("Skater Stats", color="red")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Games", games)
    c2.metric("Goals" + badge("goals"), goals, delta=f"{hat_tricks} HatTricks" if hat_tricks else None)
    c3.metric("Assists" + badge("assists"), assists, delta=f"{playmakers} PlayMakers" if playmakers else None)
    c4.metric("Points" + badge("points"), points)
    c5.metric("PIM", pim)

    st.markdown("---")

    c6, c7, c8, c9, c10 = st.columns(5)
    if great_game:
        c6.metric("Great Game!", "🌟")
    elif fire > 0.5:
        c6.metric("Hot Streak", "🔥")
    elif fire < -0.5:
        c6.metric("Cool Streak", "🧊")
    else:
        c6.metric("Per Game:", "🏒")

    c7.metric("GPG" + badge("GPG"), gpg)
    c8.metric("APG" + badge("APG"), apg)
    c9.metric("PPG" + badge("PPG"), ppg)
    if app is not None:
        c10.metric("Assist/Point" + badge("APP"), app)


def display_game_log(game_log_df: pd.DataFrame, df_games: pd.DataFrame) -> None:
	frame = active_rows(game_log_df).merge(
		df_games.reset_index(drop=True),
		on="game_id",
		how="left",
		suffixes=("", "_game"),
	)
	frame = frame.sort_values("game_date", ascending=False)
	frame["game_date"] = pd.to_datetime(frame["game_date"]).dt.date

	if "shots_on" in frame.columns:
		columns = ["game_date", "result", "shots_on", "saves", "goals_against"]
		names = {"game_date": "Date", "result": "W/L", "shots_on": "SOG", "goals_against": "Goals"}
	else:
		columns = ["game_date", "goals", "assists", "points", "penalty_min"]
		names = {"game_date": "Date", "goals": "Goals", "assists": "Assists", "points": "Points", "penalty_min": "PIM"}

	st.dataframe(frame.head(4)[columns].rename(columns=names), hide_index=True)


def display_season_total_stats(stats: pd.DataFrame, games: pd.DataFrame, rosters: pd.DataFrame, team_id: int) -> None:
	frame = merge_team_stats(stats, games, rosters, team_id)
	if frame.empty:
		st.info("No season statistics available.")
		return

	frame = frame[frame["active"].astype(bool)].reset_index(drop=True)
	df = frame.copy()

	# ---------------- GOALIES ----------------
	if "shots_on" in frame.columns or "shots_faced" in frame.columns:
		df["result"] = df.get("result", "").astype(str)
		df["wins"] = df["result"].str.upper().eq("W").astype(int)
		df["losses"] = df["result"].str.upper().eq("L").astype(int)
		df["shots_faced"] = pd.to_numeric(
			df.get("shots_faced", df.get("shots_on", 0)),
			errors="coerce"
        ).fillna(0).astype(int)
		df["goals_against"] = pd.to_numeric(df.get("goals_against", 0), errors="coerce").fillna(0).astype(int)

		df["save_pct"] = np.where(df["shots_faced"] > 0, df["saves"] / df["shots_faced"], np.nan)

		df_leaders = df.groupby("player_id", as_index=False).agg({
			"active": "sum",
			"wins": "sum",
			"losses": "sum",
			"shots_faced": "sum",
			"saves": "sum",
			"goals_against": "sum",
			"save_pct": "mean"
		})

		df_leaders = df_leaders[df_leaders["active"] != 0]

		_team_leaders(df_leaders, "G")

		totals = frame.groupby("player_first_name", as_index=False).agg(
			Games=("active", "sum"), W=("is_win", "sum"), L=("is_loss", "sum"),
			SOG=("shots_on", "sum"), Saves=("saves", "sum"), Goals=("goals_against", "sum"),
		)
		totals["Save %"] = np.where(totals["SOG"] > 0, totals["Saves"] / totals["SOG"], np.nan)
		st.dataframe(
			totals.rename(columns={"player_first_name": "Goalie"}).sort_values("W", ascending=False),
			hide_index=True,
		)
	else:
		# ---------------- SKATERS ----------------
		df_leaders = df.groupby("player_id", as_index=False).agg({
			"active": "sum", "goals": "sum", "assists": "sum", "points": "sum"
		})
		df_leaders = df_leaders[df_leaders["active"] != 0]

		_team_leaders(df_leaders, "S")

		totals = frame.groupby("player_first_name", as_index=False).agg(
			Games=("active", "sum"), Goals=("goals", "sum"), Assists=("assists", "sum"),
			Points=("points", "sum"), PIM=("penalty_min", "sum"),
		)
		st.dataframe(
			totals.rename(columns={"player_first_name": "Player"}).sort_values("Points", ascending=False),
			hide_index=True,
		)

	return

def _top3(df: pd.DataFrame, metric_fn):
	"""
	Returns list of (player_id, medal_rank) tuples.
	medal_rank: 0=gold, 1=silver, 2=bronze
	Tie-aware, max 6 medals total.
	"""
	if df.empty:
		return []

	s = metric_fn(df).replace([np.inf, -np.inf], np.nan).fillna(0)
	dfm = df.assign(_metric=s)
	dfm = dfm[dfm["_metric"] > 0]  # only non-zero stats qualify

	if dfm.empty:
		return []

	result = []
	medal_rank = 0
	medals_awarded = 0
	max_medals = 6
	max_tiers = 3  # gold/silver/bronze

	unique_vals = sorted(dfm["_metric"].unique(), reverse=True)

	for val in unique_vals:
		if medals_awarded >= max_medals or medal_rank >= max_tiers:
			break

		players = dfm[dfm["_metric"] == val]["player_id"].tolist()

		for pid in players:
			if medals_awarded >= max_medals:
				break
			result.append((pid, medal_rank))
			medals_awarded += 1

		medal_rank += 1

	return result

def _team_leaders(df: pd.DataFrame, pos: str):
	"""
	Stores leader medals in st.session_state.leader or st.session_state.goalie_leader.
	"""
	if "leader" not in st.session_state:
		st.session_state.leader = {}
	if "goalie_leader" not in st.session_state:
		st.session_state.goalie_leader = {}

	# ---------------- GOALIES ----------------
	if pos == "G":
		df = df[df["shots_faced"] >= 5]  # minimum SOG to qualify

		if not df.empty:
			# Save %
			best_save = df["save_pct"].max()
			st.session_state.goalie_leader["save"] = df.loc[df["save_pct"] == best_save, "player_id"].iloc[0]

			# Wins
			best_wins = df["wins"].max()
			st.session_state.goalie_leader["wins"] = df.loc[df["wins"] == best_wins, "player_id"].iloc[0]

		return

	# ---------------- SKATERS ----------------
	# Points, Goals, Assists
	st.session_state.leader["points"] = _top3(df, lambda d: d["points"])
	st.session_state.leader["goals"]  = _top3(df, lambda d: d["goals"])
	st.session_state.leader["assists"] = _top3(df, lambda d: d["assists"])

	# Minimum activity threshold - at least 25% of games
	df["active"] = pd.to_numeric(df["active"], errors="coerce").fillna(0).astype(int)
	df_active = df[df["active"] >= df["active"].max() / 4]

	# Per-game metrics
	st.session_state.leader["PPG"] = _top3(df_active, lambda d: d["points"] / d["active"])
	st.session_state.leader["GPG"] = _top3(df_active, lambda d: d["goals"] / d["active"])
	st.session_state.leader["APG"] = _top3(df_active, lambda d: d["assists"] / d["active"])
	st.session_state.leader["APP"] = _top3(df_active, lambda d: pd.Series(np.where(d["points"] > 0, d["assists"] / d["points"], 0), index=d.index))



