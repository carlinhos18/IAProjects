import pandas as pd
import numpy as np
import joblib
import plotly.express as px
from collections import defaultdict
from scipy.sparse import hstack, csr_matrix

from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix


df = pd.read_csv("../datasets/Games.csv", low_memory=False)
df_synt=pd.read_csv("../datasets/GamesFake.csv", low_memory=False)
df = pd.concat([df, df_synt], ignore_index=True)
df = df[[
    'gameDate',
    'hometeamName',
    'awayteamName',
    'hometeamId',
    'awayteamId',
    'winner',
    'gameType',
]]

df = df.dropna()
df['gameDate']    = pd.to_datetime(df['gameDate'])
df = df.sort_values('gameDate')   # ordenação cronológica é essencial para não haver data leakage!

df['winner']     = df['winner'].astype(str)
df['hometeamId'] = df['hometeamId'].astype(str)
df['awayteamId'] = df['awayteamId'].astype(str)

# Todas as features são calculadas ANTES de cada jogo (usando apenas informação passada),

team_stats     = {}
recent_results = defaultdict(list)
win_streaks    = defaultdict(int)
elo            = defaultdict(lambda: 1500)  # Roubado do xadre

home_winrates    = []
away_winrates    = []
home_recent_form = []
away_recent_form = []
home_elo         = []
away_elo         = []
home_streak      = []
away_streak      = []
is_playoff       = []

for _, row in df.iterrows():
    home_team = row['hometeamName']
    away_team = row['awayteamName']
    home_id   = row['hometeamId']
    away_id   = row['awayteamId']
    winner    = row['winner']

    # init
    for team in (home_team, away_team):
        if team not in team_stats:
            team_stats[team] = {'wins': 0, 'games': 0}

    home_games = team_stats[home_team]['games']
    away_games = team_stats[away_team]['games']
    home_wins  = team_stats[home_team]['wins']
    away_wins  = team_stats[away_team]['wins']

    home_wr = home_wins / home_games if home_games > 0 else 0.5
    away_wr = away_wins / away_games if away_games > 0 else 0.5

    home_winrates.append(home_wr)
    away_winrates.append(away_wr)

    #Isto tem haver ocm o facto de os jogos mais recentes importarem mais q os mais antigos
    home_history = recent_results[home_team][-5:]
    away_history = recent_results[away_team][-5:]

    home_weights = np.arange(1, len(home_history) + 1)
    away_weights = np.arange(1, len(away_history) + 1)

    home_form = np.average(home_history, weights=home_weights) if home_history else 0.5
    away_form = np.average(away_history, weights=away_weights) if away_history else 0.5

    home_recent_form.append(home_form)
    away_recent_form.append(away_form)

    
    home_streak.append(win_streaks[home_team])
    away_streak.append(win_streaks[away_team])

    home_rating = elo[home_team]
    away_rating = elo[away_team]

    home_elo.append(home_rating)
    away_elo.append(away_rating)

    #Ha diferenca nos playofs
    is_playoff.append(1 if row['gameType'] == 'Playoffs' else 0)

  
    team_stats[home_team]['games'] += 1
    team_stats[away_team]['games'] += 1

    
    expected_home = 1 / (1 + 10 ** ((away_rating - home_rating) / 400))
    actual_home   = 1 if winner == home_id else 0
    K = 32

    elo[home_team] += K * (actual_home - expected_home)
    elo[away_team] += K * ((1 - actual_home) - (1 - expected_home))

    # atualizar sts
    if winner == home_id:
        team_stats[home_team]['wins'] += 1
        recent_results[home_team].append(1)
        recent_results[away_team].append(0)
        win_streaks[home_team] += 1
        win_streaks[away_team]  = 0
    else:
        team_stats[away_team]['wins'] += 1
        recent_results[home_team].append(0)
        recent_results[away_team].append(1)
        win_streaks[away_team]  += 1
        win_streaks[home_team]   = 0




