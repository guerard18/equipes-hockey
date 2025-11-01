import os
import itertools
import time
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd

DATA_DIR = "data"
PLAYERS_CSV = os.path.join(DATA_DIR, "joueurs.csv")
HISTORY_CSV = os.path.join(DATA_DIR, "history.csv")
PAIRINGS_CSV = os.path.join(DATA_DIR, "pairings.csv")

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_players() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(PLAYERS_CSV):
        df = pd.DataFrame(columns=["nom","talent_attaque","talent_defense","present"])
        df.to_csv(PLAYERS_CSV, index=False)
        return df
    df = pd.read_csv(PLAYERS_CSV)
    if "present" in df.columns:
        df["present"] = df["present"].astype(bool)
    else:
        df["present"] = False
    df["talent_attaque"] = pd.to_numeric(df.get("talent_attaque", 0), errors="coerce").fillna(0).astype(int)
    df["talent_defense"] = pd.to_numeric(df.get("talent_defense", 0), errors="coerce").fillna(0).astype(int)
    return df

def save_players(df: pd.DataFrame):
    ensure_data_dir()
    df = df.copy()
    df["present"] = df["present"].astype(bool)
    df.to_csv(PLAYERS_CSV, index=False)

def load_history() -> pd.DataFrame:
    ensure_data_dir()
    cols = ["timestamp","team","line_type","line_index","players","team_total"]
    if not os.path.exists(HISTORY_CSV):
        pd.DataFrame(columns=cols).to_csv(HISTORY_CSV, index=False)
    return pd.read_csv(HISTORY_CSV)

def append_history(rows: List[Dict]):
    ensure_data_dir()
    hist = load_history()
    new = pd.DataFrame(rows)
    hist = pd.concat([hist, new], ignore_index=True)
    hist.to_csv(HISTORY_CSV, index=False)

def reset_history():
    ensure_data_dir()
    pd.DataFrame(columns=["timestamp","team","line_type","line_index","players","team_total"]).to_csv(HISTORY_CSV, index=False)

def load_pairings() -> pd.DataFrame:
    ensure_data_dir()
    if not os.path.exists(PAIRINGS_CSV):
        pd.DataFrame(columns=["p1","p2","count"]).to_csv(PAIRINGS_CSV, index=False)
    return pd.read_csv(PAIRINGS_CSV)

def update_pairings(lines: List[List[str]]):
    # lines: liste de lignes (trios/duos) avec noms
    ensure_data_dir()
    pair_df = load_pairings()
    # index par tuple trié
    pair_df["key"] = pair_df.apply(lambda r: tuple(sorted([r["p1"], r["p2"]])), axis=1) if len(pair_df) else []
    pair_map = {k:i for i,k in enumerate(pair_df["key"])} if len(pair_df) else {}
    updates = []
    for line in lines:
        for a,b in itertools.combinations(sorted(line), 2):
            key = (a,b)
            if key in pair_map:
                idx = pair_map[key]
                pair_df.at[idx,"count"] = int(pair_df.at[idx,"count"]) + 1
            else:
                pair_df = pd.concat([pair_df, pd.DataFrame([{"p1":a,"p2":b,"count":1,"key":key}])], ignore_index=True)
                pair_map[key] = len(pair_df)-1
    # nettoyer colonne key avant sauvegarde
    if "key" in pair_df.columns:
        pair_df = pair_df.drop(columns=["key"])
    pair_df.to_csv(PAIRINGS_CSV, index=False)

# ---------- Optimisation / formation ----------

def assign_positions(present_df: pd.DataFrame, want_fw: int, want_df: int):
    """Assigne A/D selon meilleur talent et ajuste pour atteindre les quotas (si possible)."""
    df = present_df.copy()
    df["best_role"] = np.where(df["talent_attaque"] >= df["talent_defense"], "A", "D")
    df["best_talent"] = df[["talent_attaque","talent_defense"]].max(axis=1)
    # Pré-sélection selon best_role
    fw = df[df["best_role"]=="A"].copy()
    de = df[df["best_role"]=="D"].copy()
    # Si quotas pas atteints, déplacer les plus polyvalents
    def move_needed(source, target, need, from_role, to_role):
        # score = avantage de jouer dans la destination par rapport à l'autre
        if from_role=="A":
            source["gap"] = source["talent_defense"] - source["talent_attaque"]
        else:
            source["gap"] = source["talent_attaque"] - source["talent_defense"]
        # plus grand gap = plus “facile” à basculer
        movers = source.sort_values("gap", ascending=False).head(need)
        remaining = source.drop(movers.index)
        target = pd.concat([target, movers.drop(columns=["gap"])], ignore_index=True)
        return remaining.drop(columns=["gap"], errors="ignore"), target

    # Ajuster forwards
    if len(fw) < want_fw and len(de) > 0:
        need = max(0, want_fw - len(fw))
        de, fw = move_needed(de, fw, min(need, len(de)), "D","A")
    # Ajuster defense
    if len(de) < want_df and len(fw) > 0:
        need = max(0, want_df - len(de))
        fw, de = move_needed(fw, de, min(need, len(fw)), "A","D")

    return fw.reset_index(drop=True), de.reset_index(drop=True)

