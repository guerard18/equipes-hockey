import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from utils import load_players

st.title("🧩 Formation manuelle des équipes")

# Charger les joueurs
players = load_players()
players_list = players["nom"].tolist()


# ✅ Petite fonction utilitaire
def get_df(noms):
    return players[players["nom"].isin(noms)]


def moyenne_talent(df, colonne):
    if df.empty:
        return 0
    return round(df[colonne].mean(), 2)


# ✅ Empêcher doublons dans les choix
def choix_sans_doublons(choices, all_choices, key):
    return st.multiselect(
        choices,
        all_choices,
        key=key,
        help="Impossible de choisir un joueur déjà utilisé ailleurs.",
    )


# ✅ Fonction de validation des doublons
def verifier_doublons(*listes):
    flat = [p for lst in listes for p in lst]
    dups = pd.Series(flat).duplicated(keep=False)
    doublons = list(pd.Series(flat)[dups].unique())
    return doublons


st.info(
    "Sélectionnez 2 trios (3 joueurs chacun) et 2 duos (2 joueurs chacun) pour chaque équipe."
)

st.divider()
st.subheader("⚪ Équipe BLANCS")

colB1, colB2 = st.columns(2)

with colB1:
    trioB1 = st.multiselect("Trio 1 (3 joueurs)", players_list, key="trioB1")
    trioB2 = st.multiselect("Trio 2 (3 joueurs)", players_list, key="trioB2")

with colB2:
    duoB1 = st.multiselect("Duo 1 (2 joueurs)", players_list, key="duoB1")
    duoB2 = st.multiselect("Duo 2 (2 joueurs)", players_list, key="duoB2")

st.divider()
st.subheader("⚫ Équipe NOIRS")

colN1, colN2 = st.columns(2)

with colN1:
    trioN1 = st.multiselect("Trio 1 (3 joueurs)", players_list, key="trioN1")
    trioN2 = st.multiselect("Trio 2 (3 joueurs)", players_list, key="trioN2")

with colN2:
    duoN1 = st.multiselect("Duo 1 (2 joueurs)", players_list, key="duoN1")
    duoN2 = st.multiselect("Duo 2 (2 joueurs)", players_list, key="duoN2")


# ✅ Vérification des doublons
all_groups = [trioB1, trioB2, duoB1, duoB2, trioN1, trioN2, duoN1, duoN2]
doublons = verifier_doublons(*all_groups)

if doublons:
    st.error(f"❌ Les joueurs suivants sont sélectionnés plus d'une fois : {', '.join(doublons)}")
    st.stop()


# ✅ Affichage des stats
def afficher_stats(trios, duos, couleur):
    st.markdown(f"### 📊 Statistiques {couleur}")

    totaux = []

    # Trios
    for i, trio in enumerate(trios, 1):
        df = get_df(trio)
        moy = moyenne_talent(df, "talent_attaque")
        totaux.append(moy)
        st.write(f"**Trio {i} — attaque : {moy}**")
        for p in trio:
            st.caption(p)

    # Duos
    for i, duo in enumerate(duos, 1):
        df = get_df(duo)
        moy = moyenne_talent(df, "talent_defense")
        totaux.append(moy)
        st.write(f"**Duo {i} — défense : {moy}**")
        for p in duo:
            st.caption(p)

    if totaux:
        total = round(sum(totaux) / len(totaux), 2)
        st.success(f"🎯 Moyenne totale équipe {couleur} : **{total}**")
        return total
    return 0


if st.button("📊 Afficher les statistiques"):
    st.subheader("Résultats des équipes")

    col1, col2 = st.columns(2)

    with col1:
        moyB = afficher_stats(
            trios=[trioB1, trioB2],
            duos=[duoB1, duoB2],
            couleur="BLANCS ⚪",
        )

    with col2:
        moyN = afficher_stats(
            trios=[trioN1, trioN2],
            duos=[duoN1, duoN2],
            couleur="NOIRS ⚫",
        )

st.divider()


# ✅ Génération PDF
st.subheader("📄 Générer PDF des équipes")

if st.button("💾 Télécharger PDF"):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, 770, "Équipes manuelles")

    pdf.setFont("Helvetica", 12)
    y = 740

    # BLANCS
    pdf.drawString(50, y, "⚪ BLANCS")
    y -= 20
    for i, trio in enumerate([trioB1, trioB2], 1):
        pdf.drawString(60, y, f"Trio {i}: {', '.join(trio)}")
        y -= 15
    for i, duo in enumerate([duoB1, duoB2], 1):
        pdf.drawString(60, y, f"Duo {i}: {', '.join(duo)}")
        y -= 15

    y -= 20
    pdf.drawString(50, y, "⚫ NOIRS")
    y -= 20
    for i, trio in enumerate([trioN1, trioN2], 1):
        pdf.drawString(60, y, f"Trio {i}: {', '.join(trio)}")
        y -= 15
    for i, duo in enumerate([duoN1, duoN2], 1):
        pdf.drawString(60, y, f"Duo {i}: {', '.join(duo)}")
        y -= 15

    pdf.save()
    buffer.seek(0)

    st.download_button(
        "⬇️ Télécharger le PDF",
        buffer,
        file_name="equipes_manuelles.pdf",
        mime="application/pdf",
    )

st.divider()


# ✅ Envoi par courriel
st.subheader("📧 Envoyer les équipes par courriel")

expediteur = st.text_input("Adresse Gmail d’expéditeur")
mp_app = st.text_input("Mot de passe d'application Gmail", type="password")
dest = st.text_area("Destinataires (séparés par des virgules)")

if st.button("📨 Envoyer courriel"):
    corps_html = f"""
    <h2>Équipes manuelles</h2>
    <h3>⚪ BLANCS</h3>
    <p>Trios:<br>{'<br>'.join([', '.join(t) for t in [trioB1, trioB2]])}</p>
    <p>Duos:<br>{'<br>'.join([', '.join(d) for d in [duoB1, duoB2]])}</p>

    <h3>⚫ NOIRS</h3>
    <p>Trios:<br>{'<br>'.join([', '.join(t) for t in [trioN1, trioN2]])}</p>
    <p>Duos:<br>{'<br>'.join([', '.join(d) for d in [duoN1, duoN2]])}</p>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = expediteur
        msg["To"] = dest
        msg["Subject"] = "Équipes manuelles"
        msg.attach(MIMEText(corps_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(expediteur, mp_app)
            server.send_message(msg)

        st.success("✅ Courriel envoyé avec succès !")

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
