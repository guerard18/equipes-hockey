import streamlit as st
import pandas as pd
import random
from utils import load_players, save_players

# Optionnel : commit GitHub automatique
try:
    from github_utils import save_to_github
    GITHUB_OK = True
except Exception:
    GITHUB_OK = False

st.title("1️⃣ Gestion des joueurs 🏒")
st.markdown("Ajoute, édite ou gère les joueurs. Coche **Présent** pour indiquer qui est disponible aujourd’hui.")

# --- Charger la liste des joueurs ---
players = load_players()

# --- Section d'ajout d'un joueur ---
with st.expander("➕ Ajouter un nouveau joueur"):
    with st.form("add_player"):
        nom = st.text_input("Nom du joueur")
        ta = st.number_input("Talent Attaque (1–10)", 1, 10, 5)
        td = st.number_input("Talent Défense (1–10)", 1, 10, 5)
        pres = st.checkbox("Présent aujourd’hui", value=True)
        submit = st.form_submit_button("Ajouter le joueur")

        if submit:
            nom = nom.strip()
            if not nom:
                st.error("❌ Le nom ne peut pas être vide.")
            else:
                new_row = pd.DataFrame([{
                    "nom": nom,
                    "talent_attaque": int(ta),
                    "talent_defense": int(td),
                    "present": bool(pres)
                }])
                players = pd.concat([players, new_row], ignore_index=True)
                save_players(players)
                st.success(f"✅ Joueur ajouté : {nom}")

                # Sauvegarde GitHub
                if GITHUB_OK:
                    try:
                        save_to_github("data/joueurs.csv", f"Ajout du joueur {nom}")
                    except Exception as e:
                        st.warning(f"⚠️ Impossible de synchroniser sur GitHub : {e}")

# --- Édition du tableau ---
st.subheader("📝 Modifier les joueurs existants")
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

col1, col2, col3 = st.columns(3)

# --- Bouton ENREGISTRER ---
if col1.button("💾 Enregistrer les modifications"):
    edited = edited.copy()
    edited["nom"] = edited["nom"].astype(str).str.strip()
    edited = edited.dropna(subset=["nom"])
    edited["talent_attaque"] = pd.to_numeric(edited["talent_attaque"], errors="coerce").fillna(5).astype(int).clip(1, 10)
    edited["talent_defense"] = pd.to_numeric(edited["talent_defense"], errors="coerce").fillna(5).astype(int).clip(1, 10)
    edited["present"] = edited["present"].fillna(False).astype(bool)

    save_players(edited)
    st.success("✅ Liste enregistrée avec succès.")

    if GITHUB_OK:
        try:
            save_to_github("data/joueurs.csv", "Mise à jour de la liste des joueurs")
        except Exception as e:
            st.warning(f"⚠️ Impossible de synchroniser sur GitHub : {e}")

# --- Bouton REMETTRE À ZÉRO ---
if col2.button("🔁 Remettre toutes les présences à zéro"):
    df = load_players()
    df["present"] = False
    save_players(df)
    st.session_state["reset_done"] = True  # Flag pour forcer le rerun

    st.success("✅ Toutes les présences ont été remises à zéro.")

    # Synchronisation GitHub (optionnelle)
    if GITHUB_OK:
        try:
            save_to_github("data/joueurs.csv", "Remise à zéro des présences")
        except Exception as e:
            st.warning(f"⚠️ Impossible de synchroniser sur GitHub : {e}")

    # Rafraîchir la page proprement
    st.experimental_set_query_params(refresh=random.random())
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# 🔄 Rafraîchissement automatique après reset
if st.session_state.get("reset_done"):
    st.session_state["reset_done"] = False
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- Bouton RECHARGER ---
if col3.button("♻️ Recharger la liste"):
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()
