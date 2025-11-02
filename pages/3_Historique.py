import streamlit as st
import pandas as pd
import os

st.title("📜 Historique des matchs")

path = "data/historique.csv"

if not os.path.exists(path):
    st.warning("Aucun match enregistré pour le moment.")
    st.stop()

# Charger l’historique
hist = pd.read_csv(path)

# --- Filtre de saison ---
if "Saison" in hist.columns:
    saisons = sorted(hist["Saison"].dropna().unique(), reverse=True)
    choix_saison = st.selectbox("🏒 Choisir la saison :", ["Toutes"] + saisons)
    if choix_saison != "Toutes":
        hist = hist[hist["Saison"] == choix_saison]
        st.info(f"📅 Saison sélectionnée : **{choix_saison}** — {len(hist)} matchs trouvés.")
else:
    choix_saison = "Toutes"

if hist.empty:
    st.warning("Aucun match trouvé pour cette saison.")
    st.stop()

# --- Affichage résumé ---
st.subheader("📅 Liste des matchs enregistrés")
st.dataframe(
    hist[["Date", "Saison", "Moyenne_BLANCS", "Moyenne_NOIRS", "Équipe_BLANCS", "Équipe_NOIRS"]],
    use_container_width=True
)

# --- Détails d’un match ---
st.divider()
st.subheader("🔍 Détails d’un match")

match_list = hist["Date"].astype(str).tolist()
selection = st.selectbox("Choisir une date de match :", [""] + match_list)

if selection:
    match = hist[hist["Date"].astype(str) == selection].iloc[0]
    st.markdown(f"### 🏒 Match du **{match['Date']}** ({match['Saison']})")
    st.write(f"⚪ **BLANCS (moyenne {match['Moyenne_BLANCS']})**")
    st.write(match["Équipe_BLANCS"])
    st.write(f"⚫ **NOIRS (moyenne {match['Moyenne_NOIRS']})**")
    st.write(match["Équipe_NOIRS"])

# --- Suppression sécurisée ---
st.divider()
st.subheader("🗑️ Gestion de l’historique")

st.markdown("### ⚠️ Supprimer des données")

choix_action = st.radio(
    "Que voulez-vous effacer ?",
    ["Rien", "Seulement la saison sélectionnée", "Tout l’historique"],
    horizontal=False,
)

if choix_action != "Rien":
    confirmation = st.radio(
        f"Êtes-vous certain de vouloir {choix_action.lower()} ?",
        ["Non", "Oui, supprimer définitivement"],
        horizontal=True,
    )

    if confirmation == "Oui, supprimer définitivement":
        try:
            if choix_action == "Tout l’historique":
                os.remove(path)
                st.success("✅ Historique complet supprimé avec succès.")
                st.stop()
            elif choix_action == "Seulement la saison sélectionnée" and choix_saison != "Toutes":
                hist = pd.read_csv(path)
                hist = hist[hist["Saison"] != choix_saison]
                hist.to_csv(path, index=False)
                st.success(f"✅ Saison **{choix_saison}** supprimée avec succès.")
                st.stop()
            else:
                st.warning("⚠️ Aucune saison sélectionnée à supprimer.")
        except Exception as e:
            st.error(f"Erreur lors de la suppression : {e}")
    else:
        st.info("Aucune suppression effectuée.")
