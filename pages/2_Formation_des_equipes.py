import streamlit as st
import pandas as pd
import itertools
from utils import (
    load_players, load_history, append_history,
    load_pairings, update_pairings,
    assign_positions, make_lines_balanced, combo_teams
)

st.title("2) Formation des équipes")

st.markdown("""
Coche d’abord les **Présents** dans *Gestion des joueurs*, puis génère ici **2 équipes**
avec **2 trios** (attaquants) et **2 duos** (défenseurs) par équipe.
Tu peux **éditer** avant d’enregistrer dans l’historique.
""")

players = load_players()
present = players[players["present"]].copy()

if present.empty:
    st.warning("Aucun joueur présent. Va dans **Gestion des joueurs** pour cocher des joueurs.")
    st.stop()

# Paramètres
colA, colB = st.columns(2)
with colA:
    want_fw = st.number_input("Attaquants TOTAL (2 équipes)", 6, 24, 12, step=2, help="2 trios par équipe → 6 attaquants par équipe = 12 total")
with colB:
    want_df = st.number_input("Défenseurs TOTAL (2 équipes)", 4, 20, 8, step=2, help="2 duos par équipe → 4 défenseurs par équipe = 8 total")

# Assigner postes selon meilleur talent, puis ajuster pour coller aux quotas
fw_pool, df_pool = assign_positions(present, want_fw, want_df)

short_fw = max(0, want_fw - len(fw_pool))
short_df = max(0, want_df - len(df_pool))

if short_fw > 0 or short_df > 0:
    st.warning(f"Pas assez de joueurs pour atteindre les quotas. Dispo: {len(fw_pool)} A et {len(df_pool)} D.")

# Limiter aux nombres souhaités si surplus
fw_pool = fw_pool.head(min(len(fw_pool), want_fw))
df_pool = df_pool.head(min(len(df_pool), want_df))

st.write(f"**Sélection finale pour optimisation** → Attaquants: {len(fw_pool)} • Défenseurs: {len(df_pool)}")

# Construire 4 trios d'attaquants et 4 duos de défenseurs équilibrés
if len(fw_pool) < 12 or len(df_pool) < 8:
    st.info("Par défaut: 12 A et 8 D pour 2 équipes (2 trios + 2 duos par équipe). Ajuste les quotas si besoin.")

fw_lines = make_lines_balanced(fw_pool, role="A", line_size=3, iterations=500)
df_lines = make_lines_balanced(df_pool, role="D", line_size=2, iterations=500)

if any(len(g) != 3 for g in fw_lines) or any(len(g) != 2 for g in df_lines):
    st.error("Impossible de former toutes les lignes (vérifie le nombre d'A et de D).")
    st.stop()

pairings = load_pairings()
choice = combo_teams(fw_lines, df_lines, pairings, pair_penalty=1.5)

def lines_to_names(lines):
    return [[n for n,_ in L] for L in lines]

A_fw = [fw_lines[i] for i in choice["A_fw"]]
B_fw = [fw_lines[i] for i in choice["B_fw"]]
A_df = [df_lines[i] for i in choice["A_df"]]
B_df = [df_lines[i] for i in choice["B_df"]]

def team_total(lines):
    return sum(sum(s for _,s in L) for L in lines)

scoreA = team_total(A_fw + A_df)
scoreB = team_total(B_fw + B_df)

st.success(f"Écart total de talent: **{abs(scoreA - scoreB)}**  (A: {scoreA}  |  B: {scoreB})")

# --- Mode ÉDITION ---
st.subheader("✍️ Mode édition (facultatif)")

def show_team_editor(title, fw_lines, df_lines, key_prefix):
    st.markdown(f"### {title}")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Trios (A)**")
        edited_fw = []
        for i, line in enumerate(lines_to_names(fw_lines)):
            edited = st.multiselect(f"Trio {i+1}", options=present["nom"].tolist(), default=line, key=f"{key_prefix}_fw_{i}")
            edited_fw.append(edited)
    with col2:
        st.markdown("**Duos (D)**")
        edited_df = []
        for i, line in enumerate(lines_to_names(df_lines)):
            edited = st.multiselect(f"Duo {i+1}", options=present["nom"].tolist(), default=line, key=f"{key_prefix}_df_{i}")
            edited_df.append(edited)
    return edited_fw, edited_df

