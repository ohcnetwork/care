#!/usr/bin/env python3
"""
Quick reference guide for patients using the CARE WhatsApp Bot
"""

def show_patient_quick_guide():
    """Show a quick reference guide for patients"""
    
    print("📱 CARE WhatsApp Bot - Patient Quick Reference")
    print("=" * 60)
    print()
    
    print("🚀 GETTING STARTED:")
    print("1. Type 'login' to start")
    print("2. Enter the 6-digit code sent to your phone")
    print("3. You're ready to go!")
    print()
    
    print("💬 AVAILABLE COMMANDS:")
    print("┌─────────────────────────────────────────────────────────┐")
    print("│ 📅 appointments    - View your upcoming appointments    │")
    print("│ 💊 medications     - Check your current medications     │")
    print("│ 🗓️ available slots  - See available appointment slots   │")
    print("│ 📋 records         - View your medical records          │")
    print("│ 🏥 procedures      - See recent medical procedures      │")
    print("│ 📞 book appointment - Book a new appointment            │")
    print("│ 📋 menu            - Show all options                   │")
    print("│ ❓ help            - Get help and support               │")
    print("│ 🚪 logout          - Sign out securely                  │")
    print("└─────────────────────────────────────────────────────────┘")
    print()
    
    print("🎯 QUICK TIPS:")
    print("• Just type the command name (e.g., 'appointments')")
    print("• Commands are case-insensitive")
    print("• Type 'menu' anytime to see all options")
    print("• Your session is secure and expires after 24 hours")
    print()
    
    print("🔒 PRIVACY & SECURITY:")
    print("• Only you can access your medical information")
    print("• All data is encrypted and secure")
    print("• No sensitive data is stored in WhatsApp")
    print("• Always logout when done")
    print()
    
    print("📞 NEED HELP?")
    print("• Type 'help' for in-app assistance")
    print("• Contact your healthcare provider")
    print("• Visit your facility for in-person support")
    print()
    
    print("✨ EXAMPLE CONVERSATION:")
    print("You: login")
    print("Bot: Welcome! Enter your 6-digit verification code...")
    print("You: 123456")
    print("Bot: Welcome back! How can I help you today?")
    print("You: appointments")
    print("Bot: Here are your upcoming appointments...")
    print("You: medications")
    print("Bot: Here are your current medications...")
    print("You: logout")
    print("Bot: Logged out successfully!")

if __name__ == "__main__":
    show_patient_quick_guide()