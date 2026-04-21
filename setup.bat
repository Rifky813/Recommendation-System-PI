@echo off
REM Quick Setup Script untuk Sistem Rekomendasi Karya Ilmiah
REM Windows (.bat)

echo.
echo ================================================
echo  Sistem Rekomendasi Karya Ilmiah - Setup
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python tidak ditemukan. Silakan install Python 3.8+
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Gagal install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Running pipeline orchestration...
echo (Proses ini memakan waktu 5-15 menit, silakan tunggu...)
python main.py --pages 5 --test
if errorlevel 1 (
    echo ERROR: Gagal run pipeline
    pause
    exit /b 1
)

echo.
echo [3/3] Starting Streamlit app...
echo Streamlit akan buka di http://localhost:8501
echo Press Ctrl+C untuk stop server
echo.
pause
streamlit run app.py
