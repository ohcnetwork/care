#!/usr/bin/env python3

import uuid
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from care.emr.models.patient import Patient
from care.emr.models.organization import Organization
from care.users.models import State, District, LocalBody
from care.facility.models import Facility

User = get_user_model()


class Command(BaseCommand):
    help = 'Register a phone number in CARE database for WhatsApp bot access'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            required=True,
            help='Phone number to register (e.g., +919876543210)'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['patient', 'staff'],
            required=True,
            help='User type: patient or staff'
        )
        parser.add_argument(
            '--name',
            type=str,
            required=True,
            help='Full name of the user'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address (required for staff)'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username (required for staff, auto-generated if not provided)'
        )
        parser.add_argument(
            '--user-type',
            type=str,
            choices=['Doctor', 'Nurse', 'Staff', 'Volunteer'],
            default='Staff',
            help='Staff user type (default: Staff)'
        )
        parser.add_argument(
            '--gender',
            type=str,
            choices=['Male', 'Female', 'Non-binary'],
            default='Male',
            help='Gender (default: Male)'
        )
        parser.add_argument(
            '--age',
            type=int,
            help='Age (for patients)'
        )

    def handle(self, *args, **options):
        phone_number = options['phone']
        user_type = options['type']
        name = options['name']
        
        # Normalize phone number
        normalized_phone = self.normalize_phone_number(phone_number)
        
        try:
            with transaction.atomic():
                if user_type == 'patient':
                    self.register_patient(normalized_phone, name, options)
                else:
                    self.register_staff(normalized_phone, name, options)
                    
        except Exception as e:
            raise CommandError(f'Registration failed: {str(e)}')

    def normalize_phone_number(self, phone_number):
        """Normalize phone number format"""
        phone = ''.join(filter(str.isdigit, phone_number))
        
        if len(phone) == 10:
            phone = f"+91{phone}"
        elif len(phone) == 12 and phone.startswith('91'):
            phone = f"+{phone}"
        elif not phone.startswith('+'):
            phone = f"+{phone}"
        
        return phone

    def register_patient(self, phone_number, name, options):
        """Register a patient"""
        # Check if patient already exists
        existing_patient = Patient.objects.filter(phone_number=phone_number).first()
        if existing_patient:
            self.stdout.write(
                self.style.WARNING(f'Patient with phone {phone_number} already exists: {existing_patient.name}')
            )
            return existing_patient

        # Get or create default organization
        organization, created = Organization.objects.get_or_create(
            name="Default Organization",
            defaults={
                'org_type': 'govt',
                'system_generated': True
            }
        )
        
        if created:
            self.stdout.write(f'Created default organization: {organization.name}')

        # Create patient
        patient_data = {
            'external_id': str(uuid.uuid4()),
            'name': name,
            'phone_number': phone_number,
            'organization': organization,
            'gender': options.get('gender', 'Male'),
        }
        
        if options.get('age'):
            from datetime import date, timedelta
            birth_date = date.today() - timedelta(days=options['age'] * 365)
            patient_data['date_of_birth'] = birth_date

        patient = Patient.objects.create(**patient_data)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully registered patient: {patient.name} ({patient.phone_number})')
        )
        self.stdout.write(f'Patient ID: {patient.external_id}')
        return patient

    def register_staff(self, phone_number, name, options):
        """Register a staff member"""
        # Check if user already exists
        existing_user = User.objects.filter(phone_number=phone_number).first()
        if existing_user:
            self.stdout.write(
                self.style.WARNING(f'Staff with phone {phone_number} already exists: {existing_user.get_full_name()}')
            )
            return existing_user

        email = options.get('email')
        if not email:
            # Generate email from phone number
            email = f"user_{phone_number.replace('+', '').replace('-', '')}@care.local"

        username = options.get('username')
        if not username:
            # Generate username from phone number
            username = f"user_{phone_number.replace('+', '').replace('-', '')}"

        # Ensure username is unique
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1

        # Get default location data
        state, _ = State.objects.get_or_create(name="Kerala")
        district, _ = District.objects.get_or_create(
            name="Thiruvananthapuram", 
            defaults={'state': state}
        )
        local_body, _ = LocalBody.objects.get_or_create(
            name="Thiruvananthapuram Corporation",
            defaults={'district': district, 'body_type': 20}
        )

        # Parse name
        name_parts = name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create user
        user_data = {
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone_number,
            'user_type': options.get('user_type', 'Staff'),
            'gender': options.get('gender', 'Male'),
            'state': state,
            'district': district,
            'local_body': local_body,
            'verified': True,
        }

        user = User.objects.create_user(password='temp_password_123', **user_data)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully registered staff: {user.get_full_name()} ({user.phone_number})')
        )
        self.stdout.write(f'Username: {user.username}')
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write(f'User Type: {user.user_type}')
        self.stdout.write(
            self.style.WARNING('Default password set to: temp_password_123 (please change after first login)')
        )
        return user