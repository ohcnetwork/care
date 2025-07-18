import logging
from typing import Dict, Any, Optional, List

from ..im_wrapper.base import IMMessage, IMResponse, MessageType, UserType
from ..command_types import CommandType

logger = logging.getLogger(__name__)


class CommonHandler:

    
    def handle_command(self, command_type: CommandType, message: IMMessage, user_context: Optional[Dict[str, Any]]) -> List[IMResponse]:
        """Handle common commands"""
        try:
            if command_type == CommandType.HELP:
                return self._handle_help(message, user_context)
            elif command_type == CommandType.MENU:
                return self._handle_menu(message, user_context)
            else:
                return [self._handle_welcome(message)]
        
        except Exception as e:
            logger.error(f"Error handling common command: {e}")
            return [self._create_error_response(message.sender_id)]

    def _handle_welcome(self, message: IMMessage) -> IMResponse:
        welcome_text = (
            "👋 Welcome to the Care WhatsApp Bot!\n"
            "I'm here to assist you with your healthcare needs.\n"
            "Type `help` to see what I can do for you."
        )
        return IMResponse(message.sender_id, MessageType.TEXT, welcome_text)
    
    def _handle_help(self, message: IMMessage, user_context: Optional[Dict[str, Any]]) -> List[IMResponse]:
        """Handle help command"""
        if not user_context:
            help_text = (
                "🏥 *CARE WhatsApp Bot Help*\n\n"
                "Welcome! I'm here to help you access your healthcare information.\n\n"
                "*Getting Started:*\n"
                "• Type `login` to sign in\n"
                "• Enter the 6-digit code sent to your phone\n\n"
                "*Need Help?*\n"
                "Contact your healthcare provider for registration or support."
            )
        else:
            user_type = user_context.get('user_type')
            if user_type == UserType.PATIENT:
                help_text = self._get_patient_help()
            elif user_type == UserType.HOSPITAL_STAFF:
                help_text = self._get_staff_help()
            else:
                help_text = "Help not available for your account type."
        
        return [IMResponse(message.sender_id, MessageType.TEXT, help_text)]
    
    def _handle_menu(self, message: IMMessage, user_context: Optional[Dict[str, Any]]) -> List[IMResponse]:
        """Handle menu command"""
        if not user_context:
            menu_text = (
                "🏥 *CARE WhatsApp Bot*\n\n"
                "Please log in to access the menu.\n\n"
                "Type `login` to get started."
            )
        else:
            user_type = user_context.get('user_type')
            menu_text = self.get_menu_for_user_type(user_type)
        
        return [IMResponse(message.sender_id, MessageType.TEXT, menu_text)]
    
    def get_menu_for_user_type(self, user_type: UserType) -> str:
        """Get menu text for specific user type"""
        if user_type == UserType.PATIENT:
            return self._get_patient_menu()
        elif user_type == UserType.HOSPITAL_STAFF:
            return self._get_staff_menu()
        else:
            return "Menu not available for your account type."
    
    def _get_patient_menu(self) -> str:
        """Get patient menu"""
        return (
            "👤 *Patient Menu*\n\n"
            "What would you like to do?\n\n"
            "📋 `records` - View medical records\n"
            "💊 `medications` - View current medications\n"
            "📅 `appointments` - View upcoming appointments\n"
            "🏥 `procedures` - View recent procedures\n"
            "🗓️ `available slots` - Check available appointment slots\n"
            "📞 `book appointment` - Book a new appointment\n\n"
            "ℹ️ `help` - Get help\n"
            "🚪 `logout` - Sign out"
        )
    
    def _get_staff_menu(self) -> str:
        """Get hospital staff menu"""
        return (
            "👨‍⚕️ *Hospital Staff Menu*\n\n"
            "What would you like to do?\n\n"
            "🔍 `search patient <name>` - Search for a patient\n"
            "👤 `patient info <id>` - Get patient information\n"
            "📅 `schedule appointment` - Schedule appointment\n\n"
            "ℹ️ `help` - Get help\n"
            "🚪 `logout` - Sign out"
        )
    
    def _get_patient_help(self) -> str:
        """Get patient help text"""
        return (
            "👤 *Patient Help*\n\n"
            "*Available Commands:*\n"
            "• `records` - View your medical records and history\n"
            "• `medications` - See your current medications and dosages\n"
            "• `appointments` - Check upcoming appointments\n"
            "• `procedures` - View recent medical procedures\n"
            "• `available slots` - Check available appointment slots\n"
            "• `book appointment` - Book a new appointment\n"
            "• `menu` - Show main menu\n"
            "• `logout` - Sign out of the bot\n\n"
            "*Privacy & Security:*\n"
            "• Your data is encrypted and secure\n"
            "• Only you can access your information\n"
            "• Sessions expire after 24 hours\n\n"
            "*Need Support?*\n"
            "Contact your healthcare provider for assistance."
        )
    
    def _get_staff_help(self) -> str:
        """Get hospital staff help text"""
        return (
            "👨‍⚕️ *Hospital Staff Help*\n\n"
            "*Available Commands:*\n"
            "• `search patient <name>` - Find patients by name\n"
            "• `patient info <id>` - Get detailed patient information\n"
            "• `schedule appointment` - Schedule new appointments\n"
            "• `menu` - Show main menu\n"
            "• `logout` - Sign out of the bot\n\n"
            "*Privacy Guidelines:*\n"
            "• Only access patient data when necessary\n"
            "• Do not share patient information via WhatsApp\n"
            "• Use secure channels for sensitive data\n\n"
            "*Examples:*\n"
            "• `search patient John Doe`\n"
            "• `patient info P123456`\n\n"
            "*Need Support?*\n"
            "Contact IT support for technical assistance."
        )
    
    def _create_unknown_command_response(self, phone_number: str) -> IMResponse:
        """Create response for unknown commands"""
        msg = (
            "❓ I didn't understand that command. "
            "Type `help` or `menu` for options."
        )
        return IMResponse(phone_number, MessageType.TEXT, msg)
    
    def _create_error_response(self, phone_number: str) -> IMResponse:
        """Create generic error response"""
        msg = (
            "Sorry, something went wrong while processing your request. "
            "Try again or type `help`."
        )
        return IMResponse(phone_number, MessageType.TEXT, msg)