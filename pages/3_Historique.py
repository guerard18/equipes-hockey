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
        colonnes = [
            "Date", "Moyenne_BLANCS", "Moyenne_NOIRS",
            "Trios_BLANCS", "Duos_BLANCS", "Trios_NOIRS", "Duos_NOIRS",
            "Équipe_BLANCS", "Équipe_NOIRS"
        ]
        df = df[[c for c in colonnes if c in df.columns]].sort_values("Date", ascending=False)

        # Sélecteur de match
        st.subheader("📅 Choisir une date de match")
        dates = df["Date"].dropna().unique().tolist()
        date_select = st.selectbox("Match du :", dates)
        match = df[df["Date"] == date_select].iloc[0]

        # En-tête
        st.markdown(f"### 🏒 Match du {match['Date']}")
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

        # Télécharger le match sélectionné
        st.download_button(
            label="⬇️ Télécharger ce match (CSV)",
            data=df[df["Date"] == date_select].to_csv(index=False).encode("utf-8"),
            file_name=f"match_{date_select}.csv",
            mime="text/csv"
        )

        # Tableau résumé
        st.subheader("📘 Historique complet (résumé)")
        st.dataframe(
            df[["Date", "Moyenne_BLANCS", "Moyenne_NOIRS"]],
            use_container_width=True,
            hide_index=True
        )

        # Bouton pour tout effacer
        if st.button("🧹 Effacer tout l’historique"):
            os.remove(path)
            st.success("✅ Historique effacé avec succès.")
            st.rerun()
