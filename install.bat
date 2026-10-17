@echo off
REM MyJarvis — Installer for Windows
REM Run as Administrator for auto-start setup

echo ========================================
echo  MyJarvis Installer
echo  Personal AI Assistant with ALFRED personality
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH
    echo Instale em: https://python.org/downloads
    echo Marque "Add Python to PATH" durante instalacao
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM Check pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] pip nao disponivel
    pause
    exit /b 1
)
echo [OK] pip disponivel

REM Install requirements
echo.
echo [1/5] Instalando dependencias...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [AVISO] Algumas dependencias falharam, tentando instalar individualmente...
    python -m pip install httpx pyyaml python-dotenv typer rich psutil
    python -m pip install pycaw pystray pillow pywin32 plyer pyperclip pyautogui watchdog
)

REM Install package in editable mode
echo.
echo [2/5] Instalando MyJarvis (modo editavel)...
pip install -e .
if errorlevel 1 (
    echo [ERRO] Falha ao instalar pacote
    pause
    exit /b 1
)

REM Create directories
echo.
echo [3/5] Criando diretorios...
if not exist "%USERPROFILE%\.myjarvis" mkdir "%USERPROFILE%\.myjarvis"
if not exist "%USERPROFILE%\.myjarvis\logs" mkdir "%USERPROFILE%\.myjarvis\logs"
if not exist "%USERPROFILE%\.myjarvis\skills" mkdir "%USERPROFILE%\.myjarvis\skills"
if not exist "%USERPROFILE%\.myjarvis\cache" mkdir "%USERPROFILE%\.myjarvis\cache"
echo [OK] Diretorios criados em %USERPROFILE%\.myjarvis

REM Copy config template
echo.
echo [4/5] Configurando...
if not exist "%USERPROFILE%\.myjarvis\config.toml" (
    copy config.toml "%USERPROFILE%\.myjarvis\config.toml" >nul
    echo [OK] Config copiado para %USERPROFILE%\.myjarvis\config.toml
    echo.
    echo ========================================
    echo IMPORTANTE: Edite o arquivo de configuracao
    echo %USERPROFILE%\.myjarvis\config.toml
    echo Adicione sua NVIDIA_API_KEY em:
    echo   [intelligence.engine_config]
    echo   api_key = "sua-chave-aqui"
    echo ========================================
) else (
    echo [OK] Config ja existe
)

REM Auto-start via Task Scheduler
echo.
echo [5/5] Configurando auto-start (Task Scheduler)...
schtasks /query /tn "MyJarvis" >nul 2>&1
if errorlevel 1 (
    REM Get python and script paths
    for /f "tokens=*" %%a in ('where python') do set PYTHON_EXE=%%a
    for /f "tokens=*" %%a in ('where myjarvis-daemon') do set DAEMON_EXE=%%a
    
    if defined DAEMON_EXE (
        echo Criando tarefa agendada...
        schtasks /create /tn "MyJarvis" /tr "\"%PYTHON_EXE%\" \"%DAEMON_EXE%\" --foreground" /sc ONLOGON /rl HIGHEST /f
        if errorlevel 1 (
            echo [AVISO] Nao foi possivel criar auto-start (precisa Admin)
            echo Execute como Administrador para auto-start
        ) else (
            echo [OK] Auto-start configurado
        )
    ) else (
        echo [AVISO] myjarvis-daemon nao encontrado no PATH
        echo Reinicie o terminal e rode: myjarvis-setup --autostart
    )
) else (
    echo [OK] Auto-start ja configurado
)

echo.
echo ========================================
echo  INSTALACAO CONCLUIDA!
echo ========================================
echo.
echo Proximos passos:
echo 1. Edite: %USERPROFILE%\.myjarvis\config.toml
echo 2. Adicione sua NVIDIA_API_KEY
echo 3. Teste: myjarvis ask "Ola, Jarvis"
echo 4. Daemon: myjarvis-daemon (ou myjarvis-tray para icone na bandeja)
echo.
echo Logs: %USERPROFILE%\.myjarvis\logs\
echo Config: %USERPROFILE%\.myjarvis\config.toml
echo.
pause