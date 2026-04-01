# Vytvoření virtuálního prostředí
python -m venv venv

# Aktivace virtuálního prostředí
.\venv\Scripts\Activate.ps1

# Instalace knihoven
pip install -r requirements.txt

# Instrukce pro uživatele
Write-Host "############################################################"
Write-Host "Nezapomeňte doplnit potřebné klíče do souboru .env!"
Write-Host "############################################################"

# Spuštění uvicorn serveru
uvicorn main:app --reload
