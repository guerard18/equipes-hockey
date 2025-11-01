import streamlit as st
import pandas as pd
import random
from datetime import datetime

from utils import load_players, save_history

# Optionnel : commit GitHub automatique
try:
    from github_utils import save_to_github
    GITHUB_OK = True
except Exception:
    GITHUB_OK = False


st.title("2️⃣ Formation des équipes de hockey 🏒")
st.markdown(
    "Cette page crée automatiquement deux équipes équilibrées "
    "en fonction des talents (attaque/défense) des joueurs présents."
)

# Charger la liste de joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

# Vérification minimale
if len(players_present) < 10:
    st.error("❌ Pas assez de joueurs présents pour former deux équipes. (minimum 10 requis)")
    st.stop()

# Séparer attaque et défense selon les talents les plus élevés
attaquants = []
defenseurs = []

for _, row in players_present.iterrows():
    if row["talent_attaque"] >= row["talent_defense"]:
        attaquants.append(row)
    else:
        defenseurs.append(row)

# Si déséquilibré, réajuster
if len(attaquants) < 12:
    st.warning("Peu d’attaquants disponibles — certains joueurs seront réassignés.")
if len(defenseurs) < 8:
    st.warning("Peu de défenseurs disponibles — certains joueurs seront réassignés.")

# Conversion en DataFrame
attaquants = pd.DataFrame(attaquants)
defenseurs = pd.DataFrame(defenseurs)

# Mélanger pour varier les combinaisons
attaquants = attaquants.sample(frac=1, random_state=random.randint(0, 10000)).reset_index(drop=True)
defenseurs = defenseurs.sample(frac=1, random_state=random.randint(0, 10000)).reset_index(drop=True)

# Créer les trios (3 attaquants) et duos (2 défenseurs)
fw_lines = [attaquants.iloc[i:i+3] for i in range(0, len(attaquants), 3)]
df_lines = [defenseurs.iloc[i:i+2] for i in range(0, len(defenseurs), 2)]

# Ignorer les groupes incomplets
fw_lines = [g for g in fw_lines if len(g) == 3]
df_lines = [g for g in df_lines if len(g) == 2]

# Vérification minimale encore
if len(fw_lines) < 4 or len(df_lines) < 4:
    st.error("❌ Pas assez de trios/défenseurs pour deux équipes complètes (2 trios + 2 duos chacun).")
    st.stop()

# Attribution aléatoire équilibrée
random.shuffle(fw_lines)
random.shuffle(df_lines)

# Deux équipes de 2 trios + 2 duos
teamA_fw = fw_lines[:2]
teamB_fw = fw_lines[2:4]
teamA_df = df_lines[:2]
teamB_df = df_lines[2:4]

# Calcul des moyennes de talent
def calc_avg(team_fw, team_df):
    fw_talent = sum(team_fw[i]["talent_attaque"].mean() for i in range(len(team_fw))) / len(team_fw)
    df_talent = sum(team_df[i]["talent_defense"].mean() for i in range(len(team_df))) / len(team_df)
    return round((fw_talent + df_talent) / 2, 2)

moy_A = calc_avg(teamA_fw, teamA_df)
moy_B = calc_avg(teamB_fw, teamB_df)

# Affichage clair
st.header("🟦 Équipe A")
for trio in teamA_fw:
    st.write(", ".join(trio["nom"].tolist()))
for duo in teamA_df:
    st.
