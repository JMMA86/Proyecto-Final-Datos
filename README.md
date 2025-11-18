# Análisis y Modelado Analítico de Transacciones de Supermercado

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![Apache Airflow](https://img.shields.io/badge/Airflow-2.8.1-blue.svg)](https://airflow.apache.org)

## Equipo

- Juan Manuel Marín Angarita (A00382037)
- Cristian Eduardo Botina Carpio (A00395008)

## 📋 Descripción

Solución tecnológica integral para analizar y visualizar el comportamiento de transacciones de un supermercado, incluyendo:

- 🎨 **Dashboard Interactivo con Streamlit**: Visualización en tiempo real
- 🤖 **Sistema de Recomendaciones IA**: Basado en reglas de asociación (Apriori)
- ⚙️ **Pipeline ETL con Apache Airflow**: Procesamiento automatizado
- 📊 **Análisis Avanzado**: Clustering K-Means y Market Basket Analysis

### Métricas del Dataset

- **1,108,987** transacciones analizadas
- **131,186** clientes únicos
- **112,011** productos en 50 categorías
- **4** tiendas | **Período**: Enero-Junio 2013

## 🚀 Inicio Rápido

### Opción 1: Dashboard Interactivo (Streamlit) - Recomendado

#### Windows PowerShell

```powershell
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar aplicación (script automatizado)
.\scripts\run_streamlit.ps1

# O ejecutar directamente:
streamlit run app_streamlit.py
```

#### Linux/Mac

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar aplicación
streamlit run app_streamlit.py
```

**La aplicación se abrirá en**: http://localhost:8501

### Opción 2: Pipeline ETL (Apache Airflow)

```bash
# 1. Iniciar servicios Docker
docker-compose up -d

# 2. Esperar inicialización (2-3 minutos)

# 3. Acceder a Airflow
# URL: http://localhost:8080
# Usuario: airflow
# Contraseña: airflow

# 4. Activar y ejecutar el DAG 'dataset_analysis_dag'
```

## 📁 Estructura del Proyecto

```
Proyecto-Final-Datos/
│
├── 📱 app_streamlit.py          # Dashboard interactivo Streamlit
├── 📋 requirements.txt           # Dependencias Python
├── 🐳 docker-compose.yaml        # Configuración Airflow
├── 📖 README.md                  # Este archivo
│
├── 📂 scripts/
│   └── run_streamlit.ps1        # Script automatizado de inicio
│
├── 📂 docs/
│   ├── INFORME_EJECUTIVO.md     # Informe técnico completo
│   └── img/                     # 15 visualizaciones generadas
│
├── 📂 dags/
│   └── dataset_analysis_dag.py  # Pipeline ETL Airflow
│
├── 📂 Products/
│   ├── Categories.csv           # Catálogo de categorías
│   └── ProductCategory.csv      # Mapeo producto-categoría
│
└── 📂 Transactions/
    ├── 102_Tran.csv             # Transacciones por tienda
    ├── 103_Tran.csv
    ├── 107_Tran.csv
    └── 110_Tran.csv
```

## 🎯 Funcionalidades del Dashboard

### 1. 📊 Resumen Ejecutivo

- Métricas clave del negocio (ventas, transacciones, clientes)
- Top 10 productos más vendidos
- Top 10 clientes más frecuentes
- Gráficos interactivos con Plotly

### 2. 📈 Análisis Descriptivo

- Serie temporal de ventas diarias (identificar tendencias)
- Ventas por día de la semana (patrones semanales)
- Distribución de productos por transacción
- Detección de outliers (8.09% de compras grandes)

### 3. 🎯 Segmentación de Clientes (K-Means)

- **4 clusters identificados**:
  - 🥉 Ocasionales (32.8%): Frecuencia moderada, bajo volumen
  - 🏆 VIP - Alto Valor (15.7%): Alta frecuencia y volumen
  - 🔸 Esporádicos: Baja frecuencia, volumen moderado
  - 🔹 En Desarrollo: Potencial de crecimiento
- Visualización: Pie chart + Scatter plot
- Heatmap de correlación entre variables

### 4. 💡 Sistema de Recomendación (INTERACTIVO) ⭐

#### A. Dado un Cliente → Productos Recomendados

**Uso**:

1. Selecciona un **Cliente ID** del dropdown
2. Ajusta el número de recomendaciones (3-10)
3. Haz clic en "🔍 Generar Recomendaciones"

**Recibirás**:

- Historial del cliente (transacciones, productos únicos)
- Top productos recomendados con métricas:
  - **Score**: Relevancia acumulada
  - **Confianza**: Probabilidad de compra (%)
  - **Lift**: Fuerza de asociación (>1 = positiva)
- Gráfico de barras interactivo
- Impacto esperado: +15-20% en ticket promedio

**Aplicaciones**:

- Email marketing personalizado
- Notificaciones push en app móvil
- Programa de lealtad con ofertas dirigidas

#### B. Dado un Producto → Productos Complementarios

**Uso**:

1. Selecciona un **Producto** del dropdown
2. Ajusta el número de recomendaciones (3-10)
3. Haz clic en "🔍 Generar Productos Complementarios"

**Recibirás**:

- Información del producto (frecuencia, soporte)
- Productos complementarios con:
  - **Confianza**: % de veces que se compran juntos
  - **Lift**: Factor multiplicador (ej. 12.57 = 12.57x más probable)
  - **Interpretación**: Muy fuerte / Fuerte / Moderada
- Aplicaciones prácticas sugeridas

**Aplicaciones**:

- Layout de tienda (colocar productos juntos)
- E-commerce: "Frecuentemente comprados juntos"
- Bundles promocionales con descuento
- Señalización en punto de venta

**Ejemplo destacado**:

```
Producto 98 → Producto 51
├─ Confianza: 61.58%
├─ Lift: 12.57 (¡asociación extremadamente fuerte!)
└─ Aplicación: Colocar juntos, bundle 98+51+62 con 10% descuento
```

### 5. 📉 Visualizaciones

Galería completa de 15 visualizaciones:

- Top productos y clientes
- Ranking de tiendas
- Serie temporal y ventas por día
- Clustering K-Means
- Reglas de asociación
- Heatmap de correlación
- Días pico de compra

### 6. 📄 Informe Completo

- Visualización del informe ejecutivo en Markdown
- Descarga del informe completo
- Todas las secciones del análisis

## 📊 Resultados Principales

### Segmentación de Clientes (K-Means)

| Segmento          | % Clientes | Características                                  | Estrategia Recomendada                            |
| ----------------- | ---------- | ------------------------------------------------ | ------------------------------------------------- |
| **VIP**           | 15.7%      | Alta frecuencia (19.69) y volumen (212.10)       | Programa de lealtad premium, atención prioritaria |
| **Ocasionales**   | 32.8%      | Frecuencia moderada (7.61), bajo volumen (60.59) | Campañas de activación, descuentos por volumen    |
| **Esporádicos**   | ~35%       | Baja frecuencia, compras irregulares             | Campañas de reactivación, ofertas de entrada      |
| **En Desarrollo** | ~16%       | Potencial de migración a VIP                     | Programa "Camino al VIP", gamificación            |

### Top Reglas de Asociación

| Regla   | Soporte | Confianza | Lift      | Interpretación        |
| ------- | ------- | --------- | --------- | --------------------- |
| 98 → 51 | 1.25%   | 61.58%    | **12.57** | Extremadamente fuerte |
| 97 → 51 | 1.34%   | 59.47%    | **12.14** | Extremadamente fuerte |
| 76 → 53 | 1.41%   | 53.17%    | **11.76** | Extremadamente fuerte |

**Lift > 10**: Asociación perfecta para cross-selling

### Patrones Temporales

- **Días pico**: Fines de semana (Domingo: 191,406 transacciones, +34.3%)
- **Día bajo**: Miércoles (137,245 transacciones) → Oportunidad para promociones
- **Mes pico**: Junio 2013 (pico en 15/06 con 9,476 transacciones)
- **Variabilidad**: ±1,053 transacciones diarias (17.2% CV)

## 💼 Casos de Uso Empresariales

### 1. Marketing Personalizado

**Implementación con el Dashboard**:

1. Ir a **💡 Recomendación → Tab 1 (Cliente)**
2. Filtrar clientes del segmento VIP (Cluster 2)
3. Generar recomendaciones para cada cliente
4. Crear campaña de email con productos sugeridos

**Template Email**:

```
Hola [Nombre],

Como cliente VIP, tenemos recomendaciones especiales:
🔸 Producto 53 - Basado en tus compras recientes
🔸 Producto 70 - Clientes como tú lo prefieren

[Ver ofertas con 15% descuento]
```

**Impacto**: +15-20% conversión, +25% lifetime value

### 2. Optimización de Layout

**Implementación**:

1. Ir a **💡 Recomendación → Tab 2 (Producto)**
2. Identificar productos con Lift > 10
3. Crear mapa de layout con productos cercanos

**Ejemplo**:

- Productos 98 y 51 (Lift: 12.57) → Colocar en pasillos adyacentes
- Señalización: "Los clientes que compraron 98 también llevaron 51"

**Impacto**: +10-15% ventas cruzadas

### 3. Bundles Promocionales

**Implementación**:

1. Seleccionar producto de alta demanda (Top 10)
2. Identificar top 3 complementarios
3. Crear bundle con descuento

**Ejemplo**:

```
Bundle "Combo Ganador"
├─ Producto 98
├─ Producto 51
└─ Producto 62
Ahorra 15% vs compra individual
```

## 🔧 Tecnologías Utilizadas

### Frontend & Visualización

- **Streamlit 1.28+**: Dashboard interactivo
- **Plotly 5.17+**: Gráficos interactivos (zoom, pan, export)

### Backend & Procesamiento

- **Python 3.8+**: Lenguaje principal
- **Pandas 2.0+**: Manipulación de datos
- **NumPy 1.24+**: Cálculos numéricos
- **Scikit-learn**: K-Means clustering

### Orquestación

- **Apache Airflow 2.8.1**: Pipeline ETL
- **Docker & Docker Compose**: Contenedorización
- **PostgreSQL 15**: Metadata store
- **Redis**: Message broker

### Algoritmos de IA

- **K-Means**: Segmentación de clientes (4 clusters)
- **Apriori**: Reglas de asociación (Market Basket Analysis)
- **IQR**: Detección de outliers

## 📚 Documentación

- **`docs/INFORME_EJECUTIVO.md`**: Informe técnico completo con análisis detallado
- **`docs/img/`**: 15 visualizaciones generadas (PNG alta resolución)
- **`dags/dataset_analysis_dag.py`**: Pipeline ETL con 8 tareas

## 🔧 Solución de Problemas

### Error: "No se pudieron cargar los datos"

**Solución**:

```powershell
# Verificar estructura de archivos
Get-ChildItem Products, Transactions -Recurse
```

### Error: "streamlit no encontrado"

**Solución**:

```powershell
pip install -r requirements.txt --upgrade
```

### La aplicación es lenta

**Solución**:

- Primera carga: 10-30 segundos (normal)
- Cache automático: Cargas posteriores instantáneas
- Optimización: Usar `@st.cache_data` ya implementado

### No aparecen recomendaciones

**Solución**:

- Verificar que el cliente/producto exista
- Probar con IDs de los Top 10 (garantizados)
- Ajustar número de recomendaciones

## 📖 Cumplimiento del Enunciado

### ✅ Resumen Ejecutivo

- [x] Total de ventas: 10,591,793 unidades
- [x] Número de transacciones: 1,108,987
- [x] Top 10 productos más vendidos
- [x] Top 10 clientes por transacciones
- [x] Días pico de compra
- [x] Categorías más rentables por volumen

### ✅ Visualizaciones Analíticas

- [x] Serie de tiempo (ventas diarias/mensuales)
- [x] Boxplot (distribución por cliente/categoría)
- [x] Heatmap (correlación entre variables)

### ✅ Análisis Avanzado

#### A. Segmentación de Clientes (K-Means)

- [x] 4 clusters identificados
- [x] Variables: Frecuencia, volumen, productos distintos, diversidad
- [x] Normalización: StandardScaler
- [x] Visualización: Pie chart + Scatter plot
- [x] Descripción de cada grupo
- [x] Recomendaciones de negocio por segmento

#### B. Recomendador de Productos ⭐

- [x] **Dado un cliente**: Productos complementarios basados en historial
- [x] **Dado un producto**: Productos que se compran juntos
- [x] Técnica: Apriori (soporte 1%, confianza 30%)
- [x] Métricas: Soporte, confianza, lift
- [x] **Interfaz interactiva**: Dropdowns + gráficos en tiempo real

#### C. Incorporación de Nuevos Datos

- [x] Pipeline automatizado con Airflow
- [x] Re-ejecución automática al agregar CSVs
- [x] Reproducibilidad completa

### ✅ Entregables

- [x] **Código fuente**: `app_streamlit.py` + `dags/dataset_analysis_dag.py`
- [x] **Informe técnico**: `docs/INFORME_EJECUTIVO.md` (Markdown)
- [x] **Aplicación interactiva**: Dashboard Streamlit funcional

## 🚀 Inicio Rápido Resumen

```powershell
# 1. Instalar
pip install -r requirements.txt

# 2. Ejecutar
.\scripts\run_streamlit.ps1
# O:
streamlit run app_streamlit.py

# 3. Abrir navegador
http://localhost:8501

# 4. Probar recomendaciones
# → Ir a "💡 Sistema de Recomendación"
# → Seleccionar Cliente 307063 o Producto 98
# → ¡Disfrutar!
```
