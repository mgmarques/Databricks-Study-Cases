# Raw Data Lake
Using a Raw Data Lake on Databricks is actually a very common and solid pattern in modern data architectures. 
The key is understanding what “raw” really means and how it fits into the bigger picture.
## Why a Raw Data Lake on Databricks works
Databricks is built around a **lakehouse architecture**, combining **data lakes + warehouses**. With Delta Lake, you get:
* ACID transactions (no corrupted data)
* Schema enforcement (optional but useful)
* Time travel (huge for debugging pipelines)
* Scalability for large raw datasets
## What “Raw Data Lake” should mean
Your raw layer (often called **Bronze**) should be:
* Immutable (no updates/deletes ideally)
* As close to source as possible
* Append-only
* Minimal transformations (maybe just format normalization)

Think:
* JSON from APIs
* CSV dumps from systems
* Logs, events, CDC streams
## Where Airflow fits
If you're using Apache Airflow, it typically:

* Orchestrates ingestion into the raw layer
* Triggers Databricks jobs (not replace them)
* Manages dependencies across pipelines

## When it makes the most sense
A Databricks raw lake is a great choice if:
* You already use Spark or need big data processing
* You plan to build Bronze → Silver → Gold layers
* You want unified batch + streaming pipelines
* You care about data versioning and reliability

## Common mistakes (important)
Where people go wrong:
* Transforming too much in raw (breaks lineage)
* Not partitioning data (kills performance)
* Skipping metadata/cataloging (hard to find data later)
* Using raw as a “data dump” without governance
  
## A clean modern stack (example)
Ingestion: Airflow
Raw storage: Databricks (Delta Lake Bronze)
Transform: Databricks (Spark / SQL)
Modeling: dbt
Orchestration: Airflow
# Bottom line
* A raw data lake on Databricks is a best-practice architecture
* It works especially well with Airflow orchestration
* The value comes from layering (Bronze → Silver → Gold), not just raw storage
