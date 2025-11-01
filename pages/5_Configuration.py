import streamlit as st
import json
import os

st.title("⚙️ Configuration de l'application")

path = "data/config.json"
os.makedirs("data", exist_ok=True)

if os.path.exists(path):
    with open(path, "r") as f:
        config = json.load(f)
else:
    config = {
        "nb_trios": 4,
        "nb_duos": 4,
        "envoyer_courriel": True,
        "format_match": "Match du {date}"
    }

with st.form("config_form"):
    st.subheader("🧩 Paramètres généraux")
    config["nb_trios"] = st.number_input("Nombre de trios par équipe", min_value=1, max_value=6, value=config["nb_trios"])
    config["nb_duos"] = st.number_input("Nombre de duos par équipe", min_value=1, max_value=6, value=config["nb_duos"])
    config["envoyer_courriel"] = st.checkbox("Activer l'envoi des courriels", value=config["envoyer_courriel"])
    config["format_match"] = st.text_input("Format du nom du match", value=config["format_match"])

    if st.form_submit_button("💾 Enregistrer la configuration"):
        with open(path, "w") as f:
            json.dump(config, f, indent=4)
        st.success("✅ Configuration enregistrée avec succès !")

