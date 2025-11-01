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
        # Réorganisation des colonnes
        colonnes = ["Date", "Moyenne_Blanc", "Moyenne_Noir", "Equipe_Blanc", "Equipe_Noir"]
        df = df[[c for c in colonnes if c in df.columns]]

        # Choix de la date à afficher
        st.subheader("📅 Choisir la date du match")
        dates = sorted(df["Date"].dropna().unique(), reverse=True)
        date_select = st.selectbox("Match du :", dates)
        df_sel = df[df["Date"] == date_select]

        st.dataframe(df_sel, use_container_width=True, hide_index=True)

        st.download_button(
            label="⬇️ Télécharger ce match (CSV)",
            data=df_sel.to_csv(index=False).encode("utf-8"),
            file_name=f"match_{date_select}.csv",
            mime="text/csv"
        )

        if st.button("🧹 Effacer tout l’historique"):
            os.remove(path)
            st.success("✅ Historique effacé.")
            st.rerun()
