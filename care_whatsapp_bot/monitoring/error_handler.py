"""
Comprehensive Error Handling and Monitoring for WhatsApp Bot
Provides centralized error handling, retry logic, and monitoring capabilities.
"""
import logging
import time
import json
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    error_code: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    phone_number: Optional[str] = None
    retry_count: int = 0


class WhatsAppErrorHandler:
    """Centralized error handling for WhatsApp operations"""
    
    ERROR_MAPPINGS = {
        # Authentication errors
        190: {
            'category': ErrorCategory.AUTHENTICATION,
            'severity': ErrorSeverity.HIGH,
            'message': 'Access token expired or invalid',
            'action': 'refresh_token'
        },
        104: {
            'category': ErrorCategory.AUTHENTICATION,
            'severity': ErrorSeverity.HIGH,
            'message': 'Access token required',
            'action': 'check_token_config'
        },
        
        # Rate limiting
        4: {
            'category': ErrorCategory.RATE_LIMIT,
            'severity': ErrorSeverity.MEDIUM,
            'message': 'Application request limit reached',
            'action': 'implement_backoff'
        },
        80007: {
            'category': ErrorCategory.RATE_LIMIT,
            'severity': ErrorSeverity.MEDIUM,
            'message': 'Message rate limit exceeded',
            'action': 'implement_backoff'
        },
        
        # API errors
        100: {
            'category': ErrorCategory.API_ERROR,
            'severity': ErrorSeverity.MEDIUM,
            'message': 'Invalid parameter',
            'action': 'validate_request'
        },
        131030: {
            'category': ErrorCategory.API_ERROR,
            'severity': ErrorSeverity.LOW,
            'message': 'Recipient cannot receive messages',
            'action': 'skip_user'
        }
    }
    
    def __init__(self):
        self.cache_prefix = "whatsapp_error"
        
    def handle_api_error(self, response: requests.Response, context: Dict[str, Any] = None) -> ErrorContext:
        """Handle WhatsApp API errors with detailed context"""
        try:
            error_data = response.json().get('error', {})
            error_code = error_data.get('code', 'unknown')
            error_message = error_data.get('message', 'Unknown error')
            
            error_info = self.ERROR_MAPPINGS.get(error_code, {
                'category': ErrorCategory.UNKNOWN,
                'severity': ErrorSeverity.MEDIUM,
                'message': error_message,
                'action': 'investigate'
            })
            
            error_context = ErrorContext(
                error_code=str(error_code),
                category=error_info['category'],
                severity=error_info['severity'],
                message=error_info['message'],
                details={
                    'status_code': response.status_code,
                    'api_response': error_data,
                    'suggested_action': error_info.get('action'),
                    'context': context or {}
                },
                timestamp=datetime.now()
            )
            
            self._log_error(error_context)
            self._cache_error(error_context)
            
            return error_context
            
        except Exception as e:
            logger.error(f"Error handling API error: {e}")
            return self._create_fallback_error(response, context)
    
    def handle_network_error(self, exception: Exception, context: Dict[str, Any] = None) -> ErrorContext:
        """Handle network-related errors"""
        error_context = ErrorContext(
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            message=f"Network error: {str(exception)}",
            details={
                'exception_type': type(exception).__name__,
                'context': context or {}
            },
            timestamp=datetime.now()
        )
        
        self._log_error(error_context)
        self._cache_error(error_context)
        
        return error_context
    
    def _create_fallback_error(self, response: requests.Response, context: Dict[str, Any] = None) -> ErrorContext:
        """Create a fallback error when error parsing fails"""
        return ErrorContext(
            error_code="PARSE_ERROR",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            message=f"Failed to parse error response: {response.status_code}",
            details={
                'status_code': response.status_code,
                'response_text': response.text[:500],  # Limit response text
                'context': context or {}
            },
            timestamp=datetime.now()
        )
    
    def _log_error(self, error_context: ErrorContext):
        """Log error with appropriate level based on severity"""
        log_message = f"WhatsApp Error [{error_context.error_code}]: {error_context.message}"
        
        if error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra={'error_context': asdict(error_context)})
        elif error_context.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra={'error_context': asdict(error_context)})
        elif error_context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra={'error_context': asdict(error_context)})
        else:
            logger.info(log_message, extra={'error_context': asdict(error_context)})
    
    def _cache_error(self, error_context: ErrorContext):
        """Cache error for monitoring and analytics"""
        cache_key = f"{self.cache_prefix}:{error_context.error_code}:{datetime.now().date()}"
        
        # Get existing errors for this code today
        existing_errors = cache.get(cache_key, [])
        existing_errors.append({
            'timestamp': error_context.timestamp.isoformat(),
            'severity': error_context.severity.value,
            'message': error_context.message,
            'phone_number': error_context.phone_number
        })
        
        # Keep only last 100 errors per code per day
        if len(existing_errors) > 100:
            existing_errors = existing_errors[-100:]
        
        cache.set(cache_key, existing_errors, timeout=86400)  # 24 hours
    
    def get_error_summary(self, days: int = 1) -> Dict[str, Any]:
        """Get error summary for monitoring dashboard"""
        summary = {
            'total_errors': 0,
            'by_category': {},
            'by_severity': {},
            'recent_errors': []
        }
        
        # This would typically query a proper monitoring system
        # For now, we'll use cache data
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).date()
            
            for error_code in self.ERROR_MAPPINGS.keys():
                cache_key = f"{self.cache_prefix}:{error_code}:{date}"
                errors = cache.get(cache_key, [])
                
                summary['total_errors'] += len(errors)
                
                if errors:
                    error_info = self.ERROR_MAPPINGS[error_code]
                    category = error_info['category'].value
                    severity = error_info['severity'].value
                    
                    summary['by_category'][category] = summary['by_category'].get(category, 0) + len(errors)
                    summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + len(errors)
                    
                    # Add recent errors (last 10)
                    summary['recent_errors'].extend(errors[-10:])
        
        # Sort recent errors by timestamp
        summary['recent_errors'].sort(key=lambda x: x['timestamp'], reverse=True)
        summary['recent_errors'] = summary['recent_errors'][:20]  # Keep only 20 most recent
        
        return summary


