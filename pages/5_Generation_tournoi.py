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

# --- Charger les joueurs ---
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

# --- Fonctions utilitaires ---
def snake_draft(df, nb_groupes, colonne):
    if df.empty:
        return [pd.DataFrame() for _ in range(nb_groupes)]
    df = df.sample(frac=1).sort_values(colonne, ascending=False).reset_index(drop=True)
    groupes = [[] for _ in range(nb_groupes)]
    sens = 1
    idx = 0
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

# --- Génération automatique des 4 équipes ---
def generer_equipes_tournoi(players_present):
    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    if len(attaquants) < 24:
        supl = defenseurs.nlargest(24 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseeurs.drop(supl.index)

    if len(defenseurs) < 16:
        supl = attaquants.nlargest(16 - len(defenseurs), "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    trios = snake_draft(attaquants, 8, "talent_attaque")
    duos = snake_draft(defenseurs, 8, "talent_defense")
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
        eq["moyenne"] = round((sum(moy_trios + moy_duos) / len(moy_trios + moy_duos)), 2)

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
                moy = round(trio["talent_attaque"].mean(), 2)
                st.write(f"**Trio {i} ({moy}) :** {', '.join(trio['nom'])}")
        for i, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                moy = round(duo["talent_defense"].mean(), 2)
                st.write(f"**Duo {i} ({moy}) :** {', '.join(duo['nom'])}")
        st.divider()

    # --- Paramètres de temps ---
    st.subheader("⏱️ Paramètres de l’horaire")
    start_time = st.time_input("Heure de début du premier match", time(18, 0))
    match_duration = st.number_input("Durée d’un match (minutes)", 10, 120, 25, 5)
    pause = st.number_input("Pause entre les matchs (minutes)", 0, 60, 5, 5)
    zamboni_pause = st.number_input("Durée de la pause Zamboni (minutes)", 5, 30, 10, 5)

    # --- Création optimisée des matchs ---
    def generer_matchs_equilibres(equipes):
        noms = list(equipes.keys())
        matchs_possibles = list(itertools.combinations(noms, 2))
        random.shuffle(matchs_possibles)

        horaire = []
        consecutifs = {e: 0 for e in noms}

        while matchs_possibles:
            match_choisi = None
            for match in matchs_possibles:
                e1, e2 = match
                if consecutifs[e1] < 2 and consecutifs[e2] < 2:
                    match_choisi = match
                    break

            if match_choisi is None:
                break

            horaire.append(match_choisi)
            matchs_possibles.remove(match_choisi)

            for e in consecutifs:
                if e in match_choisi:
                    consecutifs[e] += 1
                else:
                    consecutifs[e] = max(0, consecutifs[e] - 1)

        for m in matchs_possibles:
            if m not in horaire:
                horaire.append(m)

        matchs = pd.DataFrame(horaire, columns=["Équipe A", "Équipe B"])
        matchs["Phase"] = "Ronde"

        # Ajout des horaires avec pause Zamboni
        heure = datetime.combine(datetime.today(), start_time)
        horaires, evenements = [], []
        for i in range(len(matchs)):
            horaires.append(heure.strftime("%H:%M"))
            evenements.append("Match")
            heure += timedelta(minutes=match_duration + pause)
            if (i + 1) % 3 == 0 and i + 1 < len(matchs):
                horaires.append(heure.strftime("%H:%M"))
                evenements.append("🧊 Pause Zamboni")
                heure += timedelta(minutes=zamboni_pause)

        # Synchroniser
        df_final = []
        idx_match = 0
        for ev, h in zip(evenements, horaires):
            if ev == "Match":
                row = matchs.iloc[idx_match].copy()
                row["Heure"] = h
                row["Durée (min)"] = match_duration
                row["Type"] = "Match"
                df_final.append(row)
                idx_match += 1
            else:
                df_final.append(pd.Series({
                    "Heure": h,
                    "Équipe A": "🧊 Pause Zamboni",
                    "Équipe B": "",
                    "Durée (min)": zamboni_pause,
                    "Phase": "",
                    "Type": "Pause"
                }))

        return pd.DataFrame(df_final)

    if st.button("🏁 Créer le tournoi"):
        with st.spinner("⏳ Génération du tournoi..."):
            matchs = generer_matchs_equilibres(equipes)
            matchs.to_csv(BRACKET_FILE, index=False)

        st.success("✅ Tournoi créé avec succès ! Consulte **Tournoi en cours** pour suivre les matchs.")
        st.balloons()

        st.markdown("### 🕓 Horaire du tournoi")
        df_affiche = matchs.copy()
        df_affiche.index = [f"Événement {i+1}" for i in range(len(df_affiche))]
        st.dataframe(df_affiche[["Heure", "Équipe A", "Équipe B", "Durée (min)", "Phase", "Type"]])

        # --- PDF export ---
        st.subheader("📄 Télécharger le PDF de l’horaire")
        if st.button("💾 Générer le PDF de l’horaire"):
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(200, 770, f"Tournoi du {datetime.now().strftime('%Y-%m-%d')}")
            pdf.setFont("Helvetica", 12)

            y = 740
            pdf.drawString(50, y, "🕓 Horaire du tournoi :")
            y -= 20
            for i, row in matchs.iterrows():
                if row["Type"] == "Pause":
                    pdf.drawString(60, y, f"{row['Heure']} — 🧊 Pause Zamboni ({row['Durée (min)']} min)")
                else:
                    pdf.drawString(60, y, f"{row['Heure']} ({row['Durée (min)']} min): {row['Équipe A']} vs {row['Équipe B']}")
                y -= 15

            pdf.save()
            buffer.seek(0)
            st.download_button(
                label="⬇️ Télécharger le PDF",
                data=buffer,
                file_name=f"Tournoi_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

# --- Suppression sécurisée ---
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
