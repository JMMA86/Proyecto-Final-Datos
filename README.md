# Análisis de Dataset de Transacciones con Apache Airflow

## Estudiantes:

- Juan Manuel Marín Angarita (A00382037)
- Cristian Eduardo Botina Carpio (A00395008)

## Descripción

Este proyecto implementa una solución tecnológica integral para analizar y visualizar el comportamiento de transacciones de un supermercado mediante Apache Airflow. La solución genera valor a partir de los datos disponibles mediante analítica descriptiva, diagnóstica y predictiva, cumpliendo con todos los requisitos del enunciado del proyecto.

## Cumplimiento del Enunciado

### Resumen Ejecutivo Implementado

| Indicador requerido      | Implementación                       | Archivo de salida                   |
| ------------------------ | ------------------------------------ | ----------------------------------- |
| Total de ventas          | Suma total de productos vendidos     | `results/data_review.txt`           |
| Número de transacciones  | 1,108,987 transacciones              | `results/data_review.txt`           |
| Top 10 productos         | Productos más comprados por volumen  | `results/top_products.png`          |
| Top 10 clientes          | Clientes con mayor volumen de compra | `results/top10_customers.png`       |
| Días pico de compra      | Días con mayor actividad             | `results/peak_days.png`             |
| Categorías más rentables | Categorías ordenadas por volumen     | `results/top_categories_volume.png` |

### Visualizaciones Analíticas Implementadas

| Tipo requerido  | Implementación                        | Archivo generado                                                             |
| --------------- | ------------------------------------- | ---------------------------------------------------------------------------- |
| Serie de tiempo | Ventas diarias, semanales y mensuales | `results/daily_sales_timeseries.png`, `results/monthly_sales.png`            |
| Boxplot         | Distribución por cliente y categoría  | `results/boxplot_distribution.png`, `results/customer_clustering_kmeans.png` |
| Heatmap         | Correlación entre métricas de cliente | `results/correlation_heatmap.png`                                            |

### Análisis Avanzado Implementado

#### A. Segmentación de Clientes (K-Means)

- **Algoritmo**: K-Means clustering con 4 segmentos
- **Variables**: Frecuencia, volumen total, productos distintos, diversidad de categorías, días activo, compras por día
- **Normalización**: StandardScaler para todas las variables
- **Visualizaciones**: `results/customer_clustering_kmeans.png`, `results/customer_clustering_scatter.png`
- **Interpretación**: Archivo `results/customer_analysis.txt` con descripción de cada segmento

#### B. Recomendador de Productos

- **Técnica**: Reglas de asociación con algoritmo Apriori
- **Funcionalidades**:
  - Dado un cliente: Sugerir productos complementarios basados en su historial
  - Dado un producto: "Clientes que compraron X también compraron Y"
- **Métricas**: Soporte, confianza y lift para cada regla
- **Visualización**: `results/association_rules_top10.png`
- **Salida**: Archivo `results/recommendations.txt` con ejemplos de recomendaciones

#### C. Incorporación de Nuevos Datos

- **Sistema**: Pipeline automatizado en Apache Airflow
- **Proceso**: Al agregar nuevos archivos CSV en `Transactions/`, el DAG re-ejecuta todos los análisis automáticamente
- **Reproducibilidad**: Cada ejecución genera un set completo de resultados actualizados
- **Limpieza**: Archivos intermedios se limpian automáticamente tras cada ejecución

## Arquitectura de la Solución

La solución utiliza Apache Airflow 2.8.1 con las siguientes características técnicas:

- Prevención de zombie jobs con detección automática
- Gestión eficiente de recursos (CPU, memoria, disco)
- Uso de archivos intermedios en lugar de XCom para datasets grandes
- Límites de recursos en todos los contenedores Docker
- Timeouts y reintentos con exponential backoff
- Pools para control de concurrencia
- Liberación automática de memoria
- Callbacks para monitoreo y alertas

Para detalles completos, consulta: [OPTIMIZATION_GUIDE.md](./misc/OPTIMIZATION_GUIDE.md)

## Estructura del proyecto

