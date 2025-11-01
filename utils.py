import pandas as pd
import os

def save_history(equipeB, equipeN, moyB, moyN, date, triosB=None, duosB=None, triosN=None, duosN=None):
    """Sauvegarde les équipes formées dans le fichier historique"""
    path = "data/historique.csv"
    os.makedirs("data", exist_ok=True)

    def lignes_to_str(lignes, col):
        """Convertit trios/duos en texte avec moyenne"""
        if not lignes:
            return ""
        resultats = []
        for i, g in enumerate(lignes, 1):
            if g.empty:
                continue
            moy = round(g[col].mean(), 2)
            noms = ", ".join(g["nom"].tolist())
            resultats.append(f"{i}: {noms} (moy {moy})")
        return " | ".join(resultats)

    new_entry = pd.DataFrame([{
        "Date": date,
        "Moyenne_BLANCS": moyB,
        "Moyenne_NOIRS": moyN,
        "Trios_BLANCS": lignes_to_str(triosB, "talent_attaque"),
        "Duos_BLANCS": lignes_to_str(duosB, "talent_defense"),
        "Trios_NOIRS": lignes_to_str(triosN, "talent_attaque"),
        "Duos_NOIRS": lignes_to_str(duosN, "talent_defense"),
        "Équipe_BLANCS": ", ".join(equipeB),
        "Équipe_NOIRS": ", ".join(equipeN)
    }])

    if os.path.exists(path):
        df = pd.read_csv(path)
        df = pd.concat([df, new_entry], ignore_index=True)
    else:
        df = new_entry

    df.to_csv(path, index=False)
