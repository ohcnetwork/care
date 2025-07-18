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
from django.db import transaction
from care.emr.models.patient import Patient
from care.emr.models.organization import Organization

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

def create_test_patient(phone_number, name, age=None, gender='Male'):
    """Register a test patient with minimal requirements"""
    normalized_phone = normalize_phone_number(phone_number)
    
    # Check if patient already exists
    existing_patient = Patient.objects.filter(phone_number=normalized_phone).first()
    if existing_patient:
        print(f'✅ Patient with phone {normalized_phone} already exists: {existing_patient.name}')
        print(f'Patient ID: {existing_patient.external_id}')
        return existing_patient

    try:
        with transaction.atomic():
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

            # Create patient with minimal required fields
            patient_data = {
                'external_id': str(uuid.uuid4()),
                'name': name,
                'phone_number': normalized_phone,
                'geo_organization': organization,  # Using geo_organization instead of organization
                'gender': gender,
                'blood_group': 'O+',  # Default blood group
            }
            
            if age:
                from datetime import date, timedelta
                birth_date = date.today() - timedelta(days=age * 365)
                patient_data['date_of_birth'] = birth_date

            patient = Patient.objects.create(**patient_data)
            
            print(f'✅ Successfully registered patient: {patient.name} ({patient.phone_number})')
            print(f'Patient ID: {patient.external_id}')
            print(f'Organization: {patient.geo_organization.name}')
            return patient
            
    except Exception as e:
        print(f'❌ Error registering patient: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("CARE WhatsApp Bot - Create Test Patient")
    print("=======================================")
    
    # Create a test patient named John Doe
    phone = "+918767341918"  # Using the user's phone number
    name = "John Doe"       
    age = 35                
    gender = "Male"          
    
    print(f"Creating test patient:")
    print(f"Phone: {phone}")
    print(f"Name: {name}")
    print(f"Age: {age}")
    print(f"Gender: {gender}")
    print()
    
    create_test_patient(phone, name, age, gender)