#!/bin/bash

# Se déplace dans le répertoire où se trouve ce script
cd "$(dirname "$0")"

# Active l'environnement virtuel
source venv/bin/activate

# Lance l'application Streamlit
streamlit run app.py