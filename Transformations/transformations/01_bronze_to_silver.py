import dlt
from pyspark.sql.functions import (
    col, to_date, date_format, trim, initcap,
    split, size, when, concat, lit, abs, to_timestamp, regexp_extract
)

catalog = "smart_claims_dev"
bronze_schema = "01_bronze"
silver_schema = "02_silver"


# --- CLEAN TELEMATICS ---
@dlt.table(
    name=f"{catalog}.{silver_schema}.telematics",
    comment="cleaned telematics events",
    table_properties={
        "quality": "silver"
    }
)
@dlt.expect("valid_coordinates", "latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180")
def telematics():
    return (
        dlt.readStream(f"{catalog}.{bronze_schema}.telematics")
        .withColumn("event_timestamp", to_timestamp(col("event_timestamp"), "yyyy-MM-dd HH:mm:ss"))
        .drop("_rescued_data")
    )

# --- CLEAN POLICY (CDC Pattern) ---

# Step 1: Temporary view with transformations
@dlt.view(
    comment="Cleaned policy data before CDC processing"
)
@dlt.expect("valid_policy_no", "policy_no IS NOT NULL")
def policy_transformed():
    """Apply policy data transformations before CDC deduplication"""
    df = dlt.readStream(f"{catalog}.{bronze_schema}.policy")
    # Apply abs to premium and drop _rescued_data, preserve all other fields including metadata
    return df.withColumn("premium", abs("premium")).drop("_rescued_data")

# Step 2: Create target streaming table
# NOTE: This is idempotent - safe to keep after first run if schema doesn't change
dlt.create_streaming_table(
    name=f"{catalog}.{silver_schema}.policy",
    comment="Deduplicated policies (latest version only) with preserved metadata",
    table_properties={
        "quality": "silver"
    }
)

# Step 3: Apply CDC flow (replaces manual watermark + merge logic)
dlt.apply_changes(
    target=f"{catalog}.{silver_schema}.policy",
    source="policy_transformed",  # Reference the transformed view
    keys=["policy_no"],  # Primary key for deduplication
    sequence_by="pol_issue_date",  # Use pol_issue_date for ordering changes (matches your manual watermark_column)
    stored_as_scd_type=1  # Keep latest version only (SCD Type 1)
)


# --- CLEAN CLAIM (CDC Pattern) ---

# Step 1: Temporary view with transformations
@dlt.view(
    comment="Cleaned claim data before CDC processing"
)
@dlt.expect_all({
    "valid_claim_number": "claim_no IS NOT NULL",
    "valid_incident_hour": "incident_hour BETWEEN 0 AND 23"
})
def claim_transformed():
    """Apply claim data transformations before CDC deduplication"""
    df = dlt.readStream(f"{catalog}.{bronze_schema}.claim")
    # In our case data is already correct from bronze since it was sourced from MySQL
    # Just drop _rescued_data and preserve all other fields including metadata
    return df.drop("_rescued_data")

# Step 2: Create target streaming table
# NOTE: This is idempotent - safe to keep after first run if schema doesn't change
dlt.create_streaming_table(
    name=f"{catalog}.{silver_schema}.claim",
    comment="Deduplicated claims (latest version only) with preserved metadata",
    table_properties={
        "quality": "silver"
    }
)

# Step 3: Apply CDC flow (replaces manual watermark + merge logic)
dlt.apply_changes(
    target=f"{catalog}.{silver_schema}.claim",
    source="claim_transformed",  # Reference the transformed view
    keys=["claim_no", "policy_no"],  # Composite primary key for deduplication
    sequence_by="claim_date",  # Use claim_date for ordering changes (matches your manual watermark_column)
    stored_as_scd_type=1  # Keep latest version only (SCD Type 1)
)

# --- CLEAN CUSTOMER (CDC Pattern) ---
"""
For silver customer table:
✅ Adding columns to .select() → just run pipeline
✅ Changing transformation logic → just run pipeline
✅ Adding computed columns → just run pipeline
❌ Incompatible type changes → drop first
❌ Changing primary keys → drop first
⚠️ Removing columns → works but messy, consider dropping for cleanliness

\if need drop the table, probably you will need Start pipeline with "Full refresh for all datasets" option
You'll only need to drop the table in rare cases (type changes, key changes), not for normal schema additions!
"""
# Step 1: Temporary view with transformations
@dlt.view(
    comment="Transformed customer data before CDC processing"
)
@dlt.expect("valid_customer_id", "customer_id IS NOT NULL")
def customer_transformed():
    """Apply all data transformations before CDC deduplication"""
    df = dlt.readStream(f"{catalog}.{bronze_schema}.customer")

    name_normalized = when(
        size(split(trim(col("name")), ",")) == 2,
        concat(
            initcap(trim(split(col("name"), ",").getItem(1))), lit(" "),
            initcap(trim(split(col("name"), ",").getItem(0)))
        )
    ).otherwise(initcap(trim(col("name"))))

    return (
        df
        .withColumn("date_of_birth", to_date(col("date_of_birth"), "dd-MM-yyyy"))
        .withColumn("firstname", split(name_normalized, " ").getItem(0))
        .withColumn("lastname", split(name_normalized, " ").getItem(1))
        .withColumn("address", concat(col("borough"), lit(", "), col("zip_code")))
        # Preserve all metadata for CDC tracking
        .select(
            "customer_id", "date_of_birth", "borough", "neighborhood", "zip_code",
            "firstname", "lastname", "address", 
            "ingested_at", "source_file"
        )
    )

# Step 2: Create target streaming table
# NOTE: This is idempotent - safe to keep after first run if schema doesn't change
dlt.create_streaming_table(
    name=f"{catalog}.{silver_schema}.customer",
    comment="Deduplicated customers (latest version only) - source for SCD",
    table_properties={
        "quality": "silver"
    }
)

# Step 3: Apply CDC flow (replaces manual watermark + merge logic)
dlt.apply_changes(
    target=f"{catalog}.{silver_schema}.customer",
    source="customer_transformed",  # Reference the transformed view
    keys=["customer_id"],  # Primary key for deduplication
    sequence_by="ingested_at",  # Use its existing timestamp for ordering changes
    stored_as_scd_type=1  # Keep latest version only (SCD Type 1)
)

"""
# --- CLEAN TRAINING IMAGES ---
@dlt.table(
    name=f"{catalog}.{silver_schema}.training_images",
    comment="Enriched accident training images",
    table_properties={
        "quality": "silver"
    }
)
def training_images():
    df = dlt.readStream(f"{catalog}.{bronze_schema}.training_images")
    return df.withColumn(
        "label",
        regexp_extract("path", r"/(\d+)-([a-zA-Z]+)(?: \(\d+\))?\.png$", 2)
    )

# --- CLEAN CLAIM IMAGES ---
@dlt.table(
    name=f"{catalog}.{silver_schema}.claim_images",
    comment="Enriched claim images",
    table_properties={
        "quality": "silver"
    }
)
def training_images():
    df = dlt.readStream(f"{catalog}.{bronze_schema}.claim_images")
    return df.withColumn("image_name", regexp_extract(col("path"), r".*/(.*?.jpg)", 1))
"""