import pandas as pd
import os
from datetime import datetime

def load_players():
    """Charge la liste des joueurs depuis data/joueurs.csv."""
    path = "data/joueurs.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["nom", "talent_attaque", "talent_defense", "present"])

def save_players(df):
    """Sauvegarde la liste des joueurs."""
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/joueurs.csv", index=False)

def saison_from_date(date_str):
    """Retourne la saison de hockey selon la date (août à avril)."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        y = d.year
        if d.month >= 8:   # Août à décembre
            return f"{y}-{y+1}"
        else:              # Janvier à avril
            return f"{y-1}-{y}"
    except Exception:
        return "Inconnue"

def save_history(equipeB, equipeN, moyB, moyN, date_match, triosB, duosB, triosN, duosN):
    """Enregistre les équipes, moyennes et trios/duos dans data/historique.csv."""
    os.makedirs("data", exist_ok=True)
    saison = saison_from_date(date_match)

    def format_groupes(groupes):
        return "; ".join([", ".join(g["nom"].tolist()) for g in groupes if not g.empty])

    new_data = pd.DataFrame([{
        "Date": date_match,
        "Saison": saison,
        "Moyenne_BLANCS": moyB,
        "Moyenne_NOIRS": moyN,
        "Trios_BLANCS": format_groupes(triosB),
        "Duos_BLANCS": format_groupes(duosB),
        "Trios_NOIRS": format_groupes(triosN),
        "Duos_NOIRS": format_groupes(duosN),
        "Équipe_BLANCS": ", ".join(equipeB),
        "Équipe_NOIRS": ", ".join(equipeN)
    }])

    path = "data/historique.csv"
    if os.path.exists(path):
        hist = pd.read_csv(path)
        hist = pd.concat([hist, new_data], ignore_index=True)
    else:
        hist = new_data

    hist.to_csv(path, index=False)
