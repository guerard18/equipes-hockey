import streamlit as st
import pandas as pd
from utils import load_players, save_players

st.title("👥 Gestion des joueurs")

# Charger les joueurs
df = load_players()

# --- Compteur des joueurs présents ---
present_count = df["present"].sum()
st.info(f"✅ {present_count} joueurs présents sélectionnés")

st.subheader("📝 Liste complète des joueurs")
st.markdown("Modifie directement dans le tableau ci-dessous. Toutes les modifications sont enregistrées dans le fichier.")

# --- Tableau éditable ---
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    column_config={
        "nom": "Nom du joueur",
        "talent_attaque": st.column_config.NumberColumn("Talent Attaque", min_value=1, max_value=10),
        "talent_defense": st.column_config.NumberColumn("Talent Défense", min_value=1, max_value=10),
        "present": "Présent ?"
    }
)

# --- Bouton enregistrer ---
if st.button("💾 Enregistrer les modifications", use_container_width=True):
    save_players(edited_df)
    st.success("✅ Modifications enregistrées !")
    st.rerun()

st.divider()

# --- Ajouter un joueur ---
st.subheader("➕ Ajouter un joueur")
with st.form("add_player_form", clear_on_submit=True):
    new_name = st.text_input("Nom du joueur")
    new_attack = st.number_input("Talent Attaque", min_value=1, max_value=10, value=5)
    new_defense = st.number_input("Talent Défense", min_value=1, max_value=10, value=5)
    submitted = st.form_submit_button("Ajouter le joueur")

    if submitted:
        if new_name.strip() == "":
            st.warning("⚠️ Le nom ne peut pas être vide.")
        elif new_name in df["nom"].values:
            st.warning("⚠️ Ce joueur existe déjà.")
        else:
            df.loc[len(df)] = [new_name, new_attack, new_defense, False]
            save_players(df)
            st.success(f"✅ {new_name} ajouté à la liste !")
            st.rerun()

st.divider()

# --- Supprimer un joueur ---
st.subheader("❌ Supprimer un joueur")
del_player = st.selectbox("Choisir un joueur à supprimer :", df["nom"])

if st.button("🗑️ Supprimer ce joueur", use_container_width=True):
    df = df[df["nom"] != del_player]
    save_players(df)
    st.success(f"🚫 {del_player} supprimé.")
    st.rerun()

st.divider()

# --- Remettre à zéro les présences ---
st.subheader("🧹 Gestion des présences")
if st.button("🔄 Remettre toutes les présences à zéro", use_container_width=True):
    df["present"] = False
    save_players(df)
    st.success("🧼 Tous les joueurs ont été marqués comme ABSENTS.")
    st.rerun()
