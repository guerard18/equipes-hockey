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

st.title("2️⃣ Formation des équipes de hockey 🏒")
st.markdown(
    "Forme automatiquement **deux équipes équilibrées** (**BLANCS ⚪ / NOIRS ⚫**) "
    "avec 4 trios et 4 duos équilibrés, et affiche leurs moyennes de talent."
)

# --- Sélecteur de date du match ---
st.subheader("📅 Date du match")
date_match = st.date_input("Match du :", datetime.now().date())

# Charger les joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# --- Fonction pour générer deux équipes équilibrées ---
def generate_teams(players_present: pd.DataFrame):
    if players_present.empty:
        return None

    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    # équilibrage
    if len(defenseurs) < 8:
        supl = attaquants.nlargest(8 - len(defenseurs), "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    if len(attaquants) < 12:
        supl = defenseurs.nlargest(12 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

    # répartition snake draft
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

    trios = snake_draft(attaquants, 4, "talent_attaque")
    duos = snake_draft(defenseurs, 4, "talent_defense")
    random.shuffle(trios)
    random.shuffle(duos)

    equipeB_trios = trios[::2]
    equipeN_trios = trios[1::2]
    equipeB_duos = duos[::2]
    equipeN_duos = duos[1::2]

    def moyenne(unites, colonne):
        valeurs = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else 0

    moyB = round((moyenne(equipeB_trios, "talent_attaque") + moyenne(equipeB_duos, "talent_defense")) / 2, 2)
    moyN = round((moyenne(equipeN_trios, "talent_attaque") + moyenne(equipeN_duos, "talent_defense")) / 2, 2)

    # compter les joueurs
    nb_joueurs_B = sum(len(t) for t in (equipeB_trios + equipeB_duos))
    nb_joueurs_N = sum(len(t) for t in (equipeN_trios + equipeN_duos))

    return dict(
        equipeB_trios=equipeB_trios,
        equipeN_trios=equipeN_trios,
        equipeB_duos=equipeB_duos,
        equipeN_duos=equipeN_duos,
        moyB=moyB,
        moyN=moyN,
        nbB=nb_joueurs_B,
        nbN=nb_joueurs_N
    )

# --- GÉNÉRATION DES ÉQUIPES ---
if st.button("🎯 Générer les équipes équilibrées"):
    st.session_state["teams"] = generate_teams(players_present)

teams = st.session_state.get("teams")

# --- AFFICHAGE AVEC PROTECTION ---
if not teams:
    st.warning("Aucune équipe n’a encore été générée.")
elif not all(k in teams for k in ["equipeB_trios", "equipeN_trios", "equipeB_duos", "equipeN_duos"]):
    st.error("⚠️ Erreur de génération : certaines données d’équipes sont manquantes.")
    st.info("Cliquez sur **🎯 Générer les équipes équilibrées** pour relancer la création.")
else:
    # --- ÉQUIPE BLANCHE ---
    st.subheader(f"⚪ BLANCS — {teams['nbB']} joueurs")
    for i, trio in enumerate(teams["equipeB_trios"], 1):
        if not trio.empty:
            moy = round(trio["talent_attaque"].mean(), 2)
            st.write(f"**Trio {i} ({moy}) :** {', '.join(trio['nom'])}")
    for i, duo in enumerate(teams["equipeB_duos"], 1):
        if not duo.empty:
            moy = round(duo["talent_defense"].mean(), 2)
            st.write(f"**Duo {i} ({moy}) :** {', '.join(duo['nom'])}")
    st.write(f"### Moyenne totale : {teams['moyB']}")

    # --- ÉQUIPE NOIRE ---
    st.subheader(f"⚫ NOIRS — {teams['nbN']} joueurs")
    for i, trio in enumerate(teams["equipeN_trios"], 1):
        if not trio.empty:
            moy = round(trio["talent_attaque"].mean(), 2)
            st.write(f"**Trio {i} ({moy}) :** {', '.join(trio['nom'])}")
    for i, duo in enumerate(teams["equipeN_duos"], 1):
        if not duo.empty:
            moy = round(duo["talent_defense"].mean(), 2)
            st.write(f"**Duo {i} ({moy}) :** {', '.join(duo['nom'])}")
    st.write(f"### Moyenne totale : {teams['moyN']}")

    # --- Enregistrement dans l'historique ---
    if st.button("💾 Enregistrer dans l’historique"):
        equipeB = [p for t in (teams["equipeB_trios"] + teams["equipeB_duos"]) for p in t["nom"].tolist()]
        equipeN = [p for t in (teams["equipeN_trios"] + teams["equipeN_duos"]) for p in t["nom"].tolist()]
        save_history(
            equipeB, equipeN, teams["moyB"], teams["moyN"],
            date_match.strftime("%Y-%m-%d"),
            triosB=teams["equipeB_trios"], duosB=teams["equipeB_duos"],
            triosN=teams["equipeN_trios"], duosN=teams["equipeN_duos"]
        )
        st.success("✅ Équipes enregistrées dans l’historique.")

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
        pdf.drawString(50, y, f"⚪ BLANCS ({teams['nbB']} joueurs, moyenne {teams['moyB']})")
        y -= 20
        for i, trio in enumerate(teams["equipeB_trios"], 1):
            pdf.drawString(60, y, f"Trio {i}: {', '.join(trio['nom'])}")
            y -= 15
        for i, duo in enumerate(teams["equipeB_duos"], 1):
            pdf.drawString(60, y, f"Duo {i}: {', '.join(duo['nom'])}")
            y -= 15

        y -= 20
        pdf.drawString(50, y, f"⚫ NOIRS ({teams['nbN']} joueurs, moyenne {teams['moyN']})")
        y -= 20
        for i, trio in enumerate(teams["equipeN_trios"], 1):
            pdf.drawString(60, y, f"Trio {i}: {', '.join(trio['nom'])}")
            y -= 15
        for i, duo in enumerate(teams["equipeN_duos"], 1):
            pdf.drawString(60, y, f"Duo {i}: {', '.join(duo['nom'])}")
            y -= 15

        pdf.save()
        buffer.seek(0)
        st.download_button(
            label="⬇️ Télécharger le PDF",
            data=buffer,
            file_name=f"Match_{date_match}.pdf",
            mime="application/pdf"
        )

# --- BOUTON VERS TOURNOI ---
st.divider()
st.subheader("🏆 Mode tournoi")
st.markdown("Vous pouvez aussi créer un tournoi avec les joueurs présents actuels.")
if st.button("➡️ Créer un tournoi à partir des joueurs présents"):
    st.session_state["joueurs_pour_tournoi"] = players_present
    st.success("✅ Joueurs copiés vers le mode tournoi.")
    st.info("Allez maintenant dans la page **Configuration → Onglet Tournoi** pour lancer la création du tournoi.")
