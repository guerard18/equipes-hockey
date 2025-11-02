import streamlit as st
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from utils import load_players, save_history
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import itertools

st.title("2️⃣ Formation des équipes de hockey 🏒")
st.markdown(
    "Forme automatiquement entre **2 et 8 équipes équilibrées** et propose un mode **Tournoi** avec "
    "création automatique de matchs garantissant 3 parties par équipe."
)

# --- Configuration ---
st.subheader("⚙️ Configuration du match / tournoi")
date_match = st.date_input("📅 Date du match", datetime.now().date())
nb_equipes = st.slider("Nombre d'équipes :", min_value=2, max_value=8, value=4)
mode_tournoi = st.checkbox("🏆 Activer le mode tournoi (3 matchs garantis par équipe)")

# --- Noms personnalisés ---
default_names = ["BLANCS ⚪", "NOIRS ⚫", "BLEUS 🔵", "VERTS 🟢", "ROUGES 🔴", "JAUNES 🟡", "ORANGES 🟠", "GRIS ⚫⚪"]
team_names = []
st.markdown("### ✏️ Nommer vos équipes")
cols = st.columns(4)
for i in range(nb_equipes):
    with cols[i % 4]:
        team_names.append(st.text_input(f"Équipe {i+1}", default_names[i]))

# Charger les joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# --- GÉNÉRATION DES ÉQUIPES ---
def generate_teams(players_present: pd.DataFrame, nb_equipes: int):
    if players_present.empty:
        return None

    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    nb_trios_total = nb_equipes * 2  # 2 trios par équipe
    nb_duos_total = nb_equipes * 2   # 2 duos par équipe

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

    trios = snake_draft(attaquants, nb_trios_total, "talent_attaque")
    duos = snake_draft(defenseurs, nb_duos_total, "talent_defense")
    random.shuffle(trios)
    random.shuffle(duos)

    equipes = {}
    for i in range(nb_equipes):
        equipes[i] = {"trios": trios[i::nb_equipes], "duos": duos[i::nb_equipes]}

    def moyenne(unites, colonne):
        valeurs = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else 0

    for eq in equipes.values():
        moyA = moyenne(eq["trios"], "talent_attaque")
        moyD = moyenne(eq["duos"], "talent_defense")
        eq["moyenne"] = round((moyA + moyD) / 2, 2)

    return equipes


# --- GÉNÉRATION ET AFFICHAGE ---
if st.button("🎯 Générer les équipes"):
    st.session_state["teams"] = generate_teams(players_present, nb_equipes)

teams = st.session_state.get("teams")

# --- AFFICHAGE DES ÉQUIPES ---
if teams:
    for i, eq in teams.items():
        st.subheader(f"🏒 {team_names[i]} — Moyenne : {eq['moyenne']}")
        for j, trio in enumerate(eq["trios"], 1):
            if not trio.empty:
                moy = round(trio["talent_attaque"].mean(), 2)
                st.write(f"**Trio {j} ({moy}) :** {', '.join(trio['nom'])}")
        for j, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                moy = round(duo["talent_defense"].mean(), 2)
                st.write(f"**Duo {j} ({moy}) :** {', '.join(duo['nom'])}")
        st.divider()

    # --- MODE TOURNOI ---
    if mode_tournoi:
        st.subheader("🏆 Bracket du tournoi (3 matchs garantis)")

        equipes_list = [team_names[i] for i in range(nb_equipes)]

        # Round-robin partiel : chaque équipe joue 3 matchs
        matchups = []
        for i, e1 in enumerate(equipes_list):
            adversaires = [e2 for j, e2 in enumerate(equipes_list) if j != i]
            random.shuffle(adversaires)
            for opp in adversaires[:3]:
                if {e1, opp} not in [{m[0], m[1]} for m in matchups]:
                    matchups.append((e1, opp))

        tournoi_df = pd.DataFrame(matchups, columns=["Équipe A", "Équipe B"])
        st.dataframe(tournoi_df, use_container_width=True)
        st.success(f"✅ {len(tournoi_df)} matchs générés ({len(equipes_list)} équipes, 3 matchs garantis chacune).")

        if st.button("💾 Enregistrer le tournoi"):
            save_history(
                equipeB=[], equipeN=[], moyB=0, moyN=0,
                date_match=date_match.strftime("%Y-%m-%d"),
                triosB=[], duosB=[], triosN=[], duosN=[],
            )
            tournoi_df.to_csv("data/tournoi_bracket.csv", index=False)
            st.success("✅ Tournoi enregistré dans les fichiers de données.")

    # --- PDF ---
    st.divider()
    st.subheader("📄 Télécharger les équipes en PDF")

    if st.button("💾 Générer le PDF"):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(200, 770, f"Match du {date_match.strftime('%Y-%m-%d')}")
        pdf.setFont("Helvetica", 12)

        y = 740
        for i, eq in teams.items():
            pdf.drawString(50, y, f"{team_names[i]} (moyenne {eq['moyenne']})")
            y -= 20
            for j, trio in enumerate(eq["trios"], 1):
                pdf.drawString(60, y, f"Trio {j}: {', '.join(trio['nom'])}")
                y -= 15
            for j, duo in enumerate(eq["duos"], 1):
                pdf.drawString(60, y, f"Duo {j}: {', '.join(duo['nom'])}")
                y -= 15
            y -= 20

        if mode_tournoi:
            y -= 20
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(50, y, "🏆 Tournoi - Matchs")
            y -= 20
            for a, b in matchups:
                pdf.drawString(60, y, f"{a} vs {b}")
                y -= 15

        pdf.save()
        buffer.seek(0)
        st.download_button(
            label="⬇️ Télécharger le PDF",
            data=buffer,
            file_name=f"Tournoi_{date_match}.pdf" if mode_tournoi else f"Match_{date_match}.pdf",
            mime="application/pdf"
        )
