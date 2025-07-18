import logging
import re
from typing import Dict, Any, Optional, List

from .im_wrapper.base import IMMessage, IMResponse, MessageType, UserType
from .authentication import WhatsAppAuthenticator
from .command_types import CommandType
from .handlers.patient_handler import PatientHandler
from .handlers.staff_handler import StaffHandler
from .handlers.common_handler import CommonHandler

logger = logging.getLogger(__name__)


class MessageRouter:
    """Route incoming messages to appropriate handlers"""
    
    def __init__(self):
        self.authenticator = WhatsAppAuthenticator()
        self.patient_handler = PatientHandler()
        self.staff_handler = StaffHandler()
        self.common_handler = CommonHandler()
        
        self.command_patterns = {
            CommandType.LOGIN: [r'^(login|start|hi|hello)$', r'^/start$'],
            CommandType.LOGOUT: [r'^(logout|exit|quit)$', r'^/logout$'],
            CommandType.REGISTER: [r'^(register|signup|sign up|join)$', r'^/register$'],
            CommandType.VERIFY: [r'^\d{6}$'],  # 6-digit OTP
            CommandType.GET_RECORDS: [r'^(records|medical records|my records)$', r'^/records$'],
            CommandType.GET_MEDICATIONS: [r'^(medications|medicines|drugs|my medications)$', r'^/medications$'],
            CommandType.GET_APPOINTMENTS: [r'^(appointments|schedule|my appointments)$', r'^/appointments$'],
            CommandType.GET_PROCEDURES: [r'^(procedures|treatments|my procedures)$', r'^/procedures$'],
            CommandType.CHECK_AVAILABLE_SLOTS: [r'^(available slots|check slots|slots available|appointment slots)$', r'^/slots$'],
            CommandType.BOOK_APPOINTMENT: [r'^(book appointment|book slot|schedule appointment)$', r'^/book$'],
            CommandType.SEARCH_PATIENT: [r'^search patient (.+)$', r'^/search (.+)$'],
            CommandType.PATIENT_INFO: [r'^patient info (.+)$', r'^/patient (.+)$'],
            CommandType.HELP: [r'^(help|\?)$', r'^/help$'],
            CommandType.MENU: [r'^(menu|options)$', r'^/menu$'],
        }
    
    def route_message(self, message: IMMessage) -> List[IMResponse]:
        """Route incoming message to appropriate handler"""
        try:
            if message.message_type != MessageType.TEXT:
                return [self._create_unsupported_message_response(message.sender_id)]
            
            command_type, command_args = self._parse_command(message.content)
            
            is_authenticated = self.authenticator.is_authenticated(message.sender_id)
            user_context = self.authenticator.get_user_context(message.sender_id) if is_authenticated else None
            if command_type in [CommandType.LOGIN, CommandType.VERIFY, CommandType.LOGOUT, CommandType.REGISTER]:
                return self._handle_auth_command(command_type, message, command_args)
            
            if command_type in [CommandType.HELP, CommandType.MENU]:
                return self.common_handler.handle_command(command_type, message, user_context)
            if not is_authenticated:
                return [self._create_auth_required_response(message.sender_id)]
            
            if user_context['user_type'] == UserType.PATIENT:
                return self.patient_handler.handle_command(command_type, message, user_context)
            elif user_context['user_type'] == UserType.HOSPITAL_STAFF:
                return self.staff_handler.handle_command(command_type, message, user_context)
            else:
                return [self._create_unknown_user_response(message.sender_id)]
        
        except Exception as e:
            logger.error(f"Error routing message: {e}")
            return [self._create_error_response(message.sender_id)]
        
        if command_type == CommandType.UNKNOWN:
            return self.common_handler.handle_command(command_type, message, user_context)
        return [self.common_handler._handle_welcome(message)]
    
    def _parse_command(self, content: str) -> tuple[CommandType, Dict[str, Any]]:
        """Parse command from message content"""
        content_lower = content.lower().strip()
        
        for command_type, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.match(pattern, content_lower, re.IGNORECASE)
                if match:
                    args = {}
                    if match.groups():
                        args['query'] = match.group(1)
                    return command_type, args
        
        return CommandType.UNKNOWN, {'original_text': content}
    
    def _handle_auth_command(self, command_type: CommandType, message: IMMessage, args: Dict[str, Any]) -> List[IMResponse]:
        """Handle authentication-related commands"""
        if command_type == CommandType.LOGIN:
            return self._handle_login(message.sender_id)
        elif command_type == CommandType.VERIFY:
            return self._handle_otp_verification(message.sender_id, message.content.strip())
        elif command_type == CommandType.LOGOUT:
            return self._handle_logout(message.sender_id)
        elif command_type == CommandType.REGISTER:
            return self._handle_register(message.sender_id)
        
        return [self._create_error_response(message.sender_id)]
    
    def _handle_login(self, phone_number: str) -> List[IMResponse]:
        """Handle login command"""
        if self.authenticator.is_authenticated(phone_number):
            user_context = self.authenticator.get_user_context(phone_number)
            welcome_msg = f"🏥 Welcome back, {user_context.get('name', 'User')}! You are already logged in."
            menu_msg = self.common_handler.get_menu_for_user_type(user_context['user_type'])
            return [
                IMResponse(phone_number, MessageType.TEXT, welcome_msg),
                IMResponse(phone_number, MessageType.TEXT, menu_msg)
            ]
        
        user_type, user_obj = self.authenticator.identify_user_type(phone_number)
        
        if user_type == UserType.UNKNOWN:
            msg = ("🏥 Hello! Welcome to CARE - Your Digital Healthcare Companion! 👋\n\n"
                   "We're here to help you manage your healthcare needs conveniently through WhatsApp.\n\n"
                   "❌ However, your phone number is not registered in our system yet.\n\n"
                   "🆕 **NEW!** You can now register directly through WhatsApp!\n"
                   "📝 Type 'register' to create your CARE account\n\n"
                   "Or alternatively:\n"
                   "📞 Contact your healthcare provider to register your number\n"
                   "🏥 Visit our facility to get started with CARE services\n\n"
                   "🌟 Once registered, you'll be able to:\n"
                   "• View your medical records\n"
                   "• Check appointments\n"
                   "• Access medication information\n"
                   "• Book appointment slots\n"
                   "• And much more!")
            return [IMResponse(phone_number, MessageType.TEXT, msg)]
        otp = self.authenticator.generate_otp(phone_number)
        if otp:
            welcome_msg = ("🏥 Hello! Welcome to CARE - Your Digital Healthcare Companion! 👋\n\n"
                          "🌟 We're excited to help you manage your healthcare needs conveniently through WhatsApp.\n\n"
                          "🔐 For your security, we've sent a 6-digit verification code to your phone.\n\n"
                          "📱 Reply with verification code to access your CARE account.")
        else:
            welcome_msg = ("🏥 Hello! Welcome to CARE - Your Digital Healthcare Companion! 👋\n\n"
                          "❌ Sorry, we couldn't send the verification code at the moment.\n\n"
                          "🔄 Try 'login' again or contact support if issue persists.")
        return [IMResponse(phone_number, MessageType.TEXT, welcome_msg)]
    def _handle_otp_verification(self, phone_number: str, otp: str) -> List[IMResponse]:
        """Handle OTP verification"""
        if self.authenticator.verify_otp(phone_number, otp):
            user_context = self.authenticator.get_user_context(phone_number)
            if user_context:
                user_name = user_context.get('name', 'User')
                user_type_name = "Patient" if user_context['user_type'] == UserType.PATIENT else "Staff Member"
                welcome_msg = (f"🎉 Welcome to CARE, {user_name}! \n\n"
                              f"✅ You are now successfully logged in as a {user_type_name}.\n\n"
                              f"🏥 Your digital healthcare companion is ready to assist you!\n\n"
                              f"📋 Available services:")
                menu_msg = self.common_handler.get_menu_for_user_type(user_context['user_type'])
                help_msg = ("\n💡 Tips:\n"
                           "• Type any option from the menu above\n"
                           "• Type 'help' for assistance anytime\n"
                           "• Type 'menu' to see options again\n\n"
                           "How can I help you today? 😊")
                return [
                    IMResponse(phone_number, MessageType.TEXT, welcome_msg),
                    IMResponse(phone_number, MessageType.TEXT, menu_msg),
                    IMResponse(phone_number, MessageType.TEXT, help_msg)
                ]
        
        msg = ("❌ Invalid verification code. Check the 6-digit code and try again.\n\n"
               "🔄 Type 'login' to request a new verification code if needed.")
        return [IMResponse(phone_number, MessageType.TEXT, msg)]
    
    def _handle_logout(self, phone_number: str) -> List[IMResponse]:
        """Handle logout command"""
        if self.authenticator.is_authenticated(phone_number):
            self.authenticator.logout(phone_number)
            msg = "✅ Logged out successfully. Type 'login' to sign in again."
        else:
            msg = "You are not currently logged in. Type 'login' to sign in."
        
        return [IMResponse(phone_number, MessageType.TEXT, msg)]
    
    def _create_auth_required_response(self, phone_number: str) -> IMResponse:
        """Create response for unauthenticated users"""
        msg = ("🔐 Please log in first to use this service. "
               "Type 'login' to get started.")
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_unknown_user_response(self, phone_number: str) -> IMResponse:
        """Create response for unknown user types"""
        msg = ("Sorry, we couldn't identify your account type. "
               "Please contact support for assistance.")
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_unsupported_message_response(self, phone_number: str) -> IMResponse:
        """Create response for unsupported message types"""
        msg = ("Sorry, I can only process text messages at the moment. "
               "Please send your request as text.")
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_error_response(self, phone_number: str) -> IMResponse:
        """Create generic error response"""
        msg = ("Something went wrong. Try again later "
               "or contact support if issue persists.")
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _handle_register(self, phone_number: str) -> List[IMResponse]:
        """Handle user registration command"""
        try:
            # Check if user is already registered
            user_type, user_obj = self.authenticator.identify_user_type(phone_number)
            
            if user_type != UserType.UNKNOWN:
                msg = ("✅ Your phone number is already registered in our system!\n\n"
                       "🔐 Type 'login' to access your CARE account.")
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            # Import here to avoid circular imports
            from django.contrib.auth import get_user_model
            from care.facility.models import Facility
            from care.users.models import User
            import uuid
            
            User = get_user_model()
            
            # Normalize phone number (remove +91 if present)
            normalized_phone = phone_number.replace('+91', '').replace('+', '')
            if not normalized_phone.startswith('91'):
                normalized_phone = '91' + normalized_phone
            
            # Create a new patient user
            username = f"patient_{normalized_phone}"
            email = f"patient_{normalized_phone}@care.local"
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                msg = ("⚠️ A user with this phone number already exists but may not be properly configured.\n\n"
                       "📞 Please contact support for assistance.")
                return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                phone_number=normalized_phone,
                user_type=User.TYPE_VALUE_MAP.get("Patient", 5),  # Patient type
                first_name="WhatsApp",
                last_name="User",
                verified=True,  # Auto-verify WhatsApp registered users
            )
            
            # Try to get a default facility or create one
            try:
                default_facility = Facility.objects.first()
                if default_facility:
                    user.home_facility = default_facility
                    user.save()
            except Exception as e:
                logger.warning(f"Could not assign default facility: {e}")
            
            logger.info(f"Successfully registered new patient user: {username}")
            
            msg = ("🎉 Congratulations! Your CARE account has been created successfully!\n\n"
                   "✅ You are now registered as a Patient in our system.\n\n"
                   "🔐 Type 'login' to access your new CARE account and start managing your healthcare!\n\n"
                   "🌟 You can now:\n"
                   "• View your medical records\n"
                   "• Check appointments\n"
                   "• Access medication information\n"
                   "• Book appointment slots\n"
                   "• And much more!\n\n"
                   "Welcome to the CARE family! 🏥💙")
            
            return [IMResponse(phone_number, MessageType.TEXT, msg)]
            
        except Exception as e:
            logger.error(f"Error during registration for {phone_number}: {e}")
            msg = ("❌ Sorry, we encountered an error during registration.\n\n"
                   "🔄 Please try again later or contact support if the issue persists.\n\n"
                   "📞 You can also visit our facility to register in person.")
            return [IMResponse(phone_number, MessageType.TEXT, msg)]