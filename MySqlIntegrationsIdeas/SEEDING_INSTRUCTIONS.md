# MySQL Seeding Instructions for Claims Data

## Overview

This guide provides two options for seeding your local MySQL database with claims data:
1. **Python script** (`seed_mysql_local.py`) - Recommended
2. **SQL script** (`seed_mysql_local.sql`) - Alternative

Both scripts handle the column transformations required and populate the three tables: `policy`, `claim`, and `customer`.

---

## Prerequisites

### 1. MySQL Server Running Locally
- MySQL should be running on `localhost:3306`
- Database `claims_dev` should exist
- User `databricks_cdc` with password `secure_password` should have privileges

```sql
CREATE DATABASE IF NOT EXISTS claims_dev;
CREATE USER IF NOT EXISTS 'databricks_cdc'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON claims_dev.* TO 'databricks_cdc'@'localhost';
FLUSH PRIVILEGES;
```

### 2. Download CSV Files from Databricks

The CSV files are currently in your Databricks volume:
- `/Volumes/smart_claims_dev/00_landing/claimsdb/policies.csv`
- `/Volumes/smart_claims_dev/00_landing/claimsdb/claims.csv`
- `/Volumes/smart_claims_dev/00_landing/claimsdb/customers.csv`

**Download them to your local machine** to a directory like `./csv_data/`

---

## Option 1: Python Script (Recommended)

### Setup

1. **Install dependencies:**
   ```bash
   pip install mysql-connector-python pandas
   ```

2. **Download the script:**
   - Get `seed_mysql_local.py` from your Databricks workspace
   - Save it to your local machine

3. **Update configuration in the script:**
   ```python
   # Update CSV directory path
   CSV_DIR = './csv_data'  # Change to your local CSV directory
   
   # Update MySQL config if different
   MYSQL_CONFIG = {
       'host': '127.0.0.1',
       'port': 3306,
       'database': 'claims_dev',
       'user': 'databricks_cdc',
       'password': 'secure_password'
   }
   ```

### Run

```bash
python seed_mysql_local.py
```

### What It Does

✓ Connects to MySQL localhost  
✓ Creates tables if they don't exist  
✓ Truncates existing data (optional)  
✓ Reads CSV files with pandas  
✓ Applies column transformations:  
  - Policies: UPPERCASE → lowercase  
  - Claims: age→driver_age, date→incident_date, etc.  
  - Customers: Cast customer_id to INT  
✓ Inserts data in batches (1000 rows)  
✓ Verifies row counts  

### Expected Output

```
================================================================================
MySQL Database Seeder - Claims Data
================================================================================

✓ CSV directory found: ./csv_data
✓ Connected to MySQL database: claims_dev

Creating tables...
  ✓ Table 'policy' ready
  ✓ Table 'claim' ready
  ✓ Table 'customer' ready

...

Verifying row counts...
================================================================================
  policy           12,237 rows
  claim            12,991 rows
  customer          7,061 rows
================================================================================

################################################################################
# SEEDING COMPLETE!
################################################################################
```

---

## Option 2: SQL Script

### Setup

1. **Download the script:**
   - Get `seed_mysql_local.sql` from your Databricks workspace

2. **Update file paths in the script:**
   ```sql
   -- Change these paths to your local CSV locations
   LOAD DATA LOCAL INFILE '/path/to/your/policies.csv'
   LOAD DATA LOCAL INFILE '/path/to/your/claims.csv'
   LOAD DATA LOCAL INFILE '/path/to/your/customers.csv'
   ```

### Run

**From command line:**
```bash
mysql --local-infile=1 -u databricks_cdc -p claims_dev < seed_mysql_local.sql
```

**From MySQL command line:**
```sql
mysql> source /path/to/seed_mysql_local.sql;
```

### Troubleshooting LOAD DATA INFILE

If you get errors about `secure_file_priv`:

1. **Check the setting:**
   ```sql
   SHOW VARIABLES LIKE 'secure_file_priv';
   ```

2. **Solutions:**
   - Place CSV files in the allowed directory
   - Use `--local-infile=1` flag (as shown above)
   - Disable `secure_file_priv` in `my.cnf` (requires MySQL restart)

---

## Verification

After seeding, verify the data:

```sql
-- Row counts
SELECT 'policy' AS table_name, COUNT(*) AS row_count FROM policy
UNION ALL
SELECT 'claim', COUNT(*) FROM claim
UNION ALL
SELECT 'customer', COUNT(*) FROM customer;

-- Sample data
SELECT * FROM policy LIMIT 5;
SELECT * FROM claim LIMIT 5;
SELECT * FROM customer LIMIT 5;
```

**Expected counts:**
- `policy`: 12,237 rows
- `claim`: 12,991 rows
- `customer`: 7,061 rows

---

## ⚠️ IMPORTANT: Databricks Connectivity Issue

### The Problem

While you can now seed MySQL locally, **Databricks serverless compute cannot connect to `127.0.0.1` (localhost)**. When your Databricks notebook runs, `localhost` refers to the cluster node, not your local machine.

### Solutions for Incremental Ingestion

To use the incremental ingestion notebook with MySQL, you need ONE of these:

#### Option A: Cloud-Hosted MySQL (Recommended for Production)

**Use AWS RDS MySQL:**
1. Create RDS MySQL instance in AWS
2. Configure security group to allow Databricks IPs
3. Update connection string to RDS endpoint:
   ```python
   jdbc_url = "jdbc:mysql://mydb.xxxxx.us-east-1.rds.amazonaws.com:3306/claims_dev"
   ```
4. Seed RDS with the same scripts (change host to RDS endpoint)

**Benefits:**
- Works with Databricks serverless ✓
- Production-ready ✓
- Scalable ✓

#### Option B: SSH Tunnel (For Development Only)

**Not available on serverless compute** - requires init script on classic cluster

#### Option C: Delta-to-Delta Learning Lab

**Skip MySQL entirely for learning purposes:**
1. Load CSVs → Delta tables (simulates MySQL source)
2. Practice incremental ingestion patterns
3. Learn watermark-based CDC
4. Same concepts, different source

**Benefits:**
- Works on serverless ✓
- Immediate start ✓
- All incremental patterns ✓

---

## Next Steps

### If You Have AWS RDS MySQL:
1. ✓ Seed local MySQL (done with these scripts)
2. Create RDS MySQL instance
3. Seed RDS with same data (update host in script)
4. Update Databricks notebook connection to RDS endpoint
5. Run incremental ingestion notebook

### If You Want to Learn Without MySQL:
1. ✓ Seed local MySQL (done - optional for reference)
2. Create Delta-to-Delta incremental ingestion lab
3. Practice watermark-based CDC patterns
4. Later apply to real MySQL when available

---

## Files in This Package

- `seed_mysql_local.py` - Python seeding script (recommended)
- `seed_mysql_local.sql` - SQL seeding script (alternative)
- `SEEDING_INSTRUCTIONS.md` - This file

---

## Support

If you encounter issues:
1. Verify MySQL is running: `mysql -u databricks_cdc -p`
2. Check database exists: `SHOW DATABASES;`
3. Verify user privileges: `SHOW GRANTS FOR 'databricks_cdc'@'localhost';`
4. Check CSV files are in the correct directory
5. Review error messages in script output
