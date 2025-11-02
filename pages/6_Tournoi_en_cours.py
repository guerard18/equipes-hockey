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

# --- Vérifier si un tournoi est en cours ---
if not os.path.exists(BRACKET_PATH):
    st.warning("Aucun tournoi n’a encore été configuré. Rendez-vous dans la page **Configuration du tournoi**.")
    st.stop()

# Charger les matchs
try:
    matchs = pd.read_csv(BRACKET_PATH)
except Exception as e:
    st.error(f"Erreur lors du chargement du fichier tournoi : {e}")
    st.stop()

if matchs.empty:
    st.warning("Aucun match n’a encore été défini.")
    st.stop()

# --- Saisie des scores ---
st.subheader("📋 Saisie des scores")
st.info("Entrez les scores pour chaque match de ronde, puis cochez *Terminé* pour valider.")

# Ajouter colonnes manquantes si besoin
for col in ["Score A", "Score B", "Terminé"]:
    if col not in matchs.columns:
        matchs[col] = 0 if "Score" in col else False

# Affichage et saisie dynamique
edited = st.data_editor(
    matchs,
    use_container_width=True,
    num_rows="fixed",
    key="edit_matchs"
)

# Sauvegarde des scores modifiés
if st.button("💾 Enregistrer les résultats"):
    edited.to_csv(BRACKET_PATH, index=False)
    st.success("Résultats enregistrés avec succès !")

# --- Fonction classement ---
def classement_from_results(results_round: pd.DataFrame):
    """Classement à partir des matchs terminés (2 pts victoire, 1 nul, 0 défaite)."""
    if results_round is None or results_round.empty:
        return pd.DataFrame(columns=["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"])
    
    equipes = pd.unique(results_round[["Équipe A", "Équipe B"]].values.ravel("K"))
    if len(equipes) == 0:
        return pd.DataFrame(columns=["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"])

    table = {eq: {"MJ":0, "V":0, "N":0, "D":0, "BP":0, "BC":0, "Pts":0} for eq in equipes}
    for _, m in results_round.iterrows():
        if not bool(m.get("Terminé", False)):
            continue
        a, b = m["Équipe A"], m["Équipe B"]
        sa, sb = int(m.get("Score A", 0)), int(m.get("Score B", 0))
        table[a]["MJ"] += 1; table[b]["MJ"] += 1
        table[a]["BP"] += sa; table[a]["BC"] += sb
        table[b]["BP"] += sb; table[b]["BC"] += sa
        if sa > sb:
            table[a]["V"] += 1; table[b]["D"] += 1; table[a]["Pts"] += 2
        elif sb > sa:
            table[b]["V"] += 1; table[a]["D"] += 1; table[b]["Pts"] += 2
        else:
            table[a]["N"] += 1; table[b]["N"] += 1
            table[a]["Pts"] += 1; table[b]["Pts"] += 1

    clas = pd.DataFrame.from_dict(table, orient="index").reset_index().rename(columns={"index":"Équipe"})
    for col in ["BP","BC"]:
        if col not in clas.columns:
            clas[col] = 0
    clas["Diff"] = clas["BP"] - clas["BC"]
    clas = clas.sort_values(by=["Pts","Diff","BP"], ascending=False, ignore_index=True)
    clas["Rang"] = clas.index + 1
    return clas[["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"]]

# --- Classement en direct ---
st.divider()
st.subheader("📊 Classement de la ronde préliminaire")
round_only = edited[edited["Phase"] == "Ronde"]
classement = classement_from_results(round_only)

if classement.empty:
    st.warning("⚠️ Aucun match terminé pour le moment — classement vide.")
else:
    st.dataframe(classement, use_container_width=True)

# --- Création des demi-finales ---
st.divider()
st.subheader("⚔️ Demi-finales")

if not classement.empty and "Demi" not in edited["Phase"].values:
    if st.button("🏁 Générer les demi-finales"):
        if len(classement) < 4:
            st.warning("Il faut au moins 4 équipes classées pour générer les demi-finales.")
        else:
            demi1 = [classement.loc[0, "Équipe"], classement.loc[3, "Équipe"]]
            demi2 = [classement.loc[1, "Équipe"], classement.loc[2, "Équipe"]]
            new_matches = pd.DataFrame([
                {"Équipe A": demi1[0], "Équipe B": demi1[1], "Phase": "Demi", "Score A": 0, "Score B": 0, "Terminé": False},
                {"Équipe A": demi2[0], "Équipe B": demi2[1], "Phase": "Demi", "Score A": 0, "Score B": 0, "Terminé": False}
            ])
            updated = pd.concat([edited, new_matches], ignore_index=True)
            updated.to_csv(BRACKET_PATH, index=False)
            st.success("✅ Demi-finales générées !")
            st.rerun()

