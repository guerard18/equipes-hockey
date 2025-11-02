import streamlit as st
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("🏆 Tournoi en cours — 4 équipes")

BRACKET_PATH = "data/tournoi_bracket.csv"          # Matchs de ronde (créés en page 5)
RESULTS_PATH = "data/tournoi_resultats.csv"        # Ronde + séries avec scores
HISTO_PATH   = "data/historique_tournois.csv"      # Archives des tournois

os.makedirs("data", exist_ok=True)

# ---------- utilitaires ----------
def load_bracket():
    if not os.path.exists(BRACKET_PATH):
        return None
    df = pd.read_csv(BRACKET_PATH)
    # On s’assure des colonnes standard
    df = df.rename(columns={c: c.strip() for c in df.columns})
    assert {"Équipe A", "Équipe B"}.issubset(df.columns), "tournoi_bracket.csv invalide"
    # Ajoute la phase "Ronde" si absente
    if "Phase" not in df.columns:
        df["Phase"] = "Ronde"
    return df[["Équipe A", "Équipe B", "Phase"]]

def init_results_from_bracket(bracket: pd.DataFrame):
    """Crée un tableau de résultats à partir du bracket de ronde s’il n’existe pas."""
    base = bracket.copy()
    base["Score A"] = 0
    base["Score B"] = 0
    base["Terminé"] = False
    return base[["Phase", "Équipe A", "Équipe B", "Score A", "Score B", "Terminé"]]

def load_results(bracket: pd.DataFrame):
    if os.path.exists(RESULTS_PATH):
        res = pd.read_csv(RESULTS_PATH)
        # Normaliser colonnes
        expected = ["Phase", "Équipe A", "Équipe B", "Score A", "Score B", "Terminé"]
        for c in expected:
            if c not in res.columns:
                res[c] = None
        res = res[expected]
        return res
    else:
        return init_results_from_bracket(bracket)

def save_results(df: pd.DataFrame):
    df.to_csv(RESULTS_PATH, index=False)

def classement_from_results(results_round: pd.DataFrame):
    """Classement à partir des matchs de RONDE terminés (2 pts victoire, 1 nul, 0 défaite)."""
    equipes = pd.unique(results_round[["Équipe A", "Équipe B"]].values.ravel("K"))
    table = {eq: {"MJ":0, "V":0, "N":0, "D":0, "BP":0, "BC":0, "Pts":0} for eq in equipes}
    for _, m in results_round.iterrows():
        if not bool(m["Terminé"]):
            continue
        a, b = m["Équipe A"], m["Équipe B"]
        sa, sb = int(m["Score A"]), int(m["Score B"])
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
    clas["Diff"] = clas["BP"] - clas["BC"]
    clas = clas.sort_values(by=["Pts","Diff","BP"], ascending=False, ignore_index=True)
    clas["Rang"] = clas.index + 1
    return clas[["Rang","Équipe","Pts","MJ","V","N","D","BP","BC","Diff"]]

def sf_exist(results: pd.DataFrame):
    return (results["Phase"] == "Demi-finale").any()

def finale_exist(results: pd.DataFrame):
    return (results["Phase"] == "Finale").any()

def append_semifinals(results: pd.DataFrame, clas: pd.DataFrame):
    """Ajoute SF1 (1 vs 4) et SF2 (2 vs 3) si non présents."""
    if sf_exist(results):
        return results
    if len(clas) < 4:
        return results
    p1, p2, p3, p4 = clas.iloc[0]["Équipe"], clas.iloc[1]["Équipe"], clas.iloc[2]["Équipe"], clas.iloc[3]["Équipe"]
    sf_rows = pd.DataFrame([
        {"Phase":"Demi-finale","Équipe A":p1,"Équipe B":p4,"Score A":0,"Score B":0,"Terminé":False},
        {"Phase":"Demi-finale","Équipe A":p2,"Équipe B":p3,"Score A":0,"Score B":0,"Terminé":False},
    ])
    return pd.concat([results, sf_rows], ignore_index=True)

def winners_of_semifinals(results: pd.DataFrame):
    sfs = results[results["Phase"]=="Demi-finale"]
    if len(sfs) < 2 or not all(bool(x) for x in sfs["Terminé"].tolist()):
        return None
    winners = []
    for _, m in sfs.iterrows():
        sa, sb = int(m["Score A"]), int(m["Score B"])
        if sa == sb:
            return None  # on impose un vainqueur (pas d’égalité en séries)
        winners.append(m["Équipe A"] if sa > sb else m["Équipe B"])
    return winners  # [vainqueur_SF1, vainqueur_SF2]

