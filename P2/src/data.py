
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)




OUTPUT="../datasets/GamesFake.csv"
INPUT="../datasets/Games.csv"
N=200
df = pd.read_csv(INPUT, low_memory=False)
df = df.dropna(subset=['hometeamName', 'awayteamName', 'hometeamId', 'awayteamId',
                        'homeScore', 'awayScore', 'winner', 'gameType'])

df['hometeamId'] = df['hometeamId'].astype(str)
df['awayteamId'] = df['awayteamId'].astype(str)
df['winner']     = df['winner'].astype(str)
df['homeScore']  = pd.to_numeric(df['homeScore'], errors='coerce')
df['awayScore']  = pd.to_numeric(df['awayScore'], errors='coerce')
df = df.dropna(subset=['homeScore', 'awayScore'])
team_id_map = {}
for _, row in df.iterrows():
    team_id_map[row['hometeamName']] = str(row['hometeamId'])
    team_id_map[row['awayteamName']] = str(row['awayteamId'])

team_city_map = {}
for _, row in df.iterrows():
    team_city_map[row['hometeamName']] = row.get('hometeamCity', row['hometeamName'])
    team_city_map[row['awayteamName']] = row.get('awayteamCity', row['awayteamName'])

teams = list(team_id_map.keys())


home_score_mean = df['homeScore'].mean()
home_score_std  = df['homeScore'].std()
away_score_mean = df['awayScore'].mean()
away_score_std  = df['awayScore'].std()


arena_cols = ['arenaId', 'arenaName', 'arenaCity', 'arenaState']
arena_map = {}
if all(c in df.columns for c in arena_cols):
    for _, row in df.iterrows():
        team = row['hometeamName']
        if team not in arena_map:
            arena_map[team] = (
                row['arenaId'],
                row['arenaName'],
                row['arenaCity'],
                row['arenaState'],
            )


officials_pool = []
if 'officials' in df.columns:
    for val in df['officials'].dropna():
        for ref in str(val).split(','):
            ref = ref.strip()
            if ref:
                officials_pool.append(ref)
    officials_pool = list(set(officials_pool))

if not officials_pool:
    officials_pool = ["Tony Brothers", "Marc Davis", "James Capers",
                      "Ed Malloy", "Scott Foster", "Zach Zarba",
                      "Sean Wright", "Justin Van Duyne"]


game_type_counts = df['gameType'].value_counts(normalize=True)
game_types       = game_type_counts.index.tolist()
game_type_probs  = game_type_counts.values.tolist()

# gameId máximo para continuar a sequência
max_game_id = df['gameId'].max() if 'gameId' in df.columns else 42500000
max_game_id = int(max_game_id)



def pick_officials(pool, n_refs=3):
    sample = random.sample(pool, min(n_refs, len(pool)))
    return ", ".join(sample)


def generate_score(mean, std, min_val=80, max_val=150):
    score = int(np.random.normal(mean, std))
    return max(min_val, min(max_val, score))


def pick_game_label(game_type):
    if game_type == "Playoffs":
        rounds = [
            ("East First Round",  "East First Round"),
            ("West First Round",  "West First Round"),
            ("East Conf. Semifinals", "East Conf. Semifinals"),
            ("West Conf. Semifinals", "West Conf. Semifinals"),
            ("East Conf. Finals",  "East Conf. Finals"),
            ("West Conf. Finals",  "West Conf. Finals"),
            ("NBA Finals",         "NBA Finals"),
        ]
        label, sub = random.choice(rounds)
        game_num = random.randint(1, 7)
        return label, sub, f"Game {game_num}", f"Game {game_num}"
    else:
        return "Regular Season", "", "", ""


def random_game_datetime(start="2027-10-01", end="2028-06-15"):
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt   = datetime.strptime(end,   "%Y-%m-%d")
    delta    = (end_dt - start_dt).days
    rand_day = start_dt + timedelta(days=random.randint(0, delta))
    # Mairo parte das horas dos jogos é de noit
    hour   = random.choice([19, 19, 20, 20, 20, 21, 22])
    minute = random.choice([0, 30])
    dt = rand_day.replace(hour=hour, minute=minute, second=0)
    return dt

rows = []
used_ids = set()

for i in range(N):

    home_team, away_team = random.sample(teams, 2)

    home_id = team_id_map[home_team]
    away_id = team_id_map[away_team]
    home_city = team_city_map.get(home_team, home_team)
    away_city = team_city_map.get(away_team, away_team)
    home_score = generate_score(home_score_mean, home_score_std)
    away_score = generate_score(away_score_mean, away_score_std)

    # Tirar emptaes
    while home_score == away_score:
        away_score += random.choice([-1, 1])

    winner = home_id if home_score > away_score else away_id

    # Tipo de jogo
    game_type = np.random.choice(game_types, p=game_type_probs)
    game_label, game_sublabel, series_num, series_sub = pick_game_label(game_type)

    # Data/hora
    dt = random_game_datetime()
    game_date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    game_date_only = dt.strftime("%Y-%m-%d %H:%M:%S")

    # Arena
    if home_team in arena_map:
        arena_id, arena_name, arena_city, arena_state = arena_map[home_team]
    else:
        arena_id, arena_name, arena_city, arena_state = ("", f"{home_city} Arena", home_city, "")

    # Attendance realista
    attendance = random.randint(15000, 20000)

    # Árbitros
    n_refs = random.choice([3, 3, 3, 4])
    officials_str = pick_officials(officials_pool, n_refs)

    # gameId único sequencial
    new_id = max_game_id + i + 1
    while new_id in used_ids:
        new_id += 1
    used_ids.add(new_id)

    rows.append({
        "gameId":            new_id,
        "gameDateTimeEst":   game_date_str,
        "hometeamCity":      home_city,
        "hometeamName":      home_team,
        "hometeamId":        home_id,
        "awayteamCity":      away_city,
        "awayteamName":      away_team,
        "awayteamId":        away_id,
        "homeScore":         home_score,
        "awayScore":         away_score,
        "winner":            winner,
        "gameType":          game_type,
        "gameSubtype":       "",
        "gameLabel":         game_label,
        "gameSubLabel":      game_sublabel,
        "seriesGameNumber":  series_num,
        "attendance":        attendance,
        "arenaId":           arena_id,
        "arenaName":         arena_name,
        "arenaCity":         arena_city,
        "arenaState":        arena_state,
        "officials":         officials_str,
        "gameDate":          game_date_only,
    })

out_df = pd.DataFrame(rows)
out_df.to_csv(OUTPUT, index=False)