```
.
├── dags/
│   └── dataset_analysis_dag.py  # DAG principal de Airflow
├── data/                       # Carpeta para datos temporales
├── logs/                       # Logs de Airflow
├── plugins/                    # Plugins o hooks adicionales
├── results/                    # Resultados del análisis
├── Products/                   # Datos de productos y categorías
│   ├── Categories.csv
│   └── ProductCategory.csv
├── Transactions/               # Archivos de transacciones
│   ├── 102_Tran.csv
│   ├── 103_Tran.csv
│   ├── 107_Tran.csv
│   └── 110_Tran.csv
├── docker-compose.yaml         # Configuración de los servicios de Airflow
├── .env                        # Variables de entorno para el entorno Docker
└── README.md                   # Documentación
```

## Dataset

El dataset contiene información de transacciones de un supermercado colombiano:

- **Categories.csv**: Lista de categorías de productos (ID y nombre)
- **ProductCategory.csv**: Relación entre códigos de productos y categorías
- **Transactions/\*.csv**: Archivos de transacciones con fecha, tienda, cliente y lista de productos comprados

## Requisitos previos

- Docker y Docker Compose instalados
- Puertos disponibles: 8080 (interfaz web de Airflow)

## Instrucciones de ejecución

### 1. Configurar las variables de entorno

El archivo `.env` define las variables necesarias:

```env
AIRFLOW_IMAGE_NAME=apache/airflow:2.8.1
AIRFLOW_UID=50000
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
_PIP_ADDITIONAL_REQUIREMENTS=pandas
```

### 2. Levantar los servicios de Airflow

Ejecuta:

```bash
docker compose up -d
```

Espera 2-3 minutos para que todos los servicios estén completamente iniciados.

### 3. Acceder a la interfaz web