def append_final(results: pd.DataFrame, winners: list):
    if finale_exist(results) or winners is None or len(winners) != 2:
        return results
    fin = pd.DataFrame([{
        "Phase":"Finale","Équipe A": winners[0], "Équipe B": winners[1],
        "Score A":0,"Score B":0,"Terminé":False
    }])
    return pd.concat([results, fin], ignore_index=True)

def tournament_done(results: pd.DataFrame):
    fin = results[results["Phase"]=="Finale"]
    return (len(fin)==1) and bool(fin.iloc[0]["Terminé"])

def champion_and_runnerup(results: pd.DataFrame):
    fin = results[results["Phase"]=="Finale"]
    if len(fin)!=1 or not bool(fin.iloc[0]["Terminé"]):
        return None, None
    m = fin.iloc[0]
    sa, sb = int(m["Score A"]), int(m["Score B"])
    if sa == sb:
        return None, None
    champ = m["Équipe A"] if sa > sb else m["Équipe B"]
    vice  = m["Équipe B"] if sa > sb else m["Équipe A"]
    return champ, vice

def save_tournament_to_history(date_tournoi: str, results: pd.DataFrame, clas_round: pd.DataFrame):
    """Sauve un tournoi complet (avec séries) dans l’historique dédié."""
    tour_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    champ, vice = champion_and_runnerup(results)
    # on fige le classement à partir de la finale (si jouée), sinon celui de ronde
    if champ and vice:
        # Construire un classement final minimal : champ 1er, vice 2e, puis meilleurs perdants
        sfs = results[results["Phase"]=="Demi-finale"]
        perdants = []
        for _, m in sfs.iterrows():
            sa, sb = int(m["Score A"]), int(m["Score B"])
            perdants.append(m["Équipe B"] if sa > sb else m["Équipe A"])
        # ordre final : champ, vice, puis perdants triés par points/ diff de la ronde
        losers = clas_round[clas_round["Équipe"].isin(perdants)].sort_values(by=["Pts","Diff","BP"], ascending=False)["Équipe"].tolist()
        classement_final = [champ, vice] + losers
    else:
        classement_final = clas_round.sort_values(by=["Pts","Diff","BP"], ascending=False)["Équipe"].tolist()

    flat_matches = results.copy()
    flat_matches["Score"] = flat_matches["Score A"].astype(int).astype(str) + "-" + flat_matches["Score B"].astype(int).astype(str)
    flat_matches = flat_matches[["Phase","Équipe A","Équipe B","Score","Terminé"]]

    row = {
        "Tournoi_ID": tour_id,
        "Date": date_tournoi,
        "Equipes": ", ".join(sorted(pd.unique(results[["Équipe A","Équipe B"]].values.ravel("K")))),
        "Champion": champ if champ else "",
        "Vice_champion": vice if vice else "",
        "Classement_final": " | ".join(classement_final),
        "Matches": " || ".join([f"{r.Phase}:{r['Équipe A']} vs {r['Équipe B']} ({r.Score})" for _, r in flat_matches.iterrows()])
    }

    if os.path.exists(HISTO_PATH):
        hist = pd.read_csv(HISTO_PATH)
        hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    else:
        hist = pd.DataFrame([row])

    hist.to_csv(HISTO_PATH, index=False)
    return tour_id

# ---------- Chargement ----------
bracket = load_bracket()
if bracket is None:
    st.warning("Aucun tournoi actif. Va dans la page **5 — Configuration** pour créer le tournoi (4 équipes).")
    st.stop()

results = load_results(bracket)

# ---------- Saisie des scores (toutes phases) ----------
st.subheader("📝 Saisie des scores")
for idx in range(len(results)):
    cols = st.columns([2,1,0.5,1,1.2])
    with cols[0]:
        st.write(f"{results.loc[idx,'Phase']} — {results.loc[idx,'Équipe A']} vs {results.loc[idx,'Équipe B']}")
    with cols[1]:
        sa = st.number_input("Score A", min_value=0, max_value=99, value=int(results.loc[idx,"Score A"]), key=f"a{idx}")
    with cols[3]:
        sb = st.number_input("Score B", min_value=0, max_value=99, value=int(results.loc[idx,"Score B"]), key=f"b{idx}")
    with cols[4]:
        done = st.checkbox("Terminé", value=bool(results.loc[idx,"Terminé"]), key=f"t{idx}")
    results.loc[idx,"Score A"] = sa
    results.loc[idx,"Score B"] = sb
    results.loc[idx,"Terminé"] = done

