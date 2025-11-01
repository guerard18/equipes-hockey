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
    "Cette page forme **4 trios d’attaque** et **4 duos de défense** équilibrés "
    "et les répartit dans deux équipes : **⚪ Blanc** et **⚫ Noir**. "
    "Chaque clic génère une nouvelle composition aléatoire équilibrée 🎲."
)

players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

if st.button("🎯 Former de nouvelles équipes équilibrées (aléatoires)"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent.")
        st.stop()

    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )
    players_present["talent_total"] = players_present[["talent_attaque", "talent_defense"]].mean(axis=1)

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    if len(defenseurs) < 8:
        besoin = 8 - len(defenseurs)
        supl = attaquants.nlargest(besoin, "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    if len(attaquants) < 12:
        besoin = 12 - len(attaquants)
        supl = defenseurs.nlargest(besoin, "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

    def snake_draft(df, nb_groupes, colonne):
        df = df.sample(frac=1, random_state=random.randint(0, 10000)).sort_values(
            colonne, ascending=False
        ).reset_index(drop=True)
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
    equipeN_trios = trios[1::2]  # Noir
    equipeB_duos = duos[::2]
    equipeN_duos = duos[1::2]

    def moyenne_globale(unites, colonne):
        valeurs = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else 0

    moyB = round((moyenne_globale(equipeB_trios, "talent_attaque") + moyenne_globale(equipeB_duos, "talent_defense")) / 2, 2)
    moyN = round((moyenne_globale(equipeN_trios, "talent_attaque") + moyenne_globale(equipeN_duos, "talent_defense")) / 2, 2)

    def afficher_equipe(nom, trios, duos, moyenne, couleur):
        st.markdown(f"<h2 style='color:{couleur}'>{nom}</h2>", unsafe_allow_html=True)
        st.write(f"**Moyenne globale :** {moyenne}")
        for i, trio in enumerate(trios, 1):
            st.markdown(f"**Trio {i} (attaque)**")
            for _, p in trio.iterrows():
                st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
        for i, duo in enumerate(duos, 1):
            st.markdown(f"**Duo {i} (défense)**")
            for _, p in duo.iterrows():
                st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

    st.divider()
    afficher_equipe("⚪ Équipe Blanche", equipeB_trios, equipeB_duos, moyB, "gray")
    st.divider()
    afficher_equipe("⚫ Équipe Noire", equipeN_trios, equipeN_duos, moyN, "black")

    if st.button("💾 Enregistrer ces équipes dans l’historique"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        equipeB = [p for trio in equipeB_trios + equipeB_duos for p in trio["nom"].tolist()]
        equipeN = [p for trio in equipeN_trios + equipeN_duos for p in trio["nom"].tolist()]
        save_history(equipeB, equipeN, moyB, moyN, date)
        st.success("✅ Équipes enregistrées dans l’historique !")

    st.divider()
    st.subheader("📧 Envoyer les équipes par courriel")

    with st.expander("Configurer et envoyer"):
        expediteur = st.text_input("Adresse Gmail d’expéditeur")
        mot_passe = st.text_input("Mot de passe d’application Gmail", type="password")
        destinataires = st.text_area("Destinataires (séparés par des virgules)")

        def creer_tableau(titre, trios, duos, couleur):
            html = f"<h3 style='color:{couleur}'>{titre}</h3><table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;'>"
            html += "<tr><th>Type</th><th>Joueurs</th></tr>"
            for i, trio in enumerate(trios, 1):
                joueurs = ", ".join(trio["nom"].tolist())
                html += f"<tr><td>Trio {i}</td><td>{joueurs}</td></tr>"
            for i, duo in enumerate(duos, 1):
                joueurs = ", ".join(duo["nom"].tolist())
                html += f"<tr><td>Duo {i}</td><td>{joueurs}</td></tr>"
            html += "</table>"
            return html

        corps_html = f"""
        <html><body style='font-family:Arial,sans-serif;'>
        <h2>🏒 Composition des équipes ({datetime.now().strftime("%Y-%m-%d %H:%M")})</h2>
        <p><b>Moyenne Blanc:</b> {moyB} | <b>Moyenne Noir:</b> {moyN}</p>
        {creer_tableau('⚪ Équipe Blanche', equipeB_trios, equipeB_duos, 'gray')}
        <br>
        {creer_tableau('⚫ Équipe Noire', equipeN_trios, equipeN_duos, 'black')}
        <p style='margin-top:20px;'>— Envoyé automatiquement par <b>HockeyApp</b>.</p>
        </body></html>
        """

        if st.button("📨 Envoyer le courriel HTML"):
            if not expediteur or not mot_passe or not destinataires:
                st.error("❌ Remplis tous les champs avant d’envoyer.")
            else:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["From"] = expediteur
                    msg["To"] = destinataires
                    msg["Subject"] = "⚪⚫ Composition des équipes Hockey"
                    msg.attach(MIMEText(corps_html, "html", "utf-8"))

                    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                        server.login(expediteur, mot_passe)
                        server.send_message(msg)

                    st.success(f"✅ Courriel envoyé à : {destinataires}")
                except Exception as e:
                    st.error(f"⚠️ Erreur d’envoi : {e}")
