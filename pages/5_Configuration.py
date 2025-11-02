import streamlit as st
import pandas as pd
import random
import os
from utils import load_players

st.title("⚙️ Configuration du tournoi et des équipes")

os.makedirs("data", exist_ok=True)
TOURNOI_PATH = "data/tournoi_bracket.csv"

# --- Onglets ---
onglet = st.tabs(["🏒 Formation standard", "🏆 Tournoi (4 équipes)"])[1]  # On se positionne directement sur le 2ᵉ onglet

# =====================================================
# 🏆 ONGLET TOURNOI (4 ÉQUIPES FIXES)
# =====================================================
with onglet:
    st.header("Tournoi à 4 équipes fixes")
    st.info("Ce mode crée automatiquement 4 équipes équilibrées à partir des joueurs présents.")

    joueurs = load_players()
    joueurs_present = joueurs[joueurs["present"] == True].reset_index(drop=True)
    nb_joueurs = len(joueurs_present)

    if nb_joueurs < 8:
        st.warning("⚠️ Pas assez de joueurs présents pour former 4 équipes.")
        st.stop()

    st.success(f"✅ {nb_joueurs} joueurs disponibles pour le tournoi.")

    nb_equipes = 4  # Format fixe
    st.markdown("**Format : 4 équipes fixes (3 matchs garantis par équipe).**")

    # --- Formation automatique des 4 équipes ---
    def generer_equipes_tournoi(df):
        df = df.sample(frac=1, random_state=random.randint(0, 9999)).reset_index(drop=True)
        equipes = [df.iloc[i::nb_equipes] for i in range(nb_equipes)]
        noms_equipes = [f"Équipe {chr(65+i)}" for i in range(nb_equipes)]  # A, B, C, D
        return dict(zip(noms_equipes, equipes))

    if st.button("🎯 Générer les 4 équipes du tournoi"):
        equipes = generer_equipes_tournoi(joueurs_present)
        st.session_state["tournoi_equipes"] = equipes
        st.success("✅ Équipes générées avec succès !")

    equipes = st.session_state.get("tournoi_equipes", None)

    if equipes:
        st.subheader("📋 Composition des équipes")
        for nom, eq in equipes.items():
            st.markdown(f"### {nom}")
            st.write(", ".join(eq["nom"]))

        # --- Création des matchs de ronde ---
        st.divider()
        st.subheader("🏁 Création de la ronde préliminaire")

        # Tous contre tous (6 matchs total)
        matchs = [
            ("Équipe A", "Équipe B"),
            ("Équipe A", "Équipe C"),
            ("Équipe A", "Équipe D"),
            ("Équipe B", "Équipe C"),
            ("Équipe B", "Équipe D"),
            ("Équipe C", "Équipe D"),
        ]
        df_matchs = pd.DataFrame(matchs, columns=["Équipe A", "Équipe B"])
        df_matchs["Phase"] = "Ronde"
        df_matchs.to_csv(TOURNOI_PATH, index=False)

        st.success("✅ Tournoi de 4 équipes créé avec succès.")
        st.dataframe(df_matchs, use_container_width=True)

        st.info("➡️ Rendez-vous dans la page **6️⃣ Tournoi en cours** pour saisir les scores et suivre le classement.")

    # --- Réinitialiser le tournoi ---
    st.divider()
    st.subheader("🧹 Gestion du tournoi")

    if st.button("🗑️ Supprimer la configuration du tournoi"):
        confirm = st.radio("Souhaitez-vous vraiment effacer le tournoi configuré ?", ["Non", "Oui, supprimer définitivement"], horizontal=True)
        if confirm == "Oui, supprimer définitivement":
            try:
                if os.path.exists(TOURNOI_PATH):
                    os.remove(TOURNOI_PATH)
                if "tournoi_equipes" in st.session_state:
                    del st.session_state["tournoi_equipes"]
                st.success("Tournoi supprimé avec succès.")
            except Exception as e:
                st.error(f"Erreur lors de la suppression : {e}")
        else:
            st.info("Aucune suppression effectuée.")
