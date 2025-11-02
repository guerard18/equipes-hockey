import streamlit as st
import pandas as pd
import os
import random
import itertools
from datetime import datetime, timedelta, time
from utils import load_players
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

st.title("🏒 Génération du tournoi (4 équipes fixes)")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")

# ---------- Utilitaires fichier ----------
COLS = ["Heure","Équipe A","Équipe B","Durée (min)","Phase","Type","Score A","Score B","Terminé"]

def load_bracket():
    if os.path.exists(BRACKET_FILE):
        df = pd.read_csv(BRACKET_FILE)
        # Normalise colonnes manquantes
        for c in COLS:
            if c not in df.columns:
                if c in ["Score A","Score B"]:
                    df[c] = 0
                elif c == "Terminé":
                    df[c] = False
                else:
                    df[c] = ""
        return df[COLS]
    else:
        return pd.DataFrame(columns=COLS)

def save_bracket(df):
    df[COLS].to_csv(BRACKET_FILE, index=False)

def parse_hhmm(hhmm_str):
    # Convertit "HH:MM" en datetime aujourd'hui
    today = datetime.today().date()
    h, m = map(int, hhmm_str.split(":"))
    return datetime.combine(today, time(h, m))

def fmt_hhmm(dt):
    return dt.strftime("%H:%M")

# ---------- Charger joueurs ----------
def charger_joueurs():
    players = load_players()
    return players[players["present"] == True].reset_index(drop=True)

if st.button("🔄 Recharger les joueurs présents"):
    st.session_state["players_present"] = charger_joueurs()
    st.success("✅ Liste des joueurs mise à jour !")

players_present = st.session_state.get("players_present", charger_joueurs())
st.info(f"✅ {len(players_present)} joueurs présents sélectionnés")
if len(players_present) < 10:
    st.warning("⚠️ Peu de joueurs présents — la formation sera approximative.")

# ---------- Snake draft ----------
def snake_draft(df, nb_groupes, colonne):
    if df.empty:
        return [pd.DataFrame() for _ in range(nb_groupes)]
    df = df.sample(frac=1).sort_values(colonne, ascending=False).reset_index(drop=True)
    groupes = [[] for _ in range(nb_groupes)]
    sens, idx = 1, 0
    for _, joueur in df.iterrows():
        groupes[idx].append(joueur)
        idx += sens
        if idx == nb_groupes:
            sens, idx = -1, nb_groupes - 1
        elif idx < 0:
            sens, idx = 1, 0
    return [pd.DataFrame(g) for g in groupes]

# ---------- Génération équipes ----------
def generer_equipes(players_present):
    pp = players_present.copy()
    pp["poste"] = pp.apply(lambda x: "Attaquant" if x["talent_attaque"] >= x["talent_defense"] else "Défenseur", axis=1)
    attaquants = pp[pp["poste"] == "Attaquant"].copy()
    defenseurs = pp[pp["poste"] == "Défenseur"].copy()

    # Objectif tournoi: 4 équipes -> 8 trios (24 attaquants) et 8 duos (16 défenseurs)
    if len(attaquants) < 24 and len(defenseurs) > 0:
        supl = defenseurs.nlargest(24 - len(attaquants), "talent_attaque")
        attaquants = pd.concat([attaquants, supl])
        defenseurs = defenseurs.drop(supl.index)
    if len(defenseurs) < 16 and len(attaquants) > 0:
        supl = attaquants.nlargest(16 - len(defenseurs), "talent_defense")
        defenseurs = pd.concat([defenseurs, supl])
        attaquants = attaquants.drop(supl.index)

    trios = snake_draft(attaquants, 8, "talent_attaque")
    duos  = snake_draft(defenseurs, 8, "talent_defense")
    random.shuffle(trios); random.shuffle(duos)

    equipes = {
        "BLANCS ⚪": {"trios": trios[0:2], "duos": duos[0:2]},
        "NOIRS ⚫":  {"trios": trios[2:4], "duos": duos[2:4]},
        "ROUGES 🔴":{"trios": trios[4:6], "duos": duos[4:6]},
        "VERTS 🟢": {"trios": trios[6:8], "duos": duos[6:8]},
    }
    for nom, eq in equipes.items():
        moy_trios = [t["talent_attaque"].mean() for t in eq["trios"] if not t.empty]
        moy_duos  = [d["talent_defense"].mean() for d in eq["duos"] if not d.empty]
        eq["moyenne"] = round(sum(moy_trios + moy_duos) / max(1, len(moy_trios + moy_duos)), 2)
    return equipes

# ---------- Affichage équipes ----------
if st.button("🎯 Générer les équipes"):
    st.session_state["tournoi_equipes"] = generer_equipes(players_present)
    st.success("✅ Équipes générées !")