# --- Création de la finale ---
st.divider()
st.subheader("🏅 Finale")

demis = edited[edited["Phase"] == "Demi"]
finale_exists = "Finale" in edited["Phase"].values

if not finale_exists and not demis.empty:
    gagnants = []
    for _, m in demis.iterrows():
        if not m.get("Terminé", False):
            continue
        if m["Score A"] > m["Score B"]:
            gagnants.append(m["Équipe A"])
        elif m["Score B"] > m["Score A"]:
            gagnants.append(m["Équipe B"])
    if len(gagnants) == 2:
        if st.button("🥇 Générer la finale"):
            finale = pd.DataFrame([{
                "Équipe A": gagnants[0],
                "Équipe B": gagnants[1],
                "Phase": "Finale",
                "Score A": 0,
                "Score B": 0,
                "Terminé": False
            }])
            updated = pd.concat([edited, finale], ignore_index=True)
            updated.to_csv(BRACKET_PATH, index=False)
            st.success("✅ Finale générée !")
            st.rerun()

# --- Affichage bracket graphique ---
st.divider()
st.subheader("🎯 Bracket du tournoi")

def afficher_bracket():
    phases = ["Ronde", "Demi", "Finale"]
    fig, ax = plt.subplots(figsize=(9, 6))
    x_pos = {"Ronde": 0, "Demi": 1.5, "Finale": 3}
    colors = {"Ronde": "#f0f0f0", "Demi": "#d8eaff", "Finale": "#ffe4e1"}

    # Calcul dynamique des positions Y
    y_positions = {}
    for phase in phases:
        nb = len(edited[edited["Phase"] == phase])
        if nb == 0:
            y_positions[phase] = []
        else:
            y_positions[phase] = list(
                reversed([i * (4 / (nb + 1)) + 0.5 for i in range(nb)])
            )

    box_centers = {}
    for _, m in edited.iterrows():
        phase = m["Phase"]
        if phase not in phases or len(y_positions[phase]) == 0:
            continue
        x = x_pos[phase]
        y = y_positions[phase].pop(0)
        txt = f"{m['Équipe A']} {m['Score A']} - {m['Score B']} {m['Équipe B']}"
        ax.text(x, y, txt, ha="center", va="center", fontsize=9,
                bbox=dict(facecolor=colors[phase], edgecolor='black', boxstyle="round,pad=0.4"))
        box_centers.setdefault(phase, []).append((x, y, txt))

    # Flèches reliant les phases
    if "Demi" in box_centers and "Finale" in box_centers:
        for i, demi in enumerate(box_centers["Demi"]):
            fx, fy, _ = box_centers["Finale"][0]
            ax.annotate("", xy=(fx - 0.5, fy), xytext=(demi[0] + 0.5, demi[1]),
                        arrowprops=dict(arrowstyle="->", color="gray", lw=1.2))
    if "Ronde" in box_centers and "Demi" in box_centers:
        for i, demi in enumerate(box_centers["Demi"]):
            src_y = box_centers["Ronde"][i*2][1] if len(box_centers["Ronde"]) > i*2 else demi[1]
            ax.annotate("", xy=(demi[0] - 0.5, demi[1]), xytext=(x_pos["Ronde"] + 0.5, src_y),
                        arrowprops=dict(arrowstyle="->", color="gray", lw=1.2))

    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(0, 5)
    ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig)

afficher_bracket()

# --- Fin du tournoi ---
st.divider()
st.subheader("🏆 Clôturer le tournoi")

finale = edited[edited["Phase"] == "Finale"]
if not finale.empty and bool(finale.iloc[0].get("Terminé", False)):
    f = finale.iloc[0]
    champion = f["Équipe A"] if f["Score A"] > f["Score B"] else f["Équipe B"]
    vice = f["Équipe B"] if f["Équipe A"] == champion else f["Équipe A"]
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
        st.success("✅ Tournoi archivé dans l’historique des tournois.")
        os.remove(BRACKET_PATH)

# --- Suppression sécurisée ---
st.divider()
st.subheader("🧹 Supprimer le tournoi en cours")
if st.button("🗑️ Supprimer le tournoi"):
    confirm = st.radio("Souhaitez-vous vraiment supprimer le tournoi en cours ?", ["Non", "Oui, supprimer"], horizontal=True)
    if confirm == "Oui, supprimer":
        os.remove(BRACKET_PATH)
        st.success("Tournoi supprimé avec succès.")
        st.rerun()
