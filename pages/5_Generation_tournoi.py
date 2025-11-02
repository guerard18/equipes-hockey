import streamlit as st
import pandas as pd
import os
import random
import itertools
import json
from datetime import datetime, timedelta, time
from utils import load_players
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("🏒 Génération du tournoi (4 équipes fixes)")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
INFO_FILE = os.path.join(DATA_DIR, "tournoi_info.json")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Charger les joueurs présents ---
def charger_joueurs():
    players = load_players()
    return players[players["present"] == True].reset_index(drop=True)

if st.button("🔄 Recharger les joueurs présents"):
    st.session_state["players_present"] = charger_joueurs()
    st.success("✅ Liste des joueurs mise à jour !")

players_present = st.session_state.get("players_present", charger_joueurs())
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")
if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — la formation sera approximative.")

# --- Sélection de la date du tournoi ---
st.subheader("📅 Date du tournoi")
date_tournoi = st.date_input("Choisir la date du tournoi :", datetime.now().date())

# --- Snake draft équilibré ---
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
            sens, idx = -1, nb_groupes - 1
        elif idx < 0:
            sens, idx = 1, 0
    return [pd.DataFrame(g) for g in groupes]

# --- Génération des équipes équilibrées ---
def generer_equipes_tournoi(players_present):
    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    attaquants = players_present[players_present["poste"] == "Attaquant"]
    defenseeurs = players_present[players_present["poste"] == "Défenseur"]

    trios = snake_draft(attaquants, 8, "talent_attaque")
    duos = snake_draft(defenseeurs, 8, "talent_defense")
    random.shuffle(trios)
    random.shuffle(duos)

    equipes = {
        "BLANCS ⚪": {"trios": trios[0:2], "duos": duos[0:2]},
        "NOIRS ⚫": {"trios": trios[2:4], "duos": duos[2:4]},
        "ROUGES 🔴": {"trios": trios[4:6], "duos": duos[4:6]},
        "VERTS 🟢": {"trios": trios[6:8], "duos": duos[6:8]},
    }

    for nom, eq in equipes.items():
        moy_trios = [t["talent_attaque"].mean() for t in eq["trios"] if not t.empty]
        moy_duos = [d["talent_defense"].mean() for d in eq["duos"] if not d.empty]
        eq["moyenne"] = round(sum(moy_trios + moy_duos) / len(moy_trios + moy_duos), 2)
    return equipes

# --- Générer les équipes ---
if st.button("🎯 Générer les équipes du tournoi"):
    st.session_state["tournoi_equipes"] = generer_equipes_tournoi(players_present)
    st.session_state["capitaines"] = {}
    st.success("✅ Équipes du tournoi générées !")

equipes = st.session_state.get("tournoi_equipes")
capitaines = st.session_state.get("capitaines", {})

