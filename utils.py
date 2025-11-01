import pandas as pd
import os

# Charger les joueurs
def load_players():
    path = "data/joueurs.csv"
    if not os.path.exists(path):
        os.makedirs("data", exist_ok=True)
        df = pd.DataFrame(columns=["nom", "talent_attaque", "talent_defense", "present"])
        df.to_csv(path, index=False)
    else:
        df = pd.read_csv(path)
        if "present" not in df.columns:
            df["present"] = False
    return df

# Sauvegarder les joueurs
def save_players(df):
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/joueurs.csv", index=False)

# Historique des équipes
def save_history(equipeB, equipeN, moyB, moyN, date):
    """Sauvegarde les équipes formées dans le fichier historique"""
    path = "data/historique.csv"
    os.makedirs("data", exist_ok=True)

    new_entry = pd.DataFrame([{
        "Date": date,
        "Equipe_Blanc": ", ".join(equipeB),
        "Equipe_Noir": ", ".join(equipeN),
        "Moyenne_Blanc": moyB,
        "Moyenne_Noir": moyN
    }])

    if os.path.exists(path):
        df = pd.read_csv(path)
        df = pd.concat([df, new_entry], ignore_index=True)
    else:
        df = new_entry

    df.to_csv(path, index=False)
