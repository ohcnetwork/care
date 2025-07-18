#!/usr/bin/env python3
"""
Environment Configuration Validator for CARE WhatsApp Bot
Ensures all required environment variables are properly set before starting the application.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class EnvironmentValidator:
    """Validates and manages environment configuration for the CARE WhatsApp Bot."""
    
    REQUIRED_VARS = {
        'DJANGO_READ_DOT_ENV_FILE': 'Enable .env file loading',
        'WHATSAPP_ACCESS_TOKEN': 'WhatsApp Business API access token',
        'WHATSAPP_PHONE_NUMBER_ID': 'WhatsApp Business phone number ID',
        'WHATSAPP_WEBHOOK_VERIFY_TOKEN': 'Webhook verification token',
    }
    
    OPTIONAL_VARS = {
        'WHATSAPP_APP_SECRET': 'App secret for webhook signature validation',
        'WHATSAPP_WEBHOOK_URL': 'Public webhook URL',
        'DATABASE_URL': 'Database connection string',
        'REDIS_URL': 'Redis connection string',
    }
    
    def __init__(self, env_file_path: Optional[str] = None):
        self.env_file_path = env_file_path or '.env'
        self.issues: List[str] = []
        self.warnings: List[str] = []
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate environment configuration.
        
        Returns:
            Tuple of (is_valid, issues, warnings)
        """
        self._check_env_file()
        self._check_required_vars()
        self._check_optional_vars()
        self._validate_token_formats()
        
        return len(self.issues) == 0, self.issues, self.warnings
    
    def _check_env_file(self):
        """Check if .env file exists and is readable."""
        env_path = Path(self.env_file_path)
        if not env_path.exists():
            self.issues.append(f"Environment file '{self.env_file_path}' not found")
            return
        
        if not env_path.is_file():
            self.issues.append(f"'{self.env_file_path}' is not a file")
            return
        
        try:
            with open(env_path, 'r') as f:
                content = f.read()
                if not content.strip():
                    self.warnings.append("Environment file is empty")
        except PermissionError:
            self.issues.append(f"Cannot read '{self.env_file_path}' - permission denied")
    
    def _check_required_vars(self):
        """Check if all required environment variables are set."""
        for var, description in self.REQUIRED_VARS.items():
            value = os.getenv(var)
            if not value:
                self.issues.append(f"Missing required variable: {var} ({description})")
            elif value.strip() == '':
                self.issues.append(f"Empty required variable: {var} ({description})")
    
    def _check_optional_vars(self):
        """Check optional environment variables and provide warnings."""
        for var, description in self.OPTIONAL_VARS.items():
            value = os.getenv(var)
            if not value:
                self.warnings.append(f"Optional variable not set: {var} ({description})")
    
    def _validate_token_formats(self):
        """Validate the format of tokens and IDs."""
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN', '')
        if access_token and not access_token.startswith('EAA'):
            self.warnings.append("WhatsApp access token format looks unusual (should start with 'EAA')")
        
        phone_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')
        if phone_id and not phone_id.isdigit():
            self.warnings.append("WhatsApp phone number ID should be numeric")
    
    def auto_fix(self) -> bool:
        """
        Attempt to automatically fix common issues.
        
        Returns:
            True if any fixes were applied
        """
        fixes_applied = False
        
        # Fix missing DJANGO_READ_DOT_ENV_FILE
        if not os.getenv('DJANGO_READ_DOT_ENV_FILE'):
            self._add_to_env_file('DJANGO_READ_DOT_ENV_FILE', 'True')
            fixes_applied = True
        
        return fixes_applied
    
    def _add_to_env_file(self, key: str, value: str):
        """Add a key-value pair to the .env file."""
        env_path = Path(self.env_file_path)
        if not env_path.exists():
            return
        
        with open(env_path, 'a') as f:
            f.write(f"\n{key}={value}\n")
    
    def generate_report(self) -> str:
        """Generate a detailed validation report."""
        report = ["🔍 Environment Configuration Report", "=" * 50]
        
        if not self.issues and not self.warnings:
            report.append("✅ All environment variables are properly configured!")
            return "\n".join(report)
        
        if self.issues:
            report.extend(["\n❌ Issues Found:", "-" * 20])
            for issue in self.issues:
                report.append(f"  • {issue}")
        
        if self.warnings:
            report.extend(["\n⚠️  Warnings:", "-" * 20])
            for warning in self.warnings:
                report.append(f"  • {warning}")
        
        report.extend([
            "\n💡 Recommendations:",
            "-" * 20,
            "  • Run 'python env_validator.py --fix' to auto-fix common issues",
            "  • Check the ENHANCED_SETUP_GUIDE.md for detailed instructions",
            "  • Ensure all tokens are up-to-date and valid"
        ])
        
        return "\n".join(report)

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate CARE WhatsApp Bot environment configuration")
    parser.add_argument('--env-file', default='.env', help='Path to environment file')
    parser.add_argument('--fix', action='store_true', help='Attempt to auto-fix issues')
    parser.add_argument('--quiet', action='store_true', help='Only show errors')
    
    args = parser.parse_args()
    
    validator = EnvironmentValidator(args.env_file)
    is_valid, issues, warnings = validator.validate()
    
    if args.fix:
        fixes_applied = validator.auto_fix()
        if fixes_applied:
            print("🔧 Auto-fixes applied. Please restart your application.")
            # Re-validate after fixes
            validator = EnvironmentValidator(args.env_file)
            is_valid, issues, warnings = validator.validate()
    
    if not args.quiet:
        print(validator.generate_report())
    
    if not is_valid:
        sys.exit(1)
    
    print("\n✅ Environment validation passed!")

if __name__ == "__main__":
    main()