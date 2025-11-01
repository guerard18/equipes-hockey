import streamlit as st
import pandas as pd
import random
from datetime import datetime
from utils import load_players, save_history

# Optionnel : commit GitHub automatique
try:
    from github_utils import save_to_github
    GITHUB_OK = True
except Exception:
    GITHUB_OK = False

st.title("2️⃣ Formation des équipes de hockey 🏒")
st.markdown(
    "Cette page forme d’abord **4 trios d’attaque** et **4 duos de défense** "
    "ayant des moyennes de talent aussi proches que possible, puis assemble "
    "deux équipes équilibrées à partir de ces unités."
)

# ------------------------------
# Charger les joueurs présents
# ------------------------------
players = load_players()
players_present = players[players["present"] == True].reset_index(drop=True)

st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")

if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — les équipes seront formées quand même.")

# ------------------------------
# BOUTON : FORMER LES ÉQUIPES
# ------------------------------
if st.button("🎯 Former les équipes équilibrées"):

    if players_present.empty:
        st.error("❌ Aucun joueur présent.")
        st.stop()

    # Déterminer la position principale
    players_present["poste"] = players_present.apply(
        lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur",
        axis=1
    )

    # Calculer un score global
    players_present["talent_total"] = players_present[["talent_attaque", "talent_defense"]].mean(axis=1)

    attaquants = players_present[players_present["poste"] == "Attaquant"].copy()
    defenseurs = players_present[players_present["poste"] == "Défenseur"].copy()

    # S’il manque des joueurs dans un poste, combler avec les meilleurs restants
    if len(defenseurs) < 8:
        besoin = 8 - len(defenseurs)
        supl = attaquants.nlargest(besoin, "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    if len(attaquants) < 12:
        besoin = 12 - len(attaquants)
        supl = defenseurs.nlargest(besoin, "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)

    # ------------------------------
    # FONCTION snake draft équilibrée
    # ------------------------------
    def snake_draft(df, taille_groupe, nb_groupes, colonne):
        df = df.sort_values(colonne, ascending=False).reset_index(drop=True)
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

        groupes_df = []
        for g in groupes:
            groupes_df.append(pd.DataFrame(g))
        return groupes_df

    # Former 4 trios équilibrés
    trios = snake_draft(attaquants, 3, 4, "talent_attaque")

    # Former 4 duos équilibrés
    duos = snake_draft(defenseurs, 2, 4, "talent_defense")

    # ------------------------------
    # AFFICHER LES LIGNES ET MOYENNES
    # ------------------------------
    def afficher_unites(titre, unites, colonne):
        st.subheader(titre)
        moyennes = []
        for i, unite in enumerate(unites, 1):
            if not unite.empty:
                moyenne = round(unite[colonne].mean(), 2)
                moyennes.append(moyenne)
                st.markdown(f"**{titre[:-1]} {i}** — Moyenne : {moyenne}")
                for _, p in unite.iterrows():
                    st.write(f"- {p['nom']} ({p[colonne]:.1f})")
        st.info(f"Moyenne des {titre.lower()} : {round(sum(moyennes)/len(moyennes),2)} ± {round(pd.Series(moyennes).std(),2)}")

    st.header("🔢 Lignes équilibrées créées")
    afficher_unites("Trios", trios, "talent_attaque")
    afficher_unites("Duos", duos, "talent_defense")

    # ------------------------------
    # ASSIGNATION AUX ÉQUIPES
    # ------------------------------
    equipeA_trios = trios[::2]
    equipeB_trios = trios[1::2]
    equipeA_duos = duos[::2]
    equipeB_duos = duos[1::2]

    def moyenne_globale(unites, colonne):
        valeurs = [u[colonne].mean() for u in unites if not u.empty]
        return round(sum(valeurs) / len(valeurs), 2) if valeurs else 0

    moyA = round((moyenne_globale(equipeA_trios, "talent_attaque") + moyenne_globale(equipeA_duos, "talent_defense")) / 2, 2)
    moyB = round((moyenne_globale(equipeB_trios, "talent_attaque") + moyenne_globale(equipeB_duos, "talent_defense")) / 2, 2)

    st.divider()
    st.header("🟦 Équipe A")
    st.write(f"**Moyenne globale :** {moyA}")
    for i, trio in enumerate(equipeA_trios, 1):
        st.markdown(f"**Trio {i}**")
        for _, p in trio.iterrows():
            st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
    for i, duo in enumerate(equipeA_duos, 1):
        st.markdown(f"**Duo {i}**")
        for _, p in duo.iterrows():
            st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

    st.divider()
    st.header("🟥 Équipe B")
    st.write(f"**Moyenne globale :** {moyB}")
    for i, trio in enumerate(equipeB_trios, 1):
        st.markdown(f"**Trio {i}**")
        for _, p in trio.iterrows():
            st.write(f"- {p['nom']} ({p['talent_attaque']:.1f})")
    for i, duo in enumerate(equipeB_duos, 1):
        st.markdown(f"**Duo {i}**")
        for _, p in duo.iterrows():
            st.write(f"- {p['nom']} ({p['talent_defense']:.1f})")

    diff = abs(moyA - moyB)
    if diff < 0.5:
        st.success("⚖️ Les équipes sont très équilibrées !")
    elif diff < 1:
        st.info("🟡 Les équipes sont assez proches.")
    else:
        st.warning("🔴 Les équipes sont un peu déséquilibrées.")

    # ------------------------------
    # SAUVEGARDE
    # ------------------------------
    if st.button("💾 Enregistrer ces équipes dans l’historique"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        equipeA = [p for trio in equipeA_trios + equipeA_duos for p in trio["nom"].tolist()]
        equipeB = [p for trio in equipeB_trios + equipeB_duos for p in trio["nom"].tolist()]

        save_history(equipeA, equipeB, moyA, moyB, date)
        st.success("✅ Équipes enregistrées dans l’historique !")

        if GITHUB_OK:
            try:
                save_to_github("data/historique.csv", "Nouvelle répartition équilibrée (trios/duos paritaires)")
                st.toast("💾 Sauvegarde GitHub réussie")
            except Exception as e:
                st.warning(f"⚠️ Erreur de sauvegarde GitHub : {e}")
