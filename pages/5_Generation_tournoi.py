import streamlit as st
import pandas as pd
import os
import itertools
import random
from utils import load_players  # ta fonction existante pour charger les joueurs

st.title("🏒 Génération du tournoi")

DATA_DIR = "data"
PLAYER_FILE = os.path.join(DATA_DIR, "joueurs.csv")
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# --- Chargement des joueurs présents ---
joueurs = load_players()
joueurs = joueurs[joueurs["Présent"] == True]

if joueurs.empty:
    st.warning("Aucun joueur présent. Cochez d’abord les joueurs dans **Gestion des joueurs**.")
    st.stop()

st.write(f"**{len(joueurs)} joueurs présents.**")

# --- Séparation attaquants / défenseurs pour équilibrer les équipes ---
attaquants = joueurs[joueurs["Position"] == "Attaquant"].copy()
defenseurs = joueurs[joueurs["Position"] == "Défenseur"].copy()

# --- Création équilibrée de 4 équipes ---
def creer_equipes_equilibrees():
    nb_equipes = 4
    equipes = {f"Équipe {i+1}": [] for i in range(nb_equipes)}

    # Mélange pour aléatoire
    attaquants_sorted = attaquants.sample(frac=1).sort_values("Talent", ascending=False).reset_index(drop=True)
    defenseurs_sorted = defenseurs.sample(frac=1).sort_values("Talent", ascending=False).reset_index(drop=True)

    # Répartition en rond
    for i, row in attaquants_sorted.iterrows():
        equipes[f"Équipe {(i % nb_equipes) + 1}"].append(row)
    for i, row in defenseurs_sorted.iterrows():
        equipes[f"Équipe {(i % nb_equipes) + 1}"].append(row)

    equipes_df = {team: pd.DataFrame(data) for team, data in equipes.items()}
    return equipes_df

if st.button("🎲 Générer les équipes du tournoi"):
    equipes_df = creer_equipes_equilibrees()
    st.session_state["equipes_tournoi"] = equipes_df
    st.success("✅ Équipes générées !")

# --- Affichage des équipes générées ---
if "equipes_tournoi" in st.session_state:
    equipes_df = st.session_state["equipes_tournoi"]
    st.subheader("📋 Équipes du tournoi")
    cols = st.columns(4)
    for i, (nom, df) in enumerate(equipes_df.items()):
        with cols[i]:
            st.markdown(f"### 🏒 {nom}")
            st.dataframe(df[["Nom", "Position", "Talent"]], hide_index=True)
            moyenne = df["Talent"].mean()
            st.write(f"**Moyenne de talent :** {moyenne:.2f}")

# --- Génération du tournoi ---
def generer_matchs_equilibres(equipes):
    noms_equipes = list(equipes.keys())
    combinaisons = list(itertools.combinations(noms_equipes, 2))
    random.shuffle(combinaisons)

    # Construction d’un horaire pour éviter matchs consécutifs
    horaire = []
    while combinaisons:
        for eq in noms_equipes:
            for match in combinaisons:
                if eq in match and all(eq not in m for m in horaire[-2:]):  # évite 2 matchs de suite
                    horaire.append(match)
                    combinaisons.remove(match)
                    break
            if not combinaisons:
                break

    matchs = pd.DataFrame(horaire, columns=["Équipe A", "Équipe B"])
    matchs["Score A"] = 0
    matchs["Score B"] = 0
    matchs["Terminé"] = False
    matchs["Phase"] = "Ronde"
    return matchs

if "equipes_tournoi" in st.session_state:
    if st.button("🏁 Créer le tournoi"):
        equipes_df = st.session_state["equipes_tournoi"]
        matchs = generer_matchs_equilibres(equipes_df)
        matchs.to_csv(BRACKET_FILE, index=False)
        st.success("✅ Tournoi créé avec succès ! Rendez-vous dans **Tournoi en cours** pour suivre les matchs.")
        st.balloons()

# --- Suppression sécurisée du tournoi en cours ---
st.divider()
st.subheader("🧹 Réinitialiser le tournoi")
if os.path.exists(BRACKET_FILE):
    if st.button("🗑️ Supprimer le tournoi existant"):
        confirm = st.radio("Souhaitez-vous vraiment supprimer le tournoi ?", ["Non", "Oui, supprimer"], horizontal=True)
        if confirm == "Oui, supprimer":
            os.remove(BRACKET_FILE)
            st.success("Tournoi supprimé avec succès.")
            if "equipes_tournoi" in st.session_state:
                del st.session_state["equipes_tournoi"]
