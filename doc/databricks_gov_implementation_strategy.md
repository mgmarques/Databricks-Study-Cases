# Data Governance Implementation Strategy - Databricks-centric
 Let's add some concrete strategies, real tooling, be Databricks-focused, and provide clear “how-to” guidance.

### Data Governance in Practice
To effectively address data governance challenges, we implement a combination of **centralized governance controls**, **automated enforcement**, and **clear ownership models** across the data platform.

### 1. Access Control & Security

We enforce fine-grained access control using Databricks Unity Catalog as the central governance layer.

#### Strategy

* Organize data into **catalogs → schemas → tables** aligned with business domains (e.g., `finance`, `marketing`)
* Apply **Role-Based Access Control (RBAC)** at multiple levels
* Separate environments (dev, staging, prod) using isolated catalogs

#### Implementation

* Define roles:

  * `data_engineer`: full access to pipelines
  * `analyst`: read access to curated data
  * `data_steward`: governance and auditing permissions

* Example:

```sql
GRANT USE CATALOG ON CATALOG finance TO analyst;
GRANT SELECT ON TABLE finance.curated.transactions TO analyst;
```

#### Challenge Addressed

* Prevents unauthorized access
* Ensures least-privilege principles
* Simplifies audit and compliance enforcement

### 2. Data Quality Enforcement

We ensure data reliability using **automated validation rules** embedded into pipelines with Delta Live Tables.

#### Strategy

* Define **data quality expectations** at ingestion and transformation stages
* Fail or quarantine bad data early
* Continuously monitor quality metrics

#### Implementation

* Example expectations:

  * No nulls in primary keys
  * Valid ranges for numerical fields
  * Referential integrity between datasets

```python
@dlt.expect("valid_amount", "amount > 0")
@dlt.expect_or_fail("not_null_id", "transaction_id IS NOT NULL")
```

#### Challenge Addressed
* Reduces downstream data issues
* Prevents propagation of bad data
* Improves trust in analytics

### 3. Data Lineage & Observability — Compute Governance (Jobs, Workloads, Orchestration)

We enable end-to-end lineage tracking using built-in capabilities from Databricks Unity Catalog.

#### Strategy

* Automatically capture lineage across all pipelines and queries
* Provide visibility into upstream and downstream dependencies
* Enable impact analysis before schema or pipeline changes

#### Implementation

* Use Unity Catalog lineage UI to:
  * Trace dataset origins
  * Identify affected consumers
  * Audit transformations

#### What real implementation looks like
##### A. Standardize execution model
Define **workload types**:

```yaml
workload_types:
  - batch_etl
  - streaming
  - ml_training
  - ad_hoc
```

Then enforce via:

* Job templates
* Cluster policies

### B. Enforce cluster policies
Example:

```json
{
  "spark_version": {
    "type": "fixed",
    "value": "13.3.x-scala2.12"
  },
  "node_type_id": {
    "type": "allowed",
    "values": ["Standard_DS3_v2"]
  },
  "autotermination_minutes": {
    "type": "range",
    "maxValue": 60
  }
}
```

**Note**: This is **governance of cost + reliability**

##### C. Orchestration separation (important insight)
Don’t let Databricks own everything.

Use:
* Airflow / Dagster for orchestration
* Databricks for execution engine

Why?
* Clear separation of concerns
* Cross-platform lineage

**Dagster vs Airflow:**

This single design difference drives most of the trade-offs.

| Aspect                   | Dagster                             | Airflow                                       |
| ------------------------ | ----------------------------------- | --------------------------------------------- |
| **Core concept**         | Data assets (datasets first)        | Tasks & DAGs (actions first)                  |
| **Developer experience** | Modern, intuitive, strong local dev | More boilerplate, harder setup                |
| **Learning curve**       | Easier                              | Steeper                                       |
| **Testing & local dev**  | Built-in, fast iteration            | Harder to replicate locally ([dagster.io][1]) |
| **Observability**        | Strong lineage + data awareness     | Task-level monitoring                         |
| **Ecosystem**            | Growing                             | Huge, mature ecosystem ([DataCamp][2])        |
| **Flexibility**          | Opinionated                         | Extremely flexible/customizable               |
| **Scalability**          | Good, modern architecture           | Proven at large scale                         |
| **CI/CD support**        | First-class                         | More manual setup ([dagster.io][1])           |
| **Adoption**             | Newer                               | Industry standard                             |


Pick Airflow if:
* You want the **industry standard**
* Your company already uses it (very common)
* You need **tons of integrations/plugins**
* You’re running **large, mature pipelines at scale**
* You want maximum flexibility (even if messy)

