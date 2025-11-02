import streamlit as st
import pandas as pd
import os

st.title("📈 Statistiques des joueurs")

players_path = "data/joueurs.csv"
history_path = "data/historique.csv"

if not os.path.exists(history_path):
    st.warning("Aucun historique trouvé pour le moment.")
else:
    hist = pd.read_csv(history_path)
    joueurs = pd.read_csv(players_path)

    # Vérification de la colonne Date
    if "Date" not in hist.columns:
        st.error("❌ Le fichier historique ne contient pas de colonne 'Date'. Vérifie ton historique.csv.")
    else:
        stats = pd.DataFrame({"nom": joueurs["nom"].unique()})
        stats["Matchs joués"] = 0
        stats["Fois BLANCS"] = 0
        stats["Fois NOIRS"] = 0

        # Calcul des présences uniques par date
        presence_par_joueur = {}
        for _, match in hist.iterrows():
            date = str(match["Date"])
            blancs = str(match.get("Équipe_BLANCS", "")).split(", ")
            noirs = str(match.get("Équipe_NOIRS", "")).split(", ")
            joueurs_du_match = set(blancs + noirs)
            for j in joueurs_du_match:
                if j not in presence_par_joueur:
                    presence_par_joueur[j] = set()
                presence_par_joueur[j].add(date)

        # Nombre de matchs joués par joueur
        stats["Matchs joués"] = stats["nom"].apply(lambda x: len(presence_par_joueur.get(x, set())))

        # Compter les fois BLANCS / NOIRS
        for _, match in hist.iterrows():
            blancs = str(match.get("Équipe_BLANCS", "")).split(", ")
            noirs = str(match.get("Équipe_NOIRS", "")).split(", ")
            for j in stats["nom"]:
                if j in blancs:
                    stats.loc[stats["nom"] == j, "Fois BLANCS"] += 1
                elif j in noirs:
                    stats.loc[stats["nom"] == j, "Fois NOIRS"] += 1

        # Trier par matchs joués décroissants
        stats = stats.sort_values(by=["Matchs joués", "Fois BLANCS", "Fois NOIRS"], ascending=False)

        st.dataframe(stats, use_container_width=True, hide_index=True)

        total_matchs = hist["Date"].nunique() if "Date" in hist.columns else 0
        st.write(f"### 📅 Total de matchs enregistrés : {total_matchs}")

        st.download_button(
            label="⬇️ Télécharger les statistiques (CSV)",
            data=stats.to_csv(index=False).encode("utf-8"),
            file_name="statistiques_joueurs.csv",
            mime="text/csv"
        )
