@echo off
rem ============================================================
rem  Ortak kurulum: Python'u bulur, yoksa otomatik kurar.
rem  Çalıştırıldığında PYEXE değişkenini doldurur.
rem  Başarısızsa exit /b 1 döner.
rem ============================================================
set "PYEXE="

rem 1) python komutu çalışıyor mu? (Windows Store taklidi olursa
rem    --version hata verir, o yüzden sadece varlığa bakmıyoruz)
python --version >nul 2>nul && set "PYEXE=python"

rem 2) py başlatıcısı var mı? Varsa gerçek python.exe yolunu bul
if not defined PYEXE (
    for /f "delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
)

rem 3) Python 3.12 varsayılan konumda kurulu mu?
if not defined PYEXE (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

rem 4) Hiçbiri yoksa winget ile kur
if not defined PYEXE (
    echo.
    echo Python bulunamadi. Simdi otomatik kurulacak...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo.
        echo Kurulum basarisiz oldu. Python'u su adresten kendiniz kurabilirsiniz:
        echo https://www.python.org/downloads/
        echo Kurulum sihirbazinda "Add Python to PATH" secenegini isaretlemeyi unutmayin.
        pause
        exit /b 1
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

if not defined PYEXE (
    echo.
    echo Python kuruldu ama bulunamadi. Bilgisayari yeniden baslatin ve tekrar deneyin.
    pause
    exit /b 1
)

exit /b 0
