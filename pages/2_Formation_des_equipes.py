import streamlit as st
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from utils import load_players, save_history

st.title("2️⃣ Formation des équipes de hockey 🏒")
st.markdown(
    "Forme automatiquement deux équipes équilibrées (⚪ Blanc / ⚫ Noir) "
    "avec 4 trios et 4 duos équilibrés."
)

# Sélecteur de date du match
st.subheader("📅 Date du match")
date_match = st.date_input("Match du :", datetime.now().date())

# Charger les joueurs présents
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# --- FONCTION DE GÉNÉRATION DES ÉQUIPES ---
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

    if len(defenseurs) < 8:
        supl = attaquants.nlargest(8 - len(defenseurs), "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    if len(attaquants) < 12:
        supl = defenseurs.nlargest(12 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

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

    equipeB_trios = trios[::2]  # Blanc
    equipeN_trios = trios[1::2] # Noir
    equipeB_duos = duos[::2]
    equipeN_duos = duos[1::2]

    def moyenne(unites, colonne):
        valeurs = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else 0

    moyB = round((moyenne(equipeB_trios, "talent_attaque") + moyenne(equipeB_duos, "talent_defense")) / 2, 2)
    moyN = round((moyenne(equipeN_trios, "talent_attaque") + moyenne(equipeN_duos, "talent_defense")) / 2, 2)

    return dict(
        equipeB_trios=equipeB_trios,
        equipeN_trios=equipeN_trios,
        equipeB_duos=equipeB_duos,
        equipeN_duos=equipeN_duos,
        moyB=moyB,
        moyN=moyN
    )

# --- GÉNÉRATION ET AFFICHAGE ---
if st.button("🎯 Générer les équipes équilibrées"):
    st.session_state["teams"] = generate_teams(players_present)

teams = st.session_state.get("teams")

if teams:
    st.subheader("⚪ BLANCS")
    for i, trio in enumerate(teams["equipeB_trios"], 1):
        st.write(f"**Trio {i}**: {', '.join(trio['nom'])}")
    for i, duo in enumerate(teams["equipeB_duos"], 1):
        st.write(f"**Duo {i}**: {', '.join(duo['nom'])}")
    st.write(f"**Moyenne :** {teams['moyB']}")

    st.subheader("⚫ NOIRS")
    for i, trio in enumerate(teams["equipeN_trios"], 1):
        st.write(f"**Trio {i}**: {', '.join(trio['nom'])}")
    for i, duo in enumerate(teams["equipeN_duos"], 1):
        st.write(f"**Duo {i}**: {', '.join(duo['nom'])}")
    st.write(f"**Moyenne :** {teams['moyN']}")

    if st.button("💾 Enregistrer dans l’historique"):
        equipeB = [p for t in (teams["equipeB_trios"] + teams["equipeB_duos"]) for p in t["nom"].tolist()]
        equipeN = [p for t in (teams["equipeN_trios"] + teams["equipeN_duos"]) for p in t["nom"].tolist()]
        save_history(equipeB, equipeN, teams["moyB"], teams["moyN"], date_match.strftime("%Y-%m-%d"))
        st.success("✅ Équipes enregistrées dans l’historique.")

    # --- Envoi de courriel HTML ---
    st.subheader("📧 Envoyer les équipes par courriel")
    expediteur = st.text_input("Adresse Gmail d’expéditeur")
    mot_passe = st.text_input("Mot de passe d’application Gmail", type="password")
    destinataires = st.text_area("Destinataires (séparés par des virgules)")

    if st.button("📨 Envoyer le courriel HTML"):
        corps_html = f"""
        <html><body>
        <h2>🏒 Match du {date_match.strftime("%Y-%m-%d")}</h2>
        <h3>⚪ BLANCS (moyenne {teams['moyB']})</h3>
        {', '.join(equipeB)}<br><br>
        <h3>⚫ NOIRS (moyenne {teams['moyN']})</h3>
        {', '.join(equipeN)}
        </body></html>
        """
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = expediteur
            msg["To"] = destinataires
            msg["Subject"] = f"🏒 Match du {date_match.strftime('%Y-%m-%d')} - Équipes"
            msg.attach(MIMEText(corps_html, "html", "utf-8"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(expediteur, mot_passe)
                server.send_message(msg)

            st.success("✅ Courriel envoyé avec succès !")
        except Exception as e:
            st.error(f"⚠️ Erreur : {e}")
