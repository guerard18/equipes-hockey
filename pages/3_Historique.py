import streamlit as st
import pandas as pd
from utils import load_history, reset_history

st.title("3) Historique des équipes")

hist = load_history()
if hist.empty:
    st.info("Aucun historique pour le moment.")
else:
    st.dataframe(hist, use_container_width=True)
    csv = hist.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Télécharger CSV", data=csv, file_name="historique_equipes.csv", mime="text/csv")

    if st.button("🧹 Réinitialiser l’historique"):
        reset_history()
        st.success("Historique effacé.")
        st.experimental_rerun()
