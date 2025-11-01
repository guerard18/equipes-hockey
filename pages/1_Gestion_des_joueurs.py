import streamlit as st
import pandas as pd

from utils import load_players, save_players

# Essayez d'importer l’option GitHub automatique (facultatif)
try:
    from github_utils import save_to_github
    GITHUB_OK = True
except Exception:
    GITHUB_OK = False

st.title("1) Gestion des joueurs")
st.markdown("Ajoute/édite tes joueurs. **Présent** = disponible aujourd’hui.")

# --- Charger la liste actuelle depuis data/joueurs.csv ---
players = load_players()  # DataFrame avec colonnes: nom, talent_attaque, talent_defense, present

# --- Formulaire d'ajout ---
with st.expander("➕ Ajouter un joueur"):
    with st.form("add_player"):
        nom = st.text_input("Nom")
        ta = st.number_input("Talent Attaque (1–10)", 1, 10, 5)
        td = st.number_input("Talent Défense (1–10)", 1, 10, 5)
        pres = st.checkbox("Présent", value=True)
        ok = st.form_submit_button("Ajouter")
        if ok:
            nom = nom.strip()
            if nom == "":
                st.error("Le nom ne peut pas être vide.")
            else:
                new_row = pd.DataFrame([{
                    "nom": nom,
                    "talent_attaque": int(ta),
                    "talent_defense": int(td),
                    "present": bool(pres)
                }])
                players = pd.concat([players, new_row], ignore_index=True)
                save_players(players)
                st.success(f"Ajouté : {nom}")
                if GITHUB_OK:
                    try:
                        save_to_github("data/joueurs.csv", "Ajout d’un joueur")
                    except Exception as e:
                        st.warning(f"Sync GitHub impossible : {e}")

# --- Édition en tableau ---
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

col1, col2, col3 = st.columns(3)

# --- Bouton ENREGISTRER ---
if col1.button("💾 Enregistrer les modifications"):
    # Nettoyage et validation
    edited = edited.copy()
    edited["nom"] = edited["nom"].astype(str).str.strip()
    edited = edited.dropna(subset=["nom"])
    edited["talent_attaque"] = pd.to_numeric(edited["talent_attaque"], errors="coerce").fillna(5).astype(int).clip(1, 10)
    edited["talent_defense"] = pd.to_numeric(edited["talent_defense"], errors="coerce").fillna(5).astype(int).clip(1, 10)
    edited["present"] = edited["present"].fillna(False).astype(bool)

    save_players(edited)  # -> data/joueurs.csv
    st.success("Liste enregistrée ✅")

    if GITHUB_OK:
        try:
            save_to_github("data/joueurs.csv", "Mise à jour de la liste des joueurs")
        except Exception as e:
            st.warning(f"Sync GitHub impossible : {e}")

# --- Bouton REMETTRE À ZÉRO les présences ---
if col2.button("🔁 Remettre toutes les présences à zéro"):
    current = load_players()
    current["present"] = False
    save_players(current)
    st.success("✅ Toutes les présences ont été remises à zéro.")

    if GITHUB_OK:
        try:
            save_to_github("data/joueurs.csv", "Remise à zéro des présences")
        except Exception as e:
            st.warning(f"Sync GitHub impossible : {e}")

    st.experimental_rerun()  # rafraîchir l’affichage

# --- Bouton RECHARGER depuis le disque ---
if col3.button("♻️ Recharger depuis le disque"):
  st.rerun()  # rafraîchir l’affichage

