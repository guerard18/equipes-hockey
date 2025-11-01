import pandas as pd
import os

# ==========================================================
# 🔹 Gestion des joueurs
# ==========================================================

def load_players():
    """
    Charge la liste des joueurs depuis data/joueurs.csv.
    Si le fichier n'existe pas, crée une structure vide.
    """
    path = "data/joueurs.csv"
    if not os.path.exists(path):
        # Création d’un CSV vide si inexistant
        df = pd.DataFrame(columns=["nom", "talent_attaque", "talent_defense", "present"])
        os.makedirs("data", exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return df
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["nom", "talent_attaque", "talent_defense", "present"])


def save_players(df):
    """
    Sauvegarde la liste des joueurs dans data/joueurs.csv.
    """
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/joueurs.csv", index=False, encoding="utf-8-sig")


# ==========================================================
# 🔹 Gestion de l’historique des équipes
# ==========================================================

def load_history():
    """
    Charge l’historique des formations depuis data/historique.csv.
    Si le fichier n’existe pas, retourne une structure vide.
    """
    path = "data/historique.csv"
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["date", "equipe1", "equipe2", "moyenne_talent_eq1", "moyenne_talent_eq2"])
        os.makedirs("data", exist_ok=True)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        return df
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["date", "equipe1", "equipe2", "moyenne_talent_eq1", "moyenne_talent_eq2"])


def save_history(equipe1, equipe2, moy1, moy2, date):
    """
    Ajoute une nouvelle entrée à l’historique.
    """
    path = "data/historique.csv"
    os.makedirs("data", exist_ok=True)

    new_row = pd.DataFrame([{
        "date": date,
        "equipe1": ", ".join(equipe1),
        "equipe2": ", ".join(equipe2),
        "moyenne_talent_eq1": moy1,
        "moyenne_talent_eq2": moy2
    }])

    if os.path.exists(path):
        try:
            hist = pd.read_csv(path)
            hist = pd.concat([hist, new_row], ignore_index=True)
        except Exception:
            hist = new_row
    else:
        hist = new_row

    hist.to_csv(path, index=False, encoding="utf-8-sig")


def reset_history():
    """
    Efface complètement l’historique (remise à zéro).
    """
    path = "data/historique.csv"
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(columns=["date", "equipe1", "equipe2", "moyenne_talent_eq1", "moyenne_talent_eq2"])
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return True
