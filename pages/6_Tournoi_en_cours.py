import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

st.title("🏒 Tournoi en cours")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
INFO_FILE = os.path.join(DATA_DIR, "tournoi_info.json")

# --- Dictionnaire français pour la date ---
mois_fr = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}
jours_fr = {
    0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi",
    4: "vendredi", 5: "samedi", 6: "dimanche"
}

def format_date_fr(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    jour = jours_fr[d.weekday()]
    mois = mois_fr[d.month]
    return f"{jour} {d.day} {mois} {d.year}"

# --- Vérification du tournoi existant ---
if not os.path.exists(BRACKET_FILE):
    st.warning("⚠️ Aucun tournoi n’a encore été généré. Allez dans 'Génération du tournoi'.")
    st.stop()

matchs = pd.read_csv(BRACKET_FILE)
with open(INFO_FILE, "r") as f:
    info = json.load(f)

date_tournoi = format_date_fr(info["date"])
capitaines = info.get("capitaines", {})

st.subheader(f"📅 Tournoi du {date_tournoi.capitalize()}")

# --- Colonnes manquantes ---
for col in ["Score A", "Score B", "Gagnant", "Prolongation"]:
    if col not in matchs.columns:
        matchs[col] = 0 if "Score" in col else ("" if col == "Gagnant" else False)

# --- Saisie des résultats ---
st.divider()
st.subheader("📝 Entrer les résultats des matchs")

for i, row in matchs.iterrows():
    if row["Type"] == "Match":
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"### {row['Équipe A']}")
            if row['Équipe A'] in capitaines:
                st.caption(f"👑 {capitaines[row['Équipe A']]}")
            score_a = st.number_input("", min_value=0, value=int(row["Score A"]), key=f"a{i}")
        with col2:
            st.markdown(f"### {row['Équipe B']}")
            if row['Équipe B'] in capitaines:
                st.caption(f"👑 {capitaines[row['Équipe B']]}")
            score_b = st.number_input("", min_value=0, value=int(row["Score B"]), key=f"b{i}")
        with col3:
            gagnant = row["Équipe A"] if score_a > score_b else row["Équipe B"] if score_b > score_a else ""
            matchs.loc[i, ["Score A", "Score B", "Gagnant"]] = [score_a, score_b, gagnant]

st.divider()
if st.button("💾 Enregistrer les résultats"):
    matchs.to_csv(BRACKET_FILE, index=False)
    st.success("✅ Résultats enregistrés !")

# --- Classement ---
st.divider()
st.subheader("📊 Classement de la ronde")

def classement_from_results(df):
    scores = {}
    for _, row in df.iterrows():
        if row["Phase"] != "Ronde" or row["Gagnant"] == "":
            continue
        a, b = row["Équipe A"], row["Équipe B"]
        sa, sb = row["Score A"], row["Score B"]
        for team in [a, b]:
            if team not in scores:
                scores[team] = {"Pts": 0, "BP": 0, "BC": 0}
        scores[a]["BP"] += sa
        scores[a]["BC"] += sb
        scores[b]["BP"] += sb
        scores[b]["BC"] += sa
        if sa > sb:
            scores[a]["Pts"] += 2
        elif sb > sa:
            scores[b]["Pts"] += 2
    clas = pd.DataFrame(scores).T
    clas["Diff"] = clas["BP"] - clas["BC"]
    clas = clas.sort_values(["Pts", "Diff", "BP"], ascending=False).reset_index()
    clas.rename(columns={"index": "Équipe"}, inplace=True)
    return clas

classement = classement_from_results(matchs)
st.dataframe(classement)

# --- Demi-finales ---
st.divider()
st.subheader("⚔️ Demi-finales")
if "1er vs 4e" in " ".join(matchs["Équipe A"].tolist()):
    if st.button("⚙️ Mettre à jour les demi-finales maintenant"):
        if len(classement) >= 4:
            top4 = classement["Équipe"].tolist()[:4]
            matchs.loc[matchs["Équipe A"].str.contains("1er vs 4e"), ["Équipe A", "Équipe B"]] = [top4[0], top4[3]]
            matchs.loc[matchs["Équipe A"].str.contains("2e vs 3e"), ["Équipe A", "Équipe B"]] = [top4[1], top4[2]]
            matchs.to_csv(BRACKET_FILE, index=False)
            st.success("✅ Demi-finales mises à jour avec succès !")

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
            ax.text(x + 0.01, y + 0.065, m['Équipe A'], fontsize=10, fontweight="bold")
            ax.text(x + 0.01, y + 0.03, m['Équipe B'], fontsize=10, fontweight="bold")
            ax.text(x + 0.24, y + 0.04, f"{int(m['Score A'])}-{int(m['Score B'])}", fontsize=12, fontweight="bold")

    finale = matchs[matchs["Phase"] == "Finale"]
    if not finale.empty:
        m = finale.iloc[0]
        rect = Rectangle((0.55, 0.1), 0.3, 0.1, linewidth=3, edgecolor="gold", facecolor="white")
        ax.add_patch(rect)
        ax.text(0.56, 0.165, m['Équipe A'], fontsize=11, fontweight="bold")
        ax.text(0.56, 0.13, m['Équipe B'], fontsize=11, fontweight="bold")
        ax.text(0.78, 0.14, f"{int(m['Score A'])}-{int(m['Score B'])}", fontsize=12, color="gold", fontweight="bold")

        if m["Gagnant"]:
            st.markdown(f"<h2 style='text-align:center; color:gold;'>🏆 CHAMPION : {m['Gagnant']} ✨</h2>", unsafe_allow_html=True)
            st.markdown(
                """
                <style>
                @keyframes sparkle {
                    0% { opacity: 0; transform: scale(0.8) rotate(0deg); }
                    50% { opacity: 1; transform: scale(1.3) rotate(180deg); }
                    100% { opacity: 0; transform: scale(0.8) rotate(360deg); }
                }
                .sparkle {
                    position: fixed;
                    top: 0; left: 0;
                    width: 100vw; height: 100vh;
                    pointer-events: none;
                    z-index: 9999;
                    background-image: radial-gradient(circle, gold 1px, transparent 1px);
                    background-size: 10px 10px;
                    animation: sparkle 2s infinite ease-in-out;
                }
                </style>
                <div class='sparkle'></div>
                """,
                unsafe_allow_html=True,
            )

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
