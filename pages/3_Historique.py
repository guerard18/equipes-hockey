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
        # Réorganisation des colonnes dans l’ordre voulu
        colonnes = ["Date", "Moyenne_Blanc", "Moyenne_Noir", "Equipe_Blanc", "Equipe_Noir"]
        df = df[[c for c in colonnes if c in df.columns]]

        # Affichage clair et trié par date décroissante
        st.dataframe(
            df.sort_values("Date", ascending=False).reset_index(drop=True),
            use_container_width=True,
            hide_index=True
        )

        # Bouton pour téléchargement CSV
        st.download_button(
            label="⬇️ Télécharger l’historique complet (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="historique_equipes.csv",
            mime="text/csv"
        )

        # Option de suppression complète
        if st.button("🧹 Effacer tout l’historique"):
            import os
            os.remove(path)
            st.success("✅ Historique effacé avec succès. Il sera recréé à la prochaine sauvegarde.")
            st.rerun()
