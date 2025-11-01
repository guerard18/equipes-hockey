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
    "Cette page forme d’abord **4 trios d’attaque** et **4 duos de défense** équilibrés, "
    "puis assemble deux équipes les plus équitables possible à partir de ces unités."
)

# Charger les joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# ------------------------------
# BOUTON : FORMER LES ÉQUIPES
# ------------------------------
if st.button("🎯 Former les équipes équilibrées"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent.")
        st.stop()

    # Déterminer la position principale
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    # Calculer un score global
    players_present["talent_total"] = players_present[["talent_attaque", "talent_defense"]].mean(axis=1)

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    # Si pas assez de défenseurs/attaquants, équilibrer avec meilleurs disponibles
    if len(defenseurs) < 8:
        manquant = 8 - len(defenseurs)
        if len(attaquants) > manquant:
            defenseurs = pd.concat([defenseurs, attaquants.nlargest(manquant, "talent_defense")])
            attaquants = attaquants.drop(attaquants.nlargest(manquant, "talent_defense").index)

    if len(attaquants) < 12:
        manquant = 12 - len(attaquants)
        if len(defenseurs) > manquant:
            attaquants = pd.concat([attaquants, defenseurs.nlargest(manquant, "talent_attaque")])
            defenseurs = defenseurs.drop(defenseurs.nlargest(manquant, "talent_attaque").index)

    # ------------------------------
    # FORMATION DES UNITÉS
    # ------------------------------
    def former_trios(df):
        df = df.sort_values("talent_attaque", ascending=False).reset_index(drop=True)
        trios = []
        while len(df) >= 3:
            trio = df.head(3)
            df = df.iloc[3:]
            trios.append(trio)
        if len(df) > 0:
            trios.append(df)  # Trio incomplet
        return trios

    def former_duos(df):
        df = df.sort_values("talent_defense", ascending=False).reset_index(drop=True)
        duos = []
        while len(df) >= 2:
            duo = df.head(2)
            df = df.iloc[2:]
            duos.append(duo)
        if len(df) > 0:
            duos.append(df)  # Duo incomplet
        return duos

    trios = former_trios(attaquants)
    duos = former_duos(defenseurs)

    # On garde max 4 trios + 4 duos
    trios = trios[:4]
    duos = duos[:4]

    # ------------------------------
    # DISTRIBUTION DANS LES ÉQUIPES
    # ------------------------------
    equipeA_trios, equipeB_trios = [], []
    equipeA_duos, equipeB_duos = [], []
    totalA, totalB = 0, 0

    # Distribuer les trios (équilibre global)
    for trio in trios:
        score = trio["talent_attaque"].mean()
        if totalA <= totalB:
            equipeA_trios.append(trio)
            totalA += score
        else:
            equipeB_trios.append(trio)
            totalB += score

    # Distribuer les duos
    for duo in duos:
        score = duo["talent_defense"].mean()
        if totalA <= totalB:
            equipeA_duos.append(duo)
            totalA += score
        else:
            equipeB_duos.append(duo)
            totalB += score

    # Moyennes
    moyA = round(totalA / (len(equipeA_trios) + len(equipeA_duos)), 2) if len(equipeA_trios) + len(equipeA_duos) > 0 else 0
    moyB = round(totalB / (len(equipeB_trios) + len(equipeB_duos)), 2) if len(equip
