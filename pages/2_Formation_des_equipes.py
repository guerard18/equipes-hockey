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

# Charger les joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

# Avertissement si peu de joueurs
if len(players_present) < 10:
    st.warning(
        "⚠️ Moins de 10 joueurs présents. Les équipes seront formées quand même, "
        "mais elles peuvent être incomplètes."
    )

# Bouton pour former les équipes
if st.button("🎯 Former les équipes équilibrées"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent. Coche des joueurs avant de continuer.")
        st.stop()

    # Déterminer la position principale selon le meilleur talent
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    # Calculer un score global
    players_present["talent_total"] = players_present[["talent_attaque", "talent_defense"]].mean(axis=1)

    # Trier les joueurs du plus fort au plus faible
    players_present = players_present.sort_values("talent_total", ascending=False).reset_index(drop=True)

    # Alternance pour équilibrer les talents entre A et B
    teamA, teamB = [], []
    totalA, totalB = 0, 0

    for _, row in players_present.iterrows():
        if totalA <= totalB:
            teamA.append(row)
            totalA += row["talent_total"]
        else:
            teamB.append(row)
            totalB += row["talent_total"]

    teamA_df = pd.DataFrame(teamA)
    teamB_df = pd.DataFrame(teamB)

    # Compter les postes
    nbA_att = (teamA_df["poste"] == "Attaquant").sum()
    nbA_def = (teamA_df["poste"] == "Défenseur").sum()
    nbB_att = (teamB_df["poste"] == "Attaquant").sum()
    nbB_def = (teamB_df["poste"] == "Défenseur").sum()

    # Calcul des moyennes
    moy_A = round(teamA_df["talent_total"].mean(), 2)
    moy_B = round(teamB_df["talent_total"].mean(), 2)

    # --- AFFICHAGE ---
    st.header("🟦 Équipe A")
    for _, p in teamA_df.iterrows():
        st.write(f"{p['nom']} — {p['poste']} ({p['talent_total']:.1f})")
    st.write(f"**Attaquants :** {nbA_att} | **Défenseurs :** {nbA_def}")
    st.write(f"**Moyenne de talent :** {moy_A}")

    st.header("🟥 Équipe B")
    for _, p in teamB_df.iterrows():
        st.write(f"{p['nom']} — {p['poste']} ({p['talent_total']:.1f})")
    st.write(f"**Attaquants :** {nbB_att} | **Défenseurs :** {nbB_def}")
    st.write(f"**Moyenne de talent :** {moy_B}")

    # Différence de talent global
    diff = abs(moy_A - moy_B)
    if diff < 0.5:
        st.success("⚖️ Les équipes sont très équilibrées !")
    elif diff < 1:
        st.info("🟡 Les équipes sont plutôt équilibrées.")
    else:
        st.warning("🔴 Écart de talent notable entre les équipes.")

    # Bouton d'enregistrement
    if st.button("💾 Enregistrer ces équipes dans l’historique"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        equipeA = teamA_df["nom"].tolist()
        equipeB = teamB_df["nom"].tolist()

        save_history(equipeA, equipeB, moy_A, moy_B, date)
        st.success("✅ Équipes enregistrées dans l’historique !")

        if GITHUB_OK:
            try:
                save_to_github("data/historique.csv", "Nouvelle entrée d’historique équilibrée")
                st.toast("💾 Sauvegarde GitHub réussie")
            except Exception as e:
                st.warning(f"⚠️ Impossible de sauvegarder sur GitHub : {e}")
