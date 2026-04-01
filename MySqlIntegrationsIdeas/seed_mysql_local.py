#!/usr/bin/env python3
"""
MySQL Database Seeder for Claims Data

This script seeds a local MySQL database with claims data from CSV files.
Run this on your LOCAL MACHINE where MySQL localhost is accessible.

Prerequisites:
  pip install mysql-connector-python pandas

Usage:
  python seed_mysql_local.py
"""

import mysql.connector
from mysql.connector import Error
import pandas as pd
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'claims_dev',
    'user': 'databricks_cdc',
    'password': 'secure_password'
}

# Update this path to where your CSV files are located
CSV_DIR = './csv_data'  # Change to your local CSV directory

CSV_FILES = {
    'policy': 'policies.csv',
    'claim': 'claims.csv',
    'customer': 'customers.csv'
}

# ============================================================================
# TABLE DDL STATEMENTS
# ============================================================================

CREATE_TABLES = {
    'policy': """
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
        )
    """,
    
    'claim': """
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
        )
    """,
    
    'customer': """
        CREATE TABLE IF NOT EXISTS customer (
            customer_id INT PRIMARY KEY,
            date_of_birth VARCHAR(50),
            borough VARCHAR(50),
            neighborhood VARCHAR(100),
            zip_code VARCHAR(20),
            name VARCHAR(100)
        )
    """
}

# ============================================================================
# COLUMN TRANSFORMATIONS
# ============================================================================

def transform_policies(df):
    """Transform policies dataframe: lowercase all columns"""
    df.columns = df.columns.str.lower()
    return df

def transform_claims(df):
    """Transform claims dataframe: rename specific columns"""
    column_mapping = {
        'age': 'driver_age',
        'date': 'incident_date',
        'hour': 'incident_hour',
        'type': 'incident_type',
        'severity': 'incident_severity'
    }
    df = df.rename(columns=column_mapping)
    return df

def transform_customers(df):
    """Transform customers dataframe: cast customer_id to int"""
    df['customer_id'] = df['customer_id'].astype(int)
    return df

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def create_connection():
    """Create MySQL database connection"""
    try:
        connection = mysql.connector.connect(**MYSQL_CONFIG)
        if connection.is_connected():
            print(f"✓ Connected to MySQL database: {MYSQL_CONFIG['database']}")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

def create_tables(connection):
    """Create tables if they don't exist"""
    print("\nCreating tables...")
    cursor = connection.cursor()
    
    for table_name, ddl in CREATE_TABLES.items():
        try:
            cursor.execute(ddl)
            print(f"  ✓ Table '{table_name}' ready")
        except Error as e:
            print(f"  ❌ Error creating table '{table_name}': {e}")
            return False
    
    connection.commit()
    cursor.close()
    return True

def truncate_tables(connection):
    """Truncate tables before inserting (optional)"""
    print("\nTruncating tables...")
    cursor = connection.cursor()
    
    for table_name in CREATE_TABLES.keys():
        try:
            cursor.execute(f"TRUNCATE TABLE {table_name}")
            print(f"  ✓ Truncated table '{table_name}'")
        except Error as e:
            print(f"  ⚠️  Could not truncate '{table_name}': {e}")
    
    connection.commit()
    cursor.close()

def insert_data(connection, table_name, df):
    """Insert dataframe into MySQL table"""
    print(f"\nInserting data into '{table_name}'...")
    print(f"  Rows to insert: {len(df):,}")
    
    cursor = connection.cursor()
    
    # Build INSERT statement
    columns = ', '.join([f"`{col}`" for col in df.columns])
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    
    # Convert DataFrame to list of tuples
    data = [tuple(row) for row in df.values]
    
    # Insert in batches
    batch_size = 1000
    inserted = 0
    
    try:
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            cursor.executemany(insert_query, batch)
            connection.commit()
            
            inserted += len(batch)
            print(f"  Progress: {inserted:,} / {len(df):,} rows ({inserted*100//len(df)}%)")
        
        print(f"  ✓ Successfully inserted {inserted:,} rows into '{table_name}'")
        cursor.close()
        return True
        
    except Error as e:
        print(f"  ❌ Error inserting data: {e}")
        connection.rollback()
        cursor.close()
        return False

def verify_counts(connection):
    """Verify row counts in all tables"""
    print("\n" + "="*80)
    print("Verifying row counts...")
    print("="*80)
    
    cursor = connection.cursor()
    
    for table_name in CREATE_TABLES.keys():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  {table_name:<15} {count:>10,} rows")
        except Error as e:
            print(f"  {table_name:<15} ❌ Error: {e}")
    
    print("="*80)
    cursor.close()

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*80)
    print("MySQL Database Seeder - Claims Data")
    print("="*80)
    
    # Check CSV directory
    csv_path = Path(CSV_DIR)
    if not csv_path.exists():
        print(f"\n❌ CSV directory not found: {CSV_DIR}")
        print(f"\nPlease create the directory and place your CSV files there:")
        print(f"  - {CSV_FILES['policy']}")
        print(f"  - {CSV_FILES['claim']}")
        print(f"  - {CSV_FILES['customer']}")
        return
    
    print(f"\n✓ CSV directory found: {CSV_DIR}")
    
    # Connect to MySQL
    connection = create_connection()
    if not connection:
        return
    
    try:
        # Create tables
        if not create_tables(connection):
            return
        
        # Truncate tables (comment out if you want to append instead)
        truncate_tables(connection)
        
        # Process and insert policies
        print(f"\n{'='*80}")
        print("Processing policies...")
        print(f"{'='*80}")
        policies_file = csv_path / CSV_FILES['policy']
        if policies_file.exists():
            df = pd.read_csv(policies_file)
            print(f"  Read {len(df):,} rows from {CSV_FILES['policy']}")
            df = transform_policies(df)
            insert_data(connection, 'policy', df)
        else:
            print(f"  ⚠️  File not found: {policies_file}")
        
        # Process and insert claims
        print(f"\n{'='*80}")
        print("Processing claims...")
        print(f"{'='*80}")
        claims_file = csv_path / CSV_FILES['claim']
        if claims_file.exists():
            df = pd.read_csv(claims_file)
            print(f"  Read {len(df):,} rows from {CSV_FILES['claim']}")
            df = transform_claims(df)
            insert_data(connection, 'claim', df)
        else:
            print(f"  ⚠️  File not found: {claims_file}")
        
        # Process and insert customers
        print(f"\n{'='*80}")
        print("Processing customers...")
        print(f"{'='*80}")
        customers_file = csv_path / CSV_FILES['customer']
        if customers_file.exists():
            df = pd.read_csv(customers_file)
            print(f"  Read {len(df):,} rows from {CSV_FILES['customer']}")
            df = transform_customers(df)
            insert_data(connection, 'customer', df)
        else:
            print(f"  ⚠️  File not found: {customers_file}")
        
        # Verify
        verify_counts(connection)
        
        print("\n" + "#"*80)
        print("# SEEDING COMPLETE!")
        print("#"*80)
        print("\nYour MySQL database is now populated with claims data.")
        print("\n⚠️  IMPORTANT: To use this with Databricks incremental ingestion,")
        print("you'll need to either:")
        print("  1. Use a cloud-hosted MySQL (AWS RDS, Azure MySQL, etc.)")
        print("  2. Set up SSH tunneling or VPN to access localhost from Databricks")
        
    finally:
        if connection.is_connected():
            connection.close()
            print("\n✓ MySQL connection closed")

if __name__ == "__main__":
    main()
