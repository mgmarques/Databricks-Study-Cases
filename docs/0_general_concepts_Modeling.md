# Some Dimensions Modeling Patterns 

## Fact Tables
### Type 1-like (Overwrite Facts)
* Update the existing fact row.
* No history kept.

Used when:
* Fixing errors (wrong quantity, price, etc.)

### Insert New Fact (Append / Versioning)
* Instead of updating, insert a new row.
Often includes:
* Version number
* Effective date

Example:
| OrderID | Amount | Version | Date  |
| ------- | ------ | ------- | ----- |
| 1001    | 50     | 1       | Jan 1 |
| 1001    | 60     | 2       | Jan 3 |

### Snapshot Fact Tables
These are purpose-built for tracking change over time.

#### Types:
**Periodic Snapshot**
* Captures state at regular intervals
Example: daily account balance
**Accumulating Snapshot**
* Tracks lifecycle of a process
Example: order pipeline (placed → shipped → delivered)

### Audit / Change Log Tables
Store every change as a separate record
Often includes:
* Change timestamp
* Old vs new values

### Late-Arriving Facts
Facts that arrive late (e.g., delayed transactions)
Strategy:
* Insert with correct historical timestamp
* Adjust aggregates if needed

## Slowly changing dimension (SCD) types

| Type | History Stored?  | Method          |
| ---- | ---------------- | --------------- |
| 0    | ❌ No            | Ignore changes  |
| 1    | ❌ No            | Overwrite       |
| 2    | ✅ Full          | New rows        |
| 3    | ⚠️ Limited       | New columns     |
| 4    | ✅ Full          | Separate table  |
| 6    | ✅ Full          | Hybrid approach |

## Key Difference: Dimensions vs Facts
| Aspect      | Dimension Tables      | Fact Tables                   |
| ----------- | --------------------- | ----------------------------- |
| Purpose     | Describe entities     | Record events/measures        |
| Change type | Slow, attribute-based | Event-driven                  |
| History     | Managed via SCD       | Managed via inserts/snapshots |
| Updates     | Common (SCD logic)    | Rare (prefer append)          |

## Rule of Thumb
* If you're changing attributes → use SCD (dimension)
* If you're recording events over time → use:
  - Append-only facts
  - Snapshots
  - Versioning

## In modern systems (like Snowflake, BigQuery, Databricks):
Fact tables are often:
* Immutable (append-only)
* Combined with time-travel / versioning features
Note: This avoids the complexity of SCD-style updates entirely

## How Databricks takes care SCD?
In Databricks, handling Slowly Changing Dimensions is built around Delta Lake, 
which gives you powerful primitives like MERGE, time travel, and versioning. 
Instead of a rigid “built-in SCD module,” Databricks lets you implement any SCD pattern cleanly and efficiently.

### Core Mechanism: Delta Lake + MERGE
The backbone of SCD in Databricks is:
* **Delta tables**
* MERGE INTO (upsert logic)
* ACID transactions
* Time travel (table version history)

This combination makes SCD implementations scalable and reliable.

### SCD Types Supported in Databricks
#### Type 1 (Overwrite)
**How it’s done**: Use MERGE to update existing rows directly. (Upsert)

```sql
MERGE INTO dim_customer t
USING staging s
ON t.customer_id = s.customer_id
WHEN MATCHED THEN
  UPDATE SET t.name = s.name, t.city = s.city
WHEN NOT MATCHED THEN
  INSERT *
```
#### Type 2 (Full History) ⭐ Most Common
Databricks handles this very well.

Typical columns:
* effective_date
* end_date
* is_current

How it works:
* Expire old record (end_date and is_current as False)
* Insert new record (none at end_date is_current as true)
```sql
MERGE INTO dim_customer t
USING staging s
ON t.customer_id = s.customer_id AND t.is_current = true

WHEN MATCHED AND (
  t.name <> s.name OR t.city <> s.city
)
THEN UPDATE SET
  t.end_date = current_date(),
  t.is_current = false

WHEN NOT MATCHED
THEN INSERT (...)
```
Often combined with:
* Surrogate keys
* Hash comparisons for change detection
#### Type 3 (Limited History)
Add columns like:
* previous_city
* Update using MERGE

