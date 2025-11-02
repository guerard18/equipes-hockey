import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt

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
        if "Score" in col:
            matchs[col] = 0
        elif col == "Prolongation":
            matchs[col] = False
        else:
            matchs[col] = ""

# --- Saisie des résultats ---
st.divider()
st.subheader("🕓 Horaire et résultats des matchs")

for i, row in matchs.iterrows():
    heure = "" if pd.isna(row["Heure"]) else str(row["Heure"]).strip()

    # Nom des phases
    if row["Phase"] == "Ronde":
        phase_label = "Ronde éliminatoire"
    elif row["Phase"] == "Demi-finale":
        phase_label = "Demi-finale"
    elif row["Phase"] == "Finale":
        phase_label = "Finale"
    else:
        phase_label = row["Phase"]

    st.markdown(f"### 🕓 {heure} — {phase_label}")

    if row["Type"] == "Match":
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
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
            if row["Phase"] == "Ronde":
                prolong = st.checkbox("Prolongation", value=bool(row["Prolongation"]), key=f"p{i}")
                matchs.loc[i, "Prolongation"] = prolong
            else:
                st.write("")
        with col4:
            gagnant = row["Équipe A"] if score_a > score_b else row["Équipe B"] if score_b > score_a else ""
            matchs.loc[i, ["Score A", "Score B", "Gagnant"]] = [score_a, score_b, gagnant]

    else:
        texte_pause = str(row["Équipe A"]).strip()
        if texte_pause and texte_pause.lower() != "nan":
            st.info(f"🧊 {texte_pause} ({row['Durée (min)']} minutes)")
        else:
            st.info(f"🧊 Pause ({row['Durée (min)']} minutes)")

        # --- Bouton mise à jour demi ---
        if "avant la finale" not in texte_pause and any(matchs["Phase"].str.contains("Demi-finale")):
            idx_demi = matchs[matchs["Phase"] == "Demi-finale"].index.min()
            if i == idx_demi - 1:
                st.markdown("### ⚙️ **Mettre à jour les demi-finales**")
                if st.button("🔁 Mettre à jour maintenant", key="update_demi_button"):
                    st.session_state["update_demi"] = True

        # --- Bouton mise à jour finale ---
        if "avant la finale" in texte_pause and any(matchs["Phase"].str.contains("Finale")):
            st.markdown("### 🏆 **Mettre à jour la finale**")
            if st.button("🔁 Mettre à jour la finale maintenant", key="update_finale_button"):
                st.session_state["update_finale"] = True

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
        prolong = bool(row.get("Prolongation", False))
        for team in [a, b]:
            if team not in scores:
                scores[team] = {"Pts": 0, "BP": 0, "BC": 0}
        scores[a]["BP"] += sa
        scores[a]["BC"] += sb
        scores[b]["BP"] += sb
        scores[b]["BC"] += sa
        if sa > sb:
            scores[a]["Pts"] += 2
            if prolong:
                scores[b]["Pts"] += 1
        elif sb > sa:
            scores[b]["Pts"] += 2
            if prolong:
                scores[a]["Pts"] += 1
    clas = pd.DataFrame(scores).T
    clas["Diff"] = clas["BP"] - clas["BC"]
    clas = clas.sort_values(["Pts", "Diff", "BP"], ascending=False).reset_index()
    clas.rename(columns={"index": "Équipe"}, inplace=True)
    return clas

classement = classement_from_results(matchs)
st.dataframe(classement)

# --- Mise à jour des phases ---
if "update_demi" in st.session_state and st.session_state["update_demi"]:
    if len(classement) >= 4:
        top4 = classement["Équipe"].tolist()[:4]
        matchs.loc[matchs["Équipe A"].str.contains("1er vs 4e"), ["Équipe A", "Équipe B"]] = [top4[0], top4[3]]
        matchs.loc[matchs["Équipe A"].str.contains("2e vs 3e"), ["Équipe A", "Équipe B"]] = [top4[1], top4[2]]
        matchs.to_csv(BRACKET_FILE, index=False)
        st.success("✅ Demi-finales mises à jour avec succès !")
        st.session_state["update_demi"] = False

if "update_finale" in st.session_state and st.session_state["update_finale"]:
    demi = matchs[matchs["Phase"] == "Demi-finale"]
    gagnants = demi["Gagnant"].tolist()
    if len(gagnants) == 2 and all(gagnants):
        matchs.loc[matchs["Phase"] == "Finale", ["Équipe A", "Équipe B"]] = gagnants
        matchs.to_csv(BRACKET_FILE, index=False)
        st.success("✅ Finale mise à jour avec les gagnants des demi-finales !")
        st.session_state["update_finale"] = False

# --- Nouveau Bracket (style minimaliste comme l’image) ---
st.divider()
st.subheader("🎯 Bracket du tournoi")

def draw_simple_bracket():
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis("off")

    # Lignes de la demi-finale gauche
    ax.plot([0.1, 0.3], [0.8, 0.8], color='black', lw=2)
    ax.plot([0.1, 0.3], [0.6, 0.6], color='black', lw=2)
    ax.plot([0.3, 0.4], [0.8, 0.7], color='black', lw=2)
    ax.plot([0.3, 0.4], [0.6, 0.7], color='black', lw=2)

    # Lignes vers la finale
    ax.plot([0.4, 0.6], [0.7, 0.7], color='black', lw=2)
    ax.plot([0.6, 0.7], [0.7, 0.5], color='black', lw=2)

    # Lignes des demi-finales inférieures
    ax.plot([0.1, 0.3], [0.4, 0.4], color='black', lw=2)
    ax.plot([0.1, 0.3], [0.2, 0.2], color='black', lw=2)
    ax.plot([0.3, 0.4], [0.4, 0.3], color='black', lw=2)
    ax.plot([0.3, 0.4], [0.2, 0.3], color='black', lw=2)

    # Ligne de finale
    ax.plot([0.4, 0.6], [0.3, 0.3], color='black', lw=2)

    # Lien vers CHAMPION
    ax.plot([0.6, 0.8], [0.5, 0.5], color='black', lw=2)
    ax.text(0.81, 0.48, "CHAMPION", fontsize=10, fontweight="bold",
            ha='left', va='center', bbox=dict(facecolor='lightgray', edgecolor='black'))

    plt.xlim(0, 1)
    plt.ylim(0, 1)
    st.pyplot(fig)

draw_simple_bracket()