**Note**: Airflow is still dominant because of its **ecosystem + community + battle-tested reliability** ([DataCamp][2])

Pick Dagster if:
* You want a **modern developer experience**
* You care about **data lineage, assets, and observability**
* Your team is small or starting fresh
* You want **easy local development + testing**
* You prefer cleaner abstractions over flexibility

**Note**: Many teams are **moving toward Dagster (or similar tools like Prefect)** for better DX—but Airflow isn’t going away anytime soon.

Use this quick rule:
* **Startup / greenfield → Dagster**
* **Enterprise / existing stack → Airflow**
* **Career learning → Airflow first, then Dagster**


##### D. Tagging strategy
Every job must include:

```python
spark.conf.set("pipeline.owner", "finance")
spark.conf.set("pipeline.domain", "billing")
spark.conf.set("data.classification", "pii")
```

Used for:
* Cost attribution
* Access policies
* Observability
  
#### Challenge Addressed
* Eliminates “black box” pipelines
* Supports root cause analysis
* Improves collaboration across teams

---

### 4. Metadata Management & Discovery
We centralize metadata to improve discoverability and governance.

#### Strategy
* Register all datasets in Unity Catalog
* Enrich tables with:
  * Descriptions
  * Tags (e.g., PII, sensitive)
  * Ownership information

#### Implementation

```sql
COMMENT ON TABLE finance.curated.transactions IS 'Curated financial transactions dataset';
ALTER TABLE finance.curated.transactions SET TAGS ('pii' = 'true');
```

#### Challenge Addressed
* Reduces data duplication
* Improves self-service analytics
* Enables governance at scale

### 5. Auditability & Compliance — Metadata & Catalog Governance
We ensure full auditability using logs and monitoring.

#### Strategy
* Track all access and changes to data
* Maintain audit logs for compliance requirements (e.g., GDPR)
* Enable alerts for suspicious activity

#### Implementation
* Enable Databricks audit logs
* Monitor:
  * Table access
  * Permission changes
  * Data modifications

#### What real implementation looks like
##### A. Split responsibilities

| Concern                | Tool               |
| ---------------------- | ------------------ |
| Physical catalog       | Unity Catalog      |
| Business catalog       | DataHub / Collibra |
| Lineage (technical)    | Databricks         |
| Lineage (cross-system) | OpenLineage        |

**Note**: Unity Catalog ≠ enterprise metadata

##### B. Metadata model
Define mandatory fields:

```yaml
dataset:
  owner: string
  domain: string
  sla: string
  classification: [public, internal, confidential]
  source: string
```

Enforce via:
* CI/CD checks
* Table creation wrappers

##### C. Example: enforced table creation
Instead of:

```sql
CREATE TABLE sales;
```

You enforce:

```python
create_table(
  name="sales",
  owner="finance",
  classification="confidential",
  sla="daily"
)
```

##### D. Cross-platform lineage
Databricks lineage stops at its boundary, so we need:
* OpenLineage + Marquez
* Or DataHub ingestion

**Otherwise**: You lose governance across tools

-----------------------------------------
Here’s your completed section with **practical implementations**, plus a clear explanation of **Marquez** and why it’s used alongside **OpenLineage**.

---

### 5. Auditability & Compliance — Metadata & Catalog Governance

We ensure full auditability using logs and monitoring.

#### Strategy

* Track all access and changes to data
* Maintain audit logs for compliance requirements (e.g., GDPR)
* Enable alerts for suspicious activity

#### Implementation

* Enable Databricks audit logs
* Monitor:

  * Table access
  * Permission changes
  * Data modifications

---

## What real implementation looks like

### A. Split responsibilities

| Concern                | Tool               |
| ---------------------- | ------------------ |
| Physical catalog       | Unity Catalog      |
| Business catalog       | DataHub / Collibra |
| Lineage (technical)    | Databricks         |
| Lineage (cross-system) | OpenLineage        |

**Note**: Unity Catalog ≠ enterprise metadata

---

### B. Metadata model

Define mandatory fields:

```yaml
dataset:
  owner: string
  domain: string
  sla: string
  classification: [public, internal, confidential]
  source: string
```

Enforce via:

* CI/CD checks
* Table creation wrappers

---

### C. Example: enforced table creation

Instead of:

```sql
CREATE TABLE sales;
```

You enforce:

```python
create_table(
  name="sales",
  owner="finance",
  classification="confidential",
  sla="daily"
)
```

---

### D. Cross-platform lineage

Databricks lineage stops at its boundary, so we need:

