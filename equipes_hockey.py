import streamlit as st
import random
from itertools import combinations

st.set_page_config(page_title="Créateur d'équipes de hockey", page_icon="🏒")

st.title("🏒 Créateur d'équipes de hockey équilibrées (avec postes)")

st.markdown("""
Ajoute les joueurs, leur **poste** (attaquant ou défenseur) et leur **niveau de talent** (ex. sur 10).  
L'application essaiera de former deux équipes équilibrées avec environ **6 attaquants et 4 défenseurs par équipe**.
""")

# Nombre de joueurs total
n_joueurs = st.number_input("Nombre total de joueurs :", min_value=4, max_value=40, value=20, step=1)

# Génération aléatoire pour tester rapidement
if st.button("🎲 Générer des joueurs aléatoires"):
    joueurs = []
    for i in range(n_joueurs):
        poste = random.choice(["Attaquant", "Défenseur"])
        joueurs.append((f"Joueur {i+1}", poste, random.randint(1, 10)))
    st.session_state["joueurs_auto"] = joueurs
else:
    joueurs = st.session_state.get("joueurs_auto", [])

# Entrée manuelle des joueurs
st.subheader("Entre les joueurs :")
joueurs_saisis = []
for i in range(n_joueurs):
    if i < len(joueurs):
        nom_defaut, poste_defaut, talent_defaut = joueurs[i]
    else:
        nom_defaut, poste_defaut, talent_defaut = "", "Attaquant", 5
    nom = st.text_input(f"Nom du joueur {i+1}", value=nom_defaut, key=f"nom_{i}")
    poste = st.selectbox(f"Poste du joueur {i+1}", ["Attaquant", "Défenseur"], index=0 if poste_defaut == "Attaquant" else 1, key=f"poste_{i}")
    talent = st.number_input(f"Talent du joueur {i+1}", min_value=1, max_value=10, value=talent_defaut, step=1, key=f"talent_{i}")
    if nom:
        joueurs_saisis.append((nom, poste, talent))

# --- Fonction de création des équipes ---

def creer_equipes_par_poste(joueurs, nb_attaquants=6, nb_defenseurs=4):
    attaquants = [j for j in joueurs if j[1] == "Attaquant"]
    defenseurs = [j for j in joueurs if j[1] == "Défenseur"]
    
    # Vérifications
    if len(attaquants) < nb_attaquants * 2 or len(defenseurs) < nb_defenseurs * 2:
        st.warning("⚠️ Il n'y a pas assez d'attaquants ou de défenseurs pour faire 2 équipes complètes.")
    
    meilleure_diff = float("inf")
    meilleure_equipe = None
    
    # Combinaisons d'attaquants
    for eqA1 in combinations(attaquants, min(nb_attaquants, len(attaquants)//2)):
        eqA2 = [a for a in attaquants if a not in eqA1]
        # Combinaisons de défenseurs
        for eqD1 in combinations(defenseurs, min(nb_defenseurs, len(defenseurs)//2)):
            eqD2 = [d for d in defenseurs if d not in eqD1]
            equipe1 = list(eqA1) + list(eqD1)
            equipe2 = list(eqA2) + list(eqD2)
            somme1 = sum(j[2] for j in equipe1)
            somme2 = sum(j[2] for j in equipe2)
            diff = abs(somme1 - somme2)
            if diff < meilleure_diff:
                meilleure_diff = diff
                meilleure_equipe = (equipe1, equipe2)
    return meilleure_equipe, meilleure_diff

# --- Affichage du résultat ---
if st.button("🏒 Créer les équipes !") and len(joueurs_saisis) >= 4:
    (equipe1, equipe2), diff = creer_equipes_par_poste(joueurs_saisis)
    if equipe1 and equipe2:
        st.success(f"Différence totale de talent : **{diff}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Équipe 1")
            total1 = sum(j[2] for j in equipe1)
            st.write("**Attaquants :**")
            for j in [x for x in equipe1 if x[1] == "Attaquant"]:
                st.write(f"{j[0]} — {j[2]}")
            st.write("**Défenseurs :**")
            for j in [x for x in equipe1 if x[1] == "Défenseur"]:
                st.write(f"{j[0]} — {j[2]}")
            st.write(f"**Total talent : {total1}**")

        with col2:
            st.subheader("Équipe 2")
            total2 = sum(j[2] for j in equipe2)
            st.write("**Attaquants :**")
            for j in [x for x in equipe2 if x[1] == "Attaquant"]:
                st.write(f"{j[0]} — {j[2]}")
            st.write("**Défenseurs :**")
            for j in [x for x in equipe2 if x[1] == "Défenseur"]:
                st.write(f"{j[0]} — {j[2]}")
            st.wr