class RetryHandler:
    """Implements retry logic with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for {func.__name__}")
                    break
                
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}, retrying in {delay}s: {e}")
                time.sleep(delay)
        
        raise last_exception
    
    def should_retry(self, error_context: ErrorContext) -> bool:
        """Determine if an error should be retried"""
        # Don't retry authentication errors
        if error_context.category == ErrorCategory.AUTHENTICATION:
            return False
        
        # Don't retry validation errors
        if error_context.category == ErrorCategory.VALIDATION:
            return False
        
        # Retry network and rate limit errors
        if error_context.category in [ErrorCategory.NETWORK, ErrorCategory.RATE_LIMIT]:
            return True
        
        # Retry some API errors
        if error_context.category == ErrorCategory.API_ERROR and error_context.retry_count < 2:
            return True
        
        return False


class WhatsAppMonitor:
    """Monitoring and metrics collection for WhatsApp bot"""
    
    def __init__(self):
        self.metrics_prefix = "whatsapp_metrics"
    
    def record_message_sent(self, success: bool, phone_number: str, message_type: str = "text"):
        """Record message sending metrics"""
        today = datetime.now().date()
        
        # Overall metrics
        self._increment_counter(f"{self.metrics_prefix}:messages_sent:{today}")
        
        if success:
            self._increment_counter(f"{self.metrics_prefix}:messages_success:{today}")
        else:
            self._increment_counter(f"{self.metrics_prefix}:messages_failed:{today}")
        
        # By message type
        self._increment_counter(f"{self.metrics_prefix}:messages_by_type:{message_type}:{today}")
    
    def record_message_received(self, phone_number: str, message_type: str = "text"):
        """Record message receiving metrics"""
        today = datetime.now().date()
        
        self._increment_counter(f"{self.metrics_prefix}:messages_received:{today}")
        self._increment_counter(f"{self.metrics_prefix}:messages_received_by_type:{message_type}:{today}")
    
    def record_user_interaction(self, phone_number: str, command: str):
        """Record user interaction metrics"""
        today = datetime.now().date()
        
        self._increment_counter(f"{self.metrics_prefix}:user_interactions:{today}")
        self._increment_counter(f"{self.metrics_prefix}:commands:{command}:{today}")
    
    def _increment_counter(self, key: str, amount: int = 1):
        """Increment a counter in cache"""
        current_value = cache.get(key, 0)
        cache.set(key, current_value + amount, timeout=86400 * 7)  # Keep for 7 days
    
    def get_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get metrics summary for dashboard"""
        summary = {
            'messages_sent': 0,
            'messages_received': 0,
            'success_rate': 0,
            'top_commands': {},
            'daily_stats': []
        }
        
        total_sent = 0
        total_success = 0
        
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).date()
            
            sent = cache.get(f"{self.metrics_prefix}:messages_sent:{date}", 0)
            received = cache.get(f"{self.metrics_prefix}:messages_received:{date}", 0)
            success = cache.get(f"{self.metrics_prefix}:messages_success:{date}", 0)
            
            total_sent += sent
            total_success += success
            
            summary['daily_stats'].append({
                'date': date.isoformat(),
                'sent': sent,
                'received': received,
                'success': success
            })
        
        summary['messages_sent'] = total_sent
        summary['success_rate'] = (total_success / total_sent * 100) if total_sent > 0 else 0
        
        return summary


# Global instances
error_handler = WhatsAppErrorHandler()
retry_handler = RetryHandler()
monitor = WhatsAppMonitor()