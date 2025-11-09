import streamlit as st
import pandas as pd
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime

st.title("📜 Historique des tournois 🏆")

HISTO_PATH = "data/historique_tournois.csv"
os.makedirs("data", exist_ok=True)

if not os.path.exists(HISTO_PATH):
    st.warning("Aucun tournoi archivé pour le moment.")
    st.stop()

# Charger l’historique
try:
    hist = pd.read_csv(HISTO_PATH)
except Exception as e:
    st.error(f"Erreur lors du chargement de l’historique : {e}")
    st.stop()

if hist.empty:
    st.info("Aucun tournoi enregistré pour le moment.")
    st.stop()

# Nettoyage des données
hist["Date"] = pd.to_datetime(hist["Date"], errors="coerce").dt.date

# --- Filtres ---
st.subheader("🔍 Filtres")
years = sorted(hist["Date"].dropna().apply(lambda d: d.year).unique(), reverse=True)
selected_year = st.selectbox("Filtrer par année :", ["Toutes"] + [str(y) for y in years])

filtered = hist.copy()
if selected_year != "Toutes":
    filtered = filtered[filtered["Date"].apply(lambda d: str(d.year)) == selected_year]

st.success(f"{len(filtered)} tournois trouvés pour la période sélectionnée.")

# --- Tableau résumé ---
st.divider()
st.subheader("📅 Liste des tournois archivés")
st.dataframe(
    filtered[["Date", "Champion", "Vice_champion", "Equipes"]],
    use_container_width=True,
)

# --- Détails d’un tournoi ---
st.divider()
st.subheader("🔎 Détails d’un tournoi")

tournaments = filtered["Tournoi_ID"].astype(str).tolist()
selected_id = st.selectbox("Choisir un tournoi :", [""] + tournaments)

if selected_id:
    t = hist[hist["Tournoi_ID"].astype(str) == selected_id].iloc[0]
    st.markdown(f"### 🏆 Tournoi du {t['Date']}")
    st.write(f"**Champion :** 🥇 {t['Champion']}")
    st.write(f"**Vice-champion :** 🥈 {t['Vice_champion']}")
    st.write(f"**Équipes participantes :** {t['Equipes']}")
    st.write(f"**Classement final :** {t['Classement_final']}")
    st.markdown("#### 🧾 Matchs disputés")
    matchs = str(t["Matches"]).split(" || ")
    for m in matchs:
        st.write("• " + m)

    # --- PDF ---
    st.divider()
    if st.button("📄 Télécharger le résumé PDF"):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(180, 770, f"Tournoi du {t['Date']}")
        pdf.setFont("Helvetica", 12)

        y = 740
        pdf.drawString(50, y, f"Champion : {t['Champion']}")
        y -= 18
        pdf.drawString(50, y, f"Vice-champion : {t['Vice_champion']}")
        y -= 18
        pdf.drawString(50, y, f"Équipes : {t['Equipes']}")
        y -= 24
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(50, y, "Classement final :")
        y -= 16
        pdf.setFont("Helvetica", 12)
        for line in str(t["Classement_final"]).split(" | "):
            pdf.drawString(60, y, f"- {line}")
            y -= 14
        y -= 20
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(50, y, "Matchs disputés :")
        y -= 16
        pdf.setFont("Helvetica", 11)
        for m in matchs:
            pdf.drawString(60, y, m)
            y -= 13
            if y < 60:
                pdf.showPage()
                y = 750
        pdf.save()
        buffer.seek(0)
        st.download_button(
            label="⬇️ Télécharger le PDF",
            data=buffer,
            file_name=f"Tournoi_{t['Date']}.pdf",
            mime="application/pdf",
        )

# --- Suppression sécurisée ---
st.divider()
st.subheader("🧹 Gestion de l’historique")

if st.button("🗑️ Supprimer un tournoi de l’historique"):
    del_id = st.selectbox("Choisir le tournoi à supprimer :", [""] + tournaments, key="del")
    if del_id:
        confirm = st.radio(
            f"Souhaitez-vous vraiment supprimer le tournoi {del_id} ?",
            ["Non", "Oui, supprimer définitivement"],
            horizontal=True,
        )
        if confirm == "Oui, supprimer définitivement":
            hist = hist[hist["Tournoi_ID"].astype(str) != del_id]
            hist.to_csv(HISTO_PATH, index=False)
            st.success(f"Tournoi {del_id} supprimé avec succès.")
            st.experimental_rerun()
