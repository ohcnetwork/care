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

def register_patient_simple(phone_number, name, age=None, gender='Male'):
    """Register a patient with minimal requirements"""
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
                'organization': organization,
                'gender': gender,
            }
            
            if age:
                from datetime import date, timedelta
                birth_date = date.today() - timedelta(days=age * 365)
                patient_data['date_of_birth'] = birth_date

            patient = Patient.objects.create(**patient_data)
            
            print(f'✅ Successfully registered patient: {patient.name} ({patient.phone_number})')
            print(f'Patient ID: {patient.external_id}')
            print(f'Organization: {patient.organization.name}')
            return patient
            
    except Exception as e:
        print(f'❌ Error registering patient: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("CARE WhatsApp Bot Patient Registration")
    print("=====================================")
    
    # For now, let's register with your phone number
    # You can modify these values:
    phone = "+919876543210"  # Replace with your actual phone number
    name = "Test User"       # Replace with your actual name
    age = 30                 # Replace with your actual age (optional)
    gender = "Male"          # Replace with your gender
    
    print(f"Registering patient:")
    print(f"Phone: {phone}")
    print(f"Name: {name}")
    print(f"Age: {age}")
    print(f"Gender: {gender}")
    print()
    
    result = register_patient_simple(phone, name, age, gender)
    
    if result:
        print(f"\n🎉 Registration successful!")
        print(f"You can now use the WhatsApp bot with phone number: {phone}")
        print("Send 'login' to the bot to start authentication.")
        print("\nNext steps:")
        print("1. Send 'login' to your WhatsApp bot")
        print("2. You'll receive an OTP via SMS")
        print("3. Reply with the OTP to authenticate")
        print("4. Once authenticated, you can access your patient records!")
    else:
        print("\n❌ Registration failed!")