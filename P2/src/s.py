# train.py

import pandas as pd
import numpy as np
import joblib
import streamlit as st
from collections import defaultdict

from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# =========================================================
# 1. LOAD DATASET
# =========================================================

df = pd.read_csv("../datasets/Games.csv")


# IMPORTANT:
# Do NOT use homeScore or awayScore directly
# because they reveal the result of the game.

df = df[[
    'gameDate',
    'hometeamName',
    'awayteamName',
    'hometeamId',
    'awayteamId',
    'winner'
]]
print(set(df["hometeamName"]+df["awayteamName"]))
# Remove missing values
df = df.dropna()



# Convert dates
df['gameDate'] = pd.to_datetime(df['gameDate'])

# Sort chronologically
df = df.sort_values('gameDate')

# Ensure IDs have same datatype
df['winner'] = df['winner'].astype(str)
df['hometeamId'] = df['hometeamId'].astype(str)
df['awayteamId'] = df['awayteamId'].astype(str)


team_stats = {}

# Recent form tracking
recent_results = defaultdict(list)

# Feature lists
home_winrates = []
away_winrates = []

home_recent_form = []
away_recent_form = []



for _, row in df.iterrows():

    home_team = row['hometeamName']
    away_team = row['awayteamName']

    home_id = row['hometeamId']
    away_id = row['awayteamId']

    winner = row['winner']



    if home_team not in team_stats:
        team_stats[home_team] = {
            'wins': 0,
            'games': 0
        }

    if away_team not in team_stats:
        team_stats[away_team] = {
            'wins': 0,
            'games': 0
        }


    home_games = team_stats[home_team]['games']
    away_games = team_stats[away_team]['games']

    home_wins = team_stats[home_team]['wins']
    away_wins = team_stats[away_team]['wins']

    home_winrate = (
        home_wins / home_games
        if home_games > 0 else 0.5
    )

    away_winrate = (
        away_wins / away_games
        if away_games > 0 else 0.5
    )

    home_winrates.append(home_winrate)
    away_winrates.append(away_winrate)



    home_history = recent_results[home_team][-5:]
    away_history = recent_results[away_team][-5:]

    home_form = np.mean(home_history) if home_history else 0.5
    away_form = np.mean(away_history) if away_history else 0.5

    home_recent_form.append(home_form)
    away_recent_form.append(away_form)


    team_stats[home_team]['games'] += 1
    team_stats[away_team]['games'] += 1

    # Home team wins
    if winner == home_id:

        team_stats[home_team]['wins'] += 1

        recent_results[home_team].append(1)
        recent_results[away_team].append(0)

    # Away team wins
    else:

        team_stats[away_team]['wins'] += 1

        recent_results[home_team].append(0)
        recent_results[away_team].append(1)



df['home_winrate'] = home_winrates
df['away_winrate'] = away_winrates

df['home_recent_form'] = home_recent_form
df['away_recent_form'] = away_recent_form


# 1 = home team wins
# 0 = away team wins

df['target'] = (
    df['winner'] == df['hometeamId']
).astype(int)

# 7. ENCODE TEAM NAMES

# ML models cannot understand text directly

all_teams = pd.concat([
    df['hometeamName'],
    df['awayteamName']
])

team_encoder = LabelEncoder()

team_encoder.fit(all_teams)

df['home_team_encoded'] = team_encoder.transform(
    df['hometeamName']
)

df['away_team_encoded'] = team_encoder.transform(
    df['awayteamName']
)



X = df[[
    'home_team_encoded',
    'away_team_encoded',
    'home_winrate',
    'away_winrate',
    'home_recent_form',
    'away_recent_form'
]]

y = df['target']


split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


model = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=5,
    class_weight='balanced',
    random_state=42
)

model.fit(X_train, y_train)

print("\nModel trained")



predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nAccuracy:")
print(accuracy)

print("\nClassification Report:")
print(classification_report(y_test, predictions))


cm = confusion_matrix(y_test, predictions)

print("\nConfusion Matrix:")
print(cm)


print("\nFeature Importances:")

for feature, importance in zip(X.columns, model.feature_importances_):
    print(f"{feature}: {importance:.4f}")



joblib.dump(model, "../models/nba_model.pkl")

joblib.dump(team_encoder, "../models/team_encoder.pkl")

