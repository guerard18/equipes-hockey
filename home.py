import streamlit as st

st.set_page_config(page_title="Gestionnaire hockey", page_icon="🏒", layout="wide")

st.title("🏒 Gestionnaire d’équipes de hockey")
st.markdown("""
Bienvenue ! Utilise le menu **Pages** (en haut à gauche) :
- **1 — Gestion des joueurs** : ajoute/modifie les joueurs, leurs talents (Att/Def) et coche **Présent**.
- **2 — Formation des équipes** : génère 2 équipes équilibrées (2 trios + 2 duos par équipe), avec **édition** possible.
- **3 — Historique** : consulte, exporte, ou réinitialise l’historique.
""")

st.info("💡 Astuce : commence par **Gestion des joueurs** pour cocher les présents puis va sur **Formation des équipes**.")
