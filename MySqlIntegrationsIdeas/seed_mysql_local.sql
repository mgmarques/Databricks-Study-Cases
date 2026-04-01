-- ============================================================================
-- MySQL Database Seeder for Claims Data
-- ============================================================================
-- Run this script on your LOCAL MACHINE where MySQL localhost is accessible.
--
-- Usage:
--   mysql -u databricks_cdc -p claims_dev < seed_mysql_local.sql
--
-- Or from MySQL command line:
--   mysql> source /path/to/seed_mysql_local.sql;
-- ============================================================================

USE claims_dev;

-- ============================================================================
-- DROP TABLES (optional - uncomment if you want to start fresh)
-- ============================================================================

-- DROP TABLE IF EXISTS claim;
-- DROP TABLE IF EXISTS policy;
-- DROP TABLE IF EXISTS customer;

-- ============================================================================
-- CREATE TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS policy (
    policy_no VARCHAR(50) PRIMARY KEY,
    cust_id DOUBLE,
    policytype VARCHAR(50),
    pol_issue_date DATE,
    pol_eff_date DATE,
    pol_expiry_date DATE,
    make VARCHAR(50),
    model VARCHAR(100),
    model_year VARCHAR(10),
    chassis_no VARCHAR(50),
    use_of_vehicle VARCHAR(50),
    product VARCHAR(50),
    sum_insured DOUBLE,
    premium DOUBLE,
    deductable INT
);

CREATE TABLE IF NOT EXISTS claim (
    claim_no VARCHAR(50) PRIMARY KEY,
    policy_no VARCHAR(50),
    claim_date DATE,
    months_as_customer INT,
    injury INT,
    property INT,
    vehicle INT,
    total INT,
    collision_type VARCHAR(50),
    number_of_vehicles_involved INT,
    driver_age DOUBLE,
    insured_relationship VARCHAR(50),
    license_issue_date DATE,
    incident_date DATE,
    incident_hour INT,
    incident_type VARCHAR(100),
    incident_severity VARCHAR(50),
    number_of_witnesses INT,
    suspicious_activity BOOLEAN
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id INT PRIMARY KEY,
    date_of_birth VARCHAR(50),
    borough VARCHAR(50),
    neighborhood VARCHAR(100),
    zip_code VARCHAR(20),
    name VARCHAR(100)
);

-- ============================================================================
-- TRUNCATE TABLES (optional - uncomment if you want to clear existing data)
-- ============================================================================

-- TRUNCATE TABLE policy;
-- TRUNCATE TABLE claim;
-- TRUNCATE TABLE customer;

-- ============================================================================
-- LOAD DATA FROM CSV FILES
-- ============================================================================
-- 
-- IMPORTANT: Update the file paths below to match your local CSV locations
-- 
-- For LOAD DATA INFILE to work:
--   1. CSV files must be accessible to MySQL server
--   2. MySQL user needs FILE privilege: GRANT FILE ON *.* TO 'databricks_cdc'@'localhost';
--   3. Check secure_file_priv setting: SHOW VARIABLES LIKE 'secure_file_priv';
--      If set, place CSVs in that directory OR disable it temporarily
-- ============================================================================

-- Load policies.csv (with column name transformation: UPPERCASE -> lowercase)
LOAD DATA LOCAL INFILE '/path/to/your/policies.csv'
INTO TABLE policy
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(policy_no, cust_id, policytype, pol_issue_date, pol_eff_date, pol_expiry_date, 
 make, model, model_year, chassis_no, use_of_vehicle, product, sum_insured, 
 premium, deductable);

-- Load claims.csv (with column name transformations)
LOAD DATA LOCAL INFILE '/path/to/your/claims.csv'
INTO TABLE claim
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(claim_no, policy_no, claim_date, months_as_customer, injury, property, vehicle, 
 total, collision_type, number_of_vehicles_involved, @age, insured_relationship, 
 license_issue_date, @date, @hour, @type, @severity, number_of_witnesses, 
 suspicious_activity)
SET 
    driver_age = @age,
    incident_date = @date,
    incident_hour = @hour,
    incident_type = @type,
    incident_severity = @severity;

-- Load customers.csv
LOAD DATA LOCAL INFILE '/path/to/your/customers.csv'
INTO TABLE customer
FIELDS TERMINATED BY ',' 
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(customer_id, date_of_birth, borough, neighborhood, zip_code, name);

-- ============================================================================
-- VERIFY DATA LOADED
-- ============================================================================

SELECT 'policy' AS table_name, COUNT(*) AS row_count FROM policy
UNION ALL
SELECT 'claim' AS table_name, COUNT(*) AS row_count FROM claim
UNION ALL
SELECT 'customer' AS table_name, COUNT(*) AS row_count FROM customer;

-- ============================================================================
-- SAMPLE DATA VERIFICATION
-- ============================================================================

SELECT 'Policy Sample' AS section;
SELECT * FROM policy LIMIT 5;

SELECT 'Claim Sample' AS section;
SELECT * FROM claim LIMIT 5;

SELECT 'Customer Sample' AS section;
SELECT * FROM customer LIMIT 5;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 
-- If LOAD DATA INFILE doesn't work due to secure_file_priv restrictions,
-- you can:
-- 
-- Option 1: Use LOAD DATA LOCAL INFILE (as shown above)
--   Enable it: mysql --local-infile=1 -u databricks_cdc -p claims_dev
-- 
-- Option 2: Use the Python script instead (seed_mysql_local.py)
-- 
-- Option 3: Disable secure_file_priv in my.cnf:
--   [mysqld]
--   secure_file_priv = ""
--   Then restart MySQL
-- 
-- ============================================================================