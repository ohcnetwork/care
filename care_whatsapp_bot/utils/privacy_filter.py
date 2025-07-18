import logging
from typing import Dict, Any, Optional
from datetime import datetime

from django.utils import timezone
from care.emr.models.patient import Patient
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.facility.models import PatientConsultation
from care.users.models import User

logger = logging.getLogger(__name__)


class PrivacyFilter:
    """Filter sensitive patient data before sending via WhatsApp"""
    
    # Sensitive fields that should never be shared via WhatsApp
    SENSITIVE_FIELDS = {
        'social_security_number',
        'national_id',
        'passport_number',
        'insurance_id',
        'emergency_contact_details',
        'next_of_kin',
        'financial_information',
        'detailed_medical_history',
        'psychiatric_notes',
        'substance_abuse_history',
        'genetic_information',
        'hiv_status',
        'mental_health_details'
    }
    
    # Fields that should be masked or abbreviated
    MASKABLE_FIELDS = {
        'phone_number',
        'address',
        'email',
        'detailed_diagnosis',
        'prescription_details'
    }
    
    def filter_patient_data(self, patient: Patient) -> Dict[str, Any]:
        """Filter patient data for patient's own view"""
        try:
            return {
                'patient_id': patient.external_id,
                'name': patient.name,
                'age': self._calculate_age(patient),
                'gender': patient.gender,
                'blood_group': patient.blood_group,
                'phone_number': self._mask_phone_number(patient.phone_number),
                'organization': patient.organization.name if patient.organization else None
            }
        except Exception as e:
            logger.error(f"Error filtering patient data: {e}")
            return {'error': 'Data unavailable'}
    
    def filter_patient_data_for_staff(self, patient: Patient, staff_user: User) -> Dict[str, Any]:
        """Filter patient data for hospital staff view"""
        try:
            # Staff gets more information but still filtered
            return {
                'patient_id': patient.external_id,
                'name': patient.name,
                'age': self._calculate_age(patient),
                'gender': patient.gender,
                'blood_group': patient.blood_group,
                'phone_masked': self._mask_phone_number(patient.phone_number),
                'organization': patient.organization.name if patient.organization else None,
                'created_date': patient.created_date.strftime('%Y-%m-%d') if patient.created_date else None
            }
        except Exception as e:
            logger.error(f"Error filtering patient data for staff: {e}")
            return {'error': 'Data unavailable'}
    
    def filter_encounter_data(self, encounter: Encounter) -> Dict[str, Any]:
        """Filter encounter data for patient view"""
        try:
            return {
                'encounter_id': encounter.external_id,
                'date': encounter.created_date.strftime('%Y-%m-%d') if encounter.created_date else 'Unknown',
                'encounter_type': self._get_encounter_type_display(encounter),
                'chief_complaint': self._filter_chief_complaint(encounter),
                'diagnosis': self._filter_diagnosis(encounter),
                'status': encounter.status if hasattr(encounter, 'status') else 'Unknown'
            }
        except Exception as e:
            logger.error(f"Error filtering encounter data: {e}")
            return {'error': 'Encounter data unavailable'}
    
    def filter_encounter_data_for_staff(self, encounter: Encounter, staff_user: User) -> Dict[str, Any]:
        """Filter encounter data for staff view"""
        try:
            # Staff gets similar information as patients for encounters
            return self.filter_encounter_data(encounter)
        except Exception as e:
            logger.error(f"Error filtering encounter data for staff: {e}")
            return {'error': 'Encounter data unavailable'}
    
    def filter_medication_data(self, medication_request: MedicationRequest) -> Dict[str, Any]:
        """Filter medication data"""
        try:
            return {
                'medication_id': medication_request.external_id,
                'medication_name': self._get_medication_name(medication_request),
                'dosage': self._filter_dosage(medication_request),
                'frequency': self._filter_frequency(medication_request),
                'instructions': self._filter_instructions(medication_request),
                'status': medication_request.status,
                'prescribed_date': medication_request.created_date.strftime('%Y-%m-%d') if medication_request.created_date else None
            }
        except Exception as e:
            logger.error(f"Error filtering medication data: {e}")
            return {'error': 'Medication data unavailable'}
    
    def filter_appointment_data(self, consultation: PatientConsultation) -> Dict[str, Any]:
        """Filter appointment/consultation data"""
        try:
            return {
                'consultation_id': consultation.external_id,
                'date': consultation.created_date.strftime('%Y-%m-%d') if consultation.created_date else 'Unknown',
                'facility_name': consultation.facility.name if consultation.facility else 'Unknown',
                'doctor_name': self._get_doctor_name(consultation),
                'consultation_type': self._get_consultation_type(consultation),
                'status': 'Scheduled'  # Simplified status
            }
        except Exception as e:
            logger.error(f"Error filtering appointment data: {e}")
            return {'error': 'Appointment data unavailable'}
    
    def filter_procedure_data(self, encounter: Encounter) -> Dict[str, Any]:
        """Filter procedure data from encounters"""
        try:
            return {
                'encounter_id': encounter.external_id,
                'date': encounter.created_date.strftime('%Y-%m-%d') if encounter.created_date else 'Unknown',
                'procedure_name': self._get_procedure_name(encounter),
                'facility_name': self._get_facility_name(encounter),
                'status': 'Completed'  # Simplified status
            }
        except Exception as e:
            logger.error(f"Error filtering procedure data: {e}")
            return {'error': 'Procedure data unavailable'}
    
    def _calculate_age(self, patient: Patient) -> Optional[str]:
        """Calculate patient age safely"""
        try:
            if patient.date_of_birth:
                today = timezone.now().date()
                age = today.year - patient.date_of_birth.year
                if today < patient.date_of_birth.replace(year=today.year):
                    age -= 1
                return f"{age} years"
            elif patient.year_of_birth:
                current_year = timezone.now().year
                age = current_year - patient.year_of_birth
                return f"~{age} years"
            return None
        except Exception:
            return None
    
    def _mask_phone_number(self, phone_number: str) -> str:
        """Mask phone number for privacy"""
        if not phone_number:
            return "Unavailable"
        
        if len(phone_number) > 4:
            return f"****{phone_number[-4:]}"
        return "****"
    
    def _get_encounter_type_display(self, encounter: Encounter) -> str:
        """Get user-friendly encounter type"""
        try:
            type_mapping = {
                'inpatient': 'Hospital Stay',
                'outpatient': 'Clinic Visit',
                'emergency': 'Emergency Visit',
                'virtual': 'Telemedicine',
                'home': 'Home Visit'
            }
            
            encounter_type = getattr(encounter, 'encounter_class', 'outpatient')
            return type_mapping.get(encounter_type, 'Medical Visit')
        except Exception:
            return 'Medical Visit'
    
    def _filter_chief_complaint(self, encounter: Encounter) -> Optional[str]:
        try:
            return "Medical consultation"
        except Exception:
            return None
    
    def _filter_diagnosis(self, encounter: Encounter) -> Optional[str]:
        try:
            return "As per medical assessment"
        except Exception:
            return None
    
    def _get_medication_name(self, medication_request: MedicationRequest) -> str:
        """Get medication name safely"""
        try:
            return getattr(medication_request, 'medication_name', 'Prescribed medication')
        except Exception:
            return 'Prescribed medication'
    
    def _filter_dosage(self, medication_request: MedicationRequest) -> Optional[str]:
        """Filter dosage information"""
        try:
            return "As prescribed"
        except Exception:
            return None
    
    def _filter_frequency(self, medication_request: MedicationRequest) -> Optional[str]:
        """Filter frequency information"""
        try:
            return "As directed"
        except Exception:
            return None
    
    def _filter_instructions(self, medication_request: MedicationRequest) -> Optional[str]:
        """Filter medication instructions"""
        try:
            return "Follow doctor's instructions"
        except Exception:
            return None
    
    def _get_doctor_name(self, consultation: PatientConsultation) -> str:
        """Get doctor name safely"""
        try:
            if hasattr(consultation, 'assigned_to') and consultation.assigned_to:
                return f"Dr. {consultation.assigned_to.get_full_name()}"
            return "Healthcare Provider"
        except Exception:
            return "Healthcare Provider"
    
    def _get_consultation_type(self, consultation: PatientConsultation) -> str:
        """Get consultation type"""
        try:
            return getattr(consultation, 'consultation_type', 'General Consultation')
        except Exception:
            return 'General Consultation'
    
    def _get_procedure_name(self, encounter: Encounter) -> str:
        """Get procedure name from encounter"""
        try:
            return "Medical procedure"
        except Exception:
            return "Medical procedure"
    
    def _get_facility_name(self, encounter: Encounter) -> str:
        """Get facility name from encounter"""
        try:
            return "Healthcare facility"
        except Exception:
            return "Healthcare facility"