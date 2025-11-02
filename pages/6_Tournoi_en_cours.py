import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.title("🏆 Tournoi en cours")

path = "data/tournoi_bracket.csv"
results_path = "data/tournoi_resultats.csv"

if not os.path.exists(path):
    st.warning("⚠️ Aucun tournoi actif trouvé. Créez un tournoi dans la page *Formation des équipes*.")
    st.stop()

# Charger le bracket
bracket = pd.read_csv(path)
st.subheader("📋 Matchs du tournoi")
st.dataframe(bracket, use_container_width=True)

# Charger les résultats existants (si présents)
if os.path.exists(results_path):
    resultats = pd.read_csv(results_path)
else:
    resultats = bracket.copy()
    resultats["Score A"] = 0
    resultats["Score B"] = 0
    resultats["Terminé"] = False

st.divider()
st.subheader("📝 Entrer les résultats des matchs")

for i in range(len(resultats)):
    col1, col2, col3, col4, col5 = st.columns([2, 1, 0.5, 1, 2])
    with col1:
        st.write(f"{resultats.loc[i, 'Équipe A']} vs {resultats.loc[i, 'Équipe B']}")
    with col2:
        scoreA = st.number_input(f"Score {resultats.loc[i, 'Équipe A']}", 0, 20, int(resultats.loc[i, 'Score A']), key=f"A{i}")
    with col4:
        scoreB = st.number_input(f"Score {resultats.loc[i, 'Équipe B']}", 0, 20, int(resultats.loc[i, 'Score B']), key=f"B{i}")
    with col5:
        termine = st.checkbox("Terminé", value=bool(resultats.loc[i, "Terminé"]), key=f"T{i}")

    resultats.loc[i, "Score A"] = scoreA
    resultats.loc[i, "Score B"] = scoreB
    resultats.loc[i, "Terminé"] = termine

if st.button("💾 Sauvegarder les résultats"):
    resultats.to_csv(results_path, index=False)
    st.success("✅ Résultats sauvegardés avec succès.")

# --- Classement ---
st.divider()
st.subheader("📊 Classement du tournoi")

# Calcul du classement
equipes = pd.unique(resultats[["Équipe A", "Équipe B"]].values.ravel("K"))
stats = {eq: {"MJ": 0, "V": 0, "D": 0, "N": 0, "BP": 0, "BC": 0, "Pts": 0} for eq in equipes}

for _, m in resultats.iterrows():
    if not m["Terminé"]:
        continue
    a, b = m["Équipe A"], m["Équipe B"]
    sa, sb = int(m["Score A"]), int(m["Score B"])
    stats[a]["MJ"] += 1
    stats[b]["MJ"] += 1
    stats[a]["BP"] += sa
    stats[a]["BC"] += sb
    stats[b]["BP"] += sb
    stats[b]["BC"] += sa
    if sa > sb:
        stats[a]["V"] += 1
        stats[b]["D"] += 1
        stats[a]["Pts"] += 2
    elif sb > sa:
        stats[b]["V"] += 1
        stats[a]["D"] += 1
        stats[b]["Pts"] += 2
    else:
        stats[a]["N"] += 1
        stats[b]["N"] += 1
        stats[a]["Pts"] += 1
        stats[b]["Pts"] += 1

classement = pd.DataFrame.from_dict(stats, orient="index").reset_index()
classement.rename(columns={"index": "Équipe"}, inplace=True)
classement["Diff"] = classement["BP"] - classement["BC"]
classement = classement.sort_values(by=["Pts", "Diff", "BP"], ascending=False)

st.dataframe(classement, use_container_width=True)

# --- Export PDF ---
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.divider()
st.subheader("📄 Télécharger le rapport du tournoi")

if st.button("📥 Générer le PDF"):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(180, 770, f"Tournoi du {datetime.now().strftime('%Y-%m-%d')}")

    y = 740
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Résultats des matchs")
    y -= 20
    pdf.setFont("Helvetica", 12)
    for _, m in resultats.iterrows():
        txt = f"{m['Équipe A']} {m['Score A']} - {m['Score B']} {m['Équipe B']}"
        if m["Terminé"]:
            pdf.drawString(60, y, txt)
            y -= 15

    y -= 20
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Classement final")
    y -= 20
    pdf.setFont("Helvetica", 12)
    for _, row in classement.iterrows():
        pdf.drawString(60, y, f"{row['Équipe']}: {row['Pts']} pts ({row['V']}-{row['D']}-{row['N']}) Diff: {row['Diff']}")
        y -= 15

    pdf.save()
    buffer.seek(0)
    st.download_button(
        label="⬇️ Télécharger le PDF du tournoi",
        data=buffer,
        file_name="Tournoi_resultats.pdf",
        mime="application/pdf"
    )
