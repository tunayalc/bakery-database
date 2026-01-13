@echo off
title Tuna Firin Baslatiliyor...
color 0f

echo ==========================================
echo      TUNA FIRIN SİSTEMİ BAŞLATILIYOR
echo ==========================================
echo.

cd /d "%~dp0"

echo [1/3] Gerekli kütüphaneler kontrol ediliyor...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    color 0c
    echo.
    echo [HATA] Kütüphaneler yüklenirken hata oluştu!
    echo Lütfen internet bağlantınızı ve Python kurulumunuzu kontrol edin.
    pause
    exit /b
)

echo.
echo [2/3] Uygulama başlatılıyor...
echo Tarayıcınızda http://127.0.0.1:5000 adresine gidin.
echo.
echo Durdurmak için bu pencereyi kapatın veya CTRL+C yapın.
echo ------------------------------------------
echo.

python app.py

if %errorlevel% neq 0 (
    color 0c
    echo.
    echo [HATA] Uygulama beklenmedik bir şekilde kapandı!
    echo Yukarıdaki hata mesajını inceleyin.
    pause
)
