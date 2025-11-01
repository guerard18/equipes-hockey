import os
import base64
import requests
from datetime import datetime
import streamlit as st

def save_to_github(filepath: str, message: str):
    """
    Enregistre un fichier local (ex: data/joueurs.csv ou data/historique.csv)
    directement dans le dépôt GitHub via l'API REST.
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")
    user = os.environ.get("GITHUB_USER")

    if not token or not repo or not user:
        st.warning("⚠️ Impossible d'enregistrer sur GitHub : les secrets GITHUB_TOKEN, GITHUB_REPO ou GITHUB_USER sont manquants.")
        return False

    # Exemple : guerard18/equipes-hockey
    url = f"https://api.github.com/repos/{repo}/contents/{filepath}"
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Lire le contenu du fichier à sauvegarder
    try:
        with open(filepath, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        st.error(f"❌ Fichier introuvable : {filepath}")
        return False

    # Obtenir le SHA du fichier existant (nécessaire pour le mettre à jour)
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    data = {
        "message": f"{message} – {now}",
        "content": content,
        "branch": "main"
    }
    if sha:
        data["sha"] = sha

    r = requests.put(url, headers=headers, json=data)

    if r.status_code in (200, 201):
        st.toast(f"✅ Sauvegarde GitHub réussie ({os.path.basename(filepath)})", icon="💾")
        return True
    else:
        st.error(f"❌ Erreur GitHub ({r.status_code}) : {r.text}")
        return False
