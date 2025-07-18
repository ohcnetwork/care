#!/usr/bin/env python3
"""
Demo script showing what a patient would see when using WhatsApp commands
"""

def show_patient_demo():
    """Show what a patient would see when using WhatsApp commands"""
    
    print("🏥 CARE WhatsApp Bot - Patient Experience Demo")
    print("=" * 60)
    print()
    
    print("📱 Patient types: 'login'")
    print("🤖 Bot responds:")
    print("""🏥 Hello! Welcome to CARE - Your Digital Healthcare Companion! 👋

🌟 We're excited to help you manage your healthcare needs conveniently through WhatsApp.

🔐 For your security, we've sent a 6-digit verification code to your phone.

📱 Reply with verification code to access your CARE account.""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: '123456' (OTP)")
    print("🤖 Bot responds:")
    print("""🎉 Welcome to CARE, Test Patient! 

✅ You are now successfully logged in as a Patient.

🏥 Your digital healthcare companion is ready to assist you!

📋 Available services:""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'menu'")
    print("🤖 Bot responds:")
    print("""👤 *Patient Menu*

What would you like to do?

📋 `records` - View medical records
💊 `medications` - View current medications
📅 `appointments` - View upcoming appointments
🏥 `procedures` - View recent procedures
🗓️ `available slots` - Check available appointment slots
📞 `book appointment` - Book a new appointment

ℹ️ `help` - Get help
🚪 `logout` - Sign out""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'appointments'")
    print("🤖 Bot responds:")
    print("""📅 *Upcoming Appointments*

*1. 2024-01-15 10:00 AM*
Facility: City General Hospital
Doctor: Dr. Sarah Johnson
Type: Regular Checkup

*2. 2024-01-22 02:30 PM*
Facility: Community Health Center
Doctor: Dr. Michael Chen
Type: Follow-up Consultation

📞 *Reminder:* Please arrive 15 minutes early for your appointment.""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'medications'")
    print("🤖 Bot responds:")
    print("""💊 *Current Medications*

*1. Metformin 500mg*
Dosage: 500mg
Frequency: Twice daily
Instructions: Take with meals
Status: active

*2. Lisinopril 10mg*
Dosage: 10mg
Frequency: Once daily
Instructions: Take in the morning
Status: active

⚠️ Follow doctor's instructions. Don't change meds without consulting.""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'available slots'")
    print("🤖 Bot responds:")
    print("""🏥 *Available Appointment Slots*

*1. City General Hospital*
Location: 123 Main Street, Downtown
Available Doctors:
  • Dr. Sarah Johnson
  • Dr. Michael Chen
  • Dr. Emily Davis
Next Available: 2024-01-16 or 2024-01-17

*2. Community Health Center*
Location: 456 Oak Avenue, Midtown
Available Doctors:
  • Dr. Robert Wilson
  • Dr. Lisa Martinez
Next Available: 2024-01-16 or 2024-01-17

📞 *To book an appointment:*
Type 'book appointment' and follow the instructions.

⚠️ Availability may vary. Confirm with facility.""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'records'")
    print("🤖 Bot responds:")
    print("""📋 *Recent Medical Records*

*1. 2024-01-10*
Type: Regular Consultation
Chief Complaint: Routine checkup
Diagnosis: Hypertension, well controlled

*2. 2024-01-03*
Type: Follow-up Visit
Chief Complaint: Medication review
Diagnosis: Diabetes Type 2, stable

*3. 2023-12-20*
Type: Emergency Visit
Chief Complaint: Chest pain
Diagnosis: Anxiety-related chest pain

⚠️ Summary only. Visit provider for complete records.""")
    print("\n" + "-" * 50 + "\n")
    
    print("📱 Patient types: 'book appointment'")
    print("🤖 Bot responds:")
    print("""📅 *Book Appointment*

To book an appointment, please provide:

1️⃣ Preferred facility
2️⃣ Preferred doctor (optional)
3️⃣ Preferred date and time
4️⃣ Reason for visit

*Example:*
Facility: City Hospital
Doctor: Dr. Smith
Date: 2024-01-15
Time: 10:00 AM
Reason: Regular checkup

📞 *Alternative booking methods:*
• Call the facility directly
• Visit the facility in person
• Use the CARE web portal

⚠️ Feature being enhanced. Contact facility for immediate booking.""")
    print("\n" + "-" * 50 + "\n")
    
    print("✅ Demo Complete!")
    print("\n🎯 Key Features Available:")
    print("• ✅ View upcoming appointments")
    print("• ✅ Check current medications")
    print("• ✅ See available appointment slots")
    print("• ✅ View medical records")
    print("• ✅ Book appointments (guided process)")
    print("• ✅ Get help and menu options")
    print("\n🔐 All data is secure and only accessible to the authenticated patient!")

if __name__ == "__main__":
    show_patient_demo()