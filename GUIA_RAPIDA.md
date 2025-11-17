# Guia Rapida - Nuevas Funcionalidades

## Resumen de Cambios

El DAG ha sido actualizado con tres nuevos análisis que se ejecutan en paralelo, mejorando la eficiencia y ampliando las capacidades analíticas del sistema.

## Arquitectura del DAG

```
load_data → data_review → descriptive_stats
                              ↓
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                 ↓
    temporal_analysis  customer_analysis  product_association
            └─────────────────┬─────────────────┘
                              ↓
                      generate_plots
                              ↓
                        save_results
```

## Nuevos Análisis

### 1. Análisis Temporal

**Función:** `temporal_analysis`

**Métricas calculadas:**

- Ventas diarias, semanales y mensuales
- Estadísticas por día de la semana
- Media, máximo, mínimo y desviación estándar diaria

**Salidas:**

- `temporal_analysis.txt`
- `daily_sales_timeseries.png`
- `sales_by_day_of_week.png`
- `monthly_sales.png`

**Casos de uso:**

- Identificar días de mayor demanda
- Planificar inventario según patrones semanales
- Detectar tendencias y estacionalidad

### 2. Análisis de Clientes

**Función:** `customer_analysis`

**Métricas calculadas:**

- Frecuencia de compra (media, mediana, máximo)
- Tiempo promedio entre compras
- Segmentación en 4 grupos

**Segmentos:**

- **High Value**: Top 25% en frecuencia y valor
- **Frequent**: Top 25% en frecuencia
- **Big Spender**: Top 25% en valor
- **Regular**: Resto de clientes

**Salidas:**

- `customer_analysis.txt`
- `customer_segmentation.png`

**Casos de uso:**

- Programas de fidelización
- Campañas de marketing personalizadas
- Identificación de clientes de alto valor

### 3. Análisis de Asociación de Productos

**Función:** `product_association_analysis`

**Algoritmo:** Apriori simplificado

**Parámetros:**

- Soporte mínimo: 1%
- Confianza mínima: 30%

**Métricas por regla:**

- **Support**: P(A ∩ B)
- **Confidence**: P(B|A) = P(A ∩ B) / P(A)
- **Lift**: P(B|A) / P(B)

**Interpretación del Lift:**

- Lift > 1: A y B se compran juntos más de lo esperado
- Lift = 1: A y B son independientes
- Lift < 1: A y B raramente se compran juntos

**Salidas:**

- `product_association.txt`
- `association_rules.png`

**Casos de uso:**

- Colocación estratégica de productos
- Ofertas de productos complementarios
- Recomendaciones de productos

## Corrección de Variables Categóricas

### Problema identificado

Las variables `store` y `customer` se trataban como numéricas continuas, generando estadísticas sin sentido (media de IDs de tienda, etc.).

### Solución implementada

- Conversión a tipo `string` al cargar datos
- Eliminación de estadísticas numéricas inapropiadas
- Mantención de conteos y frecuencias

### Impacto

- Estadísticas más significativas
- Mejor interpretación de resultados
- Corrección metodológica

## Variables Temporales Agregadas

Se crean automáticamente al cargar los datos:

- `year`: Año de la transacción
- `month`: Mes (1-12)
- `week`: Semana del año (1-53)
- `day_of_week`: Día de la semana (0=lunes, 6=domingo)
- `day_name`: Nombre del día en inglés

## Archivos Generados

### Antes de la actualización

- data_review.txt
- descriptive_stats.txt
- 4 gráficos PNG

### Después de la actualización

- 5 archivos TXT (se añaden 3 nuevos)
- 9 gráficos PNG (se añaden 5 nuevos)

## Tiempo de Ejecución

### Mejoras de rendimiento

La ejecución paralela de los tres análisis (temporal, clientes, asociación) reduce el tiempo total comparado con ejecución secuencial.

### Estimación de tiempos

Para el dataset actual (1.1M transacciones):

- load_data: ~30 segundos
- data_review: ~10 segundos
- descriptive_stats: ~20 segundos
- Análisis paralelos: ~40 segundos (antes serían ~120 segundos)
- generate_plots: ~30 segundos
- save_results: ~10 segundos

**Total estimado: ~2 minutos** (vs ~3.5 minutos en ejecución secuencial)

## Personalización

### Ajustar parámetros de asociación

En `product_association_analysis`:

```python
min_support = 0.01  # Cambiar para más/menos items frecuentes
min_confidence = 0.3  # Cambiar para reglas más/menos estrictas
```

### Ajustar segmentación de clientes

En `customer_analysis`:

```python
freq_q75 = customer_stats['num_purchases'].quantile(0.75)  # Cambiar 0.75
value_q75 = customer_stats['total_products'].quantile(0.75)  # Cambiar 0.75
```

### Ajustar detección de outliers

En `descriptive_stats`:

```python
outliers = transactions_expanded[
    (transactions_expanded[var] < (Q1 - 1.5 * IQR)) |  # Cambiar 1.5
    (transactions_expanded[var] > (Q3 + 1.5 * IQR))    # Cambiar 1.5
]
```

## Resolución de Problemas

### Error: "No module named 'numpy'"

Solución: Agregar numpy a las dependencias en `.env`:

```env
_PIP_ADDITIONAL_REQUIREMENTS=pandas numpy
```

### Error en fechas

Si las fechas no se parsean correctamente, verificar el formato en los CSV. El formato esperado es: `YYYY-MM-DD`

### Memoria insuficiente

Para datasets muy grandes, considerar:

- Procesar transacciones en lotes
- Aumentar memoria de contenedores Docker
- Reducir min_support en análisis de asociación

### Reglas de asociación vacías

Si no se generan reglas:

- Reducir min_support (actual: 0.01)
- Reducir min_confidence (actual: 0.3)
- Verificar que hay productos que se compran juntos

## Próximos Pasos Sugeridos

1. Ejecutar el DAG actualizado
2. Revisar los nuevos archivos de resultados
3. Analizar las visualizaciones generadas
4. Ajustar parámetros según necesidades específicas
5. Implementar acciones basadas en insights descubiertos