* OpenLineage + Marquez
* Or DataHub ingestion

**Otherwise**: You lose governance across tools

---

### E. OpenLineage + Marquez (operational lineage)
* Captures **runtime lineage events** (jobs, inputs, outputs)
* Stores and visualizes them in Marquez

#### Example: Airflow integration

```python
from airflow import DAG
from airflow.operators.python import PythonOperator

def transform():
    # your ETL logic
    pass

with DAG("example_pipeline") as dag:
    task = PythonOperator(
        task_id="transform_task",
        python_callable=transform
    )
```

Enable OpenLineage in Airflow:

```bash
export OPENLINEAGE_URL=http://marquez:5000
export OPENLINEAGE_NAMESPACE=my_company
```

 **Result**:
* Every run emits lineage events
* Marquez shows:
  * dataset → job → dataset relationships
  * execution timestamps
  * run status

#### Example: Spark / Databricks (via OpenLineage)

```python
spark.conf.set("spark.openlineage.transport.type", "http")
spark.conf.set("spark.openlineage.transport.url", "http://marquez:5000")
```
Now every Spark job emits lineage automatically.

---

### E. DataHub (governance + discovery)
* Central metadata platform
* Combines:
  * lineage
  * ownership
  * documentation
  * governance

#### Example: ingest Databricks metadata into DataHub

```bash
datahub ingest -c databricks.yml
```

Example config:

```yaml
source:
  type: databricks
  config:
    workspace_url: https://adb-xxx.azuredatabricks.net
    token: ${DATABRICKS_TOKEN}

sink:
  type: datahub-rest
  config:
    server: http://datahub:8080
```

---

### Example: adding metadata programmatically

```python
from datahub.emitter.mce_builder import make_dataset_urn
from datahub.emitter.rest_emitter import DatahubRestEmitter

emitter = DatahubRestEmitter("http://datahub:8080")

dataset_urn = make_dataset_urn("hive", "sales", "PROD")

emitter.emit({
    "dataset": dataset_urn,
    "owner": "finance",
    "description": "Sales table with daily SLA"
})
```

**Result**:
* Searchable dataset catalog
* Ownership & SLA visible
* Business context added

#### Challenge Addressed
* Meets regulatory requirements
* Improves security posture
* Enables forensic analysis

---
### 6. Governance Operating Model (RBAC, ABAC, Policies)
We adopt a **hybrid governance model** combining centralized standards with domain ownership.

#### Strategy
* Central platform team defines:
  * Governance policies
  * Tooling standards

* Domain teams (data mesh approach) own:
  * Data quality
  * Data definitions
  * Access requests

#### What real implementation looks like
##### A. Multi-layer access model

| Layer    | Control             |
| -------- | ------------------- |
| Cloud    | IAM roles           |
| Platform | Databricks groups   |
| Data     | Row/column security |
| Business | BI tool permissions |

##### B. Attribute-Based Access Control (ABAC)
Instead of:

```sql
GRANT SELECT ON sales TO analysts;
```

Use tags:

```sql
ALTER TABLE sales SET TAGS ('classification' = 'confidential');
```

Then policies:

```sql
CREATE POLICY pii_policy
AS (classification != 'confidential' OR is_member('pii_access'));
```

##### C. Row-level security example
```sql
CREATE VIEW sales_secure AS
SELECT *
FROM sales
WHERE region = current_user_region()
```

---
##### D. Identity federation (often missing)
Don’t manage users in Databricks.

Use:
* Azure AD / Okta
* SCIM sync

---
##### E. Policy-as-code (this is key)
Store access rules in Git:

```yaml
policies:
  - dataset: sales
    access:
      - role: analyst
        permission: read
      - role: finance_admin
        permission: write
```

Deploy via pipeline.

---
#### Challenge Addressed
* Balances control and scalability
* Avoids bottlenecks in centralized teams
* Encourages accountability

## Final Notes - What Databricks actually gives you and its limits
The implementation here leans heavily on Databricks-native governance (Unity Catalog, etc.), which is only one slice of the governance picture.

Even Databricks itself frames governance as just one pillar in a broader architecture, alongside security, reliability, cost, etc. (Documentação Databricks)

And inside that pillar, it focuses mainly on:
* Metadata & catalog
* Access control
* Lineage
* Data quality (basic) (Documentação Databricks)

Then, it maps to maybe 3–4 of our 10 layers, not all of them.

Therefore, this implementation document applies to environments/companies that are platform-centric and rely exclusively on Databricks, while the conceptual document addresses systems governance in more complex and heterogeneous environments/companies.