def snake_partition(sorted_players: List[Tuple[str,int]], group_size: int) -> List[List[Tuple[str,int]]]:
    """Répartit en groupes de taille fixe en 'snake draft' pour équilibrer les totaux."""
    groups = [[]]
    direction = 1
    idx = 0
    for p in sorted_players:
        groups[idx].append(p)
        if len(groups[idx]) == group_size:
            if len(groups) == 4:  # on veut 4 trios/duos
                continue
            if direction == 1:
                groups.append([])
                idx += 1
            else:
                groups.append([])
                idx += 1
        # alterner sens à chaque passage complet
        if idx == 3 and len(groups[idx]) == group_size:
            direction *= -1
    # si pas exactement 4 groupes, compléter
    while len(groups) < 4:
        groups.append([])
    return groups[:4]

def make_lines_balanced(players: pd.DataFrame, role: str, line_size: int, iterations: int = 400) -> List[List[Tuple[str,int]]]:
    """Crée 4 lignes (A: 3, D: 2) équilibrées via multi-essais."""
    talent_col = "talent_attaque" if role=="A" else "talent_defense"
    items = [(r["nom"], int(r[talent_col])) for _,r in players.iterrows()]
    best = None
    best_score = 1e9
    rng = np.random.default_rng(42 + int(time.time()) % 1000)
    for _ in range(iterations):
        rng.shuffle(items)
        # tri décroissant pour snake
        cand = sorted(items, key=lambda x: x[1], reverse=True)
        groups = [[] for _ in range(4)]
        # snake simple
        path = list(range(4)) + list(range(3,-1,-1))
        gi = 0
        for name,sc in cand:
            # trouver premier groupe pas plein
            placed = False
            while not placed and gi < len(path)*10:
                idx = path[gi % len(path)]
                if len(groups[idx]) < line_size:
                    groups[idx].append((name, sc))
                    placed = True
                gi += 1
        # score = variance des totaux
        totals = [sum(s for _,s in g) for g in groups]
        score = np.var(totals)
        if score < best_score and all(len(g)==line_size for g in groups):
            best = groups
            best_score = score
    return best

def combo_teams(forward_lines, defense_pairs, pairings_df: pd.DataFrame, pair_penalty: float = 2.0):
    """
    Choisit 2 trios et 2 duos pour Team A (le reste Team B), en minimisant:
      |scoreA - scoreB| + pair_penalty * (paires_rejouées)
    """
    def line_score(line): return sum(s for _,s in line)

    # helper: compter paires déjà vues
    pair_map = {}
    if not pairings_df.empty:
        for _,r in pairings_df.iterrows():
            pair_map[tuple(sorted([r["p1"], r["p2"]]))] = int(r["count"])

    best = None
    best_cost = 1e9
    all_fw_idx = [0,1,2,3]
    all_df_idx = [0,1,2,3]
    for a_fw in itertools.combinations(all_fw_idx, 2):
        b_fw = [i for i in all_fw_idx if i not in a_fw]
        for a_df in itertools.combinations(all_df_idx, 2):
            b_df = [i for i in all_df_idx if i not in a_df]
            A_fw = [forward_lines[i] for i in a_fw]
            B_fw = [forward_lines[i] for i in b_fw]
            A_df = [defense_pairs[i]  for i in a_df]
            B_df = [defense_pairs[i]  for i in b_df]

            def total(lines):
                return sum(line_score(l) for l in lines)

            scoreA = total(A_fw) + total(A_df)
            scoreB = total(B_fw) + total(B_df)

            # pénalité paires rejouées (dans chaque ligne)
            def pair_pen(lines):
                pen = 0
                for line in lines:
                    for a,b in itertools.combinations(sorted([n for n,_ in line]), 2):
                        pen += pair_map.get((a,b), 0)
                return pen

            penalty = pair_pen(A_fw + A_df) + pair_pen(B_fw + B_df)
            cost = abs(scoreA - scoreB) + pair_penalty * penalty

            if cost < best_cost:
                best_cost = cost
                best = {
                    "A_fw": A_fw, "B_fw": B_fw,
                    "A_df": A_df, "B_df": B_df,
                    "scoreA": scoreA, "scoreB": scoreB,
                    "cost": cost
                }
    return best
