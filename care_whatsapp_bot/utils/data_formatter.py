import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date

logger = logging.getLogger(__name__)


class DataFormatter:
    """Format data for WhatsApp message display"""
    
    MAX_MESSAGE_LENGTH = 4096  # WhatsApp message limit
    MAX_LIST_ITEMS = 10  # Maximum items to show in a list
    
    def format_patient_summary(self, patient_data: Dict[str, Any]) -> str:
        """Format patient summary for display"""
        try:
            summary = "👤 *Patient Summary*\n\n"
            
            if patient_data.get('name'):
                summary += f"*Name:* {patient_data['name']}\n"
            
            if patient_data.get('patient_id'):
                summary += f"*ID:* {patient_data['patient_id']}\n"
            
            if patient_data.get('age'):
                summary += f"*Age:* {patient_data['age']}\n"
            
            if patient_data.get('gender'):
                summary += f"*Gender:* {patient_data['gender']}\n"
            
            if patient_data.get('blood_group'):
                summary += f"*Blood Group:* {patient_data['blood_group']}\n"
            
            return self._truncate_message(summary)
        
        except Exception as e:
            logger.error(f"Error formatting patient summary: {e}")
            return "❌ Error formatting patient information"
    
    def format_medication_list(self, medications: List[Dict[str, Any]]) -> str:
        """Format medication list for display"""
        try:
            if not medications:
                return "💊 *Current Medications*\n\nNo active medications found."
            
            msg = "💊 *Current Medications*\n\n"
            
            display_meds = medications[:self.MAX_LIST_ITEMS]
            
            for i, med in enumerate(display_meds, 1):
                msg += f"*{i}. {med.get('medication_name', 'Unknown medication')}*\n"
                
                if med.get('dosage'):
                    msg += f"   Dosage: {med['dosage']}\n"
                
                if med.get('frequency'):
                    msg += f"   Frequency: {med['frequency']}\n"
                
                if med.get('status'):
                    msg += f"   Status: {med['status']}\n"
                
                msg += "\n"
            
            if len(medications) > self.MAX_LIST_ITEMS:
                msg += f"... and {len(medications) - self.MAX_LIST_ITEMS} more medications\n\n"
            
            msg += "⚠️ Follow doctor's instructions."
            
            return self._truncate_message(msg)
        
        except Exception as e:
            logger.error(f"Error formatting medication list: {e}")
            return "❌ Error formatting medication information"
    
    def format_appointment_list(self, appointments: List[Dict[str, Any]]) -> str:
        """Format appointment list for display"""
        try:
            if not appointments:
                return "📅 *Upcoming Appointments*\n\nNo upcoming appointments found."
            
            msg = "📅 *Upcoming Appointments*\n\n"
            
            display_appts = appointments[:self.MAX_LIST_ITEMS]
            
            for i, appt in enumerate(display_appts, 1):
                msg += f"*{i}. {appt.get('date', 'Unknown date')}*\n"
                
                if appt.get('facility_name'):
                    msg += f"   Facility: {appt['facility_name']}\n"
                
                if appt.get('doctor_name'):
                    msg += f"   Doctor: {appt['doctor_name']}\n"
                
                if appt.get('consultation_type'):
                    msg += f"   Type: {appt['consultation_type']}\n"
                
                msg += "\n"
            
            if len(appointments) > self.MAX_LIST_ITEMS:
                msg += f"... and {len(appointments) - self.MAX_LIST_ITEMS} more appointments\n\n"
            
            msg += "📞 *Reminder:* Please arrive 15 minutes early."
            
            return self._truncate_message(msg)
        
        except Exception as e:
            logger.error(f"Error formatting appointment list: {e}")
            return "❌ Error formatting appointment information"
    
    def format_medical_records(self, records: List[Dict[str, Any]]) -> str:
        """Format medical records for display"""
        try:
            if not records:
                return "📋 *Medical Records*\n\nNo recent medical records found."
            
            msg = "📋 *Recent Medical Records*\n\n"
            
            display_records = records[:self.MAX_LIST_ITEMS]
            
            for i, record in enumerate(display_records, 1):
                msg += f"*{i}. {record.get('date', 'Unknown date')}*\n"
                
                if record.get('encounter_type'):
                    msg += f"   Type: {record['encounter_type']}\n"
                
                if record.get('chief_complaint'):
                    msg += f"   Complaint: {record['chief_complaint']}\n"
                
                if record.get('diagnosis'):
                    msg += f"   Diagnosis: {record['diagnosis']}\n"
                
                msg += "\n"
            
            if len(records) > self.MAX_LIST_ITEMS:
                msg += f"... and {len(records) - self.MAX_LIST_ITEMS} more records\n\n"
            
            msg += "⚠️ Summary only. Visit provider for complete records."
            
            return self._truncate_message(msg)
        
        except Exception as e:
            logger.error(f"Error formatting medical records: {e}")
            return "❌ Error formatting medical records"
    
    def format_search_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format patient search results for staff"""
        try:
            if not results:
                return f"🔍 No patients found matching '{query}'.\nTry searching with a different term."
            
            msg = f"🔍 *Search Results for '{query}'*\n\n"
            
            display_results = results[:self.MAX_LIST_ITEMS]
            
            for i, patient in enumerate(display_results, 1):
                msg += f"*{i}. {patient.get('name', 'Unknown')}*\n"
                
                if patient.get('patient_id'):
                    msg += f"   ID: {patient['patient_id']}\n"
                
                if patient.get('age'):
                    msg += f"   Age: {patient['age']}\n"
                
                if patient.get('gender'):
                    msg += f"   Gender: {patient['gender']}\n"
                
                if patient.get('phone_masked'):
                    msg += f"   Phone: {patient['phone_masked']}\n"
                
                msg += "\n"
            
            if len(results) > self.MAX_LIST_ITEMS:
                msg += f"... and {len(results) - self.MAX_LIST_ITEMS} more results\n\n"
            
            msg += "💡 Use `patient info <ID>` for details."
            
            return self._truncate_message(msg)
        
        except Exception as e:
            logger.error(f"Error formatting search results: {e}")
            return "❌ Error formatting search results"
    
    def format_error_message(self, error_type: str, details: str = None) -> str:
        """Format error messages consistently"""
        error_messages = {
            'authentication': "🔐 Authentication required. Please log in first.",
            'permission': "🔒 You don't have permission to access this information.",
            'not_found': "❌ The requested information was not found.",
            'invalid_input': "❓ Invalid input. Check command and try again.",
            'system_error': "⚠️ System error. Try again later.",
            'rate_limit': "⏰ Too many requests. Wait before trying again."
        }
        
        base_message = error_messages.get(error_type, "❌ An error occurred.")
        
        if details:
            return f"{base_message}\n\n{details}"
        
        return base_message
    
    def format_success_message(self, action: str, details: str = None) -> str:
        """Format success messages consistently"""
        success_messages = {
            'login': "✅ Successfully logged in!",
            'logout': "✅ Successfully logged out!",
            'data_retrieved': "✅ Information retrieved successfully!",
            'action_completed': "✅ Action completed successfully!"
        }
        
        base_message = success_messages.get(action, "✅ Success!")
        
        if details:
            return f"{base_message}\n\n{details}"
        
        return base_message
    
    def format_date(self, date_obj: Any) -> str:
        """Format date for display"""
        try:
            if isinstance(date_obj, datetime):
                return date_obj.strftime('%Y-%m-%d %H:%M')
            elif isinstance(date_obj, date):
                return date_obj.strftime('%Y-%m-%d')
            elif isinstance(date_obj, str):
                # Try to parse string date
                try:
                    parsed_date = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
                    return parsed_date.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    return date_obj
            else:
                return str(date_obj)
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return "Unknown date"
    
    def format_phone_number(self, phone: str) -> str:
        """Format phone number for display"""
        if not phone:
            return "Not available"
        
        # Remove any non-digit characters
        digits = ''.join(filter(str.isdigit, phone))
        
        if len(digits) >= 10:
            # Format as +XX XXXXX XXXXX
            if len(digits) > 10:
                country_code = digits[:-10]
                number = digits[-10:]
                return f"+{country_code} {number[:5]} {number[5:]}"
            else:
                return f"{digits[:5]} {digits[5:]}"
        
        return phone
    
    def _truncate_message(self, message: str) -> str:
        """Truncate message if it exceeds WhatsApp limits"""
        if len(message) <= self.MAX_MESSAGE_LENGTH:
            return message
        
        truncated = message[:self.MAX_MESSAGE_LENGTH - 50]
        
        last_space = truncated.rfind(' ')
        if last_space > self.MAX_MESSAGE_LENGTH - 100:
            truncated = truncated[:last_space]
        
        return truncated + "\n\n... (message truncated)\n\nFor complete information, please use the CARE web portal."
    
    def create_interactive_buttons(self, buttons: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create interactive button metadata for WhatsApp"""
        try:
            limited_buttons = buttons[:3]
            
            formatted_buttons = []
            for i, button in enumerate(limited_buttons):
                formatted_buttons.append({
                    'type': 'reply',
                    'reply': {
                        'id': f"btn_{i}_{button.get('id', i)}",
                        'title': button.get('title', f"Option {i+1}")
                    }
                })
            
            return {'buttons': formatted_buttons}
        
        except Exception as e:
            logger.error(f"Error creating interactive buttons: {e}")
            return {}