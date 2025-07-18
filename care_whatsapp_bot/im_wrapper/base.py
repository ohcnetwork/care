from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    CONTACT = "contact"


class UserType(Enum):
    PATIENT = "patient"
    HOSPITAL_STAFF = "hospital_staff"
    UNKNOWN = "unknown"


class IMMessage:
    """Standardized message format for all IM platforms"""
    
    def __init__(
        self,
        sender_id: str,
        message_type: MessageType,
        content: str,
        platform: str,
        timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.sender_id = sender_id
        self.message_type = message_type
        self.content = content
        self.platform = platform
        self.timestamp = timestamp
        self.metadata = metadata or {}


class IMResponse:
    """Standardized response format for all IM platforms"""
    
    def __init__(
        self,
        recipient_id: str,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.recipient_id = recipient_id
        self.message_type = message_type
        self.content = content
        self.metadata = metadata or {}


class BaseIMProvider(ABC):
    """Abstract base class for IM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.get_platform_name()
    
    @abstractmethod
    def get_platform_name(self) -> str:
        """Return the platform name (e.g., 'whatsapp', 'telegram')"""
        pass
    
    @abstractmethod
    def parse_incoming_message(self, raw_data: Dict[str, Any]) -> IMMessage:
        """Parse platform-specific incoming message to standardized format"""
        pass
    
    @abstractmethod
    def send_message(self, response: IMResponse) -> bool:
        """Send message through the platform"""
        pass
    
    @abstractmethod
    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """Validate webhook signature for security"""
        pass
    
    @abstractmethod
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information from the platform"""
        pass