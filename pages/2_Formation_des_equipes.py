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

# Afficher un avertissement si le nombre est insuffisant
if len(players_present) < 10:
    st.warning(
        "⚠️ Pas assez de joueurs pour former deux équipes complètes "
        "(idéalement 20 joueurs, soit 2 équipes de 10). "
        "Tu peux tout de même créer les équipes avec les présents."
    )

# Bouton pour créer les équipes (même si incomplet)
if st.button("🎲 Former les équipes avec les joueurs présents"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent. Coche des joueurs avant de continuer.")
        st.stop()

    # Séparer attaque et défense selon les talents
    attaquants = []
    defenseurs = []

    for _, row in players_present.iterrows():
        if row["talent_attaque"] >= row["talent_defense"]:
            attaquants.append(row)
        else:
            defenseurs.append(row)

    # Conversion en DataFrame
    attaquants = pd.DataFrame(attaquants)
    defenseurs = pd.DataFrame(defenseurs)

    # Mélanger pour varier les combinaisons
    if not attaquants.empty:
        attaquants = attaquants.sample(frac=1, random_state=random.randint(0, 10000)).reset_index(drop=True)
    if not defenseurs.empty:
        defenseurs = defenseurs.sample(frac=1, random_state=random.randint(0, 10000)).reset_index(drop=True)

    # Créer les trios (3 attaquants) et duos (2 défenseurs)
    fw_lines = [attaquants.iloc[i:i+3] for i in range(0, len(attaquants), 3)]
    df_lines = [defenseurs.iloc[i:i+2] for i in range(0, len(defenseurs), 2)]

    # Ignorer les groupes incomplets pour ne pas planter
    fw_lines = [g for g in fw_lines if len(g) > 0]
    df_lines = [g for g in df_lines if len(g) > 0]

    # Mélanger pour répartir aléatoirement
    random.shuffle(fw_lines)
    random.shuffle(df_lines)

    # Diviser en deux équipes
    half_fw = len(fw_lines) // 2
    half_df = len(df_lines) // 2

    teamA_fw = fw_lines[:half_fw]
    teamB_fw = fw_lines[half_fw:]
    teamA_df = df_lines[:half_df]
    teamB_df = df_lines[half_df:]

    # Gestion des cas avec peu de joueurs
    if len(fw_lines) < 2 or len(df_lines) < 2:
        st.warning("⚠️ Les équipes risquent d’être incomplètes ou déséquilibrées.")

    # Calcul des moyennes de talent
    def calc_avg(team_fw, team_df):
        if not team_fw and not team_df:
            return 0
        fw_talent = sum(team_fw[i]["talent_attaque"].mean() for i in range(len(team_fw))) / max(1, len(team_fw))
        df_talent = sum(team_df[i]["talent_defense"].mean() for i in range(len(team_df))) / max(1, len(team_df))
        return round((fw_talent + df_talent) / 2, 2)

    moy_A = calc_avg(teamA_fw, teamA_df)
    moy_B = calc_avg(teamB_fw, teamB_df)

    # --- AFFICHAGE ---
    st.header("🟦 Équipe A")
    if teamA_fw or teamA_df:
        for trio in teamA_fw:
            st.write(", ".join(trio["nom"].tolist()))
        for duo in teamA_df:
            st.write(", ".join(duo["nom"].tolist()))
        st.write(f"**Moyenne de talent :** {moy_A}")
    else:
        st.write("Aucune donnée pour cette équipe.")

    st.header("🟥 Équipe B")
    if teamB_fw or teamB_df:
        for trio in teamB_fw:
            st.write(", ".join(trio["nom"].tolist()))
        for duo in teamB_df:
            st.write(", ".join(duo["nom"].tolist()))
        st.write(f"**Moyenne de talent :** {moy_B}")
    else:
        st.write("Aucune donnée pour cette équipe.")

    # Bouton pour enregistrer
    if st.button("💾 Enregistrer ces équipes dans l’historique"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        equipeA = [p for g in teamA_fw + teamA_df for p in g["nom"].tolist()]
        equipeB = [p for g in teamB_fw + teamB_df for p in g["nom"].tolist()]

        save_history(equipeA, equipeB, moy_A, moy_B, date)
        st.success("✅ Équipes enregistrées dans l’historique !")

        if GITHUB_OK:
            try:
                save_to_github("data/historique.csv", "Nouvelle entrée d’historique")
                st.toast("💾 Sauvegarde GitHub réussie")
            except Exception as e:
                st.warning(f"⚠️ Impossible de sauvegarder sur GitHub : {e}")
