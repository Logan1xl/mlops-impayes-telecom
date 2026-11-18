@echo off
REM NaijaTel Impayes AI — lanceur de demonstration (Windows)
REM Double-cliquez sur ce fichier : la demo s'ouvre dans votre navigateur.
cd /d "%~dp0"
start "" index.html
echo ================================================
echo   NaijaTel Impayes AI — demo ouverte dans votre
echo   navigateur. 100 %% hors-ligne, aucune installation.
echo ================================================
echo.
echo Optionnel — trace MLflow (si le projet est installe) :
echo   cd .. ^&^& .venv\Scripts\mlflow.exe ui --backend-store-uri sqlite:///mlflow.db --port 5000
echo   puis ouvrir http://localhost:5000
echo.
echo Optionnel — API FastAPI live :
echo   cd .. ^&^& .venv\Scripts\uvicorn.exe impayes.api.main:app --port 8000
echo.
pause
