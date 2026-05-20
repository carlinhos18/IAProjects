import pandas as pd
import numpy as np
import joblib

from collections import defaultdict
from scipy.sparse import hstack, csr_matrix

from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier

#meti estes para comparacoes
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression


from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)
#Aqui nós simplesmente fazemos o loading do dataset e tiramos as colunas que nos interessam e exclui-mos valores null
df = pd.read_csv("../datasets/Games.csv",low_memory=False)
df = df[[
    'gameDate',
    'hometeamName',
    'awayteamName',
    'hometeamId',
    'awayteamId',
    'winner',
    'gameType'
]]
df = df.dropna()
df['gameDate'] = pd.to_datetime(df['gameDate'])
df = df.sort_values('gameDate')#é importante estar ordenado
df['winner'] = df['winner'].astype(str) 
df['hometeamId'] = df['hometeamId'].astype(str)
df['awayteamId'] = df['awayteamId'].astype(str)


#Features
team_stats = {}
recent_results = defaultdict(list)
win_streaks = defaultdict(int)
elo = defaultdict(lambda: 1500)#Provavelmente a nossa melhor feature
home_winrates = []
away_winrates = []
home_recent_form = []
away_recent_form = []
home_elo = []
away_elo = []
home_streak = []
away_streak = []
is_playoff = [] #Playofss nao é o mesmo que uma season ent separei

for _, row in df.iterrows():
    home_team = row['hometeamName']
    away_team = row['awayteamName']
    home_id = row['hometeamId']
    away_id = row['awayteamId']
    winner = row['winner']


    #Init basicamente
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

    home_wr = (
        home_wins / home_games
        if home_games > 0 else 0.5
    )

    away_wr = (
        away_wins / away_games
        if away_games > 0 else 0.5
    )

    home_winrates.append(home_wr)
    away_winrates.append(away_wr)

   
    #Os jogos mais recentes importam mais que os antigos
    home_history = recent_results[home_team][-5:]
    away_history = recent_results[away_team][-5:]

    home_weights = np.arange(1, len(home_history) + 1)
    away_weights = np.arange(1, len(away_history) + 1)

    home_form = (
        np.average(home_history, weights=home_weights)
        if home_history else 0.5
    )

    away_form = (
        np.average(away_history, weights=away_weights)
        if away_history else 0.5
    )

    home_recent_form.append(home_form)
    away_recent_form.append(away_form)

    # A sucessão de vitorias é interessante

    home_streak.append(win_streaks[home_team])
    away_streak.append(win_streaks[away_team])

    # Lembrei me do Xadrez lol

    home_rating = elo[home_team]
    away_rating = elo[away_team]
    home_elo.append(home_rating)
    away_elo.append(away_rating)

    is_playoff.append(
        1 if row['gameType'] == 'Playoffs' else 0
    )
    team_stats[home_team]['games'] += 1
    team_stats[away_team]['games'] += 1

 
    # Update dos elos

    expected_home = 1 / (
        1 + 10 ** ((away_rating - home_rating) / 400)
    )
    actual_home = 1 if winner == home_id else 0
    elo[home_team] += 32 * (actual_home - expected_home)
    elo[away_team] += 32 * (  (1 - actual_home) - (1 - expected_home) )

    # Resultados

    if winner == home_id:

        team_stats[home_team]['wins'] += 1
        recent_results[home_team].append(1)
        recent_results[away_team].append(0)
        win_streaks[home_team] += 1
        win_streaks[away_team] = 0

    else:

        team_stats[away_team]['wins'] += 1
        recent_results[home_team].append(0)
        recent_results[away_team].append(1)
        win_streaks[away_team] += 1
        win_streaks[home_team] = 0


#Guardar tudo
df['home_winrate'] = home_winrates
df['away_winrate'] = away_winrates
df['home_recent_form'] = home_recent_form
df['away_recent_form'] = away_recent_form
df['home_elo'] = home_elo
df['away_elo'] = away_elo
df['home_streak'] = home_streak
df['away_streak'] = away_streak
df['is_playoff'] = is_playoff


df['target'] = (
    df['winner'] == df['hometeamId']
).astype(int)

#Os modelos nao lem strings so numeros, E este encoder é boa pratica

team_encoder = OneHotEncoder(handle_unknown='ignore')

team_features = team_encoder.fit_transform(
    df[['hometeamName', 'awayteamName']]
)

numeric_features = df[[
    'home_winrate',
    'away_winrate',
    'home_recent_form',
    'away_recent_form',
    'is_playoff',
    'home_streak',
    'away_streak',
    'home_elo',
    'away_elo'

]]

numeric_sparse = csr_matrix(numeric_features.values)
X = hstack([team_features, numeric_sparse])
y = df['target'].values

#Features que nao sao propriamente valores
team_feature_names = team_encoder.get_feature_names_out([
    'hometeamName',
    'awayteamName'
])

numeric_feature_names = numeric_features.columns.tolist()

feature_names = list(team_feature_names) + numeric_feature_names
#isto e onde treinamos

split_index = int(len(df) * 0.8)
#Isto funciona assim Temos 10000 jogos, vamos testar nos primeiros80% dado isto estar por data e testamos o modelo nos 20% restantes

X_train = X[:split_index]
X_test = X[split_index:]

y_train = y[:split_index]
y_test = y[split_index:]

#300 arvores de profundidade max de 12,o random_state é para ser reproducivel, o balanced compensa caso home wins >> away wins. e
model1 = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=5,
    class_weight='balanced',
    random_state=42
)

model2 = GradientBoostingClassifier(
    n_estimators=300,
    max_depth=5, 
    min_samples_split=5,
    random_state=42
)

model3 = LogisticRegression(
    max_iter=1500,
    class_weight='balanced',
    solver='liblinear',
    random_state=42
)


#multi train so para ser mais facil
models = {
    'Random_Forest':model1,
    'Gradient_Boost':model2,
    'Logistic_Reg':model3
}

#model.fit(X_train, y_train)
trained_models = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    trained_models[name] = model
    print(f"\nModel {name} trained")

#Avalir modelo

for name, model in trained_models.items():

    print(f"{name} predictions:")
    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)

    print("\nAccuracy:")
    print(accuracy)

    print("\nClassification Report:")
    print(classification_report(y_test, predictions))

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))

#Isto é para a UI
#Basciamente perguntamos ao modelo que featues é que ele usou para decioes
feature_importance = pd.DataFrame({

    'Feature': feature_names,
    'Importance': model1.feature_importances_

})

feature_importance = feature_importance.sort_values(
    by='Importance',
    ascending=False
)

print("\nTop Features:")
print(feature_importance.head(20))

#Guardar modelos para meter no app.py

for name, model in trained_models.items():
    joblib.dump(model, f"../models/{name}_nba_model.pkl")



joblib.dump(team_encoder, "../models/team_encoder.pkl")
joblib.dump(feature_names, "../models/feature_names.pkl")
print("\nArtifacts saved successfully.")
