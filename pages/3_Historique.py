import streamlit as st
import pandas as pd
from utils import load_history, reset_history

# Optionnel : commit GitHub automatique
try:
    from github_utils import save_to_github
    GITHUB_OK = True
except Exception:
    GITHUB_OK = False

st.title("3️⃣ Historique des équipes 🕓")
st.markdown(
    "Voici l’historique complet des équipes formées et enregistrées. "
    "Chaque ligne représente une session de match."
)

# Charger l’historique
hist = load_history()

# --- Si aucun historique ---
if hist.empty:
    st.info("📭 Aucun historique enregistré pour le moment.")
    st.stop()

# --- Afficher l’historique dans un tableau lisible ---
st.subheader("📋 Liste des équipes passées")

# Mise en forme : trier du plus récent au plus ancien
hist = hist.sort_values("date", ascending=False).reset_index(drop=True)

for i, row in hist.iterrows():
    st.markdown(f"### 🗓️ {row['date']}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Équipe 1 :**")
        st.write(row["equipe1"])
        st.write(f"**Moyenne talent :** {row['moyenne_talent_eq1']}")
    with col2:
        st.markdown("**Équipe 2 :**")
        st.write(row["equipe2"])
        st.write(f"**Moyenne talent :** {row['moyenne_talent_eq2']}")
    st.divider()

# --- Bouton de suppression ---
st.markdown("---")
st.subheader("🧹 Gestion de l’historique")

if st.button("🗑️ Effacer tout l’historique"):
    reset_history()
    st.success("✅ Historique entièrement effacé.")
    # Sauvegarde GitHub automatique si dispo
    if GITHUB_OK:
        try:
            save_to_github("data/historique.csv", "Effacement de l’historique des équipes")
            st.toast("💾 Sauvegarde GitHub réussie (effacement)")
        except Exception as e:
            st.warning(f"⚠️ Impossible de synchroniser sur GitHub : {e}")
    st.rerun()
