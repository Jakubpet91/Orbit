#!/bin/bash

# Vytvoření virtuálního prostředí
python -m venv venv

# Aktivace virtuálního prostředí
source venv/bin/activate

# Instalace knihoven
pip install -r requirements.txt

# Instrukce pro uživatele
echo "############################################################"
echo "Nezapomeňte doplnit potřebné klíče do souboru .env!"
echo "############################################################"

# Spuštění uvicorn serveru
uvicorn main:app --reload
