import streamlit as st
import pandas as pd
from utils import load_players, save_players

st.title("1) Gestion des joueurs")

st.markdown("Ajoute/édites tes joueurs. **Présent** = disponible aujourd’hui.")

players = load_players()

with st.expander("➕ Ajouter un joueur"):
    with st.form("add_player"):
        nom = st.text_input("Nom")
        ta = st.number_input("Talent Attaque (1–10)", 1, 10, 5)
        td = st.number_input("Talent Défense (1–10)", 1, 10, 5)
        pres = st.checkbox("Présent", value=True)
        ok = st.form_submit_button("Ajouter")
        if ok and nom.strip():
            players = pd.concat([players, pd.DataFrame([{
                "nom": nom.strip(),
                "talent_attaque": int(ta),
                "talent_defense": int(td),
                "present": bool(pres)
            }])], ignore_index=True)
            save_players(players)
            st.success(f"Ajouté : {nom}")

st.subheader("📝 Éditer la liste")
edited = st.data_editor(
    players,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "nom": st.column_config.TextColumn("Nom", required=True),
        "talent_attaque": st.column_config.NumberColumn("Talent Attaque", min_value=1, max_value=10, step=1),
        "talent_defense": st.column_config.NumberColumn("Talent Défense", min_value=1, max_value=10, step=1),
        "present": st.column_config.CheckboxColumn("Présent")
    }
)

col1, col2 = st.columns(2)
if col1.button("💾 Enregistrer les modifications"):
    # Nettoyage
    edited["nom"] = edited["nom"].astype(str).str.strip()
    edited = edited.dropna(subset=["nom"])
    edited["talent_attaque"] = edited["talent_attaque"].fillna(5).astype(int).clip(1,10)
    edited["talent_defense"] = edited["talent_defense"].fillna(5).astype(int).clip(1,10)
    edited["present"] = edited["present"].fillna(False).astype(bool)
    save_players(edited)
    st.success("Liste enregistrée ✅")

if col2.button("♻️ Recharger depuis le disque"):
    st.experimental_rerun()
