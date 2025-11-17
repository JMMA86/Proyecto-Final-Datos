# Registro de Cambios

## Versión 2.0 - Noviembre 2025

### Correcciones aplicadas

#### Variables categóricas

Se corrigió el tratamiento de las variables `store` y `customer`, que anteriormente se procesaban como variables numéricas continuas. Estas variables son identificadores y deben tratarse como categóricas.

**Cambios implementados:**

- Conversión de `store` y `customer` a tipo string en la función `load_data`
- Eliminación de estadísticas numéricas (media, mediana, IQR) para estas variables
- Mantenimiento de frecuencias y conteos como estadísticas apropiadas para variables categóricas

### Nuevas funcionalidades

#### 1. Análisis temporal

Nueva función `temporal_analysis` que incluye:

- Agregación de ventas por día, semana y mes
- Identificación de picos de venta por día de la semana
- Cálculo de estadísticas de tendencia temporal
- Detección de patrones de estacionalidad

**Salidas generadas:**

- `temporal_analysis.txt`: Archivo de texto con resultados
- `daily_sales_timeseries.png`: Serie temporal de ventas diarias
- `sales_by_day_of_week.png`: Comparación por día de la semana
- `monthly_sales.png`: Evolución mensual

#### 2. Análisis de clientes

Nueva función `customer_analysis` que incluye:

- Cálculo de frecuencia de compra por cliente
- Tiempo promedio entre compras consecutivas
- Segmentación de clientes en cuatro grupos:
  - High Value: Alta frecuencia y alto valor
  - Frequent: Alta frecuencia
  - Big Spender: Alto valor
  - Regular: Frecuencia y valor regulares

**Salidas generadas:**

- `customer_analysis.txt`: Archivo de texto con resultados
- `customer_segmentation.png`: Gráfico circular de segmentación

#### 3. Análisis de asociación de productos

Nueva función `product_association_analysis` que implementa:

- Algoritmo Apriori para descubrimiento de reglas de asociación
- Cálculo de itemsets frecuentes con soporte mínimo 1%
- Generación de reglas con confianza mínima 30%
- Métricas: soporte, confianza y lift

**Salidas generadas:**

- `product_association.txt`: Top 20 reglas de asociación
- `association_rules.png`: Visualización de top 10 reglas por lift

### Mejoras en el flujo del DAG

#### Arquitectura actualizada

El DAG ahora tiene tres etapas:

1. **Etapa de carga y revisión**: Secuencial
   - load_data → data_review → descriptive_stats

2. **Etapa de análisis específicos**: Paralela
   - temporal_analysis
   - customer_analysis
   - product_association

3. **Etapa de visualización**: Secuencial
   - generate_plots → save_results

Esta arquitectura permite:

- Ejecución paralela de análisis independientes
- Reducción del tiempo total de procesamiento
- Mejor organización del código
- Facilidad para agregar nuevos análisis

### Archivos modificados

- `dags/dataset_analysis_dag.py`: Implementación de nuevas funciones y flujo actualizado
- `README.md`: Documentación completa de las nuevas funcionalidades
- `CHANGELOG.md`: Este archivo

### Dependencias adicionales

Las siguientes librerías se utilizan en el código actualizado:

- `numpy`: Para cálculos numéricos avanzados
- `itertools.combinations`: Para generación de pares de productos
- `collections.Counter`: Para conteo eficiente de itemsets
- `collections.defaultdict`: Para estructuras de datos auxiliares

Todas estas librerías están incluidas en la distribución estándar de Python y no requieren instalación adicional.

### Parámetros configurables

Los siguientes parámetros pueden ajustarse en el código:

#### Análisis de asociación

- `min_support = 0.01`: Soporte mínimo (1%)
- `min_confidence = 0.3`: Confianza mínima (30%)

#### Segmentación de clientes

- `freq_q75 = 0.75`: Percentil para frecuencia
- `value_q75 = 0.75`: Percentil para valor

#### Detección de outliers

- `IQR_factor = 1.5`: Factor multiplicador del rango intercuartílico

### Notas técnicas

#### Manejo de fechas

Se agregó conversión explícita de fechas a datetime en múltiples funciones para garantizar consistencia en el procesamiento temporal.

#### Optimización de memoria

El análisis de asociación procesa transacciones de forma eficiente usando Counter y estructuras nativas de Python.

#### Serialización XCom

Se utiliza formato ISO para fechas en la serialización JSON de dataframes con columnas datetime.

### Futuras mejoras sugeridas

- Implementación de análisis de cesta de mercado más avanzados
- Modelos predictivos de demanda
- Análisis de cohortes de clientes
- Detección de anomalías en patrones de compra
- Integración con sistemas de visualización externa
