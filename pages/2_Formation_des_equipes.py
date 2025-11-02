import streamlit as st
import pandas as pd
import random
from datetime import date
from utils import load_players, save_history
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("🏒 Formation des équipes")

# --- Charger les joueurs présents ---
players = load_players()
present_players = players[players["present"] == True].copy()

if present_players.empty:
    st.warning("Aucun joueur présent. Cochez des joueurs dans la page 'Gestion des joueurs'.")
    st.stop()

# --- Sélection de la date du match ---
date_match = st.date_input("📅 Date du match", value=date.today())

# --- Paramètres par défaut ---
NB_TRIOS = 4
NB_DUOS = 4

# --- Calcul du talent moyen ---
def talent_moyen(row):
    return (row["talent_attaque"] + row["talent_defense"]) / 2

present_players["talent_moyen"] = present_players.apply(talent_moyen, axis=1)

# --- Séparer attaquants / défenseurs selon le meilleur talent ---
attaquants = present_players[present_players["talent_attaque"] >= present_players["talent_defense"]]
defenseurs = present_players[present_players["talent_defense"] > present_players["talent_attaque"]]

# --- Vérification du nombre suffisant ---
if len(attaquants) < NB_TRIOS * 3 or len(defenseurs) < NB_DUOS * 2:
    st.warning(
        f"⚠️ Pas assez de joueurs pour {NB_TRIOS} trios et {NB_DUOS} duos par équipe. "
        f"({len(attaquants)} attaquants, {len(defenseurs)} défenseurs disponibles)"
    )

# --- Fonction d'équilibrage selon le talent moyen ---
def equilibrer_groupes(joueurs, taille):
    joueurs = joueurs.sample(frac=1).reset_index(drop=True)
    joueurs_sorted = joueurs.sort_values("talent_moyen", ascending=False)
    groupes = [[] for _ in range(len(joueurs_sorted) // taille)]
    index, sens = 0, 1
    for _, j in joueurs_sorted.iterrows():
        groupes[index].append(j["nom"])
        index += sens
        if index >= len(groupes):
            index = len(groupes) - 1
            sens = -1
        elif index < 0:
            index = 0
            sens = 1
    return groupes

# --- Créer les trios et duos équilibrés ---
nb_trios_total = min(len(attaquants) // 3, NB_TRIOS * 2)
nb_duos_total = min(len(defenseurs) // 2, NB_DUOS * 2)
trios = equilibrer_groupes(attaquants.head(nb_trios_total * 3), 3)
duos = equilibrer_groupes(defenseurs.head(nb_duos_total * 2), 2)

# --- Distribuer entre BLANCS et NOIRS ---
trios_blancs, trios_noirs = trios[::2], trios[1::2]
duos_blancs, duos_noirs = duos[::2], duos[1::2]

# --- Calcul moyenne d'une équipe ---
def moyenne_groupes(groupes):
    total, n = 0, 0
    for g in groupes:
        for j in g:
            joueur = present_players[present_players["nom"] == j]
            if not joueur.empty:
                total += joueur["talent_moyen"].values[0]
                n += 1
    return round(total / n, 2) if n > 0 else 0

moy_blancs = moyenne_groupes(trios_blancs + duos_blancs)
moy_noirs = moyenne_groupes(trios_noirs + duos_noirs)

# --- Affichage ---
st.subheader(f"⚪ **BLANCS** — Moyenne : {moy_blancs}")
for i, trio in enumerate(trios_blancs, 1):
    moy = round(sum(present_players.loc[present_players["nom"].isin(trio), "talent_moyen"]) / len(trio), 2)
    st.write(f"Trio {i} ({moy}) : {', '.join(trio)}")
for i, duo in enumerate(duos_blancs, 1):
    moy = round(sum(present_players.loc[present_players["nom"].isin(duo), "talent_moyen"]) / len(duo), 2)
    st.write(f"Duo {i} ({moy}) : {', '.join(duo)}")

st.divider()

st.subheader(f"⚫ **NOIRS** — Moyenne : {moy_noirs}")
for i, trio in enumerate(trios_noirs, 1):
    moy = round(sum(present_players.loc[present_players["nom"].isin(trio), "talent_moyen"]) / len(trio), 2)
    st.write(f"Trio {i} ({moy}) : {', '.join(trio)}")
for i, duo in enumerate(duos_noirs, 1):
    moy = round(sum(present_players.loc[present_players["nom"].isin(duo), "talent_moyen"]) / len(duo), 2)
    st.write(f"Duo {i} ({moy}) : {', '.join(duo)}")

# --- Enregistrement de l’historique ---
if st.button("💾 Enregistrer le match dans l'historique"):
    equipeB = [j for trio in trios_blancs for j in trio] + [j for duo in duos_blancs for j in duo]
    equipeN = [j for trio in trios_noirs for j in trio] + [j for duo in duos_noirs for j in duo]

    save_history(
        date_match.strftime("%Y-%m-%d"),
        moy_blancs,
        moy_noirs,
        trios_blancs,
        duos_blancs,
        trios_noirs,
        duos_noirs,
        equipeB,
        equipeN
    )

    st.success("✅ Match enregistré dans l'historique avec la saison détectée automatiquement !")

# --- Génération PDF ---
st.divider()
st.subheader("📄 Télécharger les équipes en PDF")

if st.button("📥 Générer le PDF"):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(200, 770, f"Match du {date_match.strftime('%Y-%m-%d')}")
    pdf.setFont("Helvetica", 12)

    y = 740
    pdf.drawString(50, y, f"⚪ BLANCS (moyenne {moy_blancs})")
    y -= 20
    for i, trio in enumerate(trios_blancs, 1):
        pdf.drawString(60, y, f"Trio {i}: {', '.join(trio)}")
        y -= 15
    for i, duo in enumerate(duos_blancs, 1):
        pdf.drawString(60, y, f"Duo {i}: {', '.join(duo)}")
        y -= 15

    y -= 20
    pdf.drawString(50, y, f"⚫ NOIRS (moyenne {moy_noirs})")
    y -= 20
    for i, trio in enumerate(trios_noirs, 1):
        pdf.drawString(60, y, f"Trio {i}: {', '.join(trio)}")
        y -= 15
    for i, duo in enumerate(duos_noirs, 1):
        pdf.drawString(60, y, f"Duo {i}: {', '.join(duo)}")
        y -= 15

    pdf.save()
    buffer.seek(0)
    st.download_button(
        label="⬇️ Télécharger le PDF",
        data=buffer,
        file_name=f"Match_{date_match}.pdf",
        mime="application/pdf"
    )
