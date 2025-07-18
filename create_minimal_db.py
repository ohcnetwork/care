#!/usr/bin/env python3
"""
Create minimal database for testing WhatsApp bot functionality
"""

import os
import sys
import django
import sqlite3

# Add the project directory to the Python path
sys.path.insert(0, '/Users/ashu/care')

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
os.environ.setdefault('DJANGO_READ_DOT_ENV_FILE', 'True')
os.environ.setdefault('DATABASE_URL', 'sqlite:///db.sqlite3')

def create_minimal_database():
    """Create minimal database with essential tables"""
    db_path = '/Users/ashu/care/db.sqlite3'
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️  Removed existing database: {db_path}")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔨 Creating minimal database tables...")
    
    # Create users_user table with minimal fields
    cursor.execute('''
        CREATE TABLE users_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password VARCHAR(128) NOT NULL,
            last_login DATETIME,
            is_superuser BOOLEAN NOT NULL,
            username VARCHAR(150) UNIQUE NOT NULL,
            first_name VARCHAR(150) NOT NULL,
            last_name VARCHAR(150) NOT NULL,
            email VARCHAR(254) NOT NULL,
            is_staff BOOLEAN NOT NULL,
            is_active BOOLEAN NOT NULL,
            date_joined DATETIME NOT NULL,
            external_id VARCHAR(36) UNIQUE NOT NULL,
            user_type VARCHAR(100),
            old_user_type INTEGER,
            created_by_id INTEGER,
            ward_id INTEGER,
            phone_number VARCHAR(14) NOT NULL,
            alt_phone_number VARCHAR(14),
            verified BOOLEAN NOT NULL DEFAULT 0,
            deleted BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    # Create emr_patient table with minimal fields
    cursor.execute('''
        CREATE TABLE emr_patient (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id VARCHAR(36) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            phone_number VARCHAR(14) NOT NULL,
            date_of_birth DATE,
            gender VARCHAR(100),
            created_date DATETIME NOT NULL,
            modified_date DATETIME NOT NULL,
            deleted BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    
    # Create django_migrations table
    cursor.execute('''
        CREATE TABLE django_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied DATETIME NOT NULL
        )
    ''')
    
    # Create django_content_type table
    cursor.execute('''
        CREATE TABLE django_content_type (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_label VARCHAR(100) NOT NULL,
            model VARCHAR(100) NOT NULL,
            UNIQUE(app_label, model)
        )
    ''')
    
    # Create auth_permission table
    cursor.execute('''
        CREATE TABLE auth_permission (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            content_type_id INTEGER NOT NULL,
            codename VARCHAR(100) NOT NULL,
            UNIQUE(content_type_id, codename)
        )
    ''')
    
    # Create auth_group table
    cursor.execute('''
        CREATE TABLE auth_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(150) UNIQUE NOT NULL
        )
    ''')
    
    # Create auth_group_permissions table
    cursor.execute('''
        CREATE TABLE auth_group_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            UNIQUE(group_id, permission_id)
        )
    ''')
    
    # Create users_user_groups table
    cursor.execute('''
        CREATE TABLE users_user_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            UNIQUE(user_id, group_id)
        )
    ''')
    
    # Create users_user_user_permissions table
    cursor.execute('''
        CREATE TABLE users_user_user_permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            UNIQUE(user_id, permission_id)
        )
    ''')
    
    # Insert some migration records to prevent Django from trying to run migrations
    cursor.execute('''
        INSERT INTO django_migrations (app, name, applied) VALUES 
        ('users', '0001_initial_squashed', datetime('now')),
        ('users', '0002_auto_20230613_1622', datetime('now')),
        ('users', '0003_auto_20230613_1657', datetime('now')),
        ('users', '0021_rename_gender_user_old_gender_user_geo_organization_and_more', datetime('now')),
        ('emr', '0001_initial', datetime('now')),
        ('contenttypes', '0001_initial', datetime('now')),
        ('contenttypes', '0002_remove_content_type_name', datetime('now')),
        ('auth', '0001_initial', datetime('now')),
        ('auth', '0012_alter_user_first_name_max_length', datetime('now'))
    ''')
    
    # Insert dummy data for a hospital staff user
    cursor.execute('''
        INSERT INTO users_user (
            id, password, last_login, is_superuser, username, first_name, last_name, 
            email, is_staff, is_active, date_joined, external_id, user_type, old_user_type,
            created_by_id, ward_id, phone_number, alt_phone_number, verified, deleted
        ) VALUES (
            1, 'pbkdf2_sha256$600000$dummy$hash', NULL, 0, 'testuser', 'Test', 'User',
            'test@example.com', 1, 1, '2023-01-01 00:00:00', 'test-uuid-1234', 'HOSPITAL_STAFF', 15,
            NULL, NULL, '919876543211', NULL, 1, 0
        )
    ''')
    
    # Create a test patient
    cursor.execute('''
        INSERT INTO emr_patient (
            external_id, name, phone_number, date_of_birth, gender,
            created_date, modified_date, deleted
        ) VALUES (
            'patient-uuid-123', 'Test Patient', '+918767341919', '1990-01-01', 'Male',
            datetime('now'), datetime('now'), 0
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ Minimal database created successfully!")
    print(f"📍 Database location: {db_path}")
    print("👤 Test user: +918767341918 (hospital staff)")
    print("🏥 Test patient: +918767341919 (patient)")

if __name__ == "__main__":
    create_minimal_database()