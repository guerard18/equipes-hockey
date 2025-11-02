import streamlit as st
import pandas as pd
import os

st.title("📊 Statistiques des joueurs")

path = "data/historique.csv"
players_path = "data/joueurs.csv"

if not os.path.exists(path):
    st.warning("Aucun historique trouvé pour le moment.")
    st.stop()

# Charger les données
hist = pd.read_csv(path)
players = pd.read_csv(players_path) if os.path.exists(players_path) else pd.DataFrame()

# --- Sélecteur de saison ---
if "Saison" in hist.columns:
    saisons = sorted(hist["Saison"].dropna().unique(), reverse=True)
    choix_saison = st.selectbox("🏒 Choisir la saison :", ["Toutes"] + saisons)
    if choix_saison != "Toutes":
        hist = hist[hist["Saison"] == choix_saison]
        st.info(f"📅 Saison sélectionnée : **{choix_saison}** — {len(hist)} matchs trouvés.")
else:
    st.warning("⚠️ Aucune colonne 'Saison' trouvée dans l'historique.")
    choix_saison = "Toutes"

if hist.empty:
    st.warning("Aucune donnée pour la saison sélectionnée.")
    st.stop()

# --- Calcul du nombre de matchs par joueur ---
joueurs_stats = {}

def ajouter_presence(equipe):
    if isinstance(equipe, str):
        for nom in [x.strip() for x in equipe.split(",") if x.strip()]:
            joueurs_stats[nom] = joueurs_stats.get(nom, 0) + 1

for _, row in hist.iterrows():
    ajouter_presence(row["Équipe_BLANCS"])
    ajouter_presence(row["Équipe_NOIRS"])

stats_df = pd.DataFrame(
    [{"Joueur": j, "Matchs joués": c} for j, c in joueurs_stats.items()]
).sort_values(by="Matchs joués", ascending=False)

# --- Fusion avec les talents si disponibles ---
if not players.empty:
    stats_df = stats_df.merge(players[["nom", "talent_attaque", "talent_defense"]],
                              left_on="Joueur", right_on="nom", how="left")
    stats_df.drop(columns=["nom"], inplace=True)

# --- Affichage ---
st.subheader("📋 Statistiques individuelles")
st.dataframe(stats_df, use_container_width=True)

# --- Résumé global ---
st.divider()
st.subheader("📈 Résumé global de la saison")

nb_matchs = hist["Date"].nunique()
moy_B = hist["Moyenne_BLANCS"].mean()
moy_N = hist["Moyenne_NOIRS"].mean()

col1, col2, col3 = st.columns(3)
col1.metric("Matchs joués", nb_matchs)
col2.metric("Moyenne équipe BLANCS", round(moy_B, 2))
col3.metric("Moyenne équipe NOIRS", round(moy_N, 2))

if choix_saison != "Toutes":
    st.caption(f"Filtré pour la saison {choix_saison}")