Abre tu navegador en [http://localhost:8080](http://localhost:8080)

Credenciales por defecto:

```
Usuario: airflow
Contraseña: airflow
```

### 4. Activar y ejecutar el DAG

1. En la interfaz de Airflow, busca el DAG llamado `dataset_analysis_dag`.
2. Actívalo con el switch.
3. Pulsa "Trigger DAG" para ejecutarlo manualmente.
4. **La primera tarea `setup_pools` configurará automáticamente los pools necesarios**.
5. Monitorea la ejecución y los logs desde la UI.

### 5. Verificar la salida

Una vez finalizado, se generarán los archivos de resultados en `./results/`:

#### Archivos de texto

- `data_review.txt`: Revisión inicial del dataset
- `descriptive_stats.txt`: Estadísticas descriptivas
- `temporal_analysis.txt`: Análisis temporal de ventas
- `customer_analysis.txt`: Análisis de comportamiento de clientes
- `product_association.txt`: Reglas de asociación de productos

#### Visualizaciones

- `top_products.png`: Gráfico de top productos vendidos
- `store_ranking.png`: Ranking de tiendas por transacciones
- `products_histogram.png`: Histograma de productos por transacción
- `category_distribution.png`: Distribución de categorías
- `daily_sales_timeseries.png`: Serie temporal de ventas diarias
- `sales_by_day_of_week.png`: Ventas por día de la semana
- `monthly_sales.png`: Evolución de ventas mensuales
- `customer_segmentation.png`: Segmentación de clientes
- `association_rules.png`: Top reglas de asociación de productos

## Descripción técnica del DAG

El flujo consta de ocho tareas organizadas en tres etapas:

### Etapa 1: Carga y revisión inicial

1. `load_data`  
   Carga todos los archivos CSV del dataset. Convierte las fechas a formato datetime y crea variables temporales adicionales (año, mes, semana, día de la semana). Convierte store y customer a variables categóricas.

2. `data_review`  
   Realiza revisión inicial: estructura, tipos de datos, valores faltantes, duplicados.

3. `descriptive_stats`  
   Calcula estadísticas descriptivas para variables numéricas y categóricas. Identifica outliers usando el método IQR.

### Etapa 2: Análisis específicos (ejecución paralela)

4. `temporal_analysis`  
   Analiza patrones temporales: ventas diarias, semanales, mensuales, por día de la semana y tendencias temporales.

5. `customer_analysis`  
   Analiza comportamiento de clientes: frecuencia de compra, tiempo promedio entre compras y segmentación basada en frecuencia y valor.

6. `product_association`  
   Aplica reglas de asociación usando el algoritmo Apriori para identificar productos que se compran frecuentemente juntos.

### Etapa 3: Visualización y almacenamiento

7. `generate_plots`  
   Genera visualizaciones basadas en todos los análisis realizados.

8. `save_results`  
   Guarda los resultados en archivos de texto e imágenes.

## Resultados del análisis

### Revisión inicial del dataset

#### Categories

- **Número de registros**: 50
- **Número de columnas**: 2
- **Columnas**: ['category_id', 'category_name']
- **Tipos de datos**: {'category_id': 'int64', 'category_name': 'object'}
- **Valores faltantes**: {'category_id': 0, 'category_name': 0}
- **Duplicados**: 0

#### ProductCategory

- **Número de registros**: 112,011
- **Número de columnas**: 2
- **Columnas**: ['product_code', 'category_id']
- **Tipos de datos**: {'product_code': 'object', 'category_id': 'object'}
- **Valores faltantes**: {'product_code': 0, 'category_id': 0}
- **Duplicados**: 18,473

#### Transactions

- **Número de registros**: 1,108,987
- **Número de columnas**: 9
- **Columnas**: ['date', 'store', 'customer', 'products', 'year', 'month', 'week', 'day_of_week', 'day_name']
- **Tipos de datos**: {'date': 'datetime64[ns]', 'store': 'int64', 'customer': 'int64', 'products': 'object', 'year': 'int64', 'month': 'int64', 'week': 'int64', 'day_of_week': 'int64', 'day_name': 'object'}
- **Valores faltantes**: 0 en todas las columnas
- **Duplicados**: 1

### Estadísticas descriptivas

#### Variables numéricas

##### Número de productos por transacción

| Estadística             | Valor |
| ----------------------- | ----- |
| **Media**               | 9.55  |
| **Mediana**             | 6.0   |
| **Moda**                | 1     |
| **Desviación estándar** | 10.00 |
| **Mínimo**              | 1.0   |
| **Máximo**              | 128.0 |
| **Percentil 25%**       | 3.0   |
| **Percentil 50%**       | 6.0   |
| **Percentil 75%**       | 12.0  |

**Outliers detectados**: 89,733 transacciones (8.09% del total)

- Mínimo outlier: 26 productos
- Máximo outlier: 128 productos

![Histograma de productos por transacción](results/products_histogram.png)

_La distribución muestra que la mayoría de las transacciones contienen entre 1 y 12 productos, con una cola larga hacia valores más altos._

#### Variables categóricas

##### Top 10 Categorías más populares

| Posición | Categoría    | Número de Productos | Porcentaje |
| -------- | ------------ | ------------------- | ---------- |
| 1        | Categoría 2  | 23,258              | 20.76%     |
| 2        | Categoría 9  | 5,279               | 4.71%      |
| 3        | Categoría 11 | 4,869               | 4.35%      |
| 4        | Categoría 13 | 4,541               | 4.05%      |
| 5        | Categoría 8  | 4,260               | 3.80%      |
| 6        | Categoría 14 | 3,784               | 3.38%      |
| 7        | Categoría 40 | 3,693               | 3.30%      |
| 8        | Categoría 48 | 3,434               | 3.07%      |
| 9        | Categoría 22 | 3,422               | 3.06%      |
| 10       | Categoría 5  | 3,322               | 2.97%      |

![Distribución de categorías](results/category_distribution.png)

##### Top 10 Productos más vendidos

| Posición | Producto    | Número de Ventas |
| -------- | ----------- | ---------------- |
| 1        | Producto 5  | 300,526          |
| 2        | Producto 10 | 290,313          |
| 3        | Producto 3  | 269,855          |
| 4        | Producto 4  | 260,418          |
| 5        | Producto 6  | 254,644          |
| 6        | Producto 8  | 253,899          |
| 7        | Producto 7  | 225,877          |
| 8        | Producto 16 | 224,159          |
| 9        | Producto 11 | 221,968          |
| 10       | Producto 9  | 212,480          |

![Top productos vendidos](results/top_products.png)

##### Ranking de Tiendas

| Tienda    | Transacciones | Porcentaje |
| --------- | ------------- | ---------- |
| Store 103 | 407,130       | 36.71%     |
| Store 102 | 314,286       | 28.34%     |
| Store 107 | 254,633       | 22.96%     |
| Store 110 | 132,938       | 11.99%     |

![Ranking de tiendas](results/store_ranking.png)

_La Store 103 lidera claramente con más de un tercio de todas las transacciones._

### Análisis temporal

El análisis temporal examina patrones de ventas a lo largo del tiempo para identificar tendencias, estacionalidad y picos de actividad.

#### Estadísticas de ventas diarias

| Métrica                               | Valor    |
| ------------------------------------- | -------- |
| **Media de transacciones diarias**    | 6,127    |
| **Máximo de transacciones en un día** | 9,476    |
| **Mínimo de transacciones en un día** | 2,860    |
| **Desviación estándar**               | 1,053.07 |

![Serie temporal de ventas diarias](results/daily_sales_timeseries.png)

_La serie temporal muestra variabilidad significativa en las ventas diarias, con picos notables en ciertos días del mes._

#### Top 10 días con más ventas

| Posición | Fecha      | Transacciones |
| -------- | ---------- | ------------- |
| 1        | 2013-06-15 | 9,476         |
| 2        | 2013-05-11 | 8,854         |
| 3        | 2013-02-03 | 8,523         |
| 4        | 2013-03-03 | 8,426         |
| 5        | 2013-06-01 | 8,420         |
| 6        | 2013-04-28 | 8,286         |
| 7        | 2013-04-07 | 8,265         |
| 8        | 2013-03-02 | 8,160         |
| 9        | 2013-06-29 | 8,156         |
| 10       | 2013-04-21 | 8,126         |

#### Ventas por día de la semana

| Día           | Transacciones | Total de Productos |
| ------------- | ------------- | ------------------ |
| **Lunes**     | 142,445       | 1,301,747          |
| **Martes**    | 150,739       | 1,606,571          |
| **Miércoles** | 137,245       | 1,175,689          |
| **Jueves**    | 158,766       | 1,506,585          |
| **Viernes**   | 139,371       | 1,213,602          |
| **Sábado**    | 189,015       | 1,860,948          |
| **Domingo**   | 191,406       | 1,926,651          |

![Ventas por día de la semana](results/sales_by_day_of_week.png)

**Insight**: Los fines de semana (sábado y domingo) muestran el mayor volumen de transacciones, con el domingo siendo el día más activo. Los miércoles y viernes son los días más tranquilos de la semana.

#### Evolución mensual

![Ventas mensuales](results/monthly_sales.png)

_El gráfico de ventas mensuales permite observar tendencias de largo plazo y posibles patrones estacionales en el comportamiento de compra._

### Análisis de clientes

El análisis de clientes segmenta y caracteriza el comportamiento de compra de 131,186 clientes únicos.

#### Frecuencia de compra

| Métrica                            | Valor |
| ---------------------------------- | ----- |
| **Media de compras por cliente**   | 8.45  |
| **Mediana de compras por cliente** | 4.0   |
| **Desviación estándar**            | 11.28 |
| **Mínimo de compras**              | 1     |
| **Máximo de compras**              | 535   |

**Interpretación**: La mediana de 4 compras es significativamente menor que la media de 8.45, lo que indica que hay clientes muy activos que elevan el promedio. La mayoría de los clientes realizan compras ocasionales.

#### Tiempo entre compras

Para clientes con compras recurrentes:

| Métrica                 | Valor (días) |
| ----------------------- | ------------ |
| **Promedio**            | 11.99        |
| **Mediana**             | 7.0          |
| **Desviación estándar** | 16.64        |

**Insight**: Los clientes recurrentes típicamente regresan en una semana (mediana de 7 días), aunque el promedio es de casi 12 días debido a algunos clientes con intervalos más largos.

#### Segmentación de clientes

Los 131,186 clientes se clasifican en cuatro segmentos:

| Segmento        | Número de Clientes | Porcentaje | Descripción                                     |
| --------------- | ------------------ | ---------- | ----------------------------------------------- |
| **Regular**     | 91,471             | 69.7%      | Frecuencia y valor regulares                    |
| **High Value**  | 27,067             | 20.6%      | Alta frecuencia Y alto valor (top 25% en ambas) |
| **Frequent**    | 6,755              | 5.2%       | Alta frecuencia, valor regular                  |
| **Big Spender** | 5,893              | 4.5%       | Frecuencia regular, alto valor                  |

![Segmentación de clientes](results/customer_segmentation.png)

**Estrategias recomendadas**:

- **High Value** (20.6%): Clientes VIP - Mantener satisfacción con programas de lealtad premium
- **Frequent** (5.2%): Aumentar valor de compra con técnicas de upselling/cross-selling
- **Big Spender** (4.5%): Aumentar frecuencia con recordatorios y promociones personalizadas
- **Regular** (69.7%): Oportunidades de crecimiento - campañas de activación y engagement

### Análisis de asociación de productos

Se aplicó el algoritmo Apriori para descubrir reglas de asociación entre productos, identificando combinaciones que se compran frecuentemente juntas.

#### Parámetros utilizados

- **Soporte mínimo**: 1% (productos que aparecen en al menos 1% de transacciones)
- **Confianza mínima**: 30% (probabilidad de compra conjunta)

#### Fórmulas del algoritmo Apriori

El algoritmo Apriori utiliza tres métricas fundamentales para evaluar las reglas de asociación:

##### 1. Soporte (Support)

Mide la frecuencia con la que aparece un conjunto de items en las transacciones.

$$
\text{Soporte}(X) = \frac{\text{Número de transacciones que contienen } X}{\text{Total de transacciones}}
$$

Para una regla $X \rightarrow Y$:

$$
\text{Soporte}(X \rightarrow Y) = \frac{\text{Transacciones con } X \cup Y}{\text{Total de transacciones}}
$$

**Ejemplo:** Si 58,000 transacciones de 1,108,987 contienen los productos {68, 51}:

$$
\text{Soporte}(\{68, 51\}) = \frac{58{,}000}{1{,}108{,}987} = 0.0523 = 5.23\%
$$

##### 2. Confianza (Confidence)

Mide la probabilidad de que si se compra $X$, también se compre $Y$.

$$
\text{Confianza}(X \rightarrow Y) = \frac{\text{Soporte}(X \cup Y)}{\text{Soporte}(X)} = \frac{P(X \cap Y)}{P(X)}
$$

**Ejemplo:** Si 58,000 transacciones tienen {68, 51} y 151,142 tienen {68}:

$$
\text{Confianza}(68 \rightarrow 51) = \frac{58{,}000}{151{,}142} = 0.3845 = 38.45\%
$$

**Interpretación:** El 38.45% de los clientes que compran el producto 68 también compran el producto 51.

##### 3. Lift

Mide qué tan fuerte es la asociación comparada con la independencia estadística.

$$
\text{Lift}(X \rightarrow Y) = \frac{\text{Confianza}(X \rightarrow Y)}{\text{Soporte}(Y)} = \frac{P(X \cap Y)}{P(X) \times P(Y)}
$$

**Interpretación del Lift:**

- $\text{Lift} > 1$: Asociación positiva (los items se compran juntos más de lo esperado)
- $\text{Lift} = 1$: No hay asociación (independencia estadística)
- $\text{Lift} < 1$: Asociación negativa (los items raramente se compran juntos)

**Ejemplo:** Si el soporte de {51} es 9.85%:

$$
\text{Lift}(68 \rightarrow 51) = \frac{0.3845}{0.0985} = 3.90
$$

Esto significa que la probabilidad de comprar el producto 51 es **3.90 veces mayor** cuando se compra el producto 68, en comparación con la probabilidad base.

##### Principio Apriori

El algoritmo se basa en la siguiente propiedad:

> **"Si un conjunto de items es frecuente, todos sus subconjuntos también deben ser frecuentes"**

En términos matemáticos:

$$
\text{Si } \text{Soporte}(X) < \text{min\_support}, \text{ entonces } \forall Y \supseteq X: \text{Soporte}(Y) < \text{min\_support}
$$

Esta propiedad permite **podar** eficientemente el espacio de búsqueda, descartando superconjuntos de itemsets infrecuentes sin necesidad de calcular su soporte.

#### Items frecuentes (Top 20)

| Posición | Producto    | Frecuencia en Transacciones |
| -------- | ----------- | --------------------------- |
| 1        | Producto 5  | 300,526                     |
| 2        | Producto 10 | 290,313                     |
| 3        | Producto 3  | 269,855                     |
| 4        | Producto 4  | 260,418                     |
| 5        | Producto 6  | 254,644                     |
| 6        | Producto 8  | 253,899                     |
| 7        | Producto 7  | 225,877                     |
| 8        | Producto 16 | 224,159                     |
| 9        | Producto 11 | 221,968                     |
| 10       | Producto 9  | 212,480                     |
| 11       | Producto 12 | 210,081                     |
| 12       | Producto 21 | 202,214                     |
| 13       | Producto 13 | 185,167                     |
| 14       | Producto 19 | 183,467                     |
| 15       | Producto 14 | 179,634                     |
| 16       | Producto 15 | 173,154                     |
| 17       | Producto 17 | 166,405                     |
| 18       | Producto 18 | 166,233                     |
| 19       | Producto 26 | 151,794                     |
| 20       | Producto 23 | 145,956                     |

#### Top 10 reglas de asociación (ordenadas por Lift)

| #   | Regla   | Soporte | Confianza | Lift      | Interpretación             |
| --- | ------- | ------- | --------- | --------- | -------------------------- |
| 1   | 98 → 51 | 0.0125  | 0.6158    | **12.57** | Asociación muy fuerte      |
| 2   | 97 → 51 | 0.0134  | 0.5947    | **12.14** | Asociación muy fuerte      |
| 3   | 76 → 53 | 0.0141  | 0.5317    | **11.76** | Asociación muy fuerte      |
| 4   | 53 → 76 | 0.0141  | 0.3112    | **11.76** | Asociación muy fuerte      |
| 5   | 51 → 62 | 0.0161  | 0.3282    | **9.35**  | Asociación fuerte          |
| 6   | 62 → 51 | 0.0161  | 0.4580    | **9.35**  | Asociación fuerte          |
| 7   | 87 → 68 | 0.0114  | 0.4495    | **7.35**  | Asociación fuerte          |
| 8   | 70 → 51 | 0.0103  | 0.3475    | **7.10**  | Asociación fuerte          |
| 9   | 51 → 68 | 0.0208  | 0.4253    | **6.95**  | Asociación moderada-fuerte |
| 10  | 68 → 51 | 0.0208  | 0.3406    | **6.95**  | Asociación moderada-fuerte |

![Reglas de asociación](results/association_rules.png)

#### Métricas explicadas

- **Soporte**: Frecuencia con la que aparecen ambos productos juntos en las transacciones
- **Confianza**: Probabilidad de comprar el producto B cuando se compra el producto A
- **Lift**: Factor multiplicador de la probabilidad
  - **Lift > 1**: Asociación positiva (los productos se compran juntos más de lo esperado)
  - **Lift = 1**: No hay asociación (independencia)
  - **Lift < 1**: Asociación negativa

#### Aplicaciones prácticas

Las reglas de asociación descubiertas pueden utilizarse para:

1. **Recomendaciones de productos**: Sugerir productos complementarios al cliente
2. **Diseño de promociones**: Crear bundles o paquetes de productos relacionados
3. **Optimización de layout**: Colocar productos asociados cerca en la tienda
4. **Gestión de inventario**: Coordinar el abastecimiento de productos complementarios
5. **Marketing dirigido**: Campañas personalizadas basadas en patrones de compra

**Ejemplo destacado**: La regla **98 → 51** tiene un lift de 12.57, lo que significa que cuando un cliente compra el Producto 98, tiene **12.57 veces más probabilidad** de comprar también el Producto 51 en comparación con la probabilidad base. Además, el 61.58% de las veces que se compra el Producto 98, también se compra el Producto 51.

### Visualizaciones generadas

El pipeline genera automáticamente las siguientes visualizaciones en formato PNG en la carpeta `results/`:

#### Análisis descriptivo básico

1. **Top productos vendidos** (`top_products.png`)

   - Gráfico de barras horizontales mostrando los 10 productos más vendidos
   - Permite identificar rápidamente los productos estrella del supermercado

2. **Ranking de tiendas** (`store_ranking.png`)

   - Gráfico de barras verticales con el número de transacciones por tienda
   - Visualiza claramente las diferencias de volumen entre tiendas

3. **Histograma de productos por transacción** (`products_histogram.png`)

   - Distribución del número de productos en cada transacción
   - Muestra el patrón típico de compra de los clientes

4. **Distribución de categorías** (`category_distribution.png`)
   - Gráfico de barras de las 10 categorías con más productos
   - Identifica las categorías más populares en el catálogo

#### Análisis temporal

5. **Serie temporal de ventas diarias** (`daily_sales_timeseries.png`)

   - Línea temporal mostrando la evolución diaria de transacciones
   - Permite detectar tendencias y patrones temporales

6. **Ventas por día de la semana** (`sales_by_day_of_week.png`)

   - Gráfico de barras comparando el volumen de ventas por cada día
   - Identifica los días de mayor y menor actividad comercial

7. **Ventas mensuales** (`monthly_sales.png`)
   - Evolución mensual del número de transacciones
   - Útil para detectar estacionalidad y tendencias de largo plazo

#### Análisis de clientes

8. **Segmentación de clientes** (`customer_segmentation.png`)
   - Gráfico circular mostrando la distribución de clientes por segmento
   - Visualiza la composición de la base de clientes

#### Análisis de productos

9. **Reglas de asociación** (`association_rules.png`)
   - Gráfico de barras horizontales con las top 10 reglas de asociación ordenadas por lift
   - Muestra las combinaciones de productos más significativas

---

## Principales Hallazgos

### Volumen de datos

- 1,108,987 transacciones analizadas
- 131,186 clientes únicos
- 112,011 productos en 50 categorías
- 4 tiendas en operación

### Comportamiento de compra

- Ticket promedio: 9.55 productos por transacción
- 8.09% de las transacciones son compras grandes (más de 25 productos)
- Clientes recurrentes regresan cada 7 días (mediana)

### Patrones temporales

- Fines de semana son los días más activos (domingo: 191,406 transacciones)
- Miércoles es el día más tranquilo (137,245 transacciones)
- Alta variabilidad diaria (±1,053 transacciones de desviación estándar)

### Segmentación de clientes

- 20.6% son clientes de alto valor (High Value)
- 69.7% son clientes regulares con potencial de crecimiento
- 10.7% tienen un patrón especializado (Frequent o Big Spender)

### Asociaciones de productos

- Se identificaron múltiples reglas de asociación con lift mayor a 10
- La regla más fuerte (98→51) tiene un lift de 12.57
- Estas asociaciones permiten estrategias de cross-selling efectivas

---

## Parámetros configurables

En el DAG se pueden ajustar los siguientes parámetros:

### Análisis de asociación

- `min_support`: Soporte mínimo para itemsets frecuentes (por defecto: 0.01)
- `min_confidence`: Confianza mínima para reglas de asociación (por defecto: 0.3)

### Segmentación de clientes

- Percentiles para segmentación (por defecto: 75% para frecuencia y valor)

### Detección de outliers

- Método IQR con factor 1.5 (configurable en la función `descriptive_stats`)

### Clustering K-Means

- **Número de clusters**: 4
- **Iteraciones máximas**: 300
- **Métricas calculadas**: Frecuencia, volumen total, promedio productos/transacción, productos distintos, diversidad de categorías, días activo, compras por día
- **Normalización**: StandardScaler (media=0, desviación=1)

### Sistema de recomendación

El proyecto implementa dos tipos de recomendaciones:

1. **Por cliente**: Basado en historial de compra y reglas de asociación
2. **Por producto**: "Los clientes que compraron X también compraron Y"

## Estructura técnica del DAG

### Dependencias

```
setup_pools → load_data → [data_review, descriptive_stats]
                        ↓
          [temporal_analysis, product_association, recommendation_system]
                        ↓
                customer_analysis
                        ↓
                 generate_plots
                        ↓
                  save_results
```

## Limpieza y mantenimiento

Para detener los contenedores:

```bash
docker compose down
```

Para limpiar volúmenes:

```bash
docker compose down --volumes --remove-orphans
```

Para limpiar archivos intermedios manualmente:

```bash
rm -rf ./data/intermediate/*
```

---

## Tecnologías utilizadas

- **Apache Airflow 2.8.1**: Orquestación de workflows
- **Python 3.8+**: Lenguaje principal
- **PostgreSQL 15**: Metadata store
- **Redis**: Message broker
- **Docker & Docker Compose**: Containerización
- **Pandas**: Manipulación de datos
- **Scikit-learn**: K-Means clustering
- **Matplotlib/Seaborn**: Visualizaciones

### Algoritmos

- **K-Means**: Segmentación de clientes
- **Apriori**: Reglas de asociación de productos
- **IQR**: Detección de outliers

---

## Documentación adicional

- `GUIA_TEORICA_COMPLETA.md`: Teoría completa para sustentación
- `OPTIMIZATION_GUIDE.md`: Detalles de optimizaciones
- `IMPLEMENTATION_REPORT.md`: Reporte técnico de implementación

---

## Autores

- Juan Manuel Marín Angarita (A00382037)
- Cristian Eduardo Botina Carpio (A00395008)
