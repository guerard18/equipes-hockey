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
    "Les résultats sont conservés tant que tu ne régénères pas."
)

# ------------------------------
# Chargement des joueurs présents
# ------------------------------
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")
if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# ------------------------------
# Génération d’équipes (fonction)
# ------------------------------
def generate_teams(players_present: pd.DataFrame):
    if players_present.empty:
        return None

    # Poste principal
    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )
    players_present["talent_total"] = players_present[["talent_attaque", "talent_defense"]].mean(axis=1)

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    # Compléter si un poste est sous-représenté
    if len(defenseurs) < 8 and len(attaquants) > 0:
        besoin = 8 - len(defenseurs)
        supl = attaquants.nlargest(besoin, "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    if len(attaquants) < 12 and len(defenseurs) > 0:
        besoin = 12 - len(attaquants)
        supl = defenseurs.nlargest(besoin, "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

    # Snake draft équilibré + aléatoire
    def snake_draft(df, nb_groupes, colonne):
        if df.empty:
            return [pd.DataFrame() for _ in range(nb_groupes)]
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
    duos  = snake_draft(defenseurs, 4, "talent_defense")

    # Mélange léger avant attribution
    random.shuffle(trios)
    random.shuffle(duos)

    # Attribution Blanc / Noir
    equipeB_trios = trios[::2]  # Blanc
    equipeN_trios = trios[1::2] # Noir
    equipeB_duos  = duos[::2]
    equipeN_duos  = duos[1::2]

    def moyenne_globale(unites, colonne):
        vals = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    moyB = round((moyenne_globale(equipeB_trios, "talent_attaque") + moyenne_globale(equipeB_duos, "talent_defense")) / 2, 2)
    moyN = round((moyenne_globale(equipeN_trios, "talent_attaque") + moyenne_globale(equipeN_duos, "talent_defense")) / 2, 2)

    return {
        "equipeB_trios": equipeB_trios,
        "equipeB_duos":  equipeB_duos,
        "equipeN_trios": equipeN_trios,
        "equipeN_duos":  equipeN_duos,
        "moyB": moyB,
        "moyN": moyN,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

# ------------------------------
# Boutons de génération / régénération
# ------------------------------
cols_top = st.columns(2)
if cols_top[0].button("🎯 Générer des équipes équilibrées"):
    st.session_state["teams"] = generate_teams(players_present)

if cols_top[1].button("🔁 Régénérer (nouvelle version aléatoire)"):
    st.session_state["teams"] = generate_teams(players_present)

# ------------------------------
# Affichage à partir de l'état (persistant)
# ------------------------------
teams = st.session_state.get("teams")

def afficher_unites(titre, unites, colonne):
    st.subheader(titre)
    if not unites:
        st.write("—")
        return
    moyennes = []
    for i, unite in enumerate(unites, 1):
        if unite.empty:
            continue
        moyenne = round(unite[colonne].mean(), 2)
        moyennes.append(moyenne)
        st.markdown(f"**{titre[:-1]} {i}** — Moyenne : {moyenne}")
        for _, p in unite.iterrows():
            val = p[colonne]
            st.write(f"- {p['nom']} ({val:.1f})")
    if moyennes:
        st.info(f"Moyenne des {titre.lower()} : {round(sum(moyennes)/len(moyennes),2)} ± {round(pd.Series(moyennes).std(),2)}")

def afficher_equipe(nom, trios, duos, moyenne, couleur):
    st.markdown(f"<h2 style='color:{couleur}'>{nom}</h2>", unsafe_allow_html=True)
    st.write(f"**Moyenne globale :** {moyenne}")
    for i, trio in enumerate(trios, 1):
        if trio.empty: 
            continue
        st.markdown(f"**Trio {i} (attaque)**")
        for _, p in trio.iterrows():
            st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
    for i, duo in enumerate(duos, 1):
        if duo.empty: 
            continue
        st.markdown(f"**Duo {i} (défense)**")
        for _, p in duo.iterrows():
            st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

if teams:
    st.caption(f"🕒 Généré le {teams['generated_at']}")
    st.header("🔢 Lignes équilibrées créées")
    # Affiche les 8 lignes au total (info)
    afficher_unites("Trios", teams["equipeB_trios"] + teams["equipeN_trios"], "talent_attaque")
    afficher_unites("Duos",  teams["equipeB_duos"]  + teams["equipeN_duos"],  "talent_defense")

    st.divider()
    afficher_equipe("⚪ Équipe des BLANCS", teams["equipeB_trios"], teams["equipeB_duos"], teams["moyB"], "gray")
    st.divider()
    afficher_equipe("⚫ Équipe de NOIRS",   teams["equipeN_trios"], teams["equipeN_duos"], teams["moyN"], "black")

    diff = abs(teams["moyB"] - teams["moyN"])
    if diff < 0.5:
        st.success("⚖️ Les équipes sont très équilibrées !")
    elif diff < 1:
        st.info("🟡 Les équipes sont assez proches.")
    else:
        st.warning("🔴 Les équipes sont un peu déséquilibrées.")

    # ------------------------------
    # Enregistrement dans l’historique (utilise l'état, donc ne disparaît pas)
    # ------------------------------
    if st.button("💾 Enregistrer ces équipes dans l’historique"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        equipeB = [p for grp in (teams["equipeB_trios"] + teams["equipeB_duos"]) for p in grp["nom"].tolist()]
        equipeN = [p for grp in (teams["equipeN_trios"] + teams["equipeN_duos"]) for p in grp["nom"].tolist()]
        save_history(equipeB, equipeN, teams["moyB"], teams["moyN"], date)
        st.success("✅ Équipes enregistrées dans l’historique ! (elles restent affichées ici)")

    # ------------------------------
    # Envoi par courriel HTML (depuis l'état)
    # ------------------------------
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
                if trio.empty: 
                    continue
                joueurs = ", ".join(trio["nom"].tolist())
                html += f"<tr><td>Trio {i}</td><td>{joueurs}</td></tr>"
            for i, duo in enumerate(duos, 1):
                if duo.empty: 
                    continue
                joueurs = ", ".join(duo["nom"].tolist())
                html += f"<tr><td>Duo {i}</td><td>{joueurs}</td></tr>"
            html += "</table>"
            return html

        corps_html = f"""
        <html><body style='font-family:Arial,sans-serif;'>
        <h2>🏒 Composition des équipes ({datetime.now().strftime("%Y-%m-%d %H:%M")})</h2>
        <p><b>Moyenne Blanc:</b> {teams['moyB']} | <b>Moyenne Noir:</b> {teams['moyN']}</p>
        {creer_tableau('⚪ Équipe des BLANCS', teams['equipeB_trios'], teams['equipeB_duos'], 'gray')}
        <br>
        {creer_tableau('⚫ Équipe des NOIRS', teams['equipeN_trios'], teams['equipeN_duos'], 'black')}
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
else:
    st.info("👆 Clique sur **Générer** pour créer des équipes, elles resteront affichées après l’enregistrement.")
