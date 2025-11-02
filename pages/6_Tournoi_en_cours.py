import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

st.title("🏆 Tournoi en cours")

BRACKET_PATH = "data/tournoi_bracket.csv"
HISTO_PATH = "data/historique_tournois.csv"
os.makedirs("data", exist_ok=True)

# --- Vérification tournoi existant ---
if not os.path.exists(BRACKET_PATH):
    st.warning("Aucun tournoi n’a encore été configuré. Rendez-vous dans la page **Configuration du tournoi**.")
    st.stop()

# --- Chargement des matchs ---
try:
    matchs = pd.read_csv(BRACKET_PATH)
except Exception as e:
    st.error(f"Erreur de lecture du fichier tournoi : {e}")
    st.stop()

if matchs.empty:
    st.warning("Aucun match n’a encore été défini.")
    st.stop()

# --- Édition des scores ---
st.subheader("📋 Saisie des scores")
st.info("Entrez les scores et cochez *Terminé* une fois le match joué.")

for col in ["Score A", "Score B", "Terminé"]:
    if col not in matchs.columns:
        matchs[col] = 0 if "Score" in col else False

edited = st.data_editor(
    matchs,
    use_container_width=True,
    num_rows="fixed",
    key="edit_matchs"
)

if st.button("💾 Enregistrer les résultats"):
    edited.to_csv(BRACKET_PATH, index=False)
    st.success("Résultats enregistrés !")

# --- Classement de la ronde ---
def classement_from_results(results_round: pd.DataFrame):
    if results_round.empty:
        return pd.DataFrame(columns=["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"])
    equipes = pd.unique(results_round[["Équipe A","Équipe B"]].values.ravel("K"))
    table = {eq: {"MJ":0,"V":0,"N":0,"D":0,"BP":0,"BC":0,"Pts":0} for eq in equipes}
    for _, m in results_round.iterrows():
        if not bool(m.get("Terminé", False)): continue
        a,b = m["Équipe A"], m["Équipe B"]
        sa,sb = int(m.get("Score A",0)), int(m.get("Score B",0))
        table[a]["MJ"]+=1; table[b]["MJ"]+=1
        table[a]["BP"]+=sa; table[a]["BC"]+=sb
        table[b]["BP"]+=sb; table[b]["BC"]+=sa
        if sa>sb: table[a]["V"]+=1; table[b]["D"]+=1; table[a]["Pts"]+=2
        elif sb>sa: table[b]["V"]+=1; table[a]["D"]+=1; table[b]["Pts"]+=2
        else: table[a]["N"]+=1; table[b]["N"]+=1; table[a]["Pts"]+=1; table[b]["Pts"]+=1
    clas = pd.DataFrame.from_dict(table, orient="index").reset_index().rename(columns={"index":"Équipe"})
    clas["Diff"]=clas["BP"]-clas["BC"]
    clas=clas.sort_values(by=["Pts","Diff","BP"],ascending=False,ignore_index=True)
    clas["Rang"]=clas.index+1
    return clas[["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"]]

st.divider()
st.subheader("📊 Classement de la ronde préliminaire")
round_only = edited[edited["Phase"] == "Ronde"]
classement = classement_from_results(round_only)
if not classement.empty:
    st.dataframe(classement, use_container_width=True)
else:
    st.info("Aucun match terminé pour le moment.")

# --- Demi-finales ---
st.divider()
st.subheader("⚔️ Demi-finales")

if not classement.empty and "Demi" not in edited["Phase"].values:
    if st.button("🏁 Générer les demi-finales"):
        if len(classement) < 4:
            st.warning("Il faut au moins 4 équipes classées.")
        else:
            demi1=[classement.loc[0,"Équipe"],classement.loc[3,"Équipe"]]
            demi2=[classement.loc[1,"Équipe"],classement.loc[2,"Équipe"]]
            new_matches=pd.DataFrame([
                {"Équipe A":demi1[0],"Équipe B":demi1[1],"Phase":"Demi","Score A":0,"Score B":0,"Terminé":False},
                {"Équipe A":demi2[0],"Équipe B":demi2[1],"Phase":"Demi","Score A":0,"Score B":0,"Terminé":False}
            ])
            updated=pd.concat([edited,new_matches],ignore_index=True)
            updated.to_csv(BRACKET_PATH,index=False)
            st.success("✅ Demi-finales générées !")
            st.rerun()

# --- Finale ---
st.divider()
st.subheader("🏅 Finale")

demis = edited[edited["Phase"]=="Demi"]
finale_exists = "Finale" in edited["Phase"].values
if not finale_exists and not demis.empty:
    gagnants=[]
    for _,m in demis.iterrows():
        if not m.get("Terminé",False): continue
        if m["Score A"]>m["Score B"]: gagnants.append(m["Équipe A"])
        elif m["Score B"]>m["Score A"]: gagnants.append(m["Équipe B"])
    if len(gagnants)==2:
        if st.button("🥇 Générer la finale"):
            finale=pd.DataFrame([{
                "Équipe A":gagnants[0],"Équipe B":gagnants[1],
                "Phase":"Finale","Score A":0,"Score B":0,"Terminé":False
            }])
            updated=pd.concat([edited,finale],ignore_index=True)
            updated.to_csv(BRACKET_PATH,index=False)
            st.success("✅ Finale générée !")
            st.rerun()

