import streamlit as st
import pandas as pd
import os

st.title("📜 Historique des matchs")

path = "data/historique.csv"

if not os.path.exists(path):
    st.warning("Aucun historique trouvé pour le moment.")
else:
    df = pd.read_csv(path)
    if df.empty:
        st.info("L’historique est vide pour le moment.")
    else:
        # Réorganiser les colonnes et trier
        colonnes = ["Date", "Moyenne_Blanc", "Moyenne_Noir", "Equipe_Blanc", "Equipe_Noir"]
        df = df[[c for c in colonnes if c in df.columns]].sort_values("Date", ascending=False)

        # Sélecteur de match
        st.subheader("📅 Choisir une date de match")
        dates = df["Date"].dropna().unique().tolist()
        date_select = st.selectbox("Match du :", dates)

        # Filtrage du match sélectionné
        match = df[df["Date"] == date_select].iloc[0]

        # Affichage des moyennes
        st.markdown(f"### 🗓️ Match du {match['Date']}")
        st.write(f"**Moyenne Équipe Blanche :** {match['Moyenne_Blanc']}")
        st.write(f"**Moyenne Équipe Noire :** {match['Moyenne_Noir']}")

        # Affichage clair des équipes
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### ⚪ Équipe Blanche")
            joueurs_blanc = match["Equipe_Blanc"].split(", ")
            for j in joueurs_blanc:
                st.write(f"- {j}")

        with col2:
            st.markdown("### ⚫ Équipe Noire")
            joueurs_noir = match["Equipe_Noir"].split(", ")
            for j in joueurs_noir:
                st.write(f"- {j}")

        st.divider()

        # Téléchargement CSV du match
        st.download_button(
            label="⬇️ Télécharger ce match (CSV)",
            data=df[df["Date"] == date_select].to_csv(index=False).encode("utf-8"),
            file_name=f"match_{date_select}.csv",
            mime="text/csv"
        )

        # Affichage de l'historique complet (résumé)
        st.subheader("📘 Historique complet (résumé)")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Option de suppression
        if st.button("🧹 Effacer tout l’historique"):
            os.remove(path)
            st.success("✅ Historique effacé avec succès.")
            st.rerun()
