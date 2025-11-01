import streamlit as st
import pandas as pd
import os

st.title("📜 Historique des équipes")

path = "data/historique.csv"

if not os.path.exists(path):
    st.warning("Aucun historique trouvé pour le moment.")
else:
    df = pd.read_csv(path)
    if df.empty:
        st.info("L’historique est vide pour le moment.")
    else:
        st.dataframe(df.sort_values("Date", ascending=False), use_container_width=True)
        st.download_button(
            label="⬇️ Télécharger l’historique",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="historique_equipes.csv",
            mime="text/csv"
        )