equipes = st.session_state.get("tournoi_equipes")
if equipes:
    st.subheader("📋 Composition des équipes")
    for nom, eq in equipes.items():
        st.markdown(f"### {nom} — Moyenne : **{eq['moyenne']}**")
        for i, trio in enumerate(eq["trios"], 1):
            if not trio.empty:
                st.write(f"**Trio {i} ({round(trio['talent_attaque'].mean(),2)}) :** {', '.join(trio['nom'])}")
        for i, duo in enumerate(eq["duos"], 1):
            if not duo.empty:
                st.write(f"**Duo {i} ({round(duo['talent_defense'].mean(),2)}) :** {', '.join(duo['nom'])}")
        st.divider()

# ---------- Paramètres horaires ----------
st.subheader("⏱️ Paramètres de l’horaire")
start_time      = st.time_input("Heure de début du premier match", time(18, 0))
match_duration  = st.number_input("Durée d’un match de ronde (min)", 10, 120, 25, 5)
demi_duration   = st.number_input("Durée d’une demi-finale (min)", 10, 120, 30, 5)
finale_duration = st.number_input("Durée de la finale (min)", 10, 120, 35, 5)
pause_regular   = st.number_input("Pause entre les matchs (min)", 0, 60, 5, 5)
zamboni_pause   = st.number_input("Durée pause Zamboni (min)", 5, 30, 10, 5)

# ---------- Génération de la ronde uniquement ----------
def generer_ronde(equipes, start_time, match_dur, pause_min, zamboni_min):
    """Crée 6 matchs de ronde + pauses Zamboni après chaque 3 matchs."""
    noms = list(equipes.keys())
    comb = list(itertools.combinations(noms, 2))  # 6 matchs
    random.shuffle(comb)

    # Essai d'ordre qui limite >2 consécutifs (simple heuristique)
    horaire = []
    consecutifs = {e: 0 for e in noms}
    pool = comb.copy()
    while pool:
        picked = None
        for m in pool:
            a,b = m
            if consecutifs[a] < 2 and consecutifs[b] < 2 and (not horaire or (a not in horaire[-1] and b not in horaire[-1])):
                picked = m; break
        if picked is None:
            picked = pool[0]
        horaire.append(picked)
        pool.remove(picked)
        a,b = picked
        for e in consecutifs:
            if e in picked:
                consecutifs[e] += 1
            else:
                consecutifs[e] = max(0, consecutifs[e]-1)

    rows = []
    heure = datetime.combine(datetime.today(), start_time)
    match_counter = 0
    for i, (A,B) in enumerate(horaire):
        rows.append([fmt_hhmm(heure), A, B, match_dur, "Ronde", "Match", 0, 0, True])
        heure += timedelta(minutes=match_dur + pause_min)
        match_counter += 1
        if match_counter % 3 == 0 and i != len(horaire)-1:
            rows.append([fmt_hhmm(heure), "🧊 Pause Zamboni", "", zamboni_min, "", "Pause", 0, 0, False])
            heure += timedelta(minutes=zamboni_min)
    return pd.DataFrame(rows, columns=COLS)

# ---------- Append demi-finales ----------
def append_demis(df, demi_dur, pause_min, zamboni_min):
    if (df["Phase"] == "Demi-finale").any():
        st.info("ℹ️ Les demi-finales existent déjà — aucune duplication.")
        return df

    # Heure de départ = fin du dernier événement
    if df.empty:
        st.error("Génère d’abord la ronde.")
        return df
    last_time = parse_hhmm(df.iloc[-1]["Heure"])
    last_dur  = int(df.iloc[-1]["Durée (min)"]) if str(df.iloc[-1]["Durée (min)"]).isdigit() else 0
    heure = last_time + timedelta(minutes=last_dur + (0 if df.iloc[-1]["Type"]=="Pause" else 0))

    # Pour simplifier : on met des placeholders (classement calculé ailleurs)
    rows = []
    # Demi 1
    rows.append([fmt_hhmm(heure), "Demi-finale 1 - 1er vs 4e", "", demi_dur, "Demi-finale", "Match", 0, 0, True])
    heure += timedelta(minutes=demi_dur + pause_min)
    # Compteur Zamboni: on compte globalement tous les matchs déjà présents
    total_matchs = (df["Type"]=="Match").sum() + 1
    if total_matchs % 3 == 0:
        rows.append([fmt_hhmm(heure), "🧊 Pause Zamboni", "", zamboni_min, "", "Pause", 0, 0, False])
        heure += timedelta(minutes=zamboni_min)

    # Demi 2
    rows.append([fmt_hhmm(heure), "Demi-finale 2 - 2e vs 3e", "", demi_dur, "Demi-finale", "Match", 0, 0, True])

    # Zamboni éventuel après la 2e demi selon compteur global
    total_matchs += 1
    heure2 = parse_hhmm(rows[-1][0]) + timedelta(minutes=demi_dur + pause_min)
    if total_matchs % 3 == 0:
        rows.append([fmt_hhmm(heure2), "🧊 Pause Zamboni", "", zamboni_min, "", "Pause", 0, 0, False])

    add_df = pd.DataFrame(rows, columns=COLS)
    out = pd.concat([df, add_df], ignore_index=True)
    return out