### Type 6 - Hybrid SCD (Type 1 + Type 2)
Split Columns by Behavior
* Some columns → overwrite (Type 1) → Non-historical
* Some columns → track history (Type 2) → Historical

#### Pro Tips (Real Projects)
✅ Use a hash to detect Type 2 changes instead of comparing many columns
```sql
md5(concat(city, status)) as hash_diff
```
✅ Always filter on is_current = true, it prevents updating old history rows.

✅ Use surrogate keys
* customer_sk (primary key)
* customer_id (business key)

🔹 When to Use Hybrid SCD

**Use this when:**
* Some attributes are corrections (name, email)
* Others are business-critical history (location, status, pricing tier)

**Very common in:**
* Customer dimensions
* Product pricing
* Subscription systems
```sql
MERGE INTO dim_customer t
USING staging s
ON t.customer_id = s.customer_id AND t.is_current = true

-- Step 1: Handle Type 2 changes (city, status)
WHEN MATCHED AND (
  t.city <> s.city OR t.status <> s.status
)
THEN UPDATE SET
  t.end_date = current_date(),
  t.is_current = false,
  t.name = s.name,        -- Type 1 applied here too
  t.email = s.email       -- Type 1

-- Step 2: Insert new row for Type 2
WHEN NOT MATCHED
THEN INSERT (
  customer_id, name, email, city, status,
  start_date, end_date, is_current
)
VALUES (
  s.customer_id, s.name, s.email, s.city, s.status,
  current_date(), NULL, true
)
```
## Advanced / Native Databricks Features
#### 1. Change Data Feed (CDF)
Delta Lake provides Change Data Feed, which tracks row-level changes automatically.

**Useful for:**
* Building SCD Type 2 pipelines
* Incremental processing
#### 2. Time Travel
You can query past versions of a table:
```sql
SELECT * FROM dim_customer VERSION AS OF 10
```
This gives you historical state without manually storing everything.

#### 3. Auto Loader + Structured Streaming
For real-time SCD:
* Ingest data continuously
* Apply SCD logic incrementally

Enables near real-time dimension updates.

### Tools That Simplify SCD in Databricks
#### Delta Live Tables (DLT)
* Declarative pipelines
* Built-in support for SCD logic

Example of the cleanest way to implement SCD Type 2 in Databricks:
```sql
APPLY CHANGES INTO dim_customer
FROM stream(staging)
KEYS (customer_id)
SEQUENCE BY update_timestamp
STORED AS SCD TYPE 2
```
## What Types Are Common in Databricks?
In real-world Databricks projects:
* Type 2 → Most used
* Type 1 → For corrections
* Type 3 → Rare
* Hybrid (Type 1 + 2) → Very common

# Practical Insight
Databricks doesn’t “limit” you to specific SCD types—it gives you building blocks:
* MERGE → control updates/inserts
* Delta versioning → built-in history
* DLT → declarative SCD pipelines

So you can implement:
* Type 1, 2, 3
* Hybrid patterns
* Even custom SCD logic beyond traditional definitions
  
# Quick Summary
| SCD Type  | Support in Databricks  | How                        |
| --------- | ---------------------- | -------------------------- |
| Type 1    | ✅ Native              | MERGE overwrite            |
| Type 2    | ✅ Excellent           | MERGE + flags/dates or DLT |
| Type 3    | ✅ Possible            | Custom columns             |
| Hybrid    | ✅ Common              | MERGE logic                |
| Real-time | ✅ Strong              | Streaming + CDF            |

* Hybrid	✅ Common	MERGE logic
* Real-time	✅ Strong	Streaming + CDF
