from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from airflow.models import Pool
from airflow import settings
import pandas as pd
import os
import glob
import matplotlib.pyplot as plt
from itertools import combinations
from collections import defaultdict, Counter
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import seaborn as sns
import gc
import logging

# Configurar logging
logger = logging.getLogger(__name__)

DATA_DIR = "/opt/airflow/data"
DATASET_DIR = "/opt/airflow/dataset"
RESULTS_DIR = "/opt/airflow/results"

# Crear directorio para archivos intermedios
INTERMEDIATE_DIR = os.path.join(DATA_DIR, "intermediate")


def notify_failure(context):
    """
    Callback para notificar fallos en las tareas.
    """
    task_instance = context["task_instance"]
    exception = context.get("exception")
    logger.error(f"Task {task_instance.task_id} failed!")
    logger.error(f"DAG: {task_instance.dag_id}")
    logger.error(f"Execution date: {context['execution_date']}")
    logger.error(f"Exception: {exception}")
    # Aquí podrías agregar envío de emails, Slack, etc.


def notify_retry(context):
    """
    Callback para notificar reintentos.
    """
    task_instance = context["task_instance"]
    logger.warning(
        f"Task {task_instance.task_id} is being retried (attempt {task_instance.try_number})"
    )


def get_intermediate_path(run_id, filename):
    """
    Genera path para archivo intermedio.
    """
    os.makedirs(INTERMEDIATE_DIR, exist_ok=True)
    return os.path.join(INTERMEDIATE_DIR, f"{run_id}_{filename}")


