# Governance Implementation in Practice

This section translates our governance model into **real, enforceable implementations across each architecture layer**, not just concepts.
Each layer shows:
* **What governance means in practice**
* **Which tools implement it**
* **Concrete code examples you could run today**

Our 10 governance layers define what they *really* require:

| Layer              | What it governs               | Typical tools          |
| ------------------ | ----------------------------- | ---------------------- |
| 1. Infrastructure  | Cloud, networking             | Terraform, Cloud IAM   |
| 2. Storage         | Data layout, formats          | S3/ADLS + Delta        |
| 3. Compute         | Jobs, clusters, orchestration | Databricks, Airflow    |
| 4. Data            | Schemas, contracts            | Delta, dbt             |
| 5. Metadata        | Catalog, lineage              | Unity Catalog, DataHub |
| 6. Access          | RBAC/ABAC                     | IAM, UC                |
| 7. Quality         | Tests, SLAs                   | Great Expectations     |
| 8. Observability   | Monitoring, logs              | Datadog, OpenTelemetry |
| 9. Usage / BI      | Semantic layer                | Power BI, Looker       |
| 10. Organizational | Roles, processes              | Not a tool             |

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

# Common Pitfalls

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

---
# Conclusion

Real governance is not:

* dashboards
* documentation
* policies in Confluence

It is:

```text
Code + Platform + Enforcement
```

Across your architecture:

* **Bronze (Ingestion)** → contracts + schema + early metadata
* **Silver/Gold (Storage)** → access + audit + classification
* **Processing** → quality + lineage
* **Serving** → discoverability + trust
* **Cross-layer** → unified metadata + lineage

When all layers enforce governance, you achieve:
* auditability
* compliance
* trust in data

Ultimately, it's not just a promise, but an embedded and actionable **system property**.
