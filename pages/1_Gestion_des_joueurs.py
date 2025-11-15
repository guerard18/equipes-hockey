import streamlit as st
import pandas as pd
from utils import load_players, save_players

st.title("👥 Gestion des joueurs")

# Charger les joueurs
df = load_players()

# S'assurer que les talents sont en format float avec 2 décimales
df["talent_attaque"] = df["talent_attaque"].astype(float).round(2)
df["talent_defense"] = df["talent_defense"].astype(float).round(2)

# 🧮 Compteur de joueurs présents
present_count = df["present"].sum()
st.info(f"✅ {present_count} joueurs présents sélectionnés")

# Empêcher les noms dupliqués
if df["nom"].duplicated().any():
    st.warning("⚠️ Des noms sont dupliqués ! Tu dois corriger avant d’enregistrer.")

st.subheader("Liste complète des joueurs")

edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "nom": st.column_config.TextColumn("Nom du joueur"),
        "talent_attaque": st.column_config.NumberColumn(
            "Talent Attaque",
            min_value=0.00,
            max_value=10.00,
            step=0.01,
            format="%.2f"
        ),
        "talent_defense": st.column_config.NumberColumn(
            "Talent Défense",
            min_value=0.00,
            max_value=10.00,
            step=0.01,
            format="%.2f"
        ),
        "present": st.column_config.CheckboxColumn("Présent ?")
    },
    hide_index=True
)

# Nettoyage automatique des noms
edited_df["nom"] = edited_df["nom"].fillna("").str.strip().str.upper()

# Bouton d'enregistrement
if st.button("💾 Enregistrer les modifications"):
    # Vérifier doublons
    if edited_df["nom"].duplicated().any():
        st.error("⚠️ Impossible d’enregistrer : il y a des noms en double.")
    else:
        # Sauvegarde finale
        edited_df["talent_attaque"] = edited_df["talent_attaque"].astype(float).round(2)
        edited_df["talent_defense"] = edited_df["talent_defense"].astype(float).round(2)

        save_players(edited_df)
        st.success("✅ Modifications enregistrées avec succès.")
        st.rerun()

# Bouton remise à zéro
if st.button("🧹 Remettre à zéro la présence"):
    edited_df["present"] = False
    save_players(edited_df)
    st.success("✅ Toutes les présences ont été remises à zéro.")
    st.rerun()
