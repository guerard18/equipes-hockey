import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.font_manager as fm
import locale

# Configuration de la locale pour la date en français
try:
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
except:
    locale.setlocale(locale.LC_TIME, "fr_CA.UTF-8")

st.title("🏒 Tournoi en cours")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
INFO_FILE = os.path.join(DATA_DIR, "tournoi_info.json")

if not os.path.exists(BRACKET_FILE):
    st.warning("⚠️ Aucun tournoi n’a encore été généré. Allez dans 'Génération du tournoi'.")
    st.stop()

# Charger les données du tournoi
matchs = pd.read_csv(BRACKET_FILE)
with open(INFO_FILE, "r") as f:
    info = json.load(f)

date_tournoi = datetime.strptime(info["date"], "%Y-%m-%d").strftime("%A %d %B %Y")
capitaines = info.get("capitaines", {})

st.subheader(f"📅 Tournoi du {date_tournoi.capitalize()}")

# Ajouter colonnes manquantes
if "Score A" not in matchs.columns:
    matchs["Score A"] = 0
if "Score B" not in matchs.columns:
    matchs["Score B"] = 0
if "Gagnant" not in matchs.columns:
    matchs["Gagnant"] = ""
if "Prolongation" not in matchs.columns:
    matchs["Prolongation"] = False

# --- Gestion des scores ---
st.divider()
st.subheader("📝 Entrer les résultats des matchs")

for i, row in matchs.iterrows():
    if row["Type"] == "Match":
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.markdown(f"### {row['Équipe A']}")
            st.caption(f"👑 {capitaines.get(row['Équipe A'], '')}")
            score_a = st.number_input("", min_value=0, value=int(row["Score A"]), key=f"a{i}")
        with col2:
            st.markdown(f"### {row['Équipe B']}")
            st.caption(f"👑 {capitaines.get(row['Équipe B'], '')}")
            score_b = st.number_input("", min_value=0, value=int(row["Score B"]), key=f"b{i}")
        with col3:
            gagnant = row["Équipe A"] if score_a > score_b else row["Équipe B"] if score_b > score_a else ""
            matchs.loc[i, ["Score A", "Score B", "Gagnant"]] = [score_a, score_b, gagnant]
        with col4:
            st.write("")

st.divider()
if st.button("💾 Enregistrer les résultats"):
    matchs.to_csv(BRACKET_FILE, index=False)
    st.success("✅ Résultats enregistrés avec succès !")

# --- Classement après la ronde ---
st.divider()
st.subheader("📊 Classement provisoire")

def classement_from_results(df):
    scores = {}
    for _, row in df.iterrows():
        if row["Phase"] != "Ronde" or row["Gagnant"] == "":
            continue
        a, b = row["Équipe A"], row["Équipe B"]
        score_a, score_b = row["Score A"], row["Score B"]
        for team in [a, b]:
            if team not in scores:
                scores[team] = {"Pts": 0, "BP": 0, "BC": 0}
        scores[a]["BP"] += score_a
        scores[a]["BC"] += score_b
        scores[b]["BP"] += score_b
        scores[b]["BC"] += score_a
        if score_a > score_b:
            scores[a]["Pts"] += 2
        elif score_b > score_a:
            scores[b]["Pts"] += 2
    clas = pd.DataFrame(scores).T
    clas["Diff"] = clas["BP"] - clas["BC"]
    clas = clas.sort_values(["Pts", "Diff", "BP"], ascending=False).reset_index()
    clas.rename(columns={"index": "Équipe"}, inplace=True)
    return clas

classement = classement_from_results(matchs)
st.dataframe(classement)

# --- Demi-finales automatiques ---
st.divider()
st.subheader("⚔️ Demi-finales")
if "1er vs 4e" in " ".join(matchs["Équipe A"].tolist()):
    if st.button("⚙️ Mettre à jour les demi-finales maintenant"):
        if len(classement) >= 4:
            top4 = classement["Équipe"].tolist()[:4]
            matchs.loc[matchs["Équipe A"].str.contains("1er vs 4e"), ["Équipe A", "Équipe B"]] = [top4[0], top4[3]]
            matchs.loc[matchs["Équipe A"].str.contains("2e vs 3e"), ["Équipe A", "Équipe B"]] = [top4[1], top4[2]]
            matchs.to_csv(BRACKET_FILE, index=False)
            st.success("✅ Demi-finales mises à jour !")