# --- Bracket graphique ---
st.divider()
st.subheader("🎯 Bracket du tournoi")

def afficher_bracket():
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Lignes du bracket
    ax.plot([1, 2], [8, 8], color="black")
    ax.plot([1, 2], [6, 6], color="black")
    ax.plot([2, 2], [6, 8], color="black")

    ax.plot([1, 2], [4, 4], color="black")
    ax.plot([1, 2], [2, 2], color="black")
    ax.plot([2, 2], [2, 4], color="black")

    ax.plot([2, 4], [7, 7], color="black")
    ax.plot([2, 4], [3, 3], color="black")
    ax.plot([4, 4], [3, 7], color="black")

    ax.plot([4, 6], [5, 5], color="black")
    ax.plot([6, 6], [4, 6], color="black")
    ax.plot([6, 7.5], [5, 5], color="black")

    # Case champion
    ax.add_patch(mpatches.Rectangle((7.5, 4.5), 1.8, 1, fill=True, color="lightgray", ec="black"))
    ax.text(8.4, 5.1, "CHAMPION", va="center", ha="center", fontsize=11, fontweight="bold")

    # Titres des phases
    ax.text(1.5, 9.3, "DEMI-FINALES", ha="center", fontsize=12, fontweight="bold")
    ax.text(5, 8.8, "FINALE", ha="center", fontsize=12, fontweight="bold")

    # Récupération des données
    demis = edited[edited["Phase"] == "Demi"]
    finale = edited[edited["Phase"] == "Finale"]

    # Demi 1
    if len(demis) > 0:
        m1 = demis.iloc[0]
        ax.text(1.3, 8.1, m1["Équipe A"], va="bottom", ha="left", fontsize=9)
        ax.text(1.3, 5.9, m1["Équipe B"], va="top", ha="left", fontsize=9)
        if m1.get("Terminé", False):
            ax.text(3.0, 7.3, f"{m1['Score A']}-{m1['Score B']}", ha="center", va="center", fontsize=12, fontweight="bold")

    # Demi 2
    if len(demis) > 1:
        m2 = demis.iloc[1]
        ax.text(1.3, 4.1, m2["Équipe A"], va="bottom", ha="left", fontsize=9)
        ax.text(1.3, 1.9, m2["Équipe B"], va="top", ha="left", fontsize=9)
        if m2.get("Terminé", False):
            ax.text(3.0, 3.3, f"{m2['Score A']}-{m2['Score B']}", ha="center", va="center", fontsize=12, fontweight="bold")

    # Finale
    champion_name = ""
    if not finale.empty:
        f = finale.iloc[0]
        ax.text(4.3, 6.1, f["Équipe A"], va="bottom", ha="left", fontsize=9)
        ax.text(4.3, 3.9, f["Équipe B"], va="top", ha="left", fontsize=9)
        if f.get("Terminé", False):
            ax.text(5.3, 5.3, f"{f['Score A']}-{f['Score B']}", ha="center", va="center", fontsize=13, fontweight="bold")
            champion_name = f["Équipe A"] if f["Score A"] > f["Score B"] else f["Équipe B"]

    # Nom du champion sous la case
    if champion_name:
        ax.text(8.4, 4.3, champion_name, va="top", ha="center", fontsize=11, fontweight="bold", color="darkblue")

    st.pyplot(fig)

afficher_bracket()

# --- Clôture du tournoi ---
st.divider()
st.subheader("🏆 Clôturer le tournoi")

finale = edited[edited["Phase"] == "Finale"]
if not finale.empty and bool(finale.iloc[0].get("Terminé", False)):
    f = finale.iloc[0]
    champion = f["Équipe A"] if f["Score A"] > f["Score B"] else f["Équipe B"]
    vice = f["Équipe B"] if champion == f["Équipe A"] else f["Équipe A"]
    st.success(f"🥇 Champion : {champion} | 🥈 Vice-champion : {vice}")

    if st.button("💾 Enregistrer le tournoi dans l’historique"):
        hist = pd.read_csv(HISTO_PATH) if os.path.exists(HISTO_PATH) else pd.DataFrame()
        tournoi_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        record = pd.DataFrame([{
            "Tournoi_ID": tournoi_id,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Champion": champion,
            "Vice_champion": vice,
            "Equipes": ", ".join(classement["Équipe"].tolist()),
            "Classement_final": " | ".join([f"{r}. {e}" for r,e in zip(classement['Rang'], classement['Équipe'])]),
            "Matches": " || ".join([f"{r['Équipe A']} {r['Score A']}-{r['Score B']} {r['Équipe B']}" for _,r in edited.iterrows()])
        }])
        hist = pd.concat([hist, record], ignore_index=True)
        hist.to_csv(HISTO_PATH, index=False)
        st.success("✅ Tournoi archivé dans l’historique.")
        os.remove(BRACKET_PATH)

# --- Suppression sécurisée ---
st.divider()
st.subheader("🧹 Supprimer le tournoi en cours")
if st.button("🗑️ Supprimer le tournoi"):
    confirm = st.radio("Souhaitez-vous vraiment supprimer le tournoi ?", ["Non", "Oui, supprimer"], horizontal=True)
    if confirm == "Oui, supprimer":
        os.remove(BRACKET_PATH)
        st.success("Tournoi supprimé avec succès.")
        st.rerun()
