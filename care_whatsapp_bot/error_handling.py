"""
Enhanced Error Handling and Monitoring for WhatsApp Bot
Provides structured error handling, retry logic, and monitoring capabilities.
"""
import logging
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppErrorHandler:
    """Centralized error handling for WhatsApp operations"""
    
    # Error codes and their meanings
    ERROR_CODES = {
        100: "Invalid parameter or missing permission",
        190: "Access token expired or invalid", 
        200: "Permission denied",
        368: "Temporarily blocked for policy violations",
        131000: "Message undeliverable",
        131005: "Message template not found",
        131008: "Parameter format error",
        131009: "Parameter missing",
        131014: "Template parameter count mismatch",
        131016: "Template does not exist",
        131021: "Recipient phone number not valid",
        131026: "Message quota exceeded",
        131031: "Unsupported message type",
        131047: "Re-engagement message",
        131051: "Unsupported message type for recipient",
        132000: "Generic user error",
        132001: "User's number is part of an experiment",
        132005: "User phone number not valid",
        132007: "User not found",
        132012: "Parameter value not valid",
        132015: "Generic user error",
        132016: "User has not accepted our new Terms of Service and Privacy Policy",
        133000: "Generic system error",
        133004: "Request timeout",
        133005: "Service temporarily unavailable",
        133006: "Server temporarily overloaded",
        133008: "Could not display message",
        133010: "Message failed to send",
        133015: "Generic system error",
        133016: "Service temporarily unavailable",
    }
    
    # Retry-able error codes
    RETRYABLE_ERRORS = {133004, 133005, 133006, 133016}
    
    # Rate limit error codes
    RATE_LIMIT_ERRORS = {131026, 368}
    
    def __init__(self):
        self.error_stats = {}
    
    def handle_api_error(self, error_response: Dict[str, Any], context: str = "") -> Dict[str, Any]:
        """Handle WhatsApp API error response"""
        error_info = error_response.get('error', {})
        error_code = error_info.get('code', 0)
        error_message = error_info.get('message', 'Unknown error')
        error_subcode = error_info.get('error_subcode', 0)
        fbtrace_id = error_info.get('fbtrace_id', '')
        
        # Log structured error
        logger.error(
            f"WhatsApp API Error [{context}]: "
            f"Code={error_code}, Subcode={error_subcode}, "
            f"Message='{error_message}', TraceID={fbtrace_id}"
        )
        
        # Update error statistics
        self._update_error_stats(error_code, context)
        
        # Determine error category and action
        error_category = self._categorize_error(error_code)
        suggested_action = self._get_suggested_action(error_code)
        
        return {
            'error_code': error_code,
            'error_subcode': error_subcode,
            'error_message': error_message,
            'error_category': error_category,
            'suggested_action': suggested_action,
            'is_retryable': error_code in self.RETRYABLE_ERRORS,
            'is_rate_limit': error_code in self.RATE_LIMIT_ERRORS,
            'fbtrace_id': fbtrace_id,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
    
    def _categorize_error(self, error_code: int) -> str:
        """Categorize error for better handling"""
        if error_code in {190}:
            return "authentication"
        elif error_code in {131021, 132005, 132007}:
            return "user_error"
        elif error_code in {131026, 368}:
            return "rate_limit"
        elif error_code in {133004, 133005, 133006, 133016}:
            return "temporary_failure"
        elif error_code in {131000, 131031, 131051}:
            return "message_error"
        elif error_code in {131005, 131016}:
            return "template_error"
        else:
            return "unknown"
    
    def _get_suggested_action(self, error_code: int) -> str:
        """Get suggested action for error code"""
        actions = {
            190: "Refresh access token",
            131021: "Validate phone number format",
            131026: "Implement rate limiting",
            131031: "Check message type support",
            133004: "Retry with exponential backoff",
            133005: "Retry after delay",
            368: "Review message content for policy violations"
        }
        return actions.get(error_code, "Check WhatsApp API documentation")
    
    def _update_error_stats(self, error_code: int, context: str):
        """Update error statistics for monitoring"""
        key = f"whatsapp_error_{error_code}_{context}"
        current_count = cache.get(key, 0)
        cache.set(key, current_count + 1, timeout=3600)  # 1 hour
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        # This would typically integrate with your monitoring system
        return {
            'timestamp': datetime.now().isoformat(),
            'error_counts': self.error_stats,
            'health_status': self._calculate_health_status()
        }
    
    def _calculate_health_status(self) -> str:
        """Calculate overall health status based on error rates"""
        # Implement your health calculation logic
        return "healthy"  # Simplified for example


class RetryHandler:
    """Handles retry logic for WhatsApp API calls"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def with_retry(self, retryable_errors: set = None):
        """Decorator for adding retry logic to functions"""
        if retryable_errors is None:
            retryable_errors = WhatsAppErrorHandler.RETRYABLE_ERRORS
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(self.max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        # Check if error is retryable
                        if hasattr(e, 'response') and e.response:
                            try:
                                error_data = e.response.json()
                                error_code = error_data.get('error', {}).get('code', 0)
                                if error_code not in retryable_errors:
                                    break  # Don't retry non-retryable errors
                            except:
                                pass
                        
                        if attempt < self.max_retries:
                            delay = self.base_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(
                                f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}"
                            )
                            time.sleep(delay)
                        else:
                            logger.error(f"All {self.max_retries + 1} attempts failed")
                
                raise last_exception
            
            return wrapper
        return decorator


class WhatsAppMonitor:
    """Monitoring and metrics for WhatsApp bot operations"""
    
    def __init__(self):
        self.metrics_prefix = "whatsapp_bot"
    
    def record_message_sent(self, recipient_id: str, success: bool, response_time: float = None):
        """Record message sending metrics"""
        cache_key = f"{self.metrics_prefix}_messages_sent"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, timeout=3600)
        
        if success:
            success_key = f"{self.metrics_prefix}_messages_success"
            success_count = cache.get(success_key, 0)
            cache.set(success_key, success_count + 1, timeout=3600)
        
        if response_time:
            # Record response time (simplified - in production use proper metrics)
            rt_key = f"{self.metrics_prefix}_response_time"
            cache.set(rt_key, response_time, timeout=300)
    
    def record_message_received(self, sender_id: str, message_type: str):
        """Record message receiving metrics"""
        cache_key = f"{self.metrics_prefix}_messages_received"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, timeout=3600)
        
        type_key = f"{self.metrics_prefix}_message_type_{message_type}"
        type_count = cache.get(type_key, 0)
        cache.set(type_key, type_count + 1, timeout=3600)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary for monitoring dashboard"""
        return {
            'messages_sent': cache.get(f"{self.metrics_prefix}_messages_sent", 0),
            'messages_success': cache.get(f"{self.metrics_prefix}_messages_success", 0),
            'messages_received': cache.get(f"{self.metrics_prefix}_messages_received", 0),
            'response_time': cache.get(f"{self.metrics_prefix}_response_time", 0),
            'timestamp': datetime.now().isoformat()
        }


# Global instances
error_handler = WhatsAppErrorHandler()
retry_handler = RetryHandler()
monitor = WhatsAppMonitor()