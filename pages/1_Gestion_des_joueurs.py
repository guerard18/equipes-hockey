import streamlit as st
from utils import load_players, save_players

st.title("👥 Gestion des joueurs")

df = load_players()

present_count = df["present"].sum()
st.info(f"✅ {present_count} joueurs présents sélectionnés")

st.subheader("Liste des joueurs")
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "nom": "Nom du joueur",
        "talent_attaque": "Talent Attaque",
        "talent_defense": "Talent Défense",
        "present": "Présent ?"
    },
    hide_index=True
)

if st.button("💾 Enregistrer les modifications"):
    save_players(edited_df)
    st.success("✅ Modifications enregistrées avec succès.")
    st.rerun()

if st.button("🧹 Remettre à zéro la présence"):
    edited_df["present"] = False
    save_players(edited_df)
    st.success("✅ Toutes les présences ont été remises à zéro.")
    st.rerun()
