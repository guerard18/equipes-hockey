import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.title("📜 Historique des matchs")

path = "data/historique.csv"

def saison_from_date(date_str):
    """Retourne la saison (ex: 2024-2025) à partir d'une date"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        annee = date.year
        # Saison démarre à l’automne (août)
        if date.month >= 8:
            return f"{annee}-{annee + 1}"
        else:
            return f"{annee - 1}-{annee}"
    except Exception:
        return "Inconnue"

if not os.path.exists(path):
    st.warning("Aucun historique trouvé pour le moment.")
else:
    df = pd.read_csv(path)

    if df.empty:
        st.info("L’historique est vide pour le moment.")
    else:
        # Ajouter la colonne saison si absente
        if "Saison" not in df.columns:
            df["Saison"] = df["Date"].apply(saison_from_date)
            df.to_csv(path, index=False)

        colonnes = [
            "Date", "Saison", "Moyenne_BLANCS", "Moyenne_NOIRS",
            "Trios_BLANCS", "Duos_BLANCS", "Trios_NOIRS", "Duos_NOIRS",
            "Équipe_BLANCS", "Équipe_NOIRS"
        ]
        df = df[[c for c in colonnes if c in df.columns]].sort_values("Date", ascending=False)

        # --- Filtrer par saison ---
        st.subheader("📅 Sélection de la saison")
        saisons = sorted(df["Saison"].dropna().unique(), reverse=True)
        saison_select = st.selectbox("Choisir une saison :", saisons)
        df_saison = df[df["Saison"] == saison_select]

        if df_saison.empty:
            st.warning("Aucun match enregistré pour cette saison.")
        else:
            # --- Sélecteur de match ---
            st.subheader("🏒 Choisir une date de match")
            dates = df_saison["Date"].dropna().unique().tolist()
            date_select = st.selectbox("Match du :", dates)
            match = df_saison[df_saison["Date"] == date_select].iloc[0]

            # --- Affichage du match sélectionné ---
            st.markdown(f"### 🏒 Match du {match['Date']} — Saison {saison_select}")
            st.write(f"**Moyenne BLANCS ⚪ :** {match['Moyenne_BLANCS']}")
            st.write(f"**Moyenne NOIRS ⚫ :** {match['Moyenne_NOIRS']}")

            st.divider()
            col1, col2 = st.columns(2)

            # ----- BLANCS -----
            with col1:
                st.markdown("### ⚪ BLANCS")
                st.markdown("**Trios :**")
                st.markdown(match.get("Trios_BLANCS", "Aucun trio enregistré"))
                st.markdown("**Duos :**")
                st.markdown(match.get("Duos_BLANCS", "Aucun duo enregistré"))
                st.markdown("**Joueurs :**")
                for j in match["Équipe_BLANCS"].split(", "):
                    st.write(f"- {j}")

            # ----- NOIRS -----
            with col2:
                st.markdown("### ⚫ NOIRS")
                st.markdown("**Trios :**")
                st.markdown(match.get("Trios_NOIRS", "Aucun trio enregistré"))
                st.markdown("**Duos :**")
                st.markdown(match.get("Duos_NOIRS", "Aucun duo enregistré"))
                st.markdown("**Joueurs :**")
                for j in match["Équipe_NOIRS"].split(", "):
                    st.write(f"- {j}")

            st.divider()
            st.download_button(
                label="⬇️ Télécharger ce match (CSV)",
                data=df_saison[df_saison["Date"] == date_select].to_csv(index=False).encode("utf-8"),
                file_name=f"match_{date_select}.csv",
                mime="text/csv"
            )

            # --- Tableau résumé pour la saison ---
            st.subheader(f"📘 Historique de la saison {saison_select}")
            st.dataframe(
                df_saison[["Date", "Moyenne_BLANCS", "Moyenne_NOIRS"]],
                use_container_width=True,
                hide_index=True
            )

        # --- Bouton de suppression complète ---
        st.divider()
        if st.button("🧹 Effacer tout l’historique"):
            os.remove(path)
            st.success("✅ Historique effacé avec succès.")
            st.rerun()
