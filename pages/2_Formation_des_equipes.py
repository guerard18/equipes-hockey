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
    "en fonction des talents (attaque/défense) des joueurs présents. "
    "Elle forme aussi **2 trios d’attaque** et **2 duos de défense** par équipe."
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

# ------------------------------
# BOUTON : FORMER LES ÉQUIPES
# ------------------------------
if st.button("🎯 Former les équipes équilibrées"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent. Coche des joueurs avant de continuer.")
        st.stop()

    # Déterminer la position principale
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

    # Calcul des moyennes
    moy_A = round(teamA_df["talent_total"].mean(), 2)
    moy_B = round(teamB_df["talent_total"].mean(), 2)

    # ------------------------------
    # FONCTION POUR FORMER LES LIGNES
    # ------------------------------
    def former_lignes(df):
        attaquants = df[df["poste"] == "Attaquant"].sort_values("talent_attaque", ascending=False).reset_index(drop=True)
        defenseurs = df[df["poste"] == "Défenseur"].sort_values("talent_defense", ascending=False).reset_index(drop=True)

        trios, duos = [], []

        # Créer 2 trios équilibrés
        while len(attaquants) > 0:
            trio = attaquants.head(3)
            trios.append(trio)
            attaquants = attaquants.iloc[3:]

        # Créer 2 duos équilibrés
        while len(defenseurs) > 0:
            duo = defenseurs.head(2)
            duos.append(duo)
            defenseurs = defenseurs.iloc[2:]

        # Si pas assez, compléter avec les joueurs restants
        if len(trios) < 2:
            trios.append(pd.DataFrame())
        if len(duos) < 2:
            duos.append(pd.DataFrame())

        return trios[:2], duos[:2]

    triosA, duosA = former_lignes(teamA_df)
    triosB, duosB = former_lignes(teamB_df)

    # ------------------------------
    # AFFICHAGE
    # ------------------------------
    st.header("🟦 Équipe A")
    st.write(f"**Moyenne de talent :** {moy_A}")
    for i, trio in enumerate(triosA, 1):
        if not trio.empty:
            st.markdown(f"**Trio {i} (attaque)**")
            for _, p in trio.iterrows():
                st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
    for i, duo in enumerate(duosA, 1):
        if not duo.empty:
            st.markdown(f"**Duo {i} (défense)**")
            for _, p in duo.iterrows():
                st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

    st.divider()

    st.header("🟥 Équipe B")
    st.write(f"**Moyenne de talent :** {moy_B}")
    for i, trio in enumerate(triosB, 1):
        if not trio.empty:
            st.markdown(f"**Trio {i} (attaque)**")
            for _, p in trio.iterrows():
                st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
    for i, duo in enumerate(duosB, 1):
        if not duo.empty:
            st.markdown(f"**Duo {i} (défense)**")
            for _, p in duo.iterrows():
                st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

    st.divider()

    # ------------------------------
    # Analyse d'équilibre
    # ------------------------------
    diff = abs(moy_A - moy_B)
    if diff < 0.5:
        st.success("⚖️ Les équipes sont très équilibrées !")
    elif diff < 1:
        st.info("🟡 Les équipes sont plutôt équilibrées.")
    else:
        st.warning("🔴 Écart de talent notable entre les équipes.")

    # ------------------------------
    # Sauvegarde dans l’historique
    # ------------------------------
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
