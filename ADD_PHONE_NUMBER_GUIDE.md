📱 How to Add Your Phone Number to WhatsApp Business API
========================================================

🔥 IMPORTANT: You MUST add your phone number to the allowed list before testing!

Step-by-Step Instructions:
=========================

1. 🌐 Go to Meta Developer Console
   → Open: https://developers.facebook.com/
   → Login with your Facebook account

2. 📱 Select Your WhatsApp App
   → Click on your WhatsApp Business app
   → If you don't have one, create a new app first

3. 🔧 Navigate to WhatsApp Settings
   → In the left sidebar, click "WhatsApp"
   → Click "Getting Started"

4. 📞 Add Your Phone Number
   → Scroll to "Send and receive messages" section
   → Click "Add recipient phone number"
   → Enter your phone number with country code (e.g., +918767341918)
   → Click "Add"

5. ✅ Verify Your Number
   → WhatsApp will send you an OTP
   → Enter the OTP to verify your number
   → Your number is now in the allowed list!

6. 🚀 Test the Bot
   → Run: python quick_whatsapp_test.py
   → Enter your phone number when prompted
   → Check your WhatsApp for the test message!

Alternative Method (API):
========================

You can also add numbers via API:
```bash
curl -X POST \
  "https://graph.facebook.com/v23.0/YOUR_PHONE_NUMBER_ID/phone_numbers" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+918767341918",
    "pin": "123456"
  }'
```

Current Configuration:
=====================
• Phone Number ID: 651347521403933
• Access Token: EAFYi1HZB6eFQ... (configured)
• Webhook URL: https://whatsapp-bot.botforcare.social/api/care_whatsapp_bot/webhook/
• Verify Token: GSoC2025CareBot

Troubleshooting:
===============

❌ "Recipient phone number not in allowed list"
   → Add your number in Meta Developer Console

❌ "Invalid phone number format"
   → Use international format: +918767341918

❌ "Message not delivered"
   → Check if WhatsApp is installed on your phone
   → Verify your phone number is correct

❌ "Webhook verification failed"
   → Check if your server is accessible
   → Verify the webhook URL and verify token

Ready to Test? 🚀
================

1. Add your number to the allowed list (steps above)
2. Run: python quick_whatsapp_test.py
3. Enter your phone number
4. Check WhatsApp for the test message
5. Reply with "hi" to start chatting with the bot!

Commands to try:
• hi → Welcome message
• help → Show all commands
• register → Create new account
• login → Login to existing account
• menu → Show main menu
• appointments → View appointments
• medications → View medications
• available slots → Check available slots