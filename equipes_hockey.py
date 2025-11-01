import streamlit as st
import random
from itertools import combinations

st.set_page_config(page_title="Créateur d'équipes de hockey", page_icon="🏒")

st.title("🏒 Créateur d'équipes de hockey équilibrées")

st.markdown("""
Ajoute les joueurs et leur **niveau de talent** (ex. sur 10).  
Tu peux aussi générer des joueurs aléatoires pour tester plus vite.
""")

# Nombre de joueurs
n_joueurs = st.number_input("Nombre de joueurs :", min_value=2, max_value=20, value=6, step=1)

# Bouton pour générer des joueurs aléatoires
if st.button("🎲 Générer des joueurs aléatoires"):
    joueurs = [(f"Joueur {i+1}", random.randint(1, 10)) for i in range(n_joueurs)]
    st.session_state["joueurs_auto"] = joueurs
else:
    joueurs = st.session_state.get("joueurs_auto", [])

# Saisie des joueurs
st.subheader("Entre les joueurs :")
joueurs_saisis = []
for i in range(n_joueurs):
    if i < len(joueurs):
        nom_defaut, talent_defaut = joueurs[i]
    else:
        nom_defaut, talent_defaut = "", 5
    nom = st.text_input(f"Nom du joueur {i+1}", value=nom_defaut, key=f"nom_{i}")
    talent = st.number_input(f"Talent du joueur {i+1}", min_value=1, max_value=10, value=talent_defaut, step=1, key=f"talent_{i}")
    if nom:
        joueurs_saisis.append((nom, talent))

def creer_equipes(joueurs):
    """Cherche la combinaison la plus équilibrée possible."""
    n = len(joueurs)
    if n < 2:
        return None, None
    if n % 2 != 0:
        st.warning("⚠️ Il y a un nombre impair de joueurs. Un joueur restera sans équipe.")
    meilleure_diff = float("inf")
    meilleure_equipe = None
    
    for equipe1 in combinations(joueurs, n // 2):
        equipe2 = [j for j in joueurs if j not in equipe1]
        somme1 = sum(j[1] for j in equipe1)
        somme2 = sum(j[1] for j in equipe2)
        diff = abs(somme1 - somme2)
        if diff < meilleure_diff:
            meilleure_diff = diff
            meilleure_equipe = (equipe1, equipe2)
    return meilleure_equipe, meilleure_diff

if st.button("🏒 Créer les équipes !") and len(joueurs_saisis) >= 2:
    (equipe1, equipe2), diff = creer_equipes(joueurs_saisis)
    
    st.success(f"Différence totale de talent : **{diff}**")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Équipe 1")
        total1 = sum(j[1] for j in equipe1)
        for j in equipe1:
            st.write(f"{j[0]} — {j[1]}")
        st.write(f"**Total talent : {total1}**")
    
    with col2:
        st.subheader("Équipe 2")
        total2 = sum(j[1] for j in equipe2)
        for j in equipe2:
            st.write(f"{j[0]} — {j[1]}")
        st.write(f"**Total talent : {total2}**")
    
