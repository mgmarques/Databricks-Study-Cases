# Governance Implementation in Practice
Here we will translate our governance model into **real, enforceable implementations across each architecture layer**, not just concepts.


Our [10 governance layers](https://github.com/mgmarques/Databricks-Study-Cases/blob/main/docs/2_Governance.md#governance-embedded-across-layers) define what they *really* require in termes of:

| Component        | What it governs               | Typical tools          |
| ---------------- | ----------------------------- | ---------------------- |
|  Infrastructure  | Cloud, networking             | Terraform, Cloud IAM   |
|  Storage         | Data layout, formats          | S3/ADLS + Delta        |
|  Compute         | Jobs, clusters, orchestration | Databricks, Airflow    |
|  Data            | Schemas, contracts            | Delta, dbt             |
|  Metadata        | Catalog, lineage              | Unity Catalog, DataHub |
|  Access          | RBAC/ABAC                     | IAM, UC                |
|  Quality         | Tests, SLAs                   | Great Expectations     |
|  Observability   | Monitoring, logs              | Datadog, OpenTelemetry |
|  Usage / BI      | Semantic layer                | Power BI, Looker       |
|  Organizational  | Roles, processes              | Not a tool             |

**The key insight**: **Each layer needs its own control plane**, not just Databricks.

What our improved architecture should look like:

```
            ┌──────────────────────┐
            │   Governance Layer   │
            │ (policies, metadata) │
            └─────────┬────────────┘
                      │
   ┌──────────────┬───┴──────────────┬──────────────┐
   │              │                  │              │
Compute       Storage           Metadata        Access
(Databricks)  (S3/Delta)        (DataHub)       (IAM + UC)
```

So, the goal is simple**: move from ***“we define governance”*** to ***“governance is enforced by the platform”***

To provide a guide that is not exhaustive, but practical, we will address our [Modern AI/ML-Ready Data Platform](https://github.com/mgmarques/Databricks-Study-Cases/blob/main/docs/1_Modern_Data_Architecture.md) and its every [layer](https://github.com/mgmarques/Databricks-Study-Cases/blob/main/docs/2_Governance.md#on-our-architecture) as follows:
* **What governance means in practice**
* **Which tools implement it**
* **Concrete code examples you could run today**

---
# 1. Ingestion (Bronze)
**Focus:**
Data contracts, schema enforcement, metadata capture, ownership, and sensitive data tagging.

## Governance layers:
### Governance by Design (2)
Declarative policies baked into pipelines.

**Tools**:
* dbt tests
* Delta Live Tables (DLT)

#### Practical dbt test real examples for governance

```yaml
version: 2

models:
  - name: bronze_payments
    columns:
      - name: payment_id
        tests:
          - not_null
          - unique

      - name: amount
        tests:
          - not_null

      - name: currency
        tests:
          - accepted_values:
              values: ['USD', 'EUR', 'BRL']
```

**Guarantees**:
* No null IDs
* No duplicates
* Controlled domain values

#### Practical DLT expectations

```python
import dlt

@dlt.table(
  comment="Raw payments with enforced quality rules"
)
@dlt.expect("valid_amount", "amount > 0")
@dlt.expect("valid_currency", "currency IN ('USD','EUR','BRL')")
def bronze_payments():
    return spark.readStream.format("cloudFiles").load("/raw/payments")
```

**Enforces**:
* Data validity at ingestion
* Automatic failure or quarantine

### Data Contracts (3)
Federated Bronze enforcement, schema + SLA + ownership.

**Tools**:
* Amazon MSK
* Confluent Schema Registry
* dbt models

#### Practical AWS MSK real examples for governance
Producer with schema enforcement:

```python
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient

schema_registry_conf = {'url': 'http://schema-registry:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

producer = Producer({'bootstrap.servers': 'msk-broker:9092'})

producer.produce(
    topic="payments",
    key="123",
    value='{"payment_id":123,"amount":100.5,"currency":"USD"}'
)

producer.flush()
```

#### Schema definition (contract)

```json
{
  "type": "record",
  "name": "Payment",
  "fields": [
    {"name": "payment_id", "type": "int"},
    {"name": "amount", "type": "double"},
    {"name": "currency", "type": "string"}
  ]
}
```

**Guarantees**:
* Producers cannot break the schema
* Consumers rely on a stable structure

### Metadata Capture (1)
Capture ownership + classification early.

**Tools**:
* DataHub

#### Practical metadata ingestion example

```bash
datahub ingest -c s3_ingestion.yml
```

```yaml
source:
  type: s3
  config:
    path_specs:
      - include: s3://bronze/payments/*.json

sink:
  type: datahub-rest
  config:
    server: http://datahub:8080
```

---
# 2. Storage (Silver / Gold - Lakehouse)
**Focus:**
Access control, classification enforcement, and auditability.

## Governance layers:
### Policy Enforcement (4)
Fine-grained access based on classification.

**Tools**:
* Unity Catalog

#### Practical SQL example

```sql
GRANT SELECT ON TABLE finance.sales TO `analyst_group`;
```

Row-level security:

```sql
CREATE ROW FILTER region_filter
AS (region = current_user_region());
```

### Auditability (5)
Track all access and changes.

**Tools**:

* Databricks audit logs

#### Practical audit query

```sql
SELECT user_name, action_name, table_name, event_time
FROM system.access.audit
WHERE table_name = 'finance.sales';
```

**Enables**:
* compliance audits
* incident investigation

### Metadata Enforcement (1)

#### Table properties enforcing governance

```sql
ALTER TABLE finance.sales
SET TBLPROPERTIES (
  'owner' = 'finance',
  'classification' = 'confidential',
  'sla' = 'daily'
);
```

---
# 3. Processing / Transformation
**Focus:**
Data quality, lineage, controlled transformations.

## Governance layers:
### Governance by Design (2)
**Tools**:
* DLT
* dbt

#### Practical transformation rule

```python
@dlt.table
@dlt.expect("valid_customer", "customer_id IS NOT NULL")
def silver_sales():
    return dlt.read("bronze_sales")
```

### Lineage (6) 
Cross-system lineage tracking.

**Tools**:
* OpenLineage
* Marquez

#### Practical OpenLineage configuration

```bash
export OPENLINEAGE_URL=http://marquez:5000
export OPENLINEAGE_NAMESPACE=prod
```

#### Spark lineage emission

```python
spark.conf.set("spark.openlineage.transport.type", "http")
spark.conf.set("spark.openlineage.transport.url", "http://marquez:5000")
```

**Captures**:
* inputs / outputs
* job runs
* timestamps

---
# 4. Serving / Consumption
**Focus:**
Trusted datasets, discoverability, controlled access.

## Governance layers:
### 🔹 Data Discovery & Catalog (1)

**Tools**:
* DataHub

#### Practical dataset enrichment

```python
emitter.emit({
  "dataset": "finance.sales",
  "description": "Certified finance dataset",
  "tags": ["gold", "certified"]
})
```

### Access Governance (4)

```sql
GRANT SELECT ON TABLE finance.sales TO finance_team;
```

### Usage Observability (5)
**Combine**:
* audit logs
* lineage

**Answers**:
* who used what
* downstream impact

---
# 5. Cross-Layer Governance (Metadata + Lineage Federation)
**Focus:**
Unified governance across all layers.

## Governance layers:
### Lineage Federation (6)
**Tools**:
* OpenLineage
* Marquez
* DataHub


#### Practical integration (OpenLineage → DataHub)

```yaml
source:
  type: openlineage
  config:
    endpoint: http://marquez:5000
```

✔ Unifies:

* runtime lineage
* business metadata

---
# 6. Semantic Layer
**Focus:**
Business-friendly abstraction over Gold/Silver tables, metrics standardization, unified definitions.

## Governance layers:
### Governance by Design (2)
Declarative definitions for metrics, dimensions, and authorized datasets.

**Tools**:
* dbt Semantic Layer (metrics + dimensions)
* Databricks SQL dashboards

---

#### Practical dbt Semantic Layer example

```yaml id="sem1"
metrics:
  - name: total_revenue
    label: "Total Revenue"
    description: "Sum of all sales amounts"
    type: sum
    sql: amount
    dimensions:
      - region
      - product_category
```

**Enforces**:
* standardized business metrics
* consistent definitions across dashboards and pipelines

### Access Governance (4)
Control which teams can use which semantic models.

```sql id="sem2"
GRANT SELECT ON semantic_layer.sales_metrics TO analytics_team;
```

### Auditability (5)
Track dashboard usage linked to semantic definitions:

```sql id="sem3"
SELECT dashboard_id, metric_name, executed_by, execution_time
FROM system.dashboards.query_log
WHERE metric_name='total_revenue';
```

---
# 7. Feature Store
**Focus:**
Centralized ML features with consistent lineage, quality checks, and access control.

## Governance layers:
### Governance by Design (2)
Features are defined once and reused across ML pipelines.

**Tools**:
* Databricks Feature Store
* Delta Live Tables for feature computation

#### Practical Feature definition

```python id="fs1"
from databricks.feature_store import FeatureStoreClient

fs = FeatureStoreClient()

fs.create_table(
    name="finance.customer_risk_score",
    primary_keys="customer_id",
    df=customer_risk_df,
    description="Customer risk scores for ML models"
)
```

### Data Quality / Expectations (3)
Enforce validation before storing features.

```python id="fs2"
@dlt.expect("valid_score", "risk_score BETWEEN 0 AND 1")
def features():
    return customer_risk_df
```

### Lineage (6)
OpenLineage + Marquez tracks feature creation and downstream ML models:

```python id="fs3"
openlineage.emit({
    "job": "compute_risk_features",
    "inputs": ["bronze.customers", "bronze.transactions"],
    "outputs": ["feature_store.customer_risk_score"]
})
```

### Access Governance (4)
Only ML teams or approved analysts can query features:

```sql id="fs4"
GRANT SELECT ON TABLE feature_store.customer_risk_score TO ml_team;
```

---
# 8. ML / RAG Pipelines
**Focus:**
End-to-end ML pipelines including training, inference, and retrieval-augmented generation (RAG) while keeping governance, lineage, and security.

## Governance layers:
### 🔹 Governance by Design (2)
Policies embedded in ML pipelines: feature validation, dataset access, model registration.

**Tools**:
* MLflow for model registry
* Databricks Workflows / Jobs
* Feature Store

#### Practical MLflow + Databricks example

```python id="ml1"
import mlflow
from mlflow.models.signature import infer_signature

with mlflow.start_run():
    model.fit(X_train, y_train)
    signature = infer_signature(X_train, y_train)
    mlflow.sklearn.log_model(model, "risk_model", signature=signature)
```

**Ensures*:
* versioned models
* captured input/output schema
* reproducibility

### Data Contracts & Quality (3)
Validate inputs for ML pipelines:

```python id="ml2"
assert df_features.select("risk_score").dropna().count() == df_features.count()
```

### Lineage / Observability (6)
Track data → feature → model → prediction flows:

```python id="ml3"
openlineage.emit({
    "job": "train_risk_model",
    "inputs": ["feature_store.customer_risk_score"],
    "outputs": ["ml_model_registry.risk_model"]
})
```

### Security & Access (4)
* Model access controlled via MLflow permissions
* RAG knowledge base access restricted

```python id="ml4"
GRANT EXECUTE ON MODEL mlflow_registry.risk_model TO ml_team;
```

---
## Common Pitfalls
### 1. “We have lineage” (but only inside Databricks)
* Problem: breaks at system boundaries
* Fix: use OpenLineage

### 2. Metadata is defined, but not enforced

* Problem: documentation only
* Fix: enforce via CI/CD + table properties

### 3. Governance only at the Gold layer
* Problem: too late
* Fix: enforce at Bronze

### 4. DataHub OR OpenLineage (wrong choice)
*Problem: incomplete governance
* Fix: use both together

### 5. Pitfalls in ML / RAG governance
* **Untracked features**: lineage gaps
* **Unversioned models**: audit and compliance risk
* **Uncontrolled retrieval sources**: sensitive data leakage

---
## Conclusion

Real governance is not:

* dashboards
* documentation
* policies in Confluence

It is:

```text
Code + Platform + Enforcement
```

Full Governance Across All Layers in our architecture:

| Layer                       | Governance Implementation Highlights                                                  |
| --------------------------- | ------------------------------------------------------------------------------------- |
| Bronze / Ingestion          | Data contracts, schema validation, DLT expectations, DataHub ingestion                |
| Silver / Gold Storage       | Unity Catalog access, row-level security, audit logs, classification                  |
| Processing / Transformation | Delta Live Tables + dbt, lineage (OpenLineage + Marquez), runtime quality enforcement |
| Semantic Layer              | Standardized metrics, dashboards, business-friendly abstractions, access control      |
| Feature Store               | Centralized features, quality validation, lineage tracking, team-based access         |
| Serving / Consumption       | Certified datasets, discoverability, query monitoring                                 |
| ML / RAG                    | Versioned models (MLflow), validated features, lineage, controlled retrieval sources  |

**Key takeaway:**
Governance is **not optional at higher layers**. Each layer builds on the previous one, enforcing policies **from ingestion to ML outputs**. Real tooling + practical enforcement ensures **auditability, compliance, and trust**, not just documentation.

When all layers enforce governance, you achieve:
* auditability
* compliance
* trust in data

Ultimately, it's not just a promise, but an embedded and actionable **system property**.
