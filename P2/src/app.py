import streamlit as st
import pandas as pd
import joblib

# Load model + encoder
model = joblib.load("../models/nba_model.pkl")
encoder = joblib.load("../models/team_encoder.pkl")

# Load dataset (para estatísticas simples)
df = pd.read_csv("../datasets/Games.csv")

teams = sorted(df['hometeamName'].unique())

st.title("NBA Winner Predictor")

home = st.selectbox("Home Team", teams)
away = st.selectbox("Away Team", teams)
if home == away:
    st.warning("Same team selected. Adjusting away team automatically.")
    away = st.selectbox(
        "Away Team (auto-adjusted)",
        [t for t in teams if t != home]
    )
def get_winrate(team):
    games = df[(df['hometeamName'] == team) | (df['awayteamName'] == team)]
    wins = games[games['winner'] == team]
    if len(games) == 0:
        return 0.5
    return len(wins) / len(games)

if st.button("Predict Winner"):

    home_enc = encoder.transform([home])[0]
    away_enc = encoder.transform([away])[0]

    home_wr = get_winrate(home)
    away_wr = get_winrate(away)

    # recent form simplificada
    home_form = home_wr
    away_form = away_wr

    X = pd.DataFrame([[
        home_enc,
        away_enc,
        home_wr,
        away_wr,
        home_form,
        away_form
    ]], columns=[
        "home_team_encoded",
        "away_team_encoded",
        "home_winrate",
        "away_winrate",
        "home_recent_form",
        "away_recent_form"
    ])

    pred = model.predict(X)[0]
    prob = model.predict_proba(X)[0]

    if pred == 1:
        st.success(f"Winner predicted: {home}")
    else:
        st.success(f"Winner predicted: {away}")

    st.write(f"Home probability: {prob[1]:.2f}")
    st.write(f"Away probability: {prob[0]:.2f}")