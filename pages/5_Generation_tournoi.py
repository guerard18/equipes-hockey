import streamlit as st
import pandas as pd
import os
import random
import itertools
from datetime import datetime
from utils import load_players

st.title("🏒 Génération du tournoi (4 équipes)")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- Charger les joueurs ---
def charger_joueurs():
    """Recharge toujours la version actuelle du fichier joueurs.csv"""
    players = load_players()
    return players[players["present"] == True].reset_index(drop=True)

# Bouton pour recharger
if st.button("🔄 Recharger les joueurs présents"):
    st.session_state["players_present"] = charger_joueurs()
    st.success("✅ Liste des joueurs mise à jour !")

# Charger depuis la session ou directement
players_present = st.session_state.get("players_present", charger_joueurs())

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")
if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — la formation sera approximative.")

# --- Fonction utilitaire ---
def snake_draft(df, nb_groupes, colonne):
    """Distribution équilibrée des joueurs selon le talent."""
    if df.empty:
        return [pd.DataFrame() for _ in range(nb_groupes)]
    df = df.sample(frac=1).sort_values(colonne, ascending=False).reset_index(drop=True)
    groupes = [[] for _ in range(nb_groupes)]
    sens = 1
    idx = 0
    for _, joueur in df.iterrows():
        groupes[idx].append(joueur)
        idx += sens
        if idx == nb_groupes:
            sens = -1
            idx = nb_groupes - 1
        elif idx < 0:
            sens = 1
            idx = 0
    return [pd.DataFrame(g) for g in groupes]

# --- Génération automatique des 4 équipes ---
def generer_equipes_tournoi(players_present):
    players_present = players_present.copy()
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    # Vérifier qu'on a assez de joueurs
    if len(attaquants) < 24:
        supl = defenseurs.nlargest(24 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

    if len(defenseurs) < 16:
        supl = attaquants.nlargest(16 - len(defenseurs), "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    # 8 trios (pour 4 équipes, 2 chacun)
    trios = snake_draft(attaquants, 8, "talent_attaque")
    duos = snake_draft(defenseurs, 8, "talent_defense")

    random.shuffle(trios)
    random.shuffle(duos)

    # Attribution 2 trios + 2 duos par équipe
    equipes = {
        "BLANCS ⚪": {"trios": trios[0:2], "duos": duos[0:2]},
        "NOIRS ⚫": {"trios": trios[2:4], "duos": duos[2:4]},
        "ROUGES 🔴": {"trios": trios[4:6], "duos": duos[4:6]},
        "VERTS 🟢": {"trios": trios[6:8], "duos": duos[6:8]},
    }

    # Calcul des moyennes de talent
    for nom, eq in equipes.items():
        moy_trios = [t["talent_attaque"].mean() for t in eq["trios"] if not t.empty]
        moy_duos = [d["talent_defense"].mean() for d in eq["duos"] if not d.empty]
        eq["moyenne"] = round((sum(moy_trios + moy_duos) / len(moy_trios + moy_duos)), 2)

    return equipes

# --- Affichage et génération ---
if st.button("🎯 Générer les équipes du tournoi"):
    st.session_state["tournoi_equipes"] = generer_equipes_tournoi(players_present)
    st.success("✅ Équipes du tournoi générées !")

equipes = st.session_state.get("tournoi_equipes")

if equipes:
    st.subheader("📋 Composition des équipes du tournoi")
    for nom, eq in equipes.items():
        st.markdown(f"## {nom} — Moyenne : **{eq['moyenne']}**")
        for i, trio in enumerate(eq["trios"], 1):
            if not trio.empty:
                moy = round(trio["talent_attaque"].mean(), 2)
                st.write(f"**Trio {i} ({moy}) :** {', '.join(trio['nom'])}")
        for i, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                moy = round(duo["talent_defense"].mean(), 2)
                st.write(f"**Duo {i} ({moy}) :** {', '.join(duo['nom'])}")
        st.divider()

    # --- Création des matchs ---
    def generer_matchs_equilibres(equipes):
        noms_equipes = list(equipes.keys())
        combinaisons = list(itertools.combinations(noms_equipes, 2))
        random.shuffle(combinaisons)

        horaire = []
        dernieres = {e: -1 for e in noms_equipes}
        match_index = 0

        while combinaisons:
            for eq in noms_equipes:
                for match in combinaisons:
                    if eq in match and all(match_index - dernieres[e] > 1 for e in match):
                        horaire.append(match)
                        for e in match:
                            dernieres[e] = match_index
                        match_index += 1
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

    if st.button("🏁 Créer le tournoi"):
        matchs = generer_matchs_equilibres(equipes)
        matchs.to_csv(BRACKET_FILE, index=False)
        st.success("✅ Tournoi créé avec succès ! Consulte **Tournoi en cours** pour suivre les matchs.")
        st.balloons()

# --- Suppression sécurisée ---
st.divider()
st.subheader("🧹 Réinitialiser le tournoi")
if os.path.exists(BRACKET_FILE):
    if st.button("🗑️ Supprimer le tournoi existant"):
        confirm = st.radio("Souhaitez-vous vraiment supprimer le tournoi ?", ["Non", "Oui, supprimer"], horizontal=True)
        if confirm == "Oui, supprimer":
            os.remove(BRACKET_FILE)
            if "tournoi_equipes" in st.session_state:
                del st.session_state["tournoi_equipes"]
            if "players_present" in st.session_state:
                del st.session_state["players_present"]
            st.success("✅ Tournoi supprimé avec succès.")
