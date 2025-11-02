import streamlit as st
import pandas as pd
import random
from datetime import date
from utils import load_players, save_history
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# --- Titre ---
st.title("🏒 Formation des équipes")

# --- Charger les joueurs ---
players = load_players()
present_players = players[players["present"] == True].copy()

if present_players.empty:
    st.warning("Aucun joueur présent. Cochez les joueurs dans la page 'Gestion des joueurs'.")
    st.stop()

# --- Entrer la date du match ---
date_match = st.date_input("📅 Date du match", value=date.today())

# --- Paramètres ---
NB_TRIOS = 4
NB_DUOS = 4

# --- Conversion des talents ---
def talent_moyen(joueur):
    return (joueur["talent_attaque"] + joueur["talent_defense"]) / 2

present_players["talent_moyen"] = present_players.apply(talent_moyen, axis=1)

# --- Séparer attaquants et défenseurs selon meilleur talent ---
attaquants = present_players[present_players["talent_attaque"] >= present_players["talent_defense"]]
defenseurs = present_players[present_players["talent_defense"] > present_players["talent_attaque"]]

# --- Vérification du nombre ---
if len(attaquants) < NB_TRIOS * 3 or len(defenseurs) < NB_DUOS * 2:
    st.warning(
        f"⚠️ Nombre de joueurs insuffisant pour {NB_TRIOS} trios et {NB_DUOS} duos par équipe. "
        "Tu peux quand même générer les équipes avec le bouton ci-dessous."
    )

# --- Fonction d’équilibrage simple ---
def equilibrer_groupes(joueurs, taille_groupe):
    """Crée des groupes équilibrés selon le talent moyen."""
    joueurs_sorted = joueurs.sort_values("talent_moyen", ascending=False)
    groupes = [[] for _ in range(len(joueurs_sorted) // taille_groupe)]
    sens = 1
    idx = 0
    for _, row in joueurs_sorted.iterrows():
        groupes[idx].append(row["nom"])
        idx += sens
        if idx == len(groupes):
            idx -= 1
            sens = -1
        elif idx < 0:
            idx = 0
            sens = 1
    return groupes

# --- Création des trios et duos ---
nb_trios_total = min(len(attaquants) // 3, NB_TRIOS * 2)
nb_duos_total = min(len(defenseurs) // 2, NB_DUOS * 2)

trios = equilibrer_groupes(attaquants.head(nb_trios_total * 3), 3)
duos = equilibrer_groupes(defenseurs.head(nb_duos_total * 2), 2)

# --- Distribution aux équipes ---
trios_blancs = trios[::2]
trios_noirs = trios[1::2]
duos_blancs = duos[::2]
duos_noirs = duos[1::2]

# --- Calcul des moyennes de talent ---
def moyenne_equipes(groupes, joueurs_df):
    total, n = 0, 0
    for g in groupes:
        for j in g:
            total += joueurs_df.loc[joueurs_df["nom"] == j, "talent_moyen"].values[0]
            n += 1
    return round(total / n, 2) if n > 0 else 0

moy_blancs = moyenne_equipes(trios_blancs + duos_blancs, present_players)
moy_noirs = moyenne_equipes(trios_noirs + duos_noirs, present_players)

# --- Affichage des équipes ---
st.subheader(f"⚪ BLANCS (moyenne {moy_blancs})")
for i, trio in enumerate(trios_blancs, 1):
    noms = ", ".join(trio)
    moy = round(sum(present_players.loc[present_players["nom"].isin(trio), "talent_moyen"]) / len(trio), 2)
    st.write(f"Trio {i} ({moy}): {noms}")
for i, duo in enumerate(duos_blancs, 1):
    noms = ", ".join(duo)
    moy = round(sum(present_players.loc[present_players["nom"].isin(duo), "talent_moyen"]) / len(duo), 2)
    st.write(f"Duo {i} ({moy}): {noms}")

st.divider()

st.subheader(f"⚫ NOIRS (moyenne {moy_noirs})")
for i, trio in enumerate(trios_noirs, 1):
    noms = ", ".join(trio)
    moy = round(sum(present_players.loc[present_players["nom"].isin(trio), "talent_moyen"]) / len(trio), 2)
    st.write(f"Trio {i} ({moy}): {noms}")
for i, duo in enumerate(duos_noirs, 1):
    noms = ", ".join(duo)
    moy = round(sum(present_players.loc[present_players["nom"].isin(duo), "talent_moyen"]) / len(duo), 2)
    st.write(f"Duo {i} ({moy}): {noms}")

# --- Enregistrement ---
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
    st.success("✅ Match enregistré avec succès dans l'historique !")

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
