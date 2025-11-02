import streamlit as st
import pandas as pd
import os
import random
import itertools
from datetime import datetime, timedelta, time
from utils import load_players
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("🏒 Génération du tournoi (4 équipes fixes)")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
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

    if len(attaquants) < 24:
        supl = defenseeurs.nlargest(24 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseeurs = defenseeurs.drop(supl.index)
    if len(defenseeurs) < 16:
        supl = attaquants.nlargest(16 - len(defenseeurs), "talent_defense")
        defenseeurs = pd.concat([defenseeurs, supl])
        attaquants = attaquants.drop(supl.index)

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
    st.success("✅ Équipes du tournoi générées !")

equipes = st.session_state.get("tournoi_equipes")

if equipes:
    st.subheader("📋 Composition des équipes")
    for nom, eq in equipes.items():
        st.markdown(f"### {nom} — Moyenne : **{eq['moyenne']}**")
        for i, trio in enumerate(eq["trios"], 1):
            if not trio.empty:
                st.write(f"**Trio {i} ({round(trio['talent_attaque'].mean(),2)}) :** {', '.join(trio['nom'])}")
        for i, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                st.write(f"**Duo {i} ({round(duo['talent_defense'].mean(),2)}) :** {', '.join(duo['nom'])}")
        st.divider()

    # --- Paramètres de temps ---
    st.subheader("⏱️ Paramètres de l’horaire")
    start_time = st.time_input("Heure de début du premier match", time(18, 0))
    match_duration = st.number_input("Durée d’un match de ronde (minutes)", 10, 120, 25, 5)
    demi_duration = st.number_input("Durée d’une demi-finale (minutes)", 10, 120, 30, 5)
    finale_duration = st.number_input("Durée de la finale (minutes)", 10, 120, 35, 5)
    pause = st.number_input("Pause entre les matchs (minutes)", 0, 60, 5, 5)
    zamboni_pause = st.number_input("Durée de la pause Zamboni (minutes)", 5, 30, 10, 5)

    # --- Création complète du tournoi ---
    def generer_matchs_equilibres(equipes):
        noms = list(equipes.keys())
        matchs_possibles = list(itertools.combinations(noms, 2))
        random.shuffle(matchs_possibles)

        matchs = pd.DataFrame(matchs_possibles, columns=["Équipe A", "Équipe B"])
        matchs["Phase"] = "Ronde"

        heure = datetime.combine(datetime.today(), start_time)
        rows = []
        match_counter = 0  # compteur global pour pauses Zamboni

        # --- Matchs de ronde ---
        for i, row in matchs.iterrows():
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

            # Pause Zamboni après chaque 3 matchs
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

            # Pause Zamboni après chaque 3 matchs
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

        # --- Pause forcée avant la finale ---
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
        with st.spinner("⏳ Génération du tournoi..."):
            matchs = generer_matchs_equilibres(equipes)
            matchs.to_csv(BRACKET_FILE, index=False)

        st.success("✅ Tournoi complet créé avec pauses Zamboni automatiques et pause avant la finale !")
        st.balloons()

        st.markdown("### 🕓 Horaire du tournoi")
        st.dataframe(matchs[["Heure", "Équipe A", "Équipe B", "Durée (min)", "Phase", "Type"]])

        # --- PDF ---
        st.subheader("📄 Télécharger le PDF")
        if st.button("💾 Générer le PDF"):
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(200, 770, f"Tournoi du {datetime.now().strftime('%Y-%m-%d')}")
            pdf.setFont("Helvetica", 12)
            y = 740
            pdf.drawString(50, y, "🕓 Horaire du tournoi :")
            y -= 20
            for _, r in matchs.iterrows():
                if r["Type"] == "Pause":
                    pdf.drawString(60, y, f"{r['Heure']} — {r['Équipe A']} ({r['Durée (min)']} min)")
                else:
                    pdf.drawString(60, y, f"{r['Heure']} ({r['Durée (min)']} min): {r['Équipe A']} vs {r['Équipe B']}")
                y -= 15
            pdf.save()
            buffer.seek(0)
            st.download_button(
                "⬇️ Télécharger le PDF",
                buffer,
                file_name=f"Tournoi_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

# --- Réinitialisation sécurisée ---
st.divider()
st.subheader("🧹 Réinitialiser le tournoi")
if os.path.exists(BRACKET_FILE):
    if st.button("🗑️ Supprimer le tournoi existant"):
        confirm = st.radio("Souhaitez-vous vraiment supprimer le tournoi ?", ["Non", "Oui, supprimer"], horizontal=True)
        if confirm == "Oui, supprimer":
            os.remove(BRACKET_FILE)
            for k in ["tournoi_equipes", "players_present"]:
                st.session_state.pop(k, None)
            st.success("✅ Tournoi supprimé avec succès.")
