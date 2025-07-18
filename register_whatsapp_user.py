#!/usr/bin/env python3

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('/Users/ashu/care')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import uuid
from django.contrib.auth import get_user_model
from django.db import transaction
from care.emr.models.patient import Patient
from care.emr.models.organization import Organization

User = get_user_model()

def normalize_phone_number(phone_number):
    """Normalize phone number format"""
    phone = ''.join(filter(str.isdigit, phone_number))
    
    if len(phone) == 10:
        phone = f"+91{phone}"
    elif len(phone) == 12 and phone.startswith('91'):
        phone = f"+{phone}"
    elif not phone.startswith('+'):
        phone = f"+{phone}"
    
    return phone

def register_patient(phone_number, name, age=None, gender='Male'):
    """Register a patient"""
    normalized_phone = normalize_phone_number(phone_number)
    
    # Check if patient already exists
    existing_patient = Patient.objects.filter(phone_number=normalized_phone).first()
    if existing_patient:
        print(f'Patient with phone {normalized_phone} already exists: {existing_patient.name}')
        return existing_patient

    try:
        # Get or create default organization
        organization, created = Organization.objects.get_or_create(
            name="Default Organization",
            defaults={
                'org_type': 'govt',
                'system_generated': True
            }
        )
        
        if created:
            print(f'Created default organization: {organization.name}')

        # Create patient
        patient_data = {
            'external_id': str(uuid.uuid4()),
            'name': name,
            'phone_number': normalized_phone,
            'organization': organization,
            'gender': gender,
        }
        
        if age:
            from datetime import date, timedelta
            birth_date = date.today() - timedelta(days=age * 365)
            patient_data['date_of_birth'] = birth_date

        patient = Patient.objects.create(**patient_data)
        
        print(f'Successfully registered patient: {patient.name} ({patient.phone_number})')
        print(f'Patient ID: {patient.external_id}')
        return patient
        
    except Exception as e:
        print(f'Error registering patient: {str(e)}')
        return None

def register_staff_simple(phone_number, name, email=None, user_type='Staff'):
    """Register a staff member with minimal requirements"""
    normalized_phone = normalize_phone_number(phone_number)
    
    # Check if user already exists
    existing_user = User.objects.filter(phone_number=normalized_phone).first()
    if existing_user:
        print(f'Staff with phone {normalized_phone} already exists: {existing_user.get_full_name()}')
        return existing_user

    try:
        if not email:
            # Generate email from phone number
            email = f"user_{normalized_phone.replace('+', '').replace('-', '')}@care.local"

        # Generate username from phone number
        username = f"user_{normalized_phone.replace('+', '').replace('-', '')}"
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1

        # Parse name
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create user with minimal required fields
        user_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': normalized_phone,
            'verified': True,
        }

        user = User.objects.create_user(password='temp_password_123', **user_data)
        
        print(f'Successfully registered staff: {user.get_full_name()} ({user.phone_number})')
        print(f'Username: {user.username}')
        print(f'Email: {user.email}')
        print('Default password set to: temp_password_123 (please change after first login)')
        return user
        
    except Exception as e:
        print(f'Error registering staff: {str(e)}')
        return None

if __name__ == "__main__":
    print("CARE WhatsApp Bot User Registration")
    print("===================================")
    
    # Get user input
    phone = input("Enter your phone number (e.g., +919876543210): ").strip()
    name = input("Enter your full name: ").strip()
    user_type = input("Register as (patient/staff) [patient]: ").strip().lower() or 'patient'
    
    if user_type == 'patient':
        age = input("Enter your age (optional): ").strip()
        age = int(age) if age.isdigit() else None
        gender = input("Enter your gender (Male/Female/Non-binary) [Male]: ").strip() or 'Male'
        
        result = register_patient(phone, name, age, gender)
    else:
        email = input("Enter your email (optional): ").strip() or None
        result = register_staff_simple(phone, name, email)
    
    if result:
        print(f"\n✅ Registration successful!")
        print(f"You can now use the WhatsApp bot with phone number: {phone}")
        print("Send 'login' to the bot to start authentication.")
    else:
        print("\n❌ Registration failed!")