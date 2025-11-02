import streamlit as st
import json
import os

st.title("⚙️ Configuration de l'application")

path = "data/config.json"
os.makedirs("data", exist_ok=True)

if os.path.exists(path):
    with open(path, "r") as f:
        config = json.load(f)
else:
    config = {
        "nb_trios": 4,
        "nb_duos": 4,
        "envoyer_courriel": True,
        "format_match": "Match du {date}"
    }

with st.form("config_form"):
    st.subheader("🧩 Paramètres généraux")
    config["nb_trios"] = st.number_input("Nombre de trios par équipe", min_value=1, max_value=6, value=config["nb_trios"])
    config["nb_duos"] = st.number_input("Nombre de duos par équipe", min_value=1, max_value=6, value=config["nb_duos"])
    config["envoyer_courriel"] = st.checkbox("Activer l'envoi des courriels", value=config["envoyer_courriel"])
    config["format_match"] = st.text_input("Format du nom du match", value=config["format_match"])

    if st.form_submit_button("💾 Enregistrer la configuration"):
        with open(path, "w") as f:
            json.dump(config, f, indent=4)
        st.success("✅ Configuration enregistrée avec succès !")

import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime
from utils import load_players

st.title("🏒 Configuration du match ou tournoi")

st.markdown("""
Ici, vous pouvez configurer soit un **match régulier**, soit un **tournoi** complet avec plusieurs équipes.  
Utilisez les onglets ci-dessous pour choisir le mode souhaité :
""")

# --- Onglets principaux ---
tab_match, tab_tournoi = st.tabs(["⚔️ Match régulier", "🏆 Tournoi"])

# --- Onglet 1 : Match régulier ---
with tab_match:
    st.subheader("⚙️ Configuration du match")
    date_match = st.date_input("📅 Date du match", datetime.now().date())
    duree = st.selectbox("⏱ Durée du match :", ["60 minutes", "90 minutes", "120 minutes"], index=0)
    lieu = st.text_input("🏟 Lieu du match", "Aréna local")
    st.success("Match régulier configuré. Vous pouvez aller à la page **Formation des équipes** pour créer les équipes.")

# --- Onglet 2 : Tournoi ---
with tab_tournoi:
    st.subheader("🏆 Configuration du tournoi")

    date_tournoi = st.date_input("📅 Date du tournoi", datetime.now().date())
    nb_equipes = st.slider("Nombre d'équipes :", min_value=2, max_value=8, value=4, step=1)

    # Noms d'équipes personnalisables
    default_names = [
        "BLANCS ⚪", "NOIRS ⚫", "BLEUS 🔵", "VERTS 🟢",
        "ROUGES 🔴", "JAUNES 🟡", "ORANGES 🟠", "GRIS ⚫⚪"
    ]
    st.markdown("### ✏️ Noms des équipes")
    cols = st.columns(4)
    team_names = []
    for i in range(nb_equipes):
        with cols[i % 4]:
            team_names.append(st.text_input(f"Équipe {i+1}", default_names[i]))

    # Charger les joueurs présents
    players = load_players()
    players_present = players[players["present"] == True].reset_index(drop=True)
    st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

    if len(players_present) < nb_equipes * 4:
        st.warning("⚠️ Peu de joueurs présents pour un tournoi équilibré — les équipes seront formées quand même.")

    # --- Génération d'équipes équilibrées ---
    def generate_teams(players_present: pd.DataFrame, nb_equipes: int):
        if players_present.empty:
            return {}

        players_present = players_present.copy()
        players_present["poste"] = players_present.apply(
            lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
            axis=1
        )

        attaquants = players_present[players_present["poste"] == "Attaquant"]
        defenseurs = players_present[players_present["poste"] == "Défenseur"]

        def snake_draft(df, nb_groupes, colonne):
            if df.empty:
                return [pd.DataFrame() for _ in range(nb_groupes)]
            df = df.sample(frac=1).sort_values(colonne, ascending=False).reset_index(drop=True)
            groupes = [[] for _ in range(nb_groupes)]
            sens, idx = 1, 0
            for _, joueur in df.iterrows():
                groupes[idx].append(joueur)
                idx += sens
                if idx == nb_groupes:
                    sens = -1
                    idx = nb_groupes - 1
                elif idx < 0:
                    sens = 1
                    idx = 0
            return [pd.DataFrame(g) for g in groupes]

        trios = snake_draft(attaquants, nb_equipes, "talent_attaque")
        duos = snake_draft(defenseurs, nb_equipes, "talent_defense")

        equipes = {}
        for i in range(nb_equipes):
            equipe = pd.concat([trios[i], duos[i]]).reset_index(drop=True)
            equipes[i] = equipe

        return equipes

    if st.button("🎯 Générer les équipes du tournoi"):
        equipes = generate_teams(players_present, nb_equipes)
        st.session_state["equipes_tournoi"] = equipes

    equipes = st.session_state.get("equipes_tournoi", {})

    if equipes:
        st.subheader("📋 Équipes générées")
        for i, eq in equipes.items():
            st.markdown(f"### {team_names[i]}")
            if not eq.empty:
                moyA = round(eq["talent_attaque"].mean(), 2)
                moyD = round(eq["talent_defense"].mean(), 2)
                moyT = round((moyA + moyD) / 2, 2)
                st.write(f"**Moyenne globale : {moyT}**")
                st.dataframe(eq[["nom", "talent_attaque", "talent_defense"]])

        # --- Bracket automatique (3 matchs garantis) ---
        st.subheader("🏆 Bracket du tournoi")
        equipes_list = [team_names[i] for i in range(nb_equipes)]
        matchups = []
        for i, e1 in enumerate(equipes_list):
            adversaires = [e2 for j, e2 in enumerate(equipes_list) if j != i]
            random.shuffle(adversaires)
            for opp in adversaires[:3]:
                if {e1, opp} not in [{m[0], m[1]} for m in matchups]:
                    matchups.append((e1, opp))

        tournoi_df = pd.DataFrame(matchups, columns=["Équipe A", "Équipe B"])
        st.dataframe(tournoi_df, use_container_width=True)
        st.success(f"✅ {len(tournoi_df)} matchs générés ({nb_equipes} équipes, 3 matchs chacune).")

        if st.button("💾 Enregistrer le tournoi"):
            os.makedirs("data", exist_ok=True)
            tournoi_df.to_csv("data/tournoi_bracket.csv", index=False)
            st.success("✅ Tournoi enregistré ! Vous pouvez maintenant aller à la page **Tournoi en cours** pour gérer les résultats.")