df['home_winrate']    = home_winrates
df['away_winrate']    = away_winrates
df['home_recent_form'] = home_recent_form
df['away_recent_form'] = away_recent_form
df['home_elo']        = home_elo
df['away_elo']        = away_elo
df['home_streak']     = home_streak
df['away_streak']     = away_streak
df['is_playoff']      = is_playoff

df['target'] = (df['winner'] == df['hometeamId']).astype(int)

# Os modelos só trabalham com números, por isso fazemos One-Hot Encoding das equipas.

team_encoder  = OneHotEncoder(handle_unknown='ignore')
team_features = team_encoder.fit_transform(df[['hometeamName', 'awayteamName']])

numeric_features = df[[
    'home_winrate',
    'away_winrate',
    'home_recent_form',
    'away_recent_form',
    'is_playoff',
    'home_streak',
    'away_streak',
    'home_elo',
    'away_elo',
]]

numeric_sparse = csr_matrix(numeric_features.values)
X = hstack([team_features, numeric_sparse])
y = df['target'].values

# Nomes das features
team_feature_names  = team_encoder.get_feature_names_out(['hometeamName', 'awayteamName'])
numeric_feature_names = numeric_features.columns.tolist()
feature_names = list(team_feature_names) + numeric_feature_names

#treino nos primeiros 80% dos jogos e teste nos 20% restantes. 
split_index = int(len(df) * 0.8)
X_train, X_test = X[:split_index], X[split_index:]
y_train, y_test = y[:split_index], y[split_index:]


#Usamos os melhores params
model1 = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_split=5,
    class_weight='balanced',
    random_state=42,
)


model2 = GradientBoostingClassifier(
    n_estimators=100,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42,
)

model3 = LogisticRegression(
    C=1.0,
    max_iter=1500,
    class_weight='balanced',
    solver='liblinear',
    random_state=42,
)

models = {
    'Random_Forest':  model1,
    'Gradient_Boost': model2,
    'Logistic_Reg':   model3,
}


trained_models = {}

for name, model in models.items():
    model.fit(X_train, y_train)
    trained_models[name] = model
    print(f"\nModel {name} trained")


model_metrics = []

for name, model in trained_models.items():
    print(f"\n{'='*40}")
    print(f"  {name}")
    print('='*40)

    predictions = model.predict(X_test)
    accuracy    = accuracy_score(y_test, predictions)
    report      = classification_report(y_test, predictions, output_dict=True)

    print(f"Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, predictions))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, predictions))

    model_metrics.append({
        "Model":     name,
        "Accuracy":  accuracy,
        "Precision": report["1"]["precision"],
        "Recall":    report["1"]["recall"],
        "F1-Score":  report["1"]["f1-score"],
    })

# 

rf_importance = pd.DataFrame({
    "Feature":    feature_names,
    "Importance": model1.feature_importances_,
}).sort_values(by="Importance", ascending=False)

gb_importance = pd.DataFrame({
    "Feature":    feature_names,
    "Importance": model2.feature_importances_,
}).sort_values(by="Importance", ascending=False)

lr_importance = pd.DataFrame({
    "Feature":    feature_names,
    "Importance": np.abs(model3.coef_[0]), 
}).sort_values(by="Importance", ascending=False)

for name, model in trained_models.items():
    joblib.dump(model, f"../models/{name}_nba_model.pkl")

metrics_df = pd.DataFrame(model_metrics)
#Isto foi por causa dos grafos
joblib.dump(metrics_df,     "../models/model_metrics.pkl")
joblib.dump(rf_importance,  "../models/rf_feature_importance.pkl")
joblib.dump(gb_importance,  "../models/gb_feature_importance.pkl")
joblib.dump(lr_importance,  "../models/lr_feature_importance.pkl")
joblib.dump(team_encoder,   "../models/team_encoder.pkl")
joblib.dump(feature_names,  "../models/feature_names.pkl")
joblib.dump((X_train, X_test, y_train, y_test), "../models/split_data.pkl")
print("Split data saved")
print("\nArtifacts saved successfully.")