# --- Bracket ---
st.divider()
st.subheader("🎯 Bracket du tournoi")

def afficher_bracket():
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.axis("off")

    phases = ["Demi-finale", "Finale"]
    x_pos = [0.1, 0.55]
    y_start = [0.7, 0.45]
    y_step = 0.3

    for phase, x in zip(phases, x_pos):
        matches = matchs[matchs["Phase"].str.contains(phase, na=False)]
        for j, (_, m) in enumerate(matches.iterrows()):
            y = y_start[0] - j * y_step
            rect = Rectangle((x, y), 0.3, 0.1, linewidth=2, edgecolor="black", facecolor="white")
            ax.add_patch(rect)
            team_a = f"{m['Équipe A']} {'👑'+capitaines.get(m['Équipe A'],'') if m['Équipe A'] in capitaines else ''}"
            team_b = f"{m['Équipe B']} {'👑'+capitaines.get(m['Équipe B'],'') if m['Équipe B'] in capitaines else ''}"
            ax.text(x + 0.01, y + 0.065, team_a, fontsize=10, fontweight="bold")
            ax.text(x + 0.01, y + 0.03, team_b, fontsize=10, fontweight="bold")
            ax.text(x + 0.23, y + 0.04, f"{int(m['Score A'])}-{int(m['Score B'])}", fontsize=12, fontweight="bold")

    finale = matchs[matchs["Phase"] == "Finale"]
    if not finale.empty:
        m = finale.iloc[0]
        x, y = 0.55, 0.1
        rect = Rectangle((x, y), 0.3, 0.1, linewidth=3, edgecolor="gold", facecolor="white")
        ax.add_patch(rect)
        team_a = f"{m['Équipe A']} {'👑'+capitaines.get(m['Équipe A'],'') if m['Équipe A'] in capitaines else ''}"
        team_b = f"{m['Équipe B']} {'👑'+capitaines.get(m['Équipe B'],'') if m['Équipe B'] in capitaines else ''}"
        ax.text(x + 0.01, y + 0.065, team_a, fontsize=11, fontweight="bold")
        ax.text(x + 0.01, y + 0.03, team_b, fontsize=11, fontweight="bold")
        ax.text(x + 0.24, y + 0.04, f"{int(m['Score A'])}-{int(m['Score B'])}", fontsize=12, color="gold", fontweight="bold")

        # Afficher le champion
        if m["Gagnant"]:
            st.success(f"🏆 **Équipe championne : {m['Gagnant']}**")
            st.markdown(
                f"<h2 style='text-align:center; color:gold;'>✨ CHAMPION : {m['Gagnant']} ✨</h2>",
                unsafe_allow_html=True,
            )
            st.snow()

    plt.text(0.12, 0.83, "Demi-finales", fontsize=14, fontweight="bold")
    plt.text(0.6, 0.25, "Finale", fontsize=14, fontweight="bold")
    st.pyplot(fig)

afficher_bracket()

# --- Finale ---
st.divider()
st.subheader("🏆 Finale")
if "Gagnants demi-finales" in " ".join(matchs["Équipe A"].tolist()):
    if st.button("⚙️ Mettre à jour la finale maintenant"):
        demi = matchs[matchs["Phase"] == "Demi-finale"]
        gagnants = demi["Gagnant"].tolist()
        if len(gagnants) == 2 and all(gagnants):
            matchs.loc[matchs["Phase"] == "Finale", ["Équipe A", "Équipe B"]] = gagnants
            matchs.to_csv(BRACKET_FILE, index=False)
            st.success("✅ Finale mise à jour avec les gagnants des demi-finales !")