# ---------- Append finale (avec pause forcée juste avant) ----------
def append_finale(df, finale_dur, zamboni_min):
    if (df["Phase"] == "Finale").any():
        st.info("ℹ️ La finale existe déjà — aucune duplication.")
        return df
    if df.empty:
        st.error("Génère d’abord la ronde.")
        return df

    last_time = parse_hhmm(df.iloc[-1]["Heure"])
    last_dur  = int(df.iloc[-1]["Durée (min)"]) if str(df.iloc[-1]["Durée (min)"]).isdigit() else 0
    heure = last_time + timedelta(minutes=last_dur)

    rows = []
    # Pause Zamboni forcée avant la finale (toujours)
    rows.append([fmt_hhmm(heure), "🧊 Pause Zamboni (avant la finale)", "", zamboni_min, "", "Pause", 0, 0, False])
    heure += timedelta(minutes=zamboni_min)

    # Finale
    rows.append([fmt_hhmm(heure), "🏆 Finale - Gagnants demi-finales", "", finale_dur, "Finale", "Match", 0, 0, False])

    add_df = pd.DataFrame(rows, columns=COLS)
    out = pd.concat([df, add_df], ignore_index=True)
    return out

# ---------- Zone actions ----------
st.subheader("🗓️ Planification par étapes")

# Étape Ronde
if st.button("① Générer la Ronde (6 matchs)"):
    if not equipes:
        st.error("Génère d’abord les équipes.")
    else:
        ronde = generer_ronde(equipes, start_time, match_duration, pause_regular, zamboni_pause)
        save_bracket(ronde)
        st.success("✅ Ronde générée (sans demi, sans finale).")

# Étape Demi-finales
if st.button("② Générer les Demi-finales"):
    df = load_bracket()
    if df.empty:
        st.error("Génère d’abord la ronde.")
    else:
        df2 = append_demis(df, demi_duration, pause_regular, zamboni_pause)
        save_bracket(df2)
        st.success("✅ Demi-finales ajoutées (aucun doublon).")

# Étape Finale
if st.button("③ Générer la Finale"):
    df = load_bracket()
    if df.empty:
        st.error("Génère d’abord la ronde.")
    else:
        df2 = append_finale(df, finale_duration, zamboni_pause)
        save_bracket(df2)
        st.success("✅ Finale ajoutée (avec pause Zamboni juste avant).")

# Affichage horaire actuel
st.subheader("📋 Horaire actuel")
df_show = load_bracket()
if not df_show.empty:
    df_show_idx = df_show.copy()
    df_show_idx.index = [f"Événement {i+1}" for i in range(len(df_show_idx))]
    st.dataframe(df_show_idx)

    # Export PDF de l’horaire actuel
    st.subheader("📄 Télécharger le PDF de l’horaire")
    if st.button("💾 Générer le PDF"):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(200, 770, f"Tournoi du {datetime.now().strftime('%Y-%m-%d')}")
        pdf.setFont("Helvetica", 12)
        y = 740
        pdf.drawString(50, y, "🕓 Horaire :")
        y -= 20
        for _, r in df_show.iterrows():
            if r["Type"] == "Pause":
                pdf.drawString(60, y, f"{r['Heure']} — {r['Équipe A']} ({r['Durée (min)']} min)")
            else:
                pdf.drawString(60, y, f"{r['Heure']} ({r['Durée (min)']} min): {r['Équipe A']} vs {r['Équipe B']}")
            y -= 15
            if y < 60:
                pdf.showPage()
                pdf.setFont("Helvetica", 12)
                y = 760
        pdf.save()
        buffer.seek(0)
        st.download_button(
            "⬇️ Télécharger le PDF",
            buffer,
            file_name=f"Tournoi_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
else:
    st.info("Aucun horaire pour le moment. Génère la ronde pour commencer.")

# Réinitialisation
st.divider()
st.subheader("🧹 Réinitialiser le tournoi")
if os.path.exists(BRACKET_FILE):
    if st.button("🗑️ Supprimer l’horaire"):
        confirm = st.radio("Confirmer la suppression de l’horaire ?", ["Non", "Oui"], horizontal=True)
        if confirm == "Oui":
            os.remove(BRACKET_FILE)
            st.success("✅ Horaire supprimé.")
