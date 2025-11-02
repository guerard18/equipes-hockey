import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Tournoi en cours", page_icon="🏒", layout="centered")
st.title("🏒 Tournoi en cours — Résultats, Classement & Bracket")

DATA_DIR = "data"
BRACKET_FILE = os.path.join(DATA_DIR, "tournoi_bracket.csv")
os.makedirs(DATA_DIR, exist_ok=True)

COLS = [
    "Heure", "Équipe A", "Équipe B", "Durée (min)",
    "Phase", "Type", "Score A", "Score B", "Terminé", "Prolongation"
]

# ---------- Chargement ----------
def load_bracket():
    if os.path.exists(BRACKET_FILE):
        df = pd.read_csv(BRACKET_FILE)
    else:
        df = pd.DataFrame(columns=COLS)

    for c in COLS:
        if c not in df.columns:
            if c in ["Score A", "Score B"]:
                df[c] = 0
            elif c in ["Terminé", "Prolongation"]:
                df[c] = False
            else:
                df[c] = ""

    df["Score A"] = pd.to_numeric(df["Score A"], errors="coerce").fillna(0).astype(int)
    df["Score B"] = pd.to_numeric(df["Score B"], errors="coerce").fillna(0).astype(int)
    df["Terminé"] = df["Terminé"].astype(str).str.lower().isin(["true", "1", "yes"])
    df["Prolongation"] = df["Prolongation"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df[COLS]

def save_bracket(df):
    df[COLS].to_csv(BRACKET_FILE, index=False)

# ---------- Classement ----------
def compute_standings(df: pd.DataFrame) -> pd.DataFrame:
    ronde = df[(df["Phase"] == "Ronde") & (df["Type"] == "Match") & (df["Terminé"] == True)]
    if ronde.empty:
        return pd.DataFrame()

    teams = sorted(set(ronde["Équipe A"]) | set(ronde["Équipe B"]))
    table = {t: {"Pts": 0, "BP": 0, "BC": 0, "V": 0, "D": 0, "DP": 0, "J": 0} for t in teams}

    for _, r in ronde.iterrows():
        A, B = r["Équipe A"], r["Équipe B"]
        sa, sb, ot = int(r["Score A"]), int(r["Score B"]), bool(r["Prolongation"])
        table[A]["J"] += 1; table[B]["J"] += 1
        table[A]["BP"] += sa; table[A]["BC"] += sb
        table[B]["BP"] += sb; table[B]["BC"] += sa

        if sa > sb:
            table[A]["V"] += 1
            if ot:
                table[B]["DP"] += 1; table[A]["Pts"] += 2; table[B]["Pts"] += 1
            else:
                table[B]["D"] += 1; table[A]["Pts"] += 2
        elif sb > sa:
            table[B]["V"] += 1
            if ot:
                table[A]["DP"] += 1; table[B]["Pts"] += 2; table[A]["Pts"] += 1
            else:
                table[A]["D"] += 1; table[B]["Pts"] += 2
        else:
            table[A]["Pts"] += 1; table[B]["Pts"] += 1

    clas = (
        pd.DataFrame.from_dict(table, orient="index")
        .assign(Diff=lambda x: x["BP"] - x["BC"])
        .reset_index().rename(columns={"index": "Équipe"})
        .sort_values(by=["Pts", "Diff", "BP"], ascending=[False, False, False])
        .reset_index(drop=True)
    )
    clas["Rang"] = clas.index + 1
    return clas[["Rang", "Équipe", "Pts", "BP", "BC", "Diff", "V", "DP", "D", "J"]]

# ---------- Mise à jour demi/finale ----------
def update_semifinals_names(df, standings):
    if standings is None or standings.empty:
        return df
    demi_idx = df[(df["Phase"] == "Demi-finale") & (df["Type"] == "Match")].index.tolist()
    if len(demi_idx) < 2 or len(standings) < 4:
        return df
    t1, t2, t3, t4 = standings.iloc[0]["Équipe"], standings.iloc[1]["Équipe"], standings.iloc[2]["Équipe"], standings.iloc[3]["Équipe"]
    df.at[demi_idx[0], "Équipe A"], df.at[demi_idx[0], "Équipe B"] = t1, t4
    df.at[demi_idx[1], "Équipe A"], df.at[demi_idx[1], "Équipe B"] = t2, t3
    return df

def update_final_names(df):
    demi = df[(df["Phase"] == "Demi-finale") & (df["Type"] == "Match")]
    fin = df[(df["Phase"] == "Finale") & (df["Type"] == "Match")]
    if demi.shape[0] < 2 or fin.shape[0] < 1 or not demi["Terminé"].all():
        return df
    winners = []
    for _, r in demi.iterrows():
        if int(r["Score A"]) > int(r["Score B"]): winners.append(r["Équipe A"])
        elif int(r["Score B"]) > int(r["Score A"]): winners.append(r["Équipe B"])
    if len(winners) == 2:
        fin_idx = fin.index[0]
        df.at[fin_idx, "Équipe A"], df.at[fin_idx, "Équipe B"] = winners[0], winners[1]
    return df

def champion_if_ready(df):
    fin = df[(df["Phase"] == "Finale") & (df["Type"] == "Match")]
    if fin.empty or not fin.iloc[0]["Terminé"]:
        return ""
    r = fin.iloc[0]
    return r["Équipe A"] if r["Score A"] > r["Score B"] else r["Équipe B"]

# ---------- Interface ----------
df = load_bracket()
if df.empty:
    st.info("Aucun tournoi généré. Va dans **Génération du tournoi** pour le créer.")
    st.stop()

standings = compute_standings(df)
edited = False
st.subheader("🗓️ Horaire & Résultats")

for idx, row in df.iterrows():
    # Affiche le bouton avant la première demi-finale
    if row["Phase"] == "Demi-finale" and idx > 0 and df.iloc[idx - 1]["Phase"] != "Demi-finale":
        st.markdown("#### ⚙️ Mettre à jour les demi-finales")
        if st.button("🔁 Mettre à jour les demi-finales maintenant"):
            ronde = df[(df["Phase"] == "Ronde") & (df["Type"] == "Match")]
            if not ronde.empty and ronde["Terminé"].all():
                new_df = update_semifinals_names(df.copy(), standings)
                save_bracket(new_df)
                st.success("✅ Demi-finales mises à jour avec les vraies équipes.")
                st.rerun()
            else:
                st.warning("⚠️ Tous les matchs de ronde ne sont pas terminés.")

    # Affiche le bouton avant la finale
    if row["Phase"] == "Finale" and idx > 0 and df.iloc[idx - 1]["Phase"] != "Finale":
        st.markdown("#### ⚙️ Mettre à jour la finale")
        if st.button("🔁 Mettre à jour la finale maintenant"):
            new_df = update_final_names(df.copy())
            save_bracket(new_df)
            st.success("✅ Finale mise à jour avec les gagnants des demi-finales.")
            st.rerun()

    if row["Type"] == "Pause":
        st.markdown(f"**{row['Heure']} — {row['Équipe A']}** ({int(row['Durée (min)'])} min)")
        continue

    col1, col2, col3, col4, col5 = st.columns([2, 3, 3, 2, 3])
    with col1:
        st.write(f"**{row['Heure']}**")
        st.caption(f"{row['Phase']}")
    with col2:
        st.write(row["Équipe A"])
        sa = st.number_input("", 0, 99, int(row["Score A"]), key=f"sa_{idx}")
    with col3:
        st.write(row["Équipe B"])
        sb = st.number_input("", 0, 99, int(row["Score B"]), key=f"sb_{idx}")
    with col4:
        ot = st.checkbox("Prolongation", value=row["Prolongation"], key=f"ot_{idx}")
        done = st.checkbox("Terminé", value=row["Terminé"], key=f"tm_{idx}")
    with col5:
        if st.button("💾 Enregistrer", key=f"save_{idx}"):
            df.at[idx, "Score A"], df.at[idx, "Score B"] = sa, sb
            df.at[idx, "Prolongation"], df.at[idx, "Terminé"] = ot, done
            edited = True

if edited:
    save_bracket(df)
    st.success("✅ Résultats enregistrés.")
    df = load_bracket()

# ---------- Classement ----------
st.subheader("📊 Classement (Ronde)")
if standings.empty:
    st.info("Entrez les scores de la ronde pour générer le classement.")
else:
    st.dataframe(standings, use_container_width=True)

# ---------- Champion ----------
champ = champion_if_ready(df)
if champ:
    st.markdown(
        f"""
        <style>
        @keyframes goldShine {{
            0% {{ background-position: 0% 50%; }}
            100% {{ background-position: 100% 50%; }}
        }}
        .champion {{
            text-align: center;
            font-size: 70px;
            font-weight: bold;
            background: linear-gradient(90deg, #FFD700, #FFFACD, #FFD700);
            background-size: 400% 400%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: goldShine 3s linear infinite;
            text-shadow: 2px 2px 5px #B8860B;
            margin-top: 40px;
        }}
        .subtitle {{
            text-align: center;
            color: #FFD700;
            font-size: 30px;
            text-shadow: 1px 1px 3px #B8860B;
            margin-bottom: 60px;
        }}
        </style>
        <div class="champion">🏆 {champ} 🏆</div>
        <div class="subtitle">Champion du tournoi!</div>

        <canvas id="confetti-canvas" style="position:fixed;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:9999;"></canvas>

        <script>
        const canvas = document.getElementById('confetti-canvas');
        const ctx = canvas.getContext('2d');
        let confettis = [];
        const colors = ['#FFD700','#DAA520','#FFF8DC','#FFEC8B','#F0E68C'];

        function random(min,max) {{ return Math.random()*(max-min)+min; }}
        function createConfetti() {{
            for (let i=0; i<200; i++) {{
                confettis.push({{
                    x: random(0, window.innerWidth),
                    y: random(-window.innerHeight, 0),
                    r: random(2,6),
                    d: random(1,3),
                    color: colors[Math.floor(Math.random()*colors.length)],
                    tilt: random(-10,10),
                    tiltAngleIncrement: random(0.02,0.05),
                    tiltAngle: 0
                }});
            }}
        }}
        function drawConfetti() {{
            ctx.clearRect(0,0,canvas.width,canvas.height);
            confettis.forEach(c => {{
                ctx.beginPath();
                ctx.lineWidth = c.r;
                ctx.strokeStyle = c.color;
                ctx.moveTo(c.x + c.tilt + c.r, c.y);
                ctx.lineTo(c.x + c.tilt, c.y + c.tilt + c.r);
                ctx.stroke();
            }});
            update();
        }}
        function update() {{
            confettis.forEach(c => {{
                c.tiltAngle += c.tiltAngleIncrement;
                c.y += (Math.cos(c.d) + 2 + c.r / 2) / 2;
                c.x += Math.sin(0.01);
                if (c.y > canvas.height) {{
                    c.y = 0;
                    c.x = random(0, window.innerWidth);
                }}
            }});
        }}
        function animateConfetti() {{
            drawConfetti();
            requestAnimationFrame(animateConfetti);
        }}
        window.onload = function() {{
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            createConfetti();
            animateConfetti();
        }};
        </script>
        """,
        unsafe_allow_html=True
    )

# ---------- Réinitialisation ----------
st.divider()
st.subheader("🧹 Réinitialiser les scores")
if st.button("♻️ Remettre les scores à zéro"):
    df.loc[df["Type"]=="Match", ["Score A","Score B","Terminé","Prolongation"]] = [0,0,False,False]
    save_bracket(df)
    st.success("✅ Scores remis à zéro.")
