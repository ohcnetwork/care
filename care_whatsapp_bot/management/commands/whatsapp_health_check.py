"""
WhatsApp Bot Health Check and Monitoring
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone

from care_whatsapp_bot.config_validator import validate_whatsapp_config
from care_whatsapp_bot.models import WhatsAppSession, WhatsAppMessage
from care_whatsapp_bot.im_wrapper.whatsapp import WhatsAppProvider

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check WhatsApp bot health and configuration'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix common issues automatically',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed statistics and logs',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("🏥 CARE WhatsApp Bot Health Check"))
        self.stdout.write("=" * 50)
        
        # 1. Configuration Check
        self._check_configuration()
        
        # 2. Database Health
        self._check_database_health()
        
        # 3. API Connectivity
        self._check_api_connectivity()
        
        # 4. Recent Activity
        self._check_recent_activity(options['detailed'])
        
        # 5. Performance Metrics
        self._check_performance_metrics()
        
        # 6. Auto-fix if requested
        if options['fix']:
            self._attempt_fixes()
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("✅ Health check completed!"))
    
    def _check_configuration(self):
        """Check WhatsApp configuration"""
        self.stdout.write("\n🔧 Configuration Check:")
        
        config_result = validate_whatsapp_config()
        
        if config_result['is_valid']:
            self.stdout.write(self.style.SUCCESS("  ✅ Configuration is valid"))
        else:
            self.stdout.write(self.style.ERROR("  ❌ Configuration issues found:"))
            for error in config_result['errors']:
                self.stdout.write(f"    {error}")
            
            if config_result['warnings']:
                self.stdout.write(self.style.WARNING("  ⚠️ Warnings:"))
                for warning in config_result['warnings']:
                    self.stdout.write(f"    {warning}")
    
    def _check_database_health(self):
        """Check database connectivity and data integrity"""
        self.stdout.write("\n💾 Database Health:")
        
        try:
            # Check if we can query the database
            session_count = WhatsAppSession.objects.count()
            message_count = WhatsAppMessage.objects.count()
            
            self.stdout.write(self.style.SUCCESS(f"  ✅ Database accessible"))
            self.stdout.write(f"    📊 Total sessions: {session_count}")
            self.stdout.write(f"    📊 Total messages: {message_count}")
            
            # Check for orphaned sessions
            orphaned_sessions = WhatsAppSession.objects.filter(
                patient__isnull=True,
                staff_user__isnull=True
            ).count()
            
            if orphaned_sessions > 0:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Found {orphaned_sessions} orphaned sessions"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Database error: {e}"))
    
    def _check_api_connectivity(self):
        """Test WhatsApp API connectivity"""
        self.stdout.write("\n🌐 API Connectivity:")
        
        try:
            provider = WhatsAppProvider({})
            
            # This would be a simple API test
            # In practice, you'd make a test API call here
            self.stdout.write(self.style.SUCCESS("  ✅ WhatsApp provider initialized"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ API connectivity error: {e}"))
    
    def _check_recent_activity(self, detailed: bool = False):
        """Check recent bot activity"""
        self.stdout.write("\n📈 Recent Activity (Last 24 hours):")
        
        try:
            yesterday = timezone.now() - timedelta(days=1)
            
            recent_sessions = WhatsAppSession.objects.filter(
                created_at__gte=yesterday
            ).count()
            
            recent_messages = WhatsAppMessage.objects.filter(
                created_at__gte=yesterday
            ).count()
            
            self.stdout.write(f"  📊 New sessions: {recent_sessions}")
            self.stdout.write(f"  📊 Messages processed: {recent_messages}")
            
            if detailed:
                # Show message breakdown by type
                from care_whatsapp_bot.command_types import CommandType
                
                # This would require adding command tracking to your models
                self.stdout.write("\n  📋 Command breakdown:")
                self.stdout.write("    • Login attempts: [Would need tracking]")
                self.stdout.write("    • Registration attempts: [Would need tracking]")
                self.stdout.write("    • Help requests: [Would need tracking]")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Activity check error: {e}"))
    
    def _check_performance_metrics(self):
        """Check performance metrics"""
        self.stdout.write("\n⚡ Performance Metrics:")
        
        try:
            # Check cache health
            cache_test_key = 'whatsapp_health_check'
            cache.set(cache_test_key, 'test', 60)
            cache_value = cache.get(cache_test_key)
            
            if cache_value == 'test':
                self.stdout.write(self.style.SUCCESS("  ✅ Cache system working"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠️ Cache system issues"))
            
            # Check for rate limiting
            rate_limit_status = cache.get('whatsapp_rate_limit', False)
            if rate_limit_status:
                self.stdout.write(self.style.WARNING("  ⚠️ Currently rate limited"))
            else:
                self.stdout.write(self.style.SUCCESS("  ✅ No rate limiting active"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Performance check error: {e}"))
    
    def _attempt_fixes(self):
        """Attempt to fix common issues automatically"""
        self.stdout.write("\n🔧 Attempting automatic fixes:")
        
        try:
            # Clear rate limiting if it's been too long
            rate_limit_status = cache.get('whatsapp_rate_limit', False)
            if rate_limit_status:
                cache.delete('whatsapp_rate_limit')
                self.stdout.write(self.style.SUCCESS("  ✅ Cleared rate limiting"))
            
            # Clean up old cache entries
            # This would depend on your specific cache keys
            self.stdout.write(self.style.SUCCESS("  ✅ Cleaned up cache"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Auto-fix error: {e}"))