A_fw_edit, A_df_edit = show_team_editor("Équipe A", A_fw, A_df, "A")
B_fw_edit, B_df_edit = show_team_editor("Équipe B", B_fw, B_df, "B")

st.caption("⚠️ Garde 3 joueurs par trio et 2 par duo, et évite les doublons entre équipes.")

# recalcul des scores après édition (si tailles ok)
def safe_total(fw_ed, df_ed):
    ok = all(len(t)==3 for t in fw_ed) and all(len(d)==2 for d in df_ed)
    if not ok: return None
    # score = somme du meilleur talent selon rôle de la ligne
    def line_score(names, role):
        col = "talent_attaque" if role=="A" else "talent_defense"
        sub = present.set_index("nom").reindex(names)
        return int(sub[col].sum())
    tot = sum(line_score(t,"A") for t in fw_ed) + sum(line_score(d,"D") for d in df_ed)
    return tot

postA = safe_total(A_fw_edit, A_df_edit)
postB = safe_total(B_fw_edit, B_df_edit)
if postA is not None and postB is not None:
    st.info(f"Scores après édition → A: {postA} | B: {postB} | Écart: {abs(postA - postB)}")

# --- Affichage compact des lignes choisies (avant édition) ---
with st.expander("Voir les lignes calculées (avant édition)"):
    def fmt(lines): return [" • ".join(f"{n} ({s})" for n,s in L) for L in lines]
    st.write("**A — Trios:**", fmt(A_fw))
    st.write("**A — Duos:**",  fmt(A_df))
    st.write("**B — Trios:**", fmt(B_fw))
    st.write("**B — Duos:**",  fmt(B_df))

# --- Enregistrer dans l'historique ---
if st.button("💾 Enregistrer ces équipes dans l’historique"):
    # on sauve la version ÉDITÉE si elle est valide, sinon la version calculée
    lines_A = A_fw_edit if postA is not None else lines_to_names(A_fw)
    lines_B = B_fw_edit if postB is not None else lines_to_names(B_fw)
    dlines_A = A_df_edit if postA is not None else lines_to_names(A_df)
    dlines_B = B_df_edit if postB is not None else lines_to_names(B_df)

    # mise à jour pairings avec TOUTES les lignes
    update_pairings(lines_A + dlines_A + lines_B + dlines_B)

    # calcul des totaux à sauver
    def line_score(names, role):
        col = "talent_attaque" if role=="A" else "talent_defense"
        sub = present.set_index("nom").reindex(names)
        return int(sub[col].sum())
    teamA_total = sum(line_score(t,"A") for t in lines_A) + sum(line_score(d,"D") for d in dlines_A)
    teamB_total = sum(line_score(t,"A") for t in lines_B) + sum(line_score(d,"D") for d in dlines_B)

    ts = pd.Timestamp.now().isoformat(timespec="seconds")
    rows = []
    for i, trio in enumerate(lines_A,  start=1):
        rows.append({"timestamp":ts,"team":"A","line_type":"F","line_index":i,"players":", ".join(trio),"team_total":teamA_total})
    for i, duo  in enumerate(dlines_A, start=1):
        rows.append({"timestamp":ts,"team":"A","line_type":"D","line_index":i,"players":", ".join(duo),"team_total":teamA_total})
    for i, trio in enumerate(lines_B,  start=1):
        rows.append({"timestamp":ts,"team":"B","line_type":"F","line_index":i,"players":", ".join(trio),"team_total":teamB_total})
    for i, duo  in enumerate(dlines_B, start=1):
        rows.append({"timestamp":ts,"team":"B","line_type":"D","line_index":i,"players":", ".join(duo),"team_total":teamB_total})

    append_history(rows)
    st.success("Historique mis à jour ✅")