if equipes:
    st.subheader("📋 Composition des équipes et choix des capitaines")
    for nom, eq in equipes.items():
        st.markdown(f"### {nom} — Moyenne : **{eq['moyenne']}**")
        eq_joueurs = []
        for i, trio in enumerate(eq["trios"], 1):
            if not trio.empty:
                noms = trio["nom"].tolist()
                st.write(f"**Trio {i} ({round(trio['talent_attaque'].mean(),2)}) :** {', '.join(noms)}")
                eq_joueurs += noms
        for i, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                noms = duo["nom"].tolist()
                st.write(f"**Duo {i} ({round(duo['talent_defense'].mean(),2)}) :** {', '.join(noms)}")
                eq_joueurs += noms

        capitaine = st.selectbox(f"👑 Choisir le capitaine pour {nom}", eq_joueurs, key=f"cap_{nom}")
        capitaines[nom] = capitaine
        st.markdown(f"🧢 **Capitaine choisi : {capitaine}**")
        st.divider()

    st.session_state["capitaines"] = capitaines

    # --- Paramètres de temps ---
    st.subheader("⏱️ Paramètres de l’horaire")
    start_time = st.time_input("Heure de début du premier match", time(18, 0))
    match_duration = st.number_input("Durée d’un match de ronde (minutes)", 10, 120, 25, 5)
    demi_duration = st.number_input("Durée d’une demi-finale (minutes)", 10, 120, 30, 5)
    finale_duration = st.number_input("Durée de la finale (minutes)", 10, 120, 35, 5)
    pause = st.number_input("Pause entre les matchs (minutes)", 0, 60, 5, 5)
    zamboni_pause = st.number_input("Durée de la pause Zamboni (minutes)", 5, 30, 10, 5)

    # --- Générer le tournoi ---
    def generer_matchs_equilibres(equipes):
        noms = list(equipes.keys())
        matchs_possibles = list(itertools.combinations(noms, 2))
        random.shuffle(matchs_possibles)

        matchs = pd.DataFrame(matchs_possibles, columns=["Équipe A", "Équipe B"])
        matchs["Phase"] = "Ronde"

        heure = datetime.combine(datetime.today(), start_time)
        rows = []
        match_counter = 0

        # --- Matchs de ronde ---
        for _, row in matchs.iterrows():
            rows.append({
                "Heure": heure.strftime("%H:%M"),
                "Équipe A": row["Équipe A"],
                "Équipe B": row["Équipe B"],
                "Durée (min)": match_duration,
                "Phase": "Ronde",
                "Type": "Match"
            })
            heure += timedelta(minutes=match_duration + pause)
            match_counter += 1
            if match_counter % 3 == 0:
                rows.append({
                    "Heure": heure.strftime("%H:%M"),
                    "Équipe A": "🧊 Pause Zamboni",
                    "Équipe B": "",
                    "Durée (min)": zamboni_pause,
                    "Phase": "",
                    "Type": "Pause"
                })
                heure += timedelta(minutes=zamboni_pause)

        # --- Demi-finales ---
        for j in range(2):
            rows.append({
                "Heure": heure.strftime("%H:%M"),
                "Équipe A": f"Demi-finale {j+1} - {'1er vs 4e' if j == 0 else '2e vs 3e'}",
                "Équipe B": "",
                "Durée (min)": demi_duration,
                "Phase": "Demi-finale",
                "Type": "Match"
            })
            heure += timedelta(minutes=demi_duration + pause)
            match_counter += 1
            if match_counter % 3 == 0:
                rows.append({
                    "Heure": heure.strftime("%H:%M"),
                    "Équipe A": "🧊 Pause Zamboni",
                    "Équipe B": "",
                    "Durée (min)": zamboni_pause,
                    "Phase": "",
                    "Type": "Pause"
                })
                heure += timedelta(minutes=zamboni_pause)

        # --- Pause avant la finale ---
        rows.append({
            "Heure": heure.strftime("%H:%M"),
            "Équipe A": "🧊 Pause Zamboni (avant la finale)",
            "Équipe B": "",
            "Durée (min)": zamboni_pause,
            "Phase": "",
            "Type": "Pause"
        })
        heure += timedelta(minutes=zamboni_pause)

        # --- Finale ---
        rows.append({
            "Heure": heure.strftime("%H:%M"),
            "Équipe A": "🏆 Finale - Gagnants demi-finales",
            "Équipe B": "",
            "Durée (min)": finale_duration,
            "Phase": "Finale",
            "Type": "Match"
        })

        return pd.DataFrame(rows)

    # --- Bouton principal ---
    if st.button("🏁 Créer le tournoi complet"):
        matchs = generer_matchs_equilibres(equipes)
        matchs.to_csv(BRACKET_FILE, index=False)

        info = {
            "date": date_tournoi.strftime("%Y-%m-%d"),
            "capitaines": capitaines,
            "equipes": list(equipes.keys())
        }
        with open(INFO_FILE, "w") as f:
            json.dump(info, f)

        st.success("✅ Tournoi complet créé et capitaines enregistrés !")
        st.balloons()

        st.dataframe(matchs[["Heure", "Équipe A", "Équipe B", "Durée (min)", "Phase", "Type"]])
