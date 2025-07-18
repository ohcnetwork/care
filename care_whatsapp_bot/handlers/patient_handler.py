import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Q

from care.emr.models.patient import Patient
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.facility.models import PatientConsultation

from ..im_wrapper.base import IMMessage, IMResponse, MessageType
from ..command_types import CommandType
from ..utils.privacy_filter import PrivacyFilter
from ..utils.data_formatter import DataFormatter

logger = logging.getLogger(__name__)


class PatientHandler:
    """Handle patient-specific commands and data access"""
    
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
        self.formatter = DataFormatter()
    
    def handle_command(self, command_type: CommandType, message: IMMessage, user_context: Dict[str, Any]) -> List[IMResponse]:
        """Handle patient commands"""
        try:
            patient_id = user_context.get('patient_id')
            if not patient_id:
                return [self._create_error_response(message.sender_id, "Patient information not found.")]
            
            if command_type == CommandType.GET_RECORDS:
                return self._handle_get_records(message.sender_id, patient_id)
            elif command_type == CommandType.GET_MEDICATIONS:
                return self._handle_get_medications(message.sender_id, patient_id)
            elif command_type == CommandType.GET_APPOINTMENTS:
                return self._handle_get_appointments(message.sender_id, patient_id)
            elif command_type == CommandType.GET_PROCEDURES:
                return self._handle_get_procedures(message.sender_id, patient_id)
            elif command_type == CommandType.CHECK_AVAILABLE_SLOTS:
                return self._handle_check_available_slots(message.sender_id, patient_id)
            elif command_type == CommandType.BOOK_APPOINTMENT:
                return self._handle_book_appointment(message.sender_id, patient_id)
            else:
                return [self._create_unknown_command_response(message.sender_id)]
        
        except Exception as e:
            logger.error(f"Error handling patient command: {e}")
            return [self._create_error_response(message.sender_id)]
    
    def _handle_get_records(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle get medical records command"""
        try:
            patient = Patient.objects.get(external_id=patient_id)
            
            six_months_ago = timezone.now() - timedelta(days=180)
            encounters = Encounter.objects.filter(
                patient=patient,
                created_date__gte=six_months_ago
            ).order_by('-created_date')[:5]
            
            if not encounters:
                msg = "📋 *Medical Records*\n\nNo recent medical records found."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            records_text = "📋 *Recent Medical Records*\n\n"
            
            for i, encounter in enumerate(encounters, 1):
                filtered_encounter = self.privacy_filter.filter_encounter_data(encounter)
                
                records_text += f"*{i}. {filtered_encounter['date']}*\n"
                records_text += f"Type: {filtered_encounter['encounter_type']}\n"
                
                if filtered_encounter.get('chief_complaint'):
                    records_text += f"Chief Complaint: {filtered_encounter['chief_complaint']}\n"
                
                if filtered_encounter.get('diagnosis'):
                    records_text += f"Diagnosis: {filtered_encounter['diagnosis']}\n"
                
                records_text += "\n"
            records_text += "\n⚠️ Summary only. Visit provider for complete records."
            
            return [IMResponse(phone_number, MessageType.TEXT, records_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error getting patient records: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_get_medications(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle get medications command"""
        try:
            patient = Patient.objects.get(external_id=patient_id)
            
            active_medications = MedicationRequest.objects.filter(
                patient=patient,
                status__in=['active', 'on-hold']
            ).order_by('-created_date')
            
            if not active_medications:
                msg = "💊 *Current Medications*\n\nNo active medications found."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            meds_text = "💊 *Current Medications*\n\n"
            
            for i, med_request in enumerate(active_medications, 1):
                filtered_med = self.privacy_filter.filter_medication_data(med_request)
                
                meds_text += f"*{i}. {filtered_med['medication_name']}*\n"
                
                if filtered_med.get('dosage'):
                    meds_text += f"Dosage: {filtered_med['dosage']}\n"
                
                if filtered_med.get('frequency'):
                    meds_text += f"Frequency: {filtered_med['frequency']}\n"
                
                if filtered_med.get('instructions'):
                    meds_text += f"Instructions: {filtered_med['instructions']}\n"
                
                meds_text += f"Status: {filtered_med['status']}\n\n"
            
            # Add disclaimer
            meds_text += "\n⚠️ Follow doctor's instructions. Don't change meds without consulting."
            
            return [IMResponse(phone_number, MessageType.TEXT, meds_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error getting patient medications: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_get_appointments(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle get appointments command"""
        try:
            patient = Patient.objects.get(external_id=patient_id)
            
            upcoming_consultations = PatientConsultation.objects.filter(
                patient=patient,
                discharge_date__isnull=True,
                created_date__gte=timezone.now() - timedelta(days=30)
            ).order_by('created_date')
            
            if not upcoming_consultations:
                msg = "📅 *Upcoming Appointments*\n\nNo upcoming appointments found."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            # Format appointments
            appts_text = "📅 *Upcoming Appointments*\n\n"
            
            for i, consultation in enumerate(upcoming_consultations, 1):
                filtered_appt = self.privacy_filter.filter_appointment_data(consultation)
                
                appts_text += f"*{i}. {filtered_appt['date']}*\n"
                appts_text += f"Facility: {filtered_appt['facility_name']}\n"
                
                if filtered_appt.get('doctor_name'):
                    appts_text += f"Doctor: {filtered_appt['doctor_name']}\n"
                
                if filtered_appt.get('consultation_type'):
                    appts_text += f"Type: {filtered_appt['consultation_type']}\n"
                
                appts_text += "\n"
            
            # Add reminder
            appts_text += "\n📞 *Reminder:* Please arrive 15 minutes early for your appointment."
            
            return [IMResponse(phone_number, MessageType.TEXT, appts_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error getting patient appointments: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_get_procedures(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle get procedures command"""
        try:
            patient = Patient.objects.get(external_id=patient_id)
            
            three_months_ago = timezone.now() - timedelta(days=90)
            encounters_with_procedures = Encounter.objects.filter(
                patient=patient,
                created_date__gte=three_months_ago
            ).exclude(
                Q(procedure_request__isnull=True) & Q(observation__isnull=True)
            ).order_by('-created_date')[:5]
            
            if not encounters_with_procedures:
                msg = "🏥 *Recent Procedures*\n\nNo recent procedures found."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            # Format procedures
            procedures_text = "🏥 *Recent Procedures*\n\n"
            
            for i, encounter in enumerate(encounters_with_procedures, 1):
                filtered_procedure = self.privacy_filter.filter_procedure_data(encounter)
                
                procedures_text += f"*{i}. {filtered_procedure['date']}*\n"
                
                if filtered_procedure.get('procedure_name'):
                    procedures_text += f"Procedure: {filtered_procedure['procedure_name']}\n"
                
                if filtered_procedure.get('facility_name'):
                    procedures_text += f"Facility: {filtered_procedure['facility_name']}\n"
                
                if filtered_procedure.get('status'):
                    procedures_text += f"Status: {filtered_procedure['status']}\n"
                
                procedures_text += "\n"
            
            # Add note
            procedures_text += "\n📋 Contact provider for detailed reports."
            
            return [IMResponse(phone_number, MessageType.TEXT, procedures_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error getting patient procedures: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_check_available_slots(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle check available appointment slots command"""
        try:
            from care.facility.models import Facility, FacilityUser
            from care.users.models import User
            
            patient = Patient.objects.get(external_id=patient_id)
            
            facilities = Facility.objects.filter(
                is_active=True,
                facility_type__in=['HOSPITAL', 'PRIMARY_HEALTH_CENTRE', 'COMMUNITY_HEALTH_CENTRE']
            )[:5]
            
            if not facilities:
                msg = "🏥 *Available Appointment Slots*\n\nNo facilities found with available slots."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            slots_text = "🏥 *Available Appointment Slots*\n\n"
            
            for i, facility in enumerate(facilities, 1):
                slots_text += f"*{i}. {facility.name}*\n"
                slots_text += f"Location: {facility.address}\n"
                
                next_week = timezone.now() + timedelta(days=7)
                available_staff = FacilityUser.objects.filter(
                    facility=facility,
                    created_date__lte=next_week
                ).select_related('user')[:3]
                
                if available_staff:
                    slots_text += "Available Doctors:\n"
                    for staff in available_staff:
                        slots_text += f"  • Dr. {staff.user.get_full_name() or staff.user.username}\n"
                tomorrow = timezone.now() + timedelta(days=1)
                day_after = timezone.now() + timedelta(days=2)
                slots_text += f"Next Available: {tomorrow.strftime('%Y-%m-%d')} or {day_after.strftime('%Y-%m-%d')}\n\n"
            
            slots_text += "📞 *To book an appointment:*\n"
            slots_text += "Type 'book appointment' and follow the instructions.\n\n"
            slots_text += "⚠️ Availability may vary. Confirm with facility."
            
            return [IMResponse(phone_number, MessageType.TEXT, slots_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error checking available slots: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_book_appointment(self, phone_number: str, patient_id: str) -> List[IMResponse]:
        """Handle book appointment command"""
        try:
            patient = Patient.objects.get(external_id=patient_id)
            
            booking_text = "📅 *Book Appointment*\n\n"
            booking_text += "To book an appointment, please provide:\n\n"
            booking_text += "1️⃣ Preferred facility\n"
            booking_text += "2️⃣ Preferred doctor (optional)\n"
            booking_text += "3️⃣ Preferred date and time\n"
            booking_text += "4️⃣ Reason for visit\n\n"
            
            booking_text += "*Example:*\n"
            booking_text += "Facility: City Hospital\n"
            booking_text += "Doctor: Dr. Smith\n"
            booking_text += "Date: 2024-01-15\n"
            booking_text += "Time: 10:00 AM\n"
            booking_text += "Reason: Regular checkup\n\n"
            
            booking_text += "📞 *Alternative booking methods:*\n"
            booking_text += "• Call the facility directly\n"
            booking_text += "• Visit the facility in person\n"
            booking_text += "• Use the CARE web portal\n\n"
            
            booking_text += "⚠️ Feature being enhanced. Contact facility for immediate booking."
            
            return [IMResponse(phone_number, MessageType.TEXT, booking_text)]
        
        except Patient.DoesNotExist:
            return [self._create_error_response(phone_number, "Patient not found.")]
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return [self._create_error_response(phone_number)]
    
    def _create_unknown_command_response(self, phone_number: str) -> IMResponse:
        """Create response for unknown patient commands"""
        msg = (
            "❓ I didn't understand that command. "
            "Commands: `records`, `medications`, `appointments`, `procedures`, `available slots`, `book appointment`, `menu`, `help`"
        )
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_error_response(self, phone_number: str, custom_message: str = None) -> IMResponse:
        """Create error response"""
        if custom_message:
            msg = f"❌ {custom_message}"
        else:
            msg = (
                "Sorry, something went wrong while retrieving your information. "
                "Try again or contact your provider."
            )
        return IMResponse(phone_number, MessageType.TEXT, msg)