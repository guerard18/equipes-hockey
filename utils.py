import pandas as pd
import os
from datetime import datetime

# --- Charger les joueurs ---
def load_players():
    path = "data/joueurs.csv"
    if os.path.exists(path):
        return pd.read_csv(path)
    else:
        return pd.DataFrame(columns=["nom", "talent_attaque", "talent_defense", "present"])

# --- Sauvegarder les joueurs ---
def save_players(df):
    path = "data/joueurs.csv"
    os.makedirs("data", exist_ok=True)
    df.to_csv(path, index=False)

# --- Calcul automatique de la saison de hockey ---
def saison_from_date(date_str):
    """Retourne la saison (ex: 2024-2025) selon le calendrier hockey (août à avril)."""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        annee = date.year
        mois = date.month
        # Saison : août → avril
        if mois >= 8:  # Août à décembre
            return f"{annee}-{annee + 1}"
        elif mois <= 4:  # Janvier à avril
            return f"{annee - 1}-{annee}"
        else:
            return "Hors saison"
    except Exception:
        return "Inconnue"

# --- Sauvegarder l’historique d’un match ---
def save_history(date, moyB, moyN, triosB, duosB, triosN, duosN, eqB, eqN):
    """Sauvegarde un match dans l'historique avec la saison calculée automatiquement."""
    path = "data/historique.csv"
    os.makedirs("data", exist_ok=True)

    # Calcul automatique de la saison
    saison = saison_from_date(date)

    new_data = pd.DataFrame([{
        "Date": date,
        "Saison": saison,
        "Moyenne_BLANCS": round(moyB, 2),
        "Moyenne_NOIRS": round(moyN, 2),
        "Trios_BLANCS": ", ".join([" / ".join(t) for t in triosB]),
        "Duos_BLANCS": ", ".join([" / ".join(d) for d in duosB]),
        "Trios_NOIRS": ", ".join([" / ".join(t) for t in triosN]),
        "Duos_NOIRS": ", ".join([" / ".join(d) for d in duosN]),
        "Équipe_BLANCS": ", ".join(eqB),
        "Équipe_NOIRS": ", ".join(eqN)
    }])

    # Ajouter à l’historique existant
    if os.path.exists(path):
        old = pd.read_csv(path)
        df = pd.concat([old, new_data], ignore_index=True)
    else:
        df = new_data

    df.to_csv(path, index=False)
