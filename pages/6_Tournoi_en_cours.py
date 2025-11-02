import streamlit as st
import pandas as pd
import os
from datetime import datetime
from typing import List, Tuple

st.title("🏒 Tournoi en cours — Résultats, Classement & Bracket")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# Colonnes attendues dans le CSV
COLS = [
    "Heure", "Équipe A", "Équipe B", "Durée (min)",
    "Phase", "Type", "Score A", "Score B", "Terminé", "Prolongation"
]

EQUIPES_FIXES = ["BLANCS ⚪", "NOIRS ⚫", "ROUGES 🔴", "VERTS 🟢"]

# ---------- Utilitaires lecture/écriture ----------

def load_bracket() -> pd.DataFrame:
    if os.path.exists(BRACKET_FILE):
        df = pd.read_csv(BRACKET_FILE)
    else:
        df = pd.DataFrame(columns=COLS)

    # Normaliser colonnes
    for c in COLS:
        if c not in df.columns:
            if c in ["Score A", "Score B"]:
                df[c] = 0
            elif c in ["Terminé", "Prolongation"]:
                df[c] = False
            else:
                df[c] = ""

    # Types
    df["Score A"] = pd.to_numeric(df["Score A"], errors="coerce").fillna(0).astype(int)
    df["Score B"] = pd.to_numeric(df["Score B"], errors="coerce").fillna(0).astype(int)
    if df["Terminé"].dtype != bool:
        df["Terminé"] = df["Terminé"].astype(str).str.lower().isin(["true", "1", "yes"])
    if df["Prolongation"].dtype != bool:
        df["Prolongation"] = df["Prolongation"].astype(str).str.lower().isin(["true", "1", "yes"])

    # Conserver l'ordre d'origine
    return df[COLS]

def save_bracket(df: pd.DataFrame):
    df = df.copy()
    # S’assurer que colonnes présentes
    for c in COLS:
        if c not in df.columns:
            if c in ["Score A", "Score B"]:
                df[c] = 0
            elif c in ["Terminé", "Prolongation"]:
                df[c] = False
            else:
                df[c] = ""
    df[COLS].to_csv(BRACKET_FILE, index=False)

# ---------- Classement (Ronde) ----------

def compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule le classement uniquement sur les matchs de Ronde terminés."""
    ronde = df[(df["Phase"] == "Ronde") & (df["Type"] == "Match") & (df["Terminé"] == True)].copy()
    teams = set()
    for _, r in ronde.iterrows():
        teams.add(r["Équipe A"])
        teams.add(r["Équipe B"])

    table = {t: {"Pts": 0, "BP": 0, "BC": 0, "J": 0, "V": 0, "D": 0, "DP": 0} for t in teams}

    for _, r in ronde.iterrows():
        A, B = r["Équipe A"], r["Équipe B"]
        sa, sb = int(r["Score A"]), int(r["Score B"])
        ot = bool(r["Prolongation"])

        # buts/joués
        for t in [A, B]:
            table[t]["J"] += 1
        table[A]["BP"] += sa; table[A]["BC"] += sb
        table[B]["BP"] += sb; table[B]["BC"] += sa

        if sa > sb:
            # A gagne
            table[A]["V"] += 1
            if ot:
                table[B]["DP"] += 1  # défaite en prolongation
                table[A]["Pts"] += 2
                table[B]["Pts"] += 1
            else:
                table[B]["D"] += 1
                table[A]["Pts"] += 2
        elif sb > sa:
            # B gagne
            table[B]["V"] += 1
            if ot:
                table[A]["DP"] += 1
                table[B]["Pts"] += 2
                table[A]["Pts"] += 1
            else:
                table[A]["D"] += 1
                table[B]["Pts"] += 2
        else:
            # égalité (si jamais utilisée) -> 1 point chacun
            table[A]["Pts"] += 1
            table[B]["Pts"] += 1

    clas = (
        pd.DataFrame.from_dict(table, orient="index")
        .assign(Diff=lambda x: x["BP"] - x["BC"])
        .reset_index()
        .rename(columns={"index": "Équipe"})
    )

    # Tri: Points desc, Diff desc, BP desc, J asc (optionnel)
    if not clas.empty:
        clas = clas.sort_values(by=["Pts", "Diff", "BP"], ascending=[False, False, False]).reset_index(drop=True)
        clas["Rang"] = clas.index + 1
        clas = clas[["Rang", "Équipe", "Pts", "BP", "BC", "Diff", "V", "DP", "D", "J"]]
    return clas

# ---------- Mise à jour des affichages demi/finale ----------

def update_semifinals_names(df: pd.DataFrame, standings: pd.DataFrame) -> pd.DataFrame:
    """Remplace '1er vs 4e' et '2e vs 3e' par les noms réels si classement disponible."""
    if standings is None or standings.empty:
        return df

    # On attend deux lignes Demi-finale "Match"
    demi_idx = df[(df["Phase"] == "Demi-finale") & (df["Type"] == "Match")].index.tolist()
    if len(demi_idx) < 2:
        return df

    # Extraire top 4 (si moins de 4, on ne touche pas)
    if len(standings) < 4:
        return df

    t1 = standings.iloc[0]["Équipe"]
    t2 = standings.iloc[1]["Équipe"]
    t3 = standings.iloc[2]["Équipe"]
    t4 = standings.iloc[3]["Équipe"]

    # On réécrit les équipes A/B de chaque demi clairement
    # Demi 1 : 1er vs 4e
    i0 = demi_idx[0]
    df.at[i0, "Équipe A"] = t1
    df.at[i0, "Équipe B"] = t4

    # Demi 2 : 2e vs 3e
    i1 = demi_idx[1]
    df.at[i1, "Équipe A"] = t2
    df.at[i1, "Équipe B"] = t3

    return df

def update_final_names(df: pd.DataFrame) -> pd.DataFrame:
    """Si les deux demi-finales sont terminées, remplace la finale par les gagnants."""
    demi = df[(df["Phase"] == "Demi-finale") & (df["Type"] == "Match")]
    fin  = df[(df["Phase"] == "Finale") & (df["Type"] == "Match")]

    if demi.shape[0] < 2 or fin.shape[0] < 1:
        return df

    # Vérifier si les deux demis sont terminées
    if not (demi["Terminé"].all()):
        return df

    # Gagnants
    winners: List[str] = []
    for i, r in demi.iterrows():
        sa, sb = int(r["Score A"]), int(r["Score B"])
        if sa > sb:
            winners.append(r["Équipe A"])
        elif sb > sa:
            winners.append(r["Équipe B"])
        else:
            # égalité (cas rare) -> on ne change pas la finale
            return df

    if len(winners) == 2:
        fin_idx = fin.index[0]
        df.at[fin_idx, "Équipe A"] = winners[0]
        df.at[fin_idx, "Équipe B"] = winners[1]

    return df

def champion_if_ready(df: pd.DataFrame) -> str:
    final = df[(df["Phase"] == "Finale") & (df["Type"] == "Match")]
    if final.empty:
        return ""
    r = final.iloc[0]
    if not bool(r["Terminé"]):
        return ""
    sa, sb = int(r["Score A"]), int(r["Score B"])
    if sa > sb:
        return str(r["Équipe A"])
    elif sb > sa:
        return str(r["Équipe B"])
    return ""  # égalité non gérée pour une finale

# ---------- UI : saisie résultats ----------

df = load_bracket()
if df.empty:
    st.info("Aucun horaire trouvé. Va dans **Génération du tournoi** pour créer le tournoi.")
    st.stop()

st.subheader("🗓️ Horaire & Saisie des résultats")
edited = False

for idx, row in df.iterrows():
    if row["Type"] == "Pause":
        st.markdown(f"**{row['Heure']} — {row['Équipe A']}** ({int(row['Durée (min)'])} min)")
        continue

    # Match
    col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 2, 3])
    with col1:
        st.write(f"**{row['Heure']}**")
        st.caption(f"{row['Phase']}")
    with col2:
        st.write(f"{row['Équipe A']}")
        score_a = st.number_input(
            "Score A", min_value=0, max_value=99, value=int(row["Score A"]),
            key=f"sa_{idx}"
        )
    with col3:
        st.write(f"{row['Équipe B']}")
        score_b = st.number_input(
            "Score B", min_value=0, max_value=99, value=int(row["Score B"]),
            key=f"sb_{idx}"
        )
    with col4:
        ot = st.checkbox("Prolongation ?", value=bool(row["Prolongation"]), key=f"ot_{idx}")
        term = st.checkbox("Terminé ?", value=bool(row["Terminé"]), key=f"tm_{idx}")
    with col5:
        if st.button("💾 Enregistrer", key=f"save_{idx}"):
            df.at[idx, "Score A"] = int(score_a)
            df.at[idx, "Score B"] = int(score_b)
            df.at[idx, "Prolongation"] = bool(ot)
            df.at[idx, "Terminé"] = bool(term)
            edited = True

if edited:
    save_bracket(df)
    st.success("✅ Résultats enregistrés.")
    # recharger pour cohérence
    df = load_bracket()

st.divider()

# ---------- Classement de la Ronde ----------
st.subheader("📊 Classement (Ronde)")
standings = compute_standings(df)
if standings.empty:
    st.info("Entrez les résultats de la ronde (matchs 'Terminé') pour voir le classement.")
else:
    st.dataframe(standings, use_container_width=True)

# ---------- Mise à jour automatique des Demi-finales ----------
if not standings.empty:
    # Si la ronde est complète (tous les matchs de ronde 'Terminé'), on met les noms réels en demi
    ronde = df[(df["Phase"] == "Ronde") & (df["Type"] == "Match")]
    if not ronde.empty and ronde["Terminé"].all():
        df2 = update_semifinals_names(df.copy(), standings)
        if not df2.equals(df):
            save_bracket(df2)
            df = load_bracket()
            st.success("✅ Demi-finales mises à jour avec les équipes réelles.")

# ---------- Mise à jour automatique de la Finale ----------
df2 = update_final_names(df.copy())
if not df2.equals(df):
    save_bracket(df2)
    df = load_bracket()
    st.success("✅ Finale mise à jour avec les gagnants des demi-finales.")

# ---------- Bracket (texte simple) ----------
st.subheader("🎯 Bracket")
demis = df[(df["Phase"] == "Demi-finale") & (df["Type"] == "Match")]
finale = df[(df["Phase"] == "Finale") & (df["Type"] == "Match")]

if demis.empty:
    st.info("Les demi-finales ne sont pas encore disponibles. Terminez la ronde et/ou régénérez la page 5 si nécessaire.")
else:
    # Demi 1
    r1 = demis.iloc[0]
    st.write(f"**Demi-finale 1** — {r1['Équipe A']} vs {r1['Équipe B']} "
             f"{'(OT)' if r1['Prolongation'] else ''} "
             f"{f'[{r1['Score A']}–{r1['Score B']}]' if r1['Terminé'] else ''}")
    # Demi 2
    if len(demis) > 1:
        r2 = demis.iloc[1]
        st.write(f"**Demi-finale 2** — {r2['Équipe A']} vs {r2['Équipe B']} "
                 f"{'(OT)' if r2['Prolongation'] else ''} "
                 f"{f'[{r2['Score A']}–{r2['Score B']}]' if r2['Terminé'] else ''}")

if not finale.empty:
    rf = finale.iloc[0]
    st.write(f"**Finale** — {rf['Équipe A']} vs {rf['Équipe B']} "
             f"{'(OT)' if rf['Prolongation'] else ''} "
             f"{f'[{rf['Score A']}–{rf['Score B']}]' if rf['Terminé'] else ''}")

# ---------- Champion ----------
champ = champion_if_ready(df)
if champ:
    st.success(f"🏆 **CHAMPION : {champ}**")

# ---------- Outils ----------
st.divider()
st.subheader("🧹 Outils")
colA, colB = st.columns(2)
with colA:
    if st.button("🔁 Recalculer / Mettre à jour demi & finale"):
        df = load_bracket()
        standings = compute_standings(df)
        changed = False
        if not standings.empty:
            ronde = df[(df["Phase"] == "Ronde") & (df["Type"] == "Match")]
            if not ronde.empty and ronde["Terminé"].all():
                df2 = update_semifinals_names(df.copy(), standings)
                if not df2.equals(df):
                    save_bracket(df2)
                    df = load_bracket()
                    changed = True
        df3 = update_final_names(df.copy())
        if not df3.equals(df):
            save_bracket(df3)
            df = load_bracket()
            changed = True
        if changed:
            st.success("✅ Mises à jour appliquées.")
        else:
            st.info("Aucun changement requis.")

with colB:
    if st.button("🗑️ Réinitialiser scores (garder l’horaire)"):
        df = load_bracket()
        df.loc[df["Type"]=="Match", ["Score A","Score B","Terminé","Prolongation"]] = [0,0,False,False]
        save_bracket(df)
        st.success("✅ Scores remis à zéro.")
