import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Q
from django.core.paginator import Paginator

from care.emr.models.patient import Patient
from care.emr.models.encounter import Encounter
from care.facility.models import PatientConsultation, Facility
from care.users.models import User

from ..im_wrapper.base import IMMessage, IMResponse, MessageType
from ..command_types import CommandType
from ..utils.privacy_filter import PrivacyFilter
from ..utils.data_formatter import DataFormatter

logger = logging.getLogger(__name__)


class StaffHandler:
    """Handle hospital staff commands and patient management"""
    
    def __init__(self):
        self.privacy_filter = PrivacyFilter()
        self.formatter = DataFormatter()
    
    def handle_command(self, command_type: CommandType, message: IMMessage, user_context: Dict[str, Any]) -> List[IMResponse]:
        """Handle staff commands"""
        try:
            user_id = user_context.get('user_id')
            if not user_id:
                return [self._create_error_response(message.sender_id, "Staff information not found.")]
            
            if command_type == CommandType.SEARCH_PATIENT:
                query = self._extract_search_query(message.content)
                return self._handle_patient_search(message.sender_id, user_id, query)
            elif command_type == CommandType.PATIENT_INFO:
                patient_id = self._extract_patient_id(message.content)
                return self._handle_patient_info(message.sender_id, user_id, patient_id)
            elif command_type == CommandType.SCHEDULE_APPOINTMENT:
                return self._handle_schedule_appointment(message.sender_id, user_id)
            else:
                return [self._create_unknown_command_response(message.sender_id)]
        
        except Exception as e:
            logger.error(f"Error handling staff command: {e}")
            return [self._create_error_response(message.sender_id)]
    
    def _extract_search_query(self, content: str) -> str:
        """Extract search query from message content"""
        content_lower = content.lower().strip()
        if content_lower.startswith('search patient '):
            return content[15:].strip()
        elif content_lower.startswith('/search '):
            return content[8:].strip()
        return content.strip()
    
    def _extract_patient_id(self, content: str) -> str:
        """Extract patient ID from message content"""
        content_lower = content.lower().strip()
        if content_lower.startswith('patient info '):
            return content[13:].strip()
        elif content_lower.startswith('/patient '):
            return content[9:].strip()
        return content.strip()
    
    def _handle_patient_search(self, phone_number: str, user_id: int, query: str) -> List[IMResponse]:
        """Handle patient search command"""
        try:
            if not query or len(query) < 2:
                msg = "❓ Please provide a search term (minimum 2 characters).\nExample: `search patient John Doe`"
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            staff_user = User.objects.get(id=user_id)
            
            patients = Patient.objects.filter(
                Q(name__icontains=query) |
                Q(phone_number__icontains=query) |
                Q(external_id__icontains=query)
            )[:10]  # Limit to 10 results
            
            if not patients:
                msg = f"🔍 No patients found matching '{query}'.\nTry searching with a different term."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            results_text = f"🔍 *Search Results for '{query}'*\n\n"
            
            for i, patient in enumerate(patients, 1):
                filtered_patient = self.privacy_filter.filter_patient_data_for_staff(patient, staff_user)
                
                results_text += f"*{i}. {filtered_patient['name']}*\n"
                results_text += f"ID: {filtered_patient['patient_id']}\n"
                
                if filtered_patient.get('age'):
                    results_text += f"Age: {filtered_patient['age']}\n"
                
                if filtered_patient.get('gender'):
                    results_text += f"Gender: {filtered_patient['gender']}\n"
                
                if filtered_patient.get('phone_masked'):
                    results_text += f"Phone: {filtered_patient['phone_masked']}\n"
                
                results_text += "\n"
            
            results_text += "\n💡 Use `patient info <ID>` for details."
            
            return [IMResponse(phone_number, MessageType.TEXT, results_text)]
        
        except User.DoesNotExist:
            return [self._create_error_response(phone_number, "Staff user not found.")]
        except Exception as e:
            logger.error(f"Error searching patients: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_patient_info(self, phone_number: str, user_id: int, patient_id: str) -> List[IMResponse]:
        """Handle patient info command"""
        try:
            if not patient_id:
                msg = "❓ Please provide a patient ID.\nExample: `patient info P123456`"
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            staff_user = User.objects.get(id=user_id)
            
            try:
                patient = Patient.objects.get(external_id=patient_id)
            except Patient.DoesNotExist:
                msg = f"❌ Patient with ID '{patient_id}' not found."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            if not self._check_patient_access(staff_user, patient):
                msg = "🔒 You don't have permission to access this patient's information."
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            filtered_patient = self.privacy_filter.filter_patient_data_for_staff(patient, staff_user)
            
            info_text = f"👤 *Patient Information*\n\n"
            info_text += f"*Name:* {filtered_patient['name']}\n"
            info_text += f"*ID:* {filtered_patient['patient_id']}\n"
            
            if filtered_patient.get('age'):
                info_text += f"*Age:* {filtered_patient['age']}\n"
            
            if filtered_patient.get('gender'):
                info_text += f"*Gender:* {filtered_patient['gender']}\n"
            
            if filtered_patient.get('blood_group'):
                info_text += f"*Blood Group:* {filtered_patient['blood_group']}\n"
            
            if filtered_patient.get('phone_masked'):
                info_text += f"*Phone:* {filtered_patient['phone_masked']}\n"
            
            recent_encounters = Encounter.objects.filter(
                patient=patient
            ).order_by('-created_date')[:3]
            
            if recent_encounters:
                info_text += "\n📋 *Recent Encounters:*\n"
                for encounter in recent_encounters:
                    filtered_encounter = self.privacy_filter.filter_encounter_data_for_staff(encounter, staff_user)
                    info_text += f"• {filtered_encounter['date']} - {filtered_encounter['encounter_type']}\n"
            
            info_text += "\n⚠️ Summary only. Use CARE system for complete records."
            
            return [IMResponse(phone_number, MessageType.TEXT, info_text)]
        
        except User.DoesNotExist:
            return [self._create_error_response(phone_number, "Staff user not found.")]
        except Exception as e:
            logger.error(f"Error getting patient info: {e}")
            return [self._create_error_response(phone_number)]
    
    def _handle_schedule_appointment(self, phone_number: str, user_id: int) -> List[IMResponse]:
        """Handle schedule appointment command"""
        try:
            msg = (
                "📅 *Schedule Appointment*\n\n"
                "Use the main CARE system:\n\n"
                "🖥️ Web Portal or 📱 Mobile App\n\n"
                "🔒 Full authentication required for security."
            )
            
            return [IMResponse(phone_number, MessageType.TEXT, msg)]
        
        except Exception as e:
            logger.error(f"Error handling schedule appointment: {e}")
            return [self._create_error_response(phone_number)]
    
    def _check_patient_access(self, staff_user: User, patient: Patient) -> bool:
        """Check if staff user has access to patient data"""
        try:
            return staff_user.is_active
        
        except Exception as e:
            logger.error(f"Error checking patient access: {e}")
            return False
    
    def _create_unknown_command_response(self, phone_number: str) -> IMResponse:
        """Create response for unknown staff commands"""
        msg = (
            "❓ I didn't understand that command. "
            "Commands: `search patient <name>`, `patient info <id>`, `schedule appointment`, `menu`, `help`"
        )
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_error_response(self, phone_number: str, custom_message: str = None) -> IMResponse:
        """Create error response"""
        if custom_message:
            msg = f"❌ {custom_message}"
        else:
            msg = (
                "Sorry, something went wrong while processing your request. "
                "Try again or contact IT support."
            )
        return IMResponse(phone_number, MessageType.TEXT, msg)