def cleanup_intermediate_files(run_id):
    """
    Limpia archivos intermedios de una ejecución específica.
    """
    try:
        pattern = os.path.join(INTERMEDIATE_DIR, f"{run_id}_*")
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                logger.info(f"Removed intermediate file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def setup_pools(**context):
    """
    Configura los pools necesarios para el DAG automáticamente.
    Esta función se ejecuta al inicio y crea los pools si no existen.
    """
    try:
        session = settings.Session()

        # Configurar pool para tareas pesadas
        heavy_pool = session.query(Pool).filter(Pool.pool == "heavy_compute").first()
        if not heavy_pool:
            heavy_pool = Pool(
                pool="heavy_compute",
                slots=2,
                description="Pool for heavy compute tasks (ML, clustering, plotting)",
                include_deferred=False,
            )
            session.add(heavy_pool)
            logger.info("✓ Created pool 'heavy_compute' with 2 slots")
        else:
            heavy_pool.slots = 2
            heavy_pool.description = (
                "Pool for heavy compute tasks (ML, clustering, plotting)"
            )
            heavy_pool.include_deferred = False
            logger.info("✓ Updated pool 'heavy_compute' to 2 slots")

        # Configurar pool default
        default_pool = session.query(Pool).filter(Pool.pool == "default_pool").first()
        if not default_pool:
            default_pool = Pool(
                pool="default_pool",
                slots=8,
                description="Default pool for standard tasks",
                include_deferred=False,
            )
            session.add(default_pool)
            logger.info("✓ Created pool 'default_pool' with 8 slots")
        else:
            default_pool.slots = 8
            default_pool.description = "Default pool for standard tasks"
            default_pool.include_deferred = False
            logger.info("✓ Updated pool 'default_pool' to 8 slots")

        session.commit()
        session.close()

        logger.info("✓ Pools configured successfully")

    except Exception as e:
        logger.error(f"Error configuring pools: {e}")
        logger.warning("Pools might not be configured - tasks will use default_pool")
        if "session" in locals():
            session.rollback()
            session.close()
        # No lanzar excepción para no bloquear el DAG


default_args = {
    "owner": "Marin_Botina",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(minutes=30),
    "sla": timedelta(hours=2),
    "on_failure_callback": notify_failure,
    "on_retry_callback": notify_retry,
}


def load_data(**context):
    """
    Carga todos los archivos CSV del dataset y los guarda como archivos pickle.
    Usa archivos intermedios en lugar de XCom para evitar sobrecarga de la base de datos.
    """
    run_id = context["run_id"]

    try:
        # Validar que existan los directorios
        categories_path = os.path.join(DATASET_DIR, "Products", "Categories.csv")
        product_category_path = os.path.join(
            DATASET_DIR, "Products", "ProductCategory.csv"
        )

        if not os.path.exists(categories_path):
            raise AirflowException(f"Categories file not found: {categories_path}")
        if not os.path.exists(product_category_path):
            raise AirflowException(
                f"ProductCategory file not found: {product_category_path}"
            )

        # Cargar el dataset Categories
        logger.info(f"Loading categories from {categories_path}")
        categories_df = pd.read_csv(
            categories_path,
            sep="|",
            header=None,
            names=["category_id", "category_name"],
        )

        # Cargar el dataset ProductCategory
        logger.info(f"Loading product categories from {product_category_path}")
        product_category_df = pd.read_csv(
            product_category_path,
            sep="|",
            header=None,
            names=["product_code", "category_id"],
        )

        # Cargar el dataset Transactions (todos los csv)
        transactions_files = glob.glob(
            os.path.join(DATASET_DIR, "Transactions", "*.csv")
        )
        if not transactions_files:
            raise AirflowException(
                f"No transaction files found in {os.path.join(DATASET_DIR, 'Transactions')}"
            )

        logger.info(f"Loading {len(transactions_files)} transaction files")
        transactions_list = []
        for file in transactions_files:
            logger.info(f"Reading file: {file}")
            df = pd.read_csv(
                file,
                sep="|",
                header=None,
                names=["date", "store", "customer", "products"],
            )
            transactions_list.append(df)

        transactions_df = pd.concat(transactions_list, ignore_index=True)

        # Convertir fecha a datetime y crear variables temporales
        logger.info("Processing temporal variables")
        transactions_df["date"] = pd.to_datetime(transactions_df["date"])
        transactions_df["year"] = transactions_df["date"].dt.year
        transactions_df["month"] = transactions_df["date"].dt.month
        transactions_df["week"] = transactions_df["date"].dt.isocalendar().week
        transactions_df["day_of_week"] = transactions_df["date"].dt.dayofweek
        transactions_df["day_name"] = transactions_df["date"].dt.day_name()

        # Convertir store y customer a categóricas (son IDs, no variables numéricas continuas)
        transactions_df["store"] = transactions_df["store"].astype(str)
        transactions_df["customer"] = transactions_df["customer"].astype(str)

        # Guardar en archivos pickle (en lugar de XCom)
        categories_file = get_intermediate_path(run_id, "categories.pkl")
        product_category_file = get_intermediate_path(run_id, "product_category.pkl")
        transactions_file = get_intermediate_path(run_id, "transactions.pkl")

        logger.info(f"Saving intermediate files to {INTERMEDIATE_DIR}")
        categories_df.to_pickle(categories_file)
        product_category_df.to_pickle(product_category_file)
        transactions_df.to_pickle(transactions_file)

        # Guardar solo los paths en XCom (ligero)
        context["ti"].xcom_push(key="categories_file", value=categories_file)
        context["ti"].xcom_push(
            key="product_category_file", value=product_category_file
        )
        context["ti"].xcom_push(key="transactions_file", value=transactions_file)

        logger.info(
            f"✓ Loaded {len(categories_df)} categories, {len(product_category_df)} product categories, {len(transactions_df)} transactions"
        )

        # Liberar memoria
        del categories_df, product_category_df, transactions_df, transactions_list
        gc.collect()

    except Exception as e:
        logger.error(f"Error in load_data: {e}")
        raise


def data_review(**context):
    """
    Realiza revisión inicial del dataset: estructura, tipos, nulos, duplicados.
    Carga datos desde archivos pickle en lugar de XCom.
    """
    try:
        # Obtener paths desde XCom
        categories_file = context["ti"].xcom_pull(key="categories_file")
        product_category_file = context["ti"].xcom_pull(key="product_category_file")
        transactions_file = context["ti"].xcom_pull(key="transactions_file")

        # Cargar desde pickle
        logger.info("Loading data from intermediate files")
        categories_df = pd.read_pickle(categories_file)
        product_category_df = pd.read_pickle(product_category_file)
        transactions_df = pd.read_pickle(transactions_file)

        review_results = {}

        # Categories
        review_results["categories"] = {
            "num_records": len(categories_df),
            "num_columns": len(categories_df.columns),
            "columns": categories_df.columns.tolist(),
            "dtypes": {k: str(v) for k, v in categories_df.dtypes.to_dict().items()},
            "nulls": categories_df.isnull().sum().to_dict(),
            "duplicates": int(categories_df.duplicated().sum()),
        }

        # ProductCategory
        review_results["product_category"] = {
            "num_records": len(product_category_df),
            "num_columns": len(product_category_df.columns),
            "columns": product_category_df.columns.tolist(),
            "dtypes": {
                k: str(v) for k, v in product_category_df.dtypes.to_dict().items()
            },
            "nulls": product_category_df.isnull().sum().to_dict(),
            "duplicates": int(product_category_df.duplicated().sum()),
        }

        # Transactions
        review_results["transactions"] = {
            "num_records": len(transactions_df),
            "num_columns": len(transactions_df.columns),
            "columns": transactions_df.columns.tolist(),
            "dtypes": {k: str(v) for k, v in transactions_df.dtypes.to_dict().items()},
            "nulls": transactions_df.isnull().sum().to_dict(),
            "duplicates": int(transactions_df.duplicated().sum()),
        }

        # Imprimir resultados en consola (para logs)
        for table, stats in review_results.items():
            logger.info(f"\n=== {table.upper()} ===")
            for key, value in stats.items():
                logger.info(f"{key}: {value}")

        # Guardar resultados en archivo pickle
        run_id = context["run_id"]
        review_file = get_intermediate_path(run_id, "review_results.pkl")
        pd.to_pickle(review_results, review_file)
        context["ti"].xcom_push(key="review_file", value=review_file)

        # Liberar memoria
        del categories_df, product_category_df, transactions_df
        gc.collect()

    except Exception as e:
        logger.error(f"Error in data_review: {e}")
        raise


def descriptive_stats(**context):
    """
    Calcula estadísticas descriptivas.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener paths desde XCom
        categories_file = context["ti"].xcom_pull(key="categories_file")
        product_category_file = context["ti"].xcom_pull(key="product_category_file")
        transactions_file = context["ti"].xcom_pull(key="transactions_file")

        # Cargar desde pickle
        logger.info("Loading data from intermediate files")
        categories_df = pd.read_pickle(categories_file)
        product_category_df = pd.read_pickle(product_category_file)
        transactions_df = pd.read_pickle(transactions_file)

        stats_results = {}

        # Para Transactions: expandir productos y calcular estadísticas
        transactions_expanded = transactions_df.copy()
        transactions_expanded["num_products"] = (
            transactions_expanded["products"].str.split().str.len()
        )

        # Estadísticas numéricas solo para num_products (store y customer son categóricas)
        numeric_vars = ["num_products"]
        stats_results["numeric"] = {}
        for var in numeric_vars:
            desc = transactions_expanded[[var]].describe(percentiles=[0.25, 0.5, 0.75])
            mode = transactions_expanded[var].mode().tolist()
            stats_results["numeric"][var] = {"describe": desc.to_dict(), "mode": mode}

        # Detectar outliers usando IQR para num_products
        stats_results["outliers"] = {}
        for var in numeric_vars:
            Q1 = transactions_expanded[var].quantile(0.25)
            Q3 = transactions_expanded[var].quantile(0.75)
            IQR = Q3 - Q1
            outliers = transactions_expanded[
                (transactions_expanded[var] < (Q1 - 1.5 * IQR))
                | (transactions_expanded[var] > (Q3 + 1.5 * IQR))
            ]
            stats_results["outliers"][var] = {
                "count": int(len(outliers)),
                "min_outlier": (
                    float(outliers[var].min()) if len(outliers) > 0 else None
                ),
                "max_outlier": (
                    float(outliers[var].max()) if len(outliers) > 0 else None
                ),
            }

        # Estadísticas categóricas (categorías)
        category_counts = product_category_df["category_id"].value_counts()
        category_freq = (category_counts / len(product_category_df) * 100).round(2)
        stats_results["categorical"] = {
            "category_counts": category_counts.to_dict(),
            "category_frequencies": category_freq.to_dict(),
        }

        # Frecuencia de productos (top 20)
        all_products = []
        for products in transactions_df["products"]:
            all_products.extend(products.split())
        product_counts = pd.Series(all_products).value_counts()
        stats_results["product_frequencies"] = product_counts.head(20).to_dict()

        # Frecuencias para store (ahora categórica)
        store_counts = transactions_df["store"].value_counts()
        store_freq = (store_counts / len(transactions_df) * 100).round(2)
        stats_results["store_frequencies"] = {
            "counts": store_counts.to_dict(),
            "frequencies": store_freq.to_dict(),
        }

        # Imprimir resultados
        logger.info("\n=== ESTADÍSTICAS NUMÉRICAS ===")
        for var, stats in stats_results["numeric"].items():
            logger.info(f"\n--- {var.upper()} ---")
            desc_df = pd.DataFrame(stats["describe"])
            logger.info(desc_df)
            logger.info(f"Moda: {stats['mode']}")
            logger.info(f"Outliers: {stats_results['outliers'][var]}")

        logger.info("\n=== ESTADÍSTICAS CATEGÓRICAS ===")
        logger.info("Top categorías:")
        for cat, count in list(category_counts.items())[:10]:
            logger.info(f"Categoría {cat}: {count} productos ({category_freq[cat]}%)")

        logger.info("\nTop productos:")
        for prod, count in list(product_counts.items())[:10]:
            logger.info(f"Producto {prod}: {count} veces")

        logger.info("\nTop stores:")
        for store, count in list(store_counts.items())[:10]:
            logger.info(f"Store {store}: {count} transacciones ({store_freq[store]}%)")

        # Guardar resultados en archivo pickle
        run_id = context["run_id"]
        stats_file = get_intermediate_path(run_id, "stats_results.pkl")
        pd.to_pickle(stats_results, stats_file)
        context["ti"].xcom_push(key="stats_file", value=stats_file)

        # Liberar memoria
        del categories_df, product_category_df, transactions_df
        gc.collect()

    except Exception as e:
        logger.error(f"Error in descriptive_stats: {e}")
        raise


def temporal_analysis(**context):
    """
    Analiza patrones temporales en las ventas.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener path desde XCom
        transactions_file = context["ti"].xcom_pull(key="transactions_file")

        # Cargar desde pickle
        logger.info("Loading transactions from intermediate file")
        transactions_df = pd.read_pickle(transactions_file)

        transactions_df["num_products"] = (
            transactions_df["products"].str.split().str.len()
        )

        temporal_results = {}

        # Ventas diarias
        daily_sales = (
            transactions_df.groupby("date")
            .agg({"customer": "count", "num_products": "sum"})
            .rename(
                columns={
                    "customer": "num_transactions",
                    "num_products": "total_products",
                }
            )
        )
        temporal_results["daily_sales"] = {
            str(k): v for k, v in daily_sales.to_dict("index").items()
        }

        # Ventas semanales
        weekly_sales = (
            transactions_df.groupby(["year", "week"])
            .agg({"customer": "count", "num_products": "sum"})
            .rename(
                columns={
                    "customer": "num_transactions",
                    "num_products": "total_products",
                }
            )
        )
        temporal_results["weekly_sales"] = {
            str(k): v for k, v in weekly_sales.to_dict("index").items()
        }

        # Ventas mensuales
        monthly_sales = (
            transactions_df.groupby(["year", "month"])
            .agg({"customer": "count", "num_products": "sum"})
            .rename(
                columns={
                    "customer": "num_transactions",
                    "num_products": "total_products",
                }
            )
        )
        temporal_results["monthly_sales"] = {
            str(k): v for k, v in monthly_sales.to_dict("index").items()
        }

        # Ventas por día de la semana
        day_of_week_sales = (
            transactions_df.groupby("day_name")
            .agg({"customer": "count", "num_products": "sum"})
            .rename(
                columns={
                    "customer": "num_transactions",
                    "num_products": "total_products",
                }
            )
        )
        day_order = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        day_of_week_sales = day_of_week_sales.reindex(day_order)
        temporal_results["day_of_week_sales"] = day_of_week_sales.to_dict("index")

        # Estadísticas de tendencia
        daily_sales_stats = {
            "mean_daily_transactions": float(daily_sales["num_transactions"].mean()),
            "max_daily_transactions": int(daily_sales["num_transactions"].max()),
            "min_daily_transactions": int(daily_sales["num_transactions"].min()),
            "std_daily_transactions": float(daily_sales["num_transactions"].std()),
        }
        temporal_results["daily_stats"] = daily_sales_stats

        logger.info("\n=== ANÁLISIS TEMPORAL ===")
        logger.info(f"\nEstadísticas diarias:")
        logger.info(
            f"Media de transacciones diarias: {daily_sales_stats['mean_daily_transactions']:.2f}"
        )
        logger.info(
            f"Máximo de transacciones en un día: {daily_sales_stats['max_daily_transactions']}"
        )
        logger.info(
            f"Mínimo de transacciones en un día: {daily_sales_stats['min_daily_transactions']}"
        )

        logger.info(f"\nVentas por día de la semana:")
        for day, stats in day_of_week_sales.iterrows():
            logger.info(
                f"{day}: {stats['num_transactions']} transacciones, {stats['total_products']} productos"
            )

        # Guardar resultados en archivo pickle
        run_id = context["run_id"]
        temporal_file = get_intermediate_path(run_id, "temporal_results.pkl")
        pd.to_pickle(temporal_results, temporal_file)
        context["ti"].xcom_push(key="temporal_file", value=temporal_file)

        # Liberar memoria
        del transactions_df
        gc.collect()

    except Exception as e:
        logger.error(f"Error in temporal_analysis: {e}")
        raise


def customer_analysis(**context):
    """
    Analiza patrones de comportamiento de clientes y realiza clustering con K-Means.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener paths desde XCom
        transactions_file = context["ti"].xcom_pull(key="transactions_file")
        product_category_file = context["ti"].xcom_pull(key="product_category_file")

        # Cargar desde pickle
        logger.info("Loading data from intermediate files")
        transactions_df = pd.read_pickle(transactions_file)
        product_category_df = pd.read_pickle(product_category_file)

        transactions_df["num_products"] = (
            transactions_df["products"].str.split().str.len()
        )

        customer_results = {}

        # Frecuencia de compra por cliente
        logger.info("Calculating purchase frequency...")
        customer_freq = transactions_df.groupby("customer").size()
        customer_results["purchase_frequency"] = {
            "mean": float(customer_freq.mean()),
            "median": float(customer_freq.median()),
            "std": float(customer_freq.std()),
            "max": int(customer_freq.max()),
            "min": int(customer_freq.min()),
        }

        # Tiempo promedio entre compras
        logger.info("Calculating time between purchases...")
        customer_dates = transactions_df.groupby("customer")["date"].apply(
            lambda x: x.sort_values().tolist()
        )
        time_between_purchases = []
        for customer, dates in customer_dates.items():
            if isinstance(dates, list) and len(dates) > 1:
                for i in range(1, len(dates)):
                    diff = (dates[i] - dates[i - 1]).days
                    time_between_purchases.append(diff)

        if time_between_purchases:
            customer_results["time_between_purchases"] = {
                "mean_days": float(np.mean(time_between_purchases)),
                "median_days": float(np.median(time_between_purchases)),
                "std_days": float(np.std(time_between_purchases)),
            }
        else:
            customer_results["time_between_purchases"] = None

        # === CLUSTERING K-MEANS ===
        logger.info("Starting K-Means clustering preparation...")
        # Preparar características para clustering

        # 1. Frecuencia: número de transacciones por cliente
        logger.info("Aggregating customer features...")
        customer_features = (
            transactions_df.groupby("customer")
            .agg(
                {"date": "count", "num_products": "sum"}  # Frecuencia  # Volumen total
            )
            .rename(columns={"date": "frequency", "num_products": "total_volume"})
        )

        # 2. Número de productos distintos por cliente (optimizado)
        logger.info("Calculating distinct products per customer...")

        def count_distinct_products(products_series):
            all_products = set()
            for products_str in products_series:
                all_products.update(products_str.split())
            return len(all_products)

        customer_features["distinct_products"] = transactions_df.groupby("customer")[
            "products"
        ].apply(count_distinct_products)

        # 3. Diversidad de categorías (número de categorías distintas compradas) (optimizado)
        logger.info("Calculating category diversity per customer...")
        product_to_category = product_category_df.set_index("product_code")[
            "category_id"
        ].to_dict()

        def count_category_diversity(products_series):
            all_categories = set()
            for products_str in products_series:
                for product in products_str.split():
                    if product in product_to_category:
                        all_categories.add(product_to_category[product])
            return len(all_categories)

        customer_features["category_diversity"] = transactions_df.groupby("customer")[
            "products"
        ].apply(count_category_diversity)

        # 4. Promedio de productos por transacción
        logger.info("Calculating average products per transaction...")
        customer_features["avg_products_per_transaction"] = (
            customer_features["total_volume"] / customer_features["frequency"]
        ).round(2)

        # Normalizar características para K-Means (ahora con 5 características)
        logger.info("Scaling features for K-Means (5 features)...")
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(customer_features)

        # Aplicar K-Means con 4 clusters
        logger.info("Running K-Means clustering (4 clusters)...")
        n_clusters = 4
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10, max_iter=300)
        customer_features["cluster"] = kmeans.fit_predict(features_scaled)
        logger.info(f"K-Means completed. Inertia: {kmeans.inertia_:.2f}")

        # Analizar características de cada cluster
        cluster_profiles = (
            customer_features.groupby("cluster")
            .agg(
                {
                    "frequency": ["mean", "median"],
                    "total_volume": ["mean", "median"],
                    "distinct_products": ["mean", "median"],
                    "category_diversity": ["mean", "median"],
                    "avg_products_per_transaction": ["mean", "median"],
                }
            )
            .round(2)
        )

        cluster_sizes = customer_features["cluster"].value_counts().sort_index()

        # Asignar nombres descriptivos a los clusters basados en sus características
        cluster_names = {}
        cluster_descriptions = {}

        for cluster_id in range(n_clusters):
            cluster_data = customer_features[customer_features["cluster"] == cluster_id]
            avg_freq = cluster_data["frequency"].mean()
            avg_volume = cluster_data["total_volume"].mean()
            avg_distinct = cluster_data["distinct_products"].mean()

            # Lógica para nombrar clusters
            if avg_freq > customer_features["frequency"].quantile(0.75):
                if avg_volume > customer_features["total_volume"].quantile(0.75):
                    cluster_names[cluster_id] = "VIP - Alto Valor"
                    cluster_descriptions[cluster_id] = (
                        "Clientes frecuentes con alto volumen de compra"
                    )
                else:
                    cluster_names[cluster_id] = "Frecuentes"
                    cluster_descriptions[cluster_id] = (
                        "Clientes que compran frecuentemente pero en pequeñas cantidades"
                    )
            elif avg_volume > customer_features["total_volume"].quantile(0.75):
                cluster_names[cluster_id] = "Gran Comprador"
                cluster_descriptions[cluster_id] = (
                    "Clientes que compran en grandes volúmenes pero con baja frecuencia"
                )
            else:
                cluster_names[cluster_id] = "Ocasional"
                cluster_descriptions[cluster_id] = (
                    "Clientes con baja frecuencia y volumen moderado"
                )

        # Guardar resultados de clustering
        customer_results["clustering"] = {
            "n_clusters": n_clusters,
            "cluster_sizes": {
                cluster_names[k]: int(v) for k, v in cluster_sizes.items()
            },
            "cluster_profiles": {
                cluster_names[cluster_id]: {
                    "size": int(cluster_sizes[cluster_id]),
                    "description": cluster_descriptions[cluster_id],
                    "avg_frequency": float(
                        cluster_profiles.loc[cluster_id, ("frequency", "mean")]
                    ),
                    "avg_total_volume": float(
                        cluster_profiles.loc[cluster_id, ("total_volume", "mean")]
                    ),
                    "avg_distinct_products": float(
                        cluster_profiles.loc[cluster_id, ("distinct_products", "mean")]
                    ),
                    "avg_category_diversity": float(
                        cluster_profiles.loc[cluster_id, ("category_diversity", "mean")]
                    ),
                    "avg_products_per_transaction": float(
                        cluster_profiles.loc[cluster_id, ("avg_products_per_transaction", "mean")]
                    ),
                }
                for cluster_id in range(n_clusters)
            },
        }

        # Guardar DataFrame con clusters en archivo separado
        customer_features["cluster_name"] = customer_features["cluster"].map(
            cluster_names
        )
        run_id = context["run_id"]
        clusters_file = get_intermediate_path(run_id, "customer_clusters.pkl")
        customer_features.to_pickle(clusters_file)
        context["ti"].xcom_push(key="clusters_file", value=clusters_file)

        logger.info("\n=== ANÁLISIS DE CLIENTES ===")
        logger.info(f"\nFrecuencia de compra:")
        logger.info(
            f"Promedio de compras por cliente: {customer_results['purchase_frequency']['mean']:.2f}"
        )
        logger.info(
            f"Mediana de compras por cliente: {customer_results['purchase_frequency']['median']:.2f}"
        )
        logger.info(
            f"Máximo de compras de un cliente: {customer_results['purchase_frequency']['max']}"
        )

        if customer_results["time_between_purchases"]:
            logger.info(f"\nTiempo entre compras:")
            logger.info(
                f"Promedio: {customer_results['time_between_purchases']['mean_days']:.2f} días"
            )
            logger.info(
                f"Mediana: {customer_results['time_between_purchases']['median_days']:.2f} días"
            )

        logger.info(f"\n=== CLUSTERING K-MEANS (5 características) ===")
        logger.info(f"Número de clusters: {n_clusters}")
        for cluster_name, profile in customer_results["clustering"][
            "cluster_profiles"
        ].items():
            logger.info(f"\n{cluster_name} (n={profile['size']}):")
            logger.info(f"  {profile['description']}")
            logger.info(f"  Frecuencia promedio: {profile['avg_frequency']:.2f}")
            logger.info(f"  Volumen total promedio: {profile['avg_total_volume']:.2f}")
            logger.info(
                f"  Productos distintos promedio: {profile['avg_distinct_products']:.2f}"
            )
            logger.info(
                f"  Diversidad de categorías promedio: {profile['avg_category_diversity']:.2f}"
            )
            logger.info(
                f"  Promedio prod/trans: {profile['avg_products_per_transaction']:.2f}"
            )

        # Guardar resultados en archivo pickle
        customer_file = get_intermediate_path(run_id, "customer_results.pkl")
        pd.to_pickle(customer_results, customer_file)
        context["ti"].xcom_push(key="customer_file", value=customer_file)

        # Liberar memoria
        del transactions_df, product_category_df, customer_features
        gc.collect()

    except Exception as e:
        logger.error(f"Error in customer_analysis: {e}")
        raise


def recommendation_system(**context):
    """
    Sistema de recomendación basado en reglas de asociación.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener paths desde XCom
        transactions_file = context["ti"].xcom_pull(key="transactions_file")
        association_file = context["ti"].xcom_pull(key="association_file")

        # Cargar desde pickle
        logger.info("Loading data from intermediate files")
        transactions_df = pd.read_pickle(transactions_file)
        association_results = pd.read_pickle(association_file)

        recommendation_results = {}

        # Crear estructura de reglas para búsqueda rápida
        # Diccionario: producto -> lista de productos recomendados con sus métricas
        product_recommendations = defaultdict(list)

        for rule in association_results["top_rules"]:
            antecedent = rule["antecedent"]
            consequent = rule["consequent"]
            product_recommendations[antecedent].append(
                {
                    "product": consequent,
                    "confidence": rule["confidence"],
                    "lift": rule["lift"],
                    "support": rule["support"],
                }
            )

        # Ordenar recomendaciones por lift
        for product in product_recommendations:
            product_recommendations[product] = sorted(
                product_recommendations[product], key=lambda x: x["lift"], reverse=True
            )

        # Función 1: Recomendar para un cliente específico
        def recommend_for_customer(customer_id, top_n=5):
            """
            Dado un cliente, recomendar productos basados en su historial.
            """
            # Obtener productos que el cliente ya compró
            customer_trans = transactions_df[transactions_df["customer"] == customer_id]
            if customer_trans.empty:
                return []

            customer_products = set()
            for products_str in customer_trans["products"]:
                customer_products.update(products_str.split())

            # Buscar recomendaciones basadas en productos comprados
            recommendations_dict = {}
            for product in customer_products:
                if product in product_recommendations:
                    for rec in product_recommendations[product]:
                        rec_product = rec["product"]
                        # No recomendar productos que ya compró
                        if rec_product not in customer_products:
                            if rec_product not in recommendations_dict:
                                recommendations_dict[rec_product] = {
                                    "score": 0,
                                    "count": 0,
                                    "avg_confidence": 0,
                                    "avg_lift": 0,
                                }
                            recommendations_dict[rec_product]["score"] += rec["lift"]
                            recommendations_dict[rec_product]["count"] += 1
                            recommendations_dict[rec_product]["avg_confidence"] += rec[
                                "confidence"
                            ]
                            recommendations_dict[rec_product]["avg_lift"] += rec["lift"]

            # Promediar métricas
            for prod in recommendations_dict:
                count = recommendations_dict[prod]["count"]
                recommendations_dict[prod]["avg_confidence"] /= count
                recommendations_dict[prod]["avg_lift"] /= count

            # Ordenar por score y tomar top N
            sorted_recs = sorted(
                recommendations_dict.items(), key=lambda x: x[1]["score"], reverse=True
            )[:top_n]

            return [(prod, data) for prod, data in sorted_recs]

        # Función 2: Recomendar para un producto específico
        def recommend_for_product(product_id, top_n=5):
            """
            Dado un producto, recomendar productos que suelen comprarse juntos.
            """
            if product_id not in product_recommendations:
                return []

            recommendations = product_recommendations[product_id][:top_n]
            return [(rec["product"], rec) for rec in recommendations]

        # Ejemplo: Generar recomendaciones para los top 10 clientes más frecuentes
        customer_freq = (
            transactions_df.groupby("customer").size().sort_values(ascending=False)
        )
        top_customers = customer_freq.head(10).index.tolist()

        customer_recommendations_examples = {}
        for customer in top_customers:
            recs = recommend_for_customer(customer, top_n=5)
            if recs:
                customer_recommendations_examples[customer] = [
                    {
                        "product": prod,
                        "score": float(data["score"]),
                        "avg_confidence": float(data["avg_confidence"]),
                        "avg_lift": float(data["avg_lift"]),
                    }
                    for prod, data in recs
                ]

        recommendation_results["customer_recommendations_examples"] = (
            customer_recommendations_examples
        )

        # Ejemplo: Generar recomendaciones para los top 10 productos más vendidos
        all_products = []
        for products in transactions_df["products"]:
            all_products.extend(products.split())
        product_counts = Counter(all_products)
        top_products = [prod for prod, count in product_counts.most_common(20)]

        product_recommendations_examples = {}
        for product in top_products:
            recs = recommend_for_product(product, top_n=5)
            if recs:
                product_recommendations_examples[product] = [
                    {
                        "product": rec_prod,
                        "confidence": float(data["confidence"]),
                        "lift": float(data["lift"]),
                        "support": float(data["support"]),
                    }
                    for rec_prod, data in recs
                ]

        recommendation_results["product_recommendations_examples"] = (
            product_recommendations_examples
        )

        logger.info("\n=== SISTEMA DE RECOMENDACIÓN ===")
        logger.info(
            f"\nRecomendaciones generadas para {len(customer_recommendations_examples)} clientes"
        )
        logger.info(
            f"Recomendaciones generadas para {len(product_recommendations_examples)} productos"
        )

        # Mostrar algunos ejemplos
        logger.info("\nEjemplo de recomendaciones para clientes:")
        for i, (customer, recs) in enumerate(
            list(customer_recommendations_examples.items())[:3], 1
        ):
            logger.info(f"\n  Cliente {customer}:")
            for rec in recs[:3]:
                logger.info(
                    f"    - Producto {rec['product']} (Score: {rec['score']:.2f}, Lift: {rec['avg_lift']:.2f})"
                )

        logger.info("\nEjemplo de recomendaciones para productos:")
        for i, (product, recs) in enumerate(
            list(product_recommendations_examples.items())[:3], 1
        ):
            logger.info(f"\n  Producto {product}:")
            for rec in recs[:3]:
                logger.info(
                    f"    - Producto {rec['product']} (Lift: {rec['lift']:.2f}, Confidence: {rec['confidence']:.2f})"
                )

        # Guardar resultados en archivo pickle
        run_id = context["run_id"]
        recommendation_file = get_intermediate_path(
            run_id, "recommendation_results.pkl"
        )
        pd.to_pickle(recommendation_results, recommendation_file)
        context["ti"].xcom_push(key="recommendation_file", value=recommendation_file)

        # Liberar memoria
        del transactions_df, association_results
        gc.collect()

    except Exception as e:
        logger.error(f"Error in recommendation_system: {e}")
        raise


def product_association_analysis(**context):
    """
    Analiza reglas de asociación entre productos usando el algoritmo Apriori.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener path desde XCom
        transactions_file = context["ti"].xcom_pull(key="transactions_file")

        # Cargar desde pickle
        logger.info("Loading transactions from intermediate file")
        transactions_df = pd.read_pickle(transactions_file)

        # Convertir transacciones a lista de listas de productos
        transactions_list = []
        for products_str in transactions_df["products"]:
            products = products_str.split()
            transactions_list.append(products)

        # Parámetros para Apriori
        min_support = 0.01  # 1% de las transacciones
        min_confidence = 0.3  # 30% de confianza

        association_results = {}

        # Calcular frecuencia de itemsets individuales
        item_counts = Counter()
        for transaction in transactions_list:
            for item in set(transaction):
                item_counts[item] += 1

        total_transactions = len(transactions_list)
        frequent_items = {
            item: count
            for item, count in item_counts.items()
            if count / total_transactions >= min_support
        }

        association_results["frequent_items"] = {
            k: int(v)
            for k, v in sorted(
                frequent_items.items(), key=lambda x: x[1], reverse=True
            )[:20]
        }

        # Calcular pares frecuentes
        pair_counts = Counter()
        for transaction in transactions_list:
            items = list(set(transaction))
            for pair in combinations(sorted(items), 2):
                pair_counts[pair] += 1

        frequent_pairs = {
            pair: count
            for pair, count in pair_counts.items()
            if count / total_transactions >= min_support
        }

        # Calcular reglas de asociación
        rules = []
        for (item_a, item_b), count_ab in frequent_pairs.items():
            support_ab = count_ab / total_transactions
            support_a = item_counts[item_a] / total_transactions
            support_b = item_counts[item_b] / total_transactions

            # Regla A -> B
            confidence_ab = count_ab / item_counts[item_a]
            lift_ab = confidence_ab / support_b

            if confidence_ab >= min_confidence:
                rules.append(
                    {
                        "antecedent": item_a,
                        "consequent": item_b,
                        "support": float(support_ab),
                        "confidence": float(confidence_ab),
                        "lift": float(lift_ab),
                    }
                )

            # Regla B -> A
            confidence_ba = count_ab / item_counts[item_b]
            lift_ba = confidence_ba / support_a

            if confidence_ba >= min_confidence:
                rules.append(
                    {
                        "antecedent": item_b,
                        "consequent": item_a,
                        "support": float(support_ab),
                        "confidence": float(confidence_ba),
                        "lift": float(lift_ba),
                    }
                )

        # Ordenar por lift y tomar las top 20
        rules_sorted = sorted(rules, key=lambda x: x["lift"], reverse=True)[:20]
        association_results["top_rules"] = rules_sorted

        logger.info("\n=== ANÁLISIS DE ASOCIACIÓN DE PRODUCTOS ===")
        logger.info(f"\nTotal de transacciones: {total_transactions}")
        logger.info(f"Items frecuentes encontrados: {len(frequent_items)}")
        logger.info(f"Pares frecuentes encontrados: {len(frequent_pairs)}")
        logger.info(f"Reglas generadas: {len(rules)}")

        logger.info(f"\nTop 10 reglas de asociación (ordenadas por lift):")
        for i, rule in enumerate(rules_sorted[:10], 1):
            logger.info(
                f"{i}. {rule['antecedent']} -> {rule['consequent']}: "
                f"Support={rule['support']:.4f}, "
                f"Confidence={rule['confidence']:.4f}, "
                f"Lift={rule['lift']:.4f}"
            )

        # Guardar resultados en archivo pickle
        run_id = context["run_id"]
        association_file = get_intermediate_path(run_id, "association_results.pkl")
        pd.to_pickle(association_results, association_file)
        context["ti"].xcom_push(key="association_file", value=association_file)

        # Liberar memoria
        del transactions_df, transactions_list
        gc.collect()

    except Exception as e:
        logger.error(f"Error in product_association_analysis: {e}")
        raise


def generate_plots(**context):
    """
    Genera gráficas basadas en las estadísticas calculadas.
    Carga datos desde archivos pickle y libera memoria después de cada gráfico.
    """
    try:
        # Obtener paths desde XCom
        categories_file = context["ti"].xcom_pull(key="categories_file")
        product_category_file = context["ti"].xcom_pull(key="product_category_file")
        transactions_file = context["ti"].xcom_pull(key="transactions_file")
        stats_file = context["ti"].xcom_pull(key="stats_file")
        temporal_file = context["ti"].xcom_pull(key="temporal_file")
        customer_file = context["ti"].xcom_pull(key="customer_file")
        association_file = context["ti"].xcom_pull(key="association_file")
        clusters_file = context["ti"].xcom_pull(key="clusters_file")

        # Cargar desde pickle
        logger.info("Loading data from intermediate files")
        categories_df = pd.read_pickle(categories_file)
        product_category_df = pd.read_pickle(product_category_file)
        transactions_df = pd.read_pickle(transactions_file)
        stats_results = pd.read_pickle(stats_file)
        temporal_results = pd.read_pickle(temporal_file)
        customer_results = pd.read_pickle(customer_file)
        association_results = pd.read_pickle(association_file)

        os.makedirs(RESULTS_DIR, exist_ok=True)

        logger.info("Starting plot generation (15 plots total)")

        # Gráficas originales

        # 1. Top productos vendidos
        logger.info("Generating plot 1/14: Top products")
        product_counts = pd.Series(stats_results["product_frequencies"]).head(10)
        plt.figure(figsize=(10, 6))
        product_counts.plot(kind="barh", color="skyblue")
        plt.title("Top 10 Productos Mas Vendidos")
        plt.xlabel("Numero de Ventas")
        plt.ylabel("Producto")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "top_products.png"), dpi=100, bbox_inches="tight"
        )
        plt.close("all")
        gc.collect()

        # 2. Ranking de tiendas
        logger.info("Generating plot 2/14: Store ranking")
        store_counts = pd.Series(stats_results["store_frequencies"]["counts"])
        plt.figure(figsize=(8, 6))
        store_counts.plot(kind="bar", color="lightgreen")
        plt.title("Ranking de Tiendas por Numero de Transacciones")
        plt.xlabel("Tienda")
        plt.ylabel("Numero de Transacciones")
        plt.xticks(rotation=0)
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "store_ranking.png"), dpi=100, bbox_inches="tight"
        )
        plt.close("all")
        gc.collect()

        # 3. Histograma de número de productos por transacción
        logger.info("Generating plot 3/14: Products histogram")
        transactions_expanded = transactions_df.copy()
        transactions_expanded["num_products"] = (
            transactions_expanded["products"].str.split().str.len()
        )
        plt.figure(figsize=(10, 6))
        plt.hist(
            transactions_expanded["num_products"], bins=30, edgecolor="black", alpha=0.7
        )
        plt.title("Distribucion del Numero de Productos por Transaccion")
        plt.xlabel("Numero de Productos")
        plt.ylabel("Frecuencia")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "products_histogram.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        del transactions_expanded
        gc.collect()

        # 4. Distribución de categorías
        logger.info("Generating plot 4/14: Category distribution")
        category_id_to_name = categories_df.set_index("category_id")[
            "category_name"
        ].to_dict()
        category_counts = pd.Series(stats_results["categorical"]["category_counts"])
        category_counts_named = category_counts.rename(index=category_id_to_name).head(
            10
        )
        plt.figure(figsize=(12, 6))
        category_counts_named.plot(kind="bar", color="coral")
        plt.title("Top 10 Categorias por Numero de Productos")
        plt.xlabel("Categoria")
        plt.ylabel("Numero de Productos")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "category_distribution.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # Nuevas gráficas de análisis temporal

        # 5. Ventas diarias (serie temporal)
        logger.info("Generating plot 5/14: Daily sales timeseries")
        daily_sales_df = pd.DataFrame(temporal_results["daily_sales"]).T
        daily_sales_df.index = pd.to_datetime(daily_sales_df.index)
        plt.figure(figsize=(14, 6))
        plt.plot(daily_sales_df.index, daily_sales_df["num_transactions"], linewidth=1)
        plt.title("Serie Temporal de Transacciones Diarias")
        plt.xlabel("Fecha")
        plt.ylabel("Numero de Transacciones")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "daily_sales_timeseries.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # 6. Ventas por día de la semana
        logger.info("Generating plot 6/14: Sales by day of week")
        day_of_week_df = pd.DataFrame(temporal_results["day_of_week_sales"]).T
        plt.figure(figsize=(10, 6))
        day_of_week_df["num_transactions"].plot(kind="bar", color="steelblue")
        plt.title("Transacciones por Dia de la Semana")
        plt.xlabel("Dia de la Semana")
        plt.ylabel("Numero de Transacciones")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "sales_by_day_of_week.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # 7. Ventas mensuales
        logger.info("Generating plot 7/14: Monthly sales")
        monthly_sales_list = []
        for key, value in temporal_results["monthly_sales"].items():
            year, month = eval(key)
            monthly_sales_list.append(
                {
                    "year": year,
                    "month": month,
                    "num_transactions": value["num_transactions"],
                }
            )
        monthly_sales_df = pd.DataFrame(monthly_sales_list)
        monthly_sales_df["date"] = pd.to_datetime(
            monthly_sales_df[["year", "month"]].assign(day=1)
        )
        monthly_sales_df = monthly_sales_df.sort_values("date")

        plt.figure(figsize=(12, 6))
        plt.plot(
            monthly_sales_df["date"],
            monthly_sales_df["num_transactions"],
            marker="o",
            linewidth=2,
        )
        plt.title("Ventas Mensuales")
        plt.xlabel("Mes")
        plt.ylabel("Numero de Transacciones")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "monthly_sales.png"), dpi=100, bbox_inches="tight"
        )
        plt.close("all")
        gc.collect()

        # Nuevas gráficas de análisis de clientes

        # 8. Clustering K-Means de clientes
        logger.info("Generating plot 8/14: Customer clustering (K-Means)")
        if (
            "clustering" in customer_results
            and "cluster_sizes" in customer_results["clustering"]
        ):
            cluster_sizes_df = pd.Series(
                customer_results["clustering"]["cluster_sizes"]
            )
            plt.figure(figsize=(12, 8))
            # Colores más contrastantes para distinguir mejor los 4 clusters
            colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
            wedges, texts, autotexts = plt.pie(
                cluster_sizes_df.values,
                labels=cluster_sizes_df.index,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90,
                textprops={'fontsize': 11, 'weight': 'bold'},
                explode=[0.05] * len(cluster_sizes_df),  # Separar ligeramente las porciones
            )
            # Hacer más legibles los porcentajes
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(12)
                autotext.set_weight('bold')
            plt.title("Clustering K-Means de Clientes (4 Segmentos)", fontsize=14, weight='bold')
            plt.tight_layout()
            plt.savefig(
                os.path.join(RESULTS_DIR, "customer_clustering_kmeans.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close("all")
            gc.collect()

            # Visualización 2D del clustering (proyección desde 4D)
            logger.info("Generating plot 8b/14: Customer clustering scatter")
            customer_clusters_df = pd.read_pickle(clusters_file)
            plt.figure(figsize=(14, 9))

            # Scatter plot de frecuencia vs volumen total coloreado por cluster
            # Nota: Los clusters fueron calculados en 4D (frecuencia, volumen, productos distintos, categorías)
            # Esta es solo una proyección 2D para visualización
            cluster_colors = {0: '#e74c3c', 1: '#3498db', 2: '#2ecc71', 3: '#f39c12'}
            cluster_names_map = {
                0: customer_clusters_df[customer_clusters_df['cluster']==0]['cluster_name'].iloc[0] if len(customer_clusters_df[customer_clusters_df['cluster']==0]) > 0 else 'Cluster 0',
                1: customer_clusters_df[customer_clusters_df['cluster']==1]['cluster_name'].iloc[0] if len(customer_clusters_df[customer_clusters_df['cluster']==1]) > 0 else 'Cluster 1',
                2: customer_clusters_df[customer_clusters_df['cluster']==2]['cluster_name'].iloc[0] if len(customer_clusters_df[customer_clusters_df['cluster']==2]) > 0 else 'Cluster 2',
                3: customer_clusters_df[customer_clusters_df['cluster']==3]['cluster_name'].iloc[0] if len(customer_clusters_df[customer_clusters_df['cluster']==3]) > 0 else 'Cluster 3',
            }
            
            for cluster_id in sorted(customer_clusters_df['cluster'].unique()):
                cluster_data = customer_clusters_df[customer_clusters_df['cluster'] == cluster_id]
                plt.scatter(
                    cluster_data['frequency'],
                    cluster_data['total_volume'],
                    c=cluster_colors[cluster_id],
                    label=cluster_names_map[cluster_id],
                    alpha=0.6,
                    s=100,
                    edgecolors='black',
                    linewidths=0.5
                )
            
            plt.xlabel("Frecuencia de Compra (# Transacciones)", fontsize=12, weight='bold')
            plt.ylabel("Volumen Total (# Productos)", fontsize=12, weight='bold')
            plt.title("K-Means: Proyección 2D (Frecuencia vs Volumen)\nClusters calculados en 5D: Frecuencia + Volumen + Productos Distintos + Diversidad Categorías + Prom Prod/Trans", 
                     fontsize=13, weight='bold')
            plt.legend(title='Segmento de Cliente', loc='best', fontsize=10)
            plt.grid(True, alpha=0.3, linestyle='--')
            plt.tight_layout()
            plt.savefig(
                os.path.join(RESULTS_DIR, "customer_clustering_scatter.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close("all")
            del customer_clusters_df
            gc.collect()

            # Visualización adicional: Gráfico de barras comparativo de características por cluster
            logger.info("Generating plot 8c/14: Cluster profiles comparison")
            cluster_profiles_data = customer_results["clustering"]["cluster_profiles"]
            
            fig, axes = plt.subplots(3, 2, figsize=(16, 16))
            fig.suptitle("Perfiles de los 4 Clusters K-Means - Comparación de 5 Características", 
                        fontsize=16, weight='bold')
            
            cluster_names_list = list(cluster_profiles_data.keys())
            cluster_colors_list = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
            
            # Gráfico 1: Frecuencia promedio
            frequencies = [cluster_profiles_data[name]['avg_frequency'] for name in cluster_names_list]
            axes[0, 0].bar(range(len(cluster_names_list)), frequencies, color=cluster_colors_list, edgecolor='black', linewidth=1.5)
            axes[0, 0].set_xticks(range(len(cluster_names_list)))
            axes[0, 0].set_xticklabels(cluster_names_list, rotation=15, ha='right', fontsize=10)
            axes[0, 0].set_ylabel('Frecuencia Promedio', fontsize=11, weight='bold')
            axes[0, 0].set_title('Frecuencia de Compra por Cluster', fontsize=12, weight='bold')
            axes[0, 0].grid(axis='y', alpha=0.3, linestyle='--')
            
            # Gráfico 2: Volumen total promedio
            volumes = [cluster_profiles_data[name]['avg_total_volume'] for name in cluster_names_list]
            axes[0, 1].bar(range(len(cluster_names_list)), volumes, color=cluster_colors_list, edgecolor='black', linewidth=1.5)
            axes[0, 1].set_xticks(range(len(cluster_names_list)))
            axes[0, 1].set_xticklabels(cluster_names_list, rotation=15, ha='right', fontsize=10)
            axes[0, 1].set_ylabel('Volumen Total Promedio', fontsize=11, weight='bold')
            axes[0, 1].set_title('Volumen de Compra por Cluster', fontsize=12, weight='bold')
            axes[0, 1].grid(axis='y', alpha=0.3, linestyle='--')
            
            # Gráfico 3: Productos distintos promedio
            distinct_prods = [cluster_profiles_data[name]['avg_distinct_products'] for name in cluster_names_list]
            axes[1, 0].bar(range(len(cluster_names_list)), distinct_prods, color=cluster_colors_list, edgecolor='black', linewidth=1.5)
            axes[1, 0].set_xticks(range(len(cluster_names_list)))
            axes[1, 0].set_xticklabels(cluster_names_list, rotation=15, ha='right', fontsize=10)
            axes[1, 0].set_ylabel('Productos Distintos Promedio', fontsize=11, weight='bold')
            axes[1, 0].set_title('Variedad de Productos por Cluster', fontsize=12, weight='bold')
            axes[1, 0].grid(axis='y', alpha=0.3, linestyle='--')
            
            # Gráfico 4: Diversidad de categorías promedio
            category_div = [cluster_profiles_data[name]['avg_category_diversity'] for name in cluster_names_list]
            axes[1, 1].bar(range(len(cluster_names_list)), category_div, color=cluster_colors_list, edgecolor='black', linewidth=1.5)
            axes[1, 1].set_xticks(range(len(cluster_names_list)))
            axes[1, 1].set_xticklabels(cluster_names_list, rotation=15, ha='right', fontsize=10)
            axes[1, 1].set_ylabel('Diversidad de Categorías Promedio', fontsize=11, weight='bold')
            axes[1, 1].set_title('Diversidad de Categorías por Cluster', fontsize=12, weight='bold')
            axes[1, 1].grid(axis='y', alpha=0.3, linestyle='--')
            
            # Gráfico 5: Promedio de productos por transacción
            avg_prod_trans = [cluster_profiles_data[name]['avg_products_per_transaction'] for name in cluster_names_list]
            axes[2, 0].bar(range(len(cluster_names_list)), avg_prod_trans, color=cluster_colors_list, edgecolor='black', linewidth=1.5)
            axes[2, 0].set_xticks(range(len(cluster_names_list)))
            axes[2, 0].set_xticklabels(cluster_names_list, rotation=15, ha='right', fontsize=10)
            axes[2, 0].set_ylabel('Promedio Prod/Trans', fontsize=11, weight='bold')
            axes[2, 0].set_title('Productos Promedio por Transacción por Cluster', fontsize=12, weight='bold')
            axes[2, 0].grid(axis='y', alpha=0.3, linestyle='--')
            
            # Ocultar el panel vacío (2, 1)
            axes[2, 1].axis('off')
            
            plt.tight_layout()
            plt.savefig(
                os.path.join(RESULTS_DIR, "customer_clustering_profiles.png"),
                dpi=150,
                bbox_inches="tight",
            )
            plt.close("all")
            gc.collect()

        # 9. Top reglas de asociación
        logger.info("Generating plot 9/14: Association rules")
        if association_results["top_rules"]:
            top_rules = association_results["top_rules"][:10]
            rules_labels = [f"{r['antecedent']}->{r['consequent']}" for r in top_rules]
            rules_lift = [r["lift"] for r in top_rules]

            plt.figure(figsize=(12, 6))
            plt.barh(range(len(rules_labels)), rules_lift, color="teal")
            plt.yticks(range(len(rules_labels)), rules_labels)
            plt.xlabel("Lift")
            plt.title("Top 10 Reglas de Asociacion (por Lift)")
            plt.tight_layout()
            plt.savefig(
                os.path.join(RESULTS_DIR, "association_rules.png"),
                dpi=100,
                bbox_inches="tight",
            )
            plt.close("all")
            gc.collect()

        # === NUEVAS VISUALIZACIONES ANALÍTICAS REQUERIDAS ===

        # 10. Top 10 Clientes (Resumen Ejecutivo)
        logger.info("Generating plot 10/14: Top 10 customers")
        customer_transaction_counts = (
            transactions_df.groupby("customer")
            .size()
            .sort_values(ascending=False)
            .head(10)
        )
        plt.figure(figsize=(10, 6))
        customer_transaction_counts.plot(kind="barh", color="orange")
        plt.title("Top 10 Clientes por Numero de Transacciones")
        plt.xlabel("Numero de Transacciones")
        plt.ylabel("Cliente ID")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "top_10_customers.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # 11. Boxplot - Distribución de productos por cliente y por categoría
        logger.info("Generating plot 11/14: Boxplot distribution")

        # Calcular productos por cliente (contar productos en la columna 'products')
        def count_products(products_str):
            return len(products_str.split())

        transactions_df["num_products"] = transactions_df["products"].apply(
            count_products
        )
        customer_product_counts = transactions_df.groupby("customer")[
            "num_products"
        ].sum()

        # Calcular productos por categoría
        # Expandir productos y mapear a categorías
        product_to_category = product_category_df.set_index("product_code")[
            "category_id"
        ].to_dict()
        category_product_counts = []

        for products_str in transactions_df["products"]:
            for product in products_str.split():
                if product in product_to_category:
                    category_product_counts.append(product_to_category[product])

        category_counts_series = pd.Series(category_product_counts).value_counts()

        # Crear figura con subplots
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Boxplot 1: Distribución por cliente
        axes[0].boxplot([customer_product_counts], labels=["Clientes"])
        axes[0].set_ylabel("Total de Productos Comprados")
        axes[0].set_title("Distribucion de Productos por Cliente")
        axes[0].grid(axis="y", alpha=0.3)

        # Boxplot 2: Distribución por categoría (top 10 categorías)
        top_categories = category_counts_series.head(10)
        axes[1].barh(range(len(top_categories)), top_categories.values)
        axes[1].set_yticks(range(len(top_categories)))
        axes[1].set_yticklabels([f"Cat {cat}" for cat in top_categories.index])
        axes[1].set_xlabel("Numero de Productos")
        axes[1].set_title("Top 10 Categorias por Volumen")

        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "boxplot_distribution.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # 12. Heatmap - Correlación entre variables numéricas
        logger.info("Generating plot 12/14: Correlation heatmap")
        # Crear DataFrame con variables numéricas por cliente usando vectorización

        # Funciones auxiliares para agrupar
        def count_distinct_products_heatmap(products_series):
            all_products = set()
            for products_str in products_series:
                all_products.update(products_str.split())
            return len(all_products)

        def count_category_diversity_heatmap(products_series):
            categories_purchased = set()
            for products_str in products_series:
                for product in products_str.split():
                    if product in product_to_category:
                        categories_purchased.add(product_to_category[product])
            return len(categories_purchased)

        # Agrupar por cliente y calcular métricas
        features_df = pd.DataFrame()
        features_df["Frecuencia"] = transactions_df.groupby("customer").size()
        features_df["Volumen_Total"] = transactions_df.groupby("customer")[
            "num_products"
        ].sum()
        features_df["Promedio_Productos"] = transactions_df.groupby("customer")[
            "num_products"
        ].mean()
        features_df["Productos_Distintos"] = transactions_df.groupby("customer")[
            "products"
        ].apply(count_distinct_products_heatmap)
        features_df["Diversidad_Categorias"] = transactions_df.groupby("customer")[
            "products"
        ].apply(count_category_diversity_heatmap)
        features_df = features_df.reset_index(drop=True)
        correlation_matrix = features_df.corr()

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            correlation_matrix,
            annot=True,
            cmap="coolwarm",
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8},
        )
        plt.title("Heatmap de Correlacion entre Variables de Cliente")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "correlation_heatmap.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        # 13. Días pico de compra (agregado por día)
        logger.info("Generating plot 13/14: Peak days")
        daily_transactions = transactions_df.groupby(
            transactions_df["date"].dt.date
        ).size()
        top_days = daily_transactions.sort_values(ascending=False).head(10)

        plt.figure(figsize=(12, 6))
        plt.bar(range(len(top_days)), top_days.values, color="purple", alpha=0.7)
        plt.xticks(
            range(len(top_days)),
            [str(d) for d in top_days.index],
            rotation=45,
            ha="right",
        )
        plt.xlabel("Fecha")
        plt.ylabel("Numero de Transacciones")
        plt.title("Top 10 Dias Pico de Compra")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "peak_days.png"), dpi=100, bbox_inches="tight"
        )
        plt.close("all")
        gc.collect()

        # 14. Categorías más "rentables" (por volumen/frecuencia relativa)
        logger.info("Generating plot 14/14: Categories by volume")
        category_volume = defaultdict(int)
        for products_str in transactions_df["products"]:
            for product in products_str.split():
                if product in product_to_category:
                    category_volume[product_to_category[product]] += 1

        category_volume_series = (
            pd.Series(category_volume).sort_values(ascending=False).head(10)
        )

        # Mapear a nombres si están disponibles
        category_id_to_name = categories_df.set_index("category_id")[
            "category_name"
        ].to_dict()
        category_labels = [
            category_id_to_name.get(cat, f"Cat {cat}")
            for cat in category_volume_series.index
        ]

        plt.figure(figsize=(12, 6))
        plt.barh(
            range(len(category_volume_series)),
            category_volume_series.values,
            color="gold",
        )
        plt.yticks(range(len(category_volume_series)), category_labels)
        plt.xlabel("Volumen Total (Frecuencia de Productos)")
        plt.title("Top 10 Categorias por Volumen (Rentabilidad Relativa)")
        plt.tight_layout()
        plt.savefig(
            os.path.join(RESULTS_DIR, "categories_by_volume.png"),
            dpi=100,
            bbox_inches="tight",
        )
        plt.close("all")
        gc.collect()

        logger.info("✓ All 14 plots generated and saved successfully")

        # Liberar toda la memoria
        del categories_df, product_category_df, transactions_df
        del stats_results, temporal_results, customer_results, association_results
        gc.collect()

    except Exception as e:
        logger.error(f"Error in generate_plots: {e}")
        plt.close("all")  # Cerrar cualquier figura abierta
        raise


def save_results(**context):
    """
    Guarda los resultados en archivos.
    Carga datos desde archivos pickle.
    """
    try:
        # Obtener paths desde XCom
        review_file = context["ti"].xcom_pull(key="review_file")
        stats_file = context["ti"].xcom_pull(key="stats_file")
        temporal_file = context["ti"].xcom_pull(key="temporal_file")
        customer_file = context["ti"].xcom_pull(key="customer_file")
        association_file = context["ti"].xcom_pull(key="association_file")

        # Cargar desde pickle
        logger.info("Loading results from intermediate files")
        review_results = pd.read_pickle(review_file)
        stats_results = pd.read_pickle(stats_file)
        temporal_results = pd.read_pickle(temporal_file)
        customer_results = pd.read_pickle(customer_file)
        association_results = pd.read_pickle(association_file)

        os.makedirs(RESULTS_DIR, exist_ok=True)
        logger.info(f"Saving results to {RESULTS_DIR}")

        # Guardar revisión de datos
        with open(os.path.join(RESULTS_DIR, "data_review.txt"), "w") as f:
            for table, stats in review_results.items():
                f.write(f"=== {table.upper()} ===\n")
                for key, value in stats.items():
                    f.write(f"{key}: {value}\n")
                f.write("\n")

        # Guardar estadísticas descriptivas
        with open(os.path.join(RESULTS_DIR, "descriptive_stats.txt"), "w") as f:
            f.write("=== ESTADÍSTICAS NUMÉRICAS ===\n")
            for var, stats in stats_results["numeric"].items():
                f.write(f"\n--- {var.upper()} ---\n")
                desc_df = pd.DataFrame(stats["describe"])
                f.write(desc_df.to_string())
                f.write(f"\nModa: {stats['mode']}\n")
                f.write(f"Outliers: {stats_results['outliers'][var]}\n")

            f.write("\n=== ESTADÍSTICAS CATEGÓRICAS ===\n")
            f.write("Categorías:\n")
            for cat, count in list(
                stats_results["categorical"]["category_counts"].items()
            )[:10]:
                freq = stats_results["categorical"]["category_frequencies"][cat]
                f.write(f"Categoría {cat}: {count} productos ({freq}%)\n")

            f.write("\nTop productos:\n")
            for prod, count in list(stats_results["product_frequencies"].items())[:10]:
                f.write(f"Producto {prod}: {count} veces\n")

            f.write("\nTop stores:\n")
            for store, count in list(
                stats_results["store_frequencies"]["counts"].items()
            )[:10]:
                freq = stats_results["store_frequencies"]["frequencies"][store]
                f.write(f"Store {store}: {count} transacciones ({freq}%)\n")

        # Guardar análisis temporal
        with open(os.path.join(RESULTS_DIR, "temporal_analysis.txt"), "w") as f:
            f.write("=== ANÁLISIS TEMPORAL ===\n\n")

            f.write("Estadísticas diarias:\n")
            for key, value in temporal_results["daily_stats"].items():
                f.write(f"{key}: {value}\n")

            f.write("\nVentas por día de la semana:\n")
            for day, stats in temporal_results["day_of_week_sales"].items():
                f.write(
                    f"{day}: {stats['num_transactions']} transacciones, {stats['total_products']} productos\n"
                )

            f.write("\nTop 10 días con más ventas:\n")
            daily_sales_sorted = sorted(
                temporal_results["daily_sales"].items(),
                key=lambda x: x[1]["num_transactions"],
                reverse=True,
            )[:10]
            for date, stats in daily_sales_sorted:
                f.write(f"{date}: {stats['num_transactions']} transacciones\n")

        # Guardar análisis de clientes (incluyendo clustering K-Means)
        with open(os.path.join(RESULTS_DIR, "customer_analysis.txt"), "w") as f:
            f.write("=== ANÁLISIS DE CLIENTES ===\n\n")

            f.write("Frecuencia de compra:\n")
            for key, value in customer_results["purchase_frequency"].items():
                f.write(f"{key}: {value}\n")

            if customer_results["time_between_purchases"]:
                f.write("\nTiempo entre compras:\n")
                for key, value in customer_results["time_between_purchases"].items():
                    f.write(f"{key}: {value}\n")

            if "clustering" in customer_results:
                f.write("\n=== CLUSTERING K-MEANS ===\n\n")
                f.write(
                    f"Número de clusters: {customer_results['clustering']['n_clusters']}\n\n"
                )

                for cluster_name, profile in customer_results["clustering"][
                    "cluster_profiles"
                ].items():
                    f.write(f"\n{cluster_name} (n={profile['size']}):\n")
                    f.write(f"  Descripción: {profile['description']}\n")
                    f.write(f"  Frecuencia promedio: {profile['avg_frequency']:.2f}\n")
                    f.write(
                        f"  Volumen total promedio: {profile['avg_total_volume']:.2f}\n"
                    )
                    f.write(
                        f"  Productos distintos promedio: {profile['avg_distinct_products']:.2f}\n"
                    )
                    f.write(
                        f"  Diversidad de categorías promedio: {profile['avg_category_diversity']:.2f}\n"
                    )

        # Guardar análisis de asociación de productos
        with open(os.path.join(RESULTS_DIR, "product_association.txt"), "w") as f:
            f.write("=== ANÁLISIS DE ASOCIACIÓN DE PRODUCTOS ===\n\n")

            f.write("Items frecuentes (Top 20):\n")
            for item, count in association_results["frequent_items"].items():
                f.write(f"Producto {item}: {count} transacciones\n")

            f.write(f"\nReglas de asociación (Top 20 por lift):\n")
            for i, rule in enumerate(association_results["top_rules"], 1):
                f.write(
                    f"{i}. {rule['antecedent']} -> {rule['consequent']}: "
                    f"Support={rule['support']:.4f}, "
                    f"Confidence={rule['confidence']:.4f}, "
                    f"Lift={rule['lift']:.4f}\n"
                )

        # Guardar sistema de recomendaciones
        recommendation_file = context["ti"].xcom_pull(key="recommendation_file")
        if recommendation_file:
            recommendation_results = pd.read_pickle(recommendation_file)
            with open(os.path.join(RESULTS_DIR, "recommendations.txt"), "w") as f:
                f.write("=== SISTEMA DE RECOMENDACIÓN ===\n\n")

                f.write("RECOMENDACIONES PARA CLIENTES:\n\n")
                for customer, recs in list(
                    recommendation_results["customer_recommendations_examples"].items()
                )[:10]:
                    f.write(f"\nCliente {customer}:\n")
                    for i, rec in enumerate(recs[:5], 1):
                        f.write(
                            f"  {i}. Producto {rec['product']} "
                            f"(Score: {rec['score']:.2f}, Lift: {rec['avg_lift']:.2f})\n"
                        )

                f.write("\n\nRECOMENDACIONES PARA PRODUCTOS:\n\n")
                for product, recs in list(
                    recommendation_results["product_recommendations_examples"].items()
                )[:10]:
                    f.write(f"\nProducto {product}:\n")
                    for i, rec in enumerate(recs[:5], 1):
                        f.write(
                            f"  {i}. Producto {rec['product']} "
                            f"(Lift: {rec['lift']:.2f}, Confidence: {rec['confidence']:.2f})\n"
                        )

        # === INFORME EJECUTIVO CONSOLIDADO ===
        transactions_file = context["ti"].xcom_pull(key="transactions_file")
        transactions_df = pd.read_pickle(transactions_file)
        transactions_df["num_products"] = (
            transactions_df["products"].str.split().str.len()
        )

        with open(
            os.path.join(RESULTS_DIR, "INFORME_EJECUTIVO.txt"), "w", encoding="utf-8"
        ) as f:
            f.write("=" * 80 + "\n")
            f.write(" " * 20 + "INFORME EJECUTIVO\n")
            f.write(" " * 10 + "Análisis y Modelado Analítico de Transacciones\n")
            f.write("=" * 80 + "\n\n")

            # RESUMEN EJECUTIVO
            f.write("1. RESUMEN EJECUTIVO\n")
            f.write("-" * 80 + "\n\n")

            total_ventas = transactions_df["num_products"].sum()
            num_transacciones = len(transactions_df)

            f.write(f"Total de ventas (unidades): {total_ventas:,}\n")
            f.write(f"Número de transacciones: {num_transacciones:,}\n")
            f.write(
                f"Promedio de productos por transacción: {total_ventas/num_transacciones:.2f}\n"
            )
            f.write(
                f"Número de clientes únicos: {transactions_df['customer'].nunique():,}\n"
            )
            f.write(f"Número de tiendas: {transactions_df['store'].nunique()}\n\n")

            # Top 10 productos
            f.write("Top 10 Productos Más Vendidos:\n")
            for i, (prod, count) in enumerate(
                list(stats_results["product_frequencies"].items())[:10], 1
            ):
                f.write(f"  {i}. Producto {prod}: {count} ventas\n")

            # Top 10 clientes
            f.write("\nTop 10 Clientes:\n")
            top_customers = (
                transactions_df.groupby("customer")
                .size()
                .sort_values(ascending=False)
                .head(10)
            )
            for i, (customer, count) in enumerate(top_customers.items(), 1):
                f.write(f"  {i}. Cliente {customer}: {count} transacciones\n")

            # Días pico
            f.write("\nTop 5 Días Pico de Compra:\n")
            daily_sales_sorted = sorted(
                temporal_results["daily_sales"].items(),
                key=lambda x: x[1]["num_transactions"],
                reverse=True,
            )[:5]
            for i, (date, stats) in enumerate(daily_sales_sorted, 1):
                f.write(f"  {i}. {date}: {stats['num_transactions']} transacciones\n")

            # Categorías más rentables
            f.write("\nTop 5 Categorías por Volumen:\n")
            for i, (cat, count) in enumerate(
                list(stats_results["categorical"]["category_counts"].items())[:5], 1
            ):
                freq = stats_results["categorical"]["category_frequencies"][cat]
                f.write(f"  {i}. Categoría {cat}: {count} productos ({freq}%)\n")

            # ANÁLISIS DESCRIPTIVO
            f.write("\n\n2. ANÁLISIS DESCRIPTIVO\n")
            f.write("-" * 80 + "\n\n")

            f.write("2.1 Análisis Temporal\n")
            f.write(
                "  - Tendencia: Se identificaron patrones de venta diarios y semanales.\n"
            )
            f.write(
                f"  - Promedio de transacciones diarias: {temporal_results['daily_stats']['mean_daily_transactions']:.2f}\n"
            )
            f.write(f"  - Día de la semana con más ventas: ")
            day_sales = temporal_results["day_of_week_sales"]
            max_day = max(day_sales.items(), key=lambda x: x[1]["num_transactions"])
            f.write(f"{max_day[0]} ({max_day[1]['num_transactions']} transacciones)\n")

            f.write("\n2.2 Análisis de Clientes\n")
            f.write(
                f"  - Frecuencia promedio de compra: {customer_results['purchase_frequency']['mean']:.2f} transacciones\n"
            )
            if customer_results["time_between_purchases"]:
                f.write(
                    f"  - Tiempo promedio entre compras: {customer_results['time_between_purchases']['mean_days']:.2f} días\n"
                )

            # ANÁLISIS AVANZADO - CLUSTERING
            f.write("\n\n3. ANÁLISIS AVANZADO: SEGMENTACIÓN DE CLIENTES (K-MEANS)\n")
            f.write("-" * 80 + "\n\n")

            if "clustering" in customer_results:
                f.write("Se aplicó clustering K-Means con 4 grupos basados en:\n")
                f.write("  - Frecuencia de compra\n")
                f.write("  - Volumen total de productos\n")
                f.write("  - Número de productos distintos\n")
                f.write("  - Diversidad de categorías compradas\n\n")

                for cluster_name, profile in customer_results["clustering"][
                    "cluster_profiles"
                ].items():
                    f.write(
                        f"{cluster_name} ({profile['size']} clientes, {profile['size']/len(transactions_df['customer'].unique())*100:.1f}%):\n"
                    )
                    f.write(f"  {profile['description']}\n")
                    f.write(f"  - Frecuencia: {profile['avg_frequency']:.2f}\n")
                    f.write(f"  - Volumen: {profile['avg_total_volume']:.2f}\n")
                    f.write(
                        f"  - Productos distintos: {profile['avg_distinct_products']:.2f}\n"
                    )
                    f.write(
                        f"  - Diversidad de categorías: {profile['avg_category_diversity']:.2f}\n\n"
                    )

            # ANÁLISIS AVANZADO - RECOMENDACIONES
            f.write("\n4. ANÁLISIS AVANZADO: SISTEMA DE RECOMENDACIÓN\n")
            f.write("-" * 80 + "\n\n")

            f.write(
                "Sistema basado en reglas de asociación (Market Basket Analysis):\n"
            )
            f.write(
                f"  - Items frecuentes identificados: {len(association_results['frequent_items'])}\n"
            )
            f.write(
                f"  - Reglas de asociación generadas: {len(association_results['top_rules'])}\n\n"
            )

            f.write("Ejemplos de recomendaciones:\n")
            if recommendation_results:
                # Ejemplo de recomendación para cliente
                if recommendation_results["customer_recommendations_examples"]:
                    first_customer = list(
                        recommendation_results[
                            "customer_recommendations_examples"
                        ].keys()
                    )[0]
                    recs = recommendation_results["customer_recommendations_examples"][
                        first_customer
                    ]
                    f.write(f"\n  Cliente {first_customer}:\n")
                    for rec in recs[:3]:
                        f.write(
                            f"    → Producto {rec['product']} (relevancia: {rec['score']:.2f})\n"
                        )

                # Ejemplo de recomendación para producto
                if recommendation_results["product_recommendations_examples"]:
                    first_product = list(
                        recommendation_results[
                            "product_recommendations_examples"
                        ].keys()
                    )[0]
                    recs = recommendation_results["product_recommendations_examples"][
                        first_product
                    ]
                    f.write(f"\n  Producto {first_product}:\n")
                    for rec in recs[:3]:
                        f.write(
                            f"    → Producto {rec['product']} (lift: {rec['lift']:.2f})\n"
                        )

            # PRINCIPALES HALLAZGOS
            f.write("\n\n5. PRINCIPALES HALLAZGOS\n")
            f.write("-" * 80 + "\n\n")

            f.write(
                "• Patrones temporales: Existen días específicos con mayor actividad de compra.\n"
            )
            f.write(
                "• Segmentación clara: Se identificaron 4 grupos de clientes con comportamientos distintos.\n"
            )
            f.write(
                "• Productos complementarios: Se detectaron productos que frecuentemente se compran juntos.\n"
            )
            f.write(
                "• Oportunidades de cross-selling: El sistema de recomendación identifica productos relevantes.\n"
            )

            # RECOMENDACIONES DE NEGOCIO
            f.write("\n\n6. RECOMENDACIONES DE NEGOCIO\n")
            f.write("-" * 80 + "\n\n")

            if "clustering" in customer_results:
                for cluster_name, profile in customer_results["clustering"][
                    "cluster_profiles"
                ].items():
                    f.write(f"\n{cluster_name}:\n")
                    if "VIP" in cluster_name or "Alto Valor" in cluster_name:
                        f.write("  - Implementar programa de lealtad premium\n")
                        f.write("  - Ofrecer descuentos por volumen\n")
                        f.write("  - Comunicación personalizada prioritaria\n")
                    elif "Frecuente" in cluster_name:
                        f.write("  - Incentivar aumento de ticket promedio\n")
                        f.write("  - Promociones en categorías complementarias\n")
                        f.write("  - Gamificación para aumentar engagement\n")
                    elif "Gran Comprador" in cluster_name:
                        f.write("  - Aumentar frecuencia con recordatorios\n")
                        f.write("  - Facilitar proceso de recompra\n")
                        f.write("  - Suscripción o pedidos recurrentes\n")
                    else:
                        f.write("  - Campañas de reactivación\n")
                        f.write("  - Ofertas de entrada atractivas\n")
                        f.write("  - Comunicación menos frecuente pero relevante\n")

            f.write("\nEstrategias de merchandising:\n")
            f.write(
                "  - Colocar productos complementarios cercanos (según reglas de asociación)\n"
            )
            f.write("  - Implementar recomendaciones en punto de venta\n")
            f.write(
                "  - Diseñar combos basados en productos frecuentemente comprados juntos\n"
            )

            f.write("\n\n7. CONCLUSIONES\n")
            f.write("-" * 80 + "\n\n")

            f.write(
                "El análisis reveló patrones significativos en el comportamiento de compra que pueden\n"
            )
            f.write(
                "ser aprovechados para mejorar la estrategia comercial. La segmentación de clientes\n"
            )
            f.write(
                "permite personalizar la experiencia y maximizar el valor de cada grupo. El sistema\n"
            )
            f.write(
                "de recomendación basado en reglas de asociación ofrece oportunidades claras de\n"
            )
            f.write("cross-selling y up-selling.\n\n")

            f.write("=" * 80 + "\n")
            f.write("Fin del informe\n")
            f.write("=" * 80 + "\n")

        logger.info("✓ All results saved successfully to files")

        # Limpiar archivos intermedios al final
        run_id = context["run_id"]
        cleanup_intermediate_files(run_id)
        logger.info("✓ Intermediate files cleaned up")

    except Exception as e:
        logger.error(f"Error in save_results: {e}")
        raise


# Definición del DAG
with DAG(
    dag_id="dataset_analysis_dag",
    default_args=default_args,
    description="Análisis de dataset de transacciones con gestión optimizada de recursos",
    schedule_interval=None,
    start_date=datetime(2025, 10, 11),
    catchup=False,
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=3),
    tags=["dataset", "analysis", "optimized"],
) as dag:

    t_setup_pools = PythonOperator(
        task_id="setup_pools",
        python_callable=setup_pools,
        execution_timeout=timedelta(minutes=2),
    )

    t_load = PythonOperator(
        task_id="load_data",
        python_callable=load_data,
        execution_timeout=timedelta(minutes=15),
        pool="default_pool",
    )

    t_review = PythonOperator(
        task_id="data_review",
        python_callable=data_review,
        execution_timeout=timedelta(minutes=10),
        pool="default_pool",
    )

    t_stats = PythonOperator(
        task_id="descriptive_stats",
        python_callable=descriptive_stats,
        execution_timeout=timedelta(minutes=20),
        pool="default_pool",
    )

    t_temporal = PythonOperator(
        task_id="temporal_analysis",
        python_callable=temporal_analysis,
        execution_timeout=timedelta(minutes=15),
        pool="default_pool",
    )

    t_customer = PythonOperator(
        task_id="customer_analysis",
        python_callable=customer_analysis,
        execution_timeout=timedelta(minutes=60),
        pool="heavy_compute",  # Pool para tareas pesadas
    )

    t_association = PythonOperator(
        task_id="product_association",
        python_callable=product_association_analysis,
        execution_timeout=timedelta(minutes=30),
        pool="heavy_compute",  # Pool para tareas pesadas
    )

    t_recommendation = PythonOperator(
        task_id="recommendation_system",
        python_callable=recommendation_system,
        execution_timeout=timedelta(minutes=20),
        pool="default_pool",
    )

    t_generate_plots = PythonOperator(
        task_id="generate_plots",
        python_callable=generate_plots,
        execution_timeout=timedelta(minutes=30),
        pool="heavy_compute",  # Pool para tareas pesadas
    )

    t_save = PythonOperator(
        task_id="save_results",
        python_callable=save_results,
        execution_timeout=timedelta(minutes=15),
        pool="default_pool",
    )

    # Definir flujo de tareas
    t_setup_pools >> t_load >> t_review >> t_stats
    t_stats >> [t_temporal, t_customer, t_association]
    t_association >> t_recommendation
    [t_temporal, t_customer, t_recommendation] >> t_generate_plots >> t_save
