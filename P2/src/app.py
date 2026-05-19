import streamlit as st
import pandas as pd
import numpy as np
import joblib

from collections import defaultdict
from scipy.sparse import hstack, csr_matrix



st.set_page_config(
    page_title="NBA Game Predictor",
    layout="centered"
)


@st.cache_resource
def load_artifacts():
    model = joblib.load("../models/nba_model.pkl")
    encoder = joblib.load("../models/team_encoder.pkl")
    return model, encoder

model, encoder = load_artifacts()
#os @st.cache data metem isto mais rapido

@st.cache_data
def load_data():
    df = pd.read_csv("../datasets/Games.csv")
    df['gameDate'] = pd.to_datetime(df['gameDate'])
    df['winner'] = df['winner'].astype(str)
    df['hometeamId'] = df['hometeamId'].astype(str)
    df['awayteamId'] = df['awayteamId'].astype(str)
    df = df.sort_values('gameDate').reset_index(drop=True)
    return df

df = load_data()




@st.cache_data
def build_team_mappings(df):
    team_to_id = {}
    for _, row in df.iterrows():
        team_to_id[row['hometeamName']] = str(row['hometeamId'])
        team_to_id[row['awayteamName']] = str(row['awayteamId'])
    return team_to_id

team_to_id = build_team_mappings(df)
teams = sorted(df['hometeamName'].unique())


@st.cache_data
def calculate_elo_ratings(df):
    elo = defaultdict(lambda: 1500)
    for _, row in df.iterrows():
        home_team = row['hometeamName']
        away_team = row['awayteamName']
        winner = row['winner']
        home_id = row['hometeamId']
        home_rating = elo[home_team]
        away_rating = elo[away_team]
        expected_home = 1 / (1 + 10 ** ((away_rating - home_rating) / 400))
        actual_home = 1 if winner == home_id else 0
        K = 32
        elo[home_team] += K * (actual_home - expected_home)
        elo[away_team] += K * ((1 - actual_home) - (1 - expected_home))
    return dict(elo)

@st.cache_data
def get_winrate(team, df):
    team_id = team_to_id[team]
    games = df[(df['hometeamName'] == team) | (df['awayteamName'] == team)]
    if len(games) == 0:
        return 0.5
    wins = len(games[games['winner'] == team_id])
    return wins / len(games)

@st.cache_data
def get_recent_form(team, df, last_n=5):
    team_id = team_to_id[team]
    games = df[
        (df['hometeamName'] == team) | (df['awayteamName'] == team)
    ].tail(last_n)
    if len(games) == 0:
        return 0.5
    results = [1 if g['winner'] == team_id else 0 for _, g in games.iterrows()]
    weights = np.arange(1, len(results) + 1)
    return float(np.average(results, weights=weights))

@st.cache_data
def get_win_streak(team, df):
    team_id = team_to_id[team]
    games = df[
        (df['hometeamName'] == team) | (df['awayteamName'] == team)
    ].sort_values('gameDate', ascending=False)
    streak = 0
    for _, game in games.iterrows():
        if game['winner'] == team_id:
            streak += 1
        else:
            break
    return streak

@st.cache_data
def get_head_to_head(home, away, df, last_n=10):
    h2h = df[
        ((df['hometeamName'] == home) & (df['awayteamName'] == away)) |
        ((df['hometeamName'] == away) & (df['awayteamName'] == home))
    ].tail(last_n)
    if len(h2h) == 0:
        return 0, 0
    home_id = team_to_id[home]
    home_wins = len(h2h[h2h['winner'] == home_id])
    return home_wins, len(h2h)

# Precompute ELO once
elo_ratings = calculate_elo_ratings(df)


st.title("NBA Game Outcome Predictor")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Home Team")
    home = st.selectbox("Select Home Team", teams, key="home")

with col2:
    st.subheader("Away Team")
    away_options = [t for t in teams if t != home]
    away = st.selectbox("Select Away Team", away_options, key="away")

is_playoff = st.checkbox("Is it a Playoff Game")

st.divider()

# prev


if home and away:
    h2h_wins, h2h_total = get_head_to_head(home, away, df)
    home_streak = get_win_streak(home, df)
    away_streak = get_win_streak(away, df)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("last 10 between them", f"{h2h_wins}–{h2h_total - h2h_wins}")#
    with c2:
        st.metric(f"{home} Streak", f"{home_streak}W" if home_streak > 0 else "0")
    with c3:
        st.metric(f"{away} Streak", f"{away_streak}W" if away_streak > 0 else "0")

st.divider()

# PREDICTION


if st.button("Predict Winner", use_container_width=True, type="primary"):

    # Team encoding
    team_input = pd.DataFrame([{
        'hometeamName': home,
        'awayteamName': away
    }])
    team_features = encoder.transform(team_input)

    # Numeric features
    home_wr = get_winrate(home, df)
    away_wr = get_winrate(away, df)
    home_form = get_recent_form(home, df)
    away_form = get_recent_form(away, df)
    home_streak_val = get_win_streak(home, df)
    away_streak_val = get_win_streak(away, df)
    home_elo = elo_ratings.get(home, 1500)
    away_elo = elo_ratings.get(away, 1500)

    numeric_features = pd.DataFrame([[
        home_wr, away_wr,
        home_form, away_form,
        1 if is_playoff else 0,
        home_streak_val, away_streak_val,
        home_elo, away_elo
    ]], columns=[
        'home_winrate', 'away_winrate',
        'home_recent_form', 'away_recent_form',
        'is_playoff',
        'home_streak', 'away_streak',
        'home_elo', 'away_elo'
    ])

    numeric_sparse = csr_matrix(numeric_features.values)
    X = hstack([team_features, numeric_sparse])

    prediction = model.predict(X)[0]
    probabilities = model.predict_proba(X)[0]

    home_prob = probabilities[1]
    away_prob = probabilities[0]

    # RESULTS


    winner_name = home if prediction == 1 else away
    st.success(f"Predicted Winner: **{winner_name}**")

    # CPodemos tirar this 
    confidence = max(home_prob, away_prob)
    if confidence >= 0.70:
        st.info("High confidence prediction")
    elif confidence >= 0.55:
        st.info("Moderate confidence prediction")
    else:
        st.warning("Low confidence,this is a very close matchup")

    st.divider()

    # Win probabilities
    st.subheader("Win Probabilities")
    col_h, col_a = st.columns(2)
    with col_h:
        st.metric(home, f"{home_prob:.1%}")
        st.progress(float(home_prob))
    with col_a:
        st.metric(away, f"{away_prob:.1%}")
        st.progress(float(away_prob))

    st.divider()

    # Match insights
    st.subheader("Match Insights")

    insights_df = pd.DataFrame({
        "Metric": [
            "Win Rate", "Recent Form (last 5)",
            "Current Win Streak", "ELO Rating"
        ],
        home: [
            f"{home_wr:.1%}", f"{home_form:.1%}",
            f"{home_streak_val}", f"{home_elo:.0f}"
        ],
        away: [
            f"{away_wr:.1%}", f"{away_form:.1%}",
            f"{away_streak_val}", f"{away_elo:.0f}"
        ]
    })

    st.dataframe(insights_df, use_container_width=True, hide_index=True)

    # Head-to-head recap
    if h2h_total > 0:
        st.divider()
        st.subheader("Head-to-Head History (last 10 games)")
        away_h2h_wins = h2h_total - h2h_wins
        st.write(f"**{home}** won **{h2h_wins}** of their last {h2h_total} matchups against **{away}**")
    else:
        st.info("No head-to-head history available between these teams.")