if st.button("💾 Sauvegarder les scores"):
    save_results(results)
    st.success("Scores sauvegardés.")

# ---------- Classement de la ronde ----------
st.divider()
st.subheader("📊 Classement — Ronde")
round_only = results[results["Phase"]=="Ronde"].copy()
classement = classement_from_results(round_only)
st.dataframe(classement, use_container_width=True)

# ---------- Générer Demi-finales ----------
all_round_done = len(round_only) > 0 and all(bool(x) for x in round_only["Terminé"].tolist())
if not sf_exist(results):
    st.info("➡️ Les demi-finales seront 1er vs 4e et 2e vs 3e une fois la ronde terminée.")
    if all_round_done and st.button("🏁 Générer les demi-finales"):
        results = append_semifinals(results, classement)
        save_results(results)
        st.success("Demi-finales créées.")
else:
    st.success("✅ Demi-finales déjà créées.")

# ---------- Générer Finale ----------
if sf_exist(results) and not finale_exist(results):
    winners = winners_of_semifinals(results)
    if winners is None:
        st.warning("Complète les deux demi-finales (sans égalité) pour générer la finale.")
    else:
        if st.button("🏆 Générer la finale"):
            results = append_final(results, winners)
            save_results(results)
            st.success(f"Finale créée : {winners[0]} vs {winners[1]}")

# ---------- PDF du tournoi ----------
st.divider()
st.subheader("📄 Export PDF du tournoi")
if st.button("📥 Générer le PDF"):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(180, 770, f"Tournoi — {datetime.now().strftime('%Y-%m-%d')}")

    y = 740
    for phase in ["Ronde","Demi-finale","Finale"]:
        subset = results[results["Phase"]==phase]
        if subset.empty: 
            continue
        pdf.setFont("Helvetica-Bold", 13); pdf.drawString(50, y, phase); y -= 18
        pdf.setFont("Helvetica", 11)
        for _, m in subset.iterrows():
            line = f"{m['Équipe A']} {int(m['Score A'])} - {int(m['Score B'])} {m['Équipe B']} {'(OK)' if bool(m['Terminé']) else ''}"
            pdf.drawString(60, y, line); y -= 14
        y -= 8

    pdf.save()
    buffer.seek(0)
    st.download_button("⬇️ Télécharger le PDF", data=buffer, file_name="Tournoi.pdf", mime="application/pdf")

# ---------- Enregistrer le tournoi dans l'historique ----------
st.divider()
st.subheader("🗂️ Historique des tournois")
date_input = st.date_input("Date du tournoi (pour l’archive)", datetime.now().date())

if tournament_done(results):
    if st.button("💾 Enregistrer ce tournoi dans l’historique"):
        tid = save_tournament_to_history(str(date_input), results, classement)
        st.success(f"Tournoi archivé avec l’ID **{tid}**.")
else:
    st.info("La finale doit être terminée pour archiver le tournoi (ou force l’archivage via l’historique manuel).")

# Afficher l’historique existant
if os.path.exists(HISTO_PATH):
    hist = pd.read_csv(HISTO_PATH)
    st.markdown("### 📚 Tournois enregistrés")
    if not hist.empty:
        st.dataframe(hist[["Tournoi_ID","Date","Champion","Vice_champion","Equipes"]].sort_values("Date", ascending=False), use_container_width=True)
    else:
        st.caption("Aucun tournoi archivé pour le moment.")
else:
    st.caption("Aucun tournoi archivé pour le moment.")

# ---------- Supprimer / Réinitialiser le tournoi actif ----------
st.divider()
st.subheader("🧹 Gestion du tournoi actif")
if st.button("🗑️ Supprimer le tournoi en cours"):
    confirm = st.radio("Confirmez-vous la suppression du tournoi ACTIF ?", ["Non","Oui, supprimer définitivement"], horizontal=True)
    if confirm == "Oui, supprimer définitivement":
        try:
            if os.path.exists(BRACKET_PATH): os.remove(BRACKET_PATH)
            if os.path.exists(RESULTS_PATH): os.remove(RESULTS_PATH)
            st.success("Tournoi actif supprimé.")
            st.stop()
        except Exception as e:
            st.error(f"Erreur: {e}")
    else:
        st.info("Aucune suppression effectuée.")
