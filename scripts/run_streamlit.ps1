# Script de inicio para Streamlit
# Proyecto: Analisis de Transacciones de Supermercado

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando Aplicacion Streamlit" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Python
Write-Host "Verificando Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python no encontrado" -ForegroundColor Red
    exit 1
}
Write-Host "OK: $pythonVersion" -ForegroundColor Green

# Verificar requirements.txt
if (-Not (Test-Path "requirements.txt")) {
    Write-Host "Error: requirements.txt no encontrado" -ForegroundColor Red
    exit 1
}

# Instalar dependencias
Write-Host ""
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al instalar dependencias" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Dependencias instaladas" -ForegroundColor Green

# Verificar archivos necesarios
Write-Host ""
Write-Host "Verificando archivos..." -ForegroundColor Yellow
if (-Not (Test-Path "app_streamlit.py")) {
    Write-Host "Error: app_streamlit.py no encontrado" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Archivos verificados" -ForegroundColor Green

# Iniciar Streamlit
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Iniciando aplicacion..." -ForegroundColor Cyan
Write-Host "URL: http://localhost:8501" -ForegroundColor Green
Write-Host "Presiona Ctrl+C para detener" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

streamlit run app_streamlit.py
