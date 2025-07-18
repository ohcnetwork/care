# CARE WhatsApp Bot Plugin

A comprehensive WhatsApp bot integration for the CARE platform, enabling patients and hospital staff to interact with the system through WhatsApp messages.

## Features

### For Patients
- 🔐 **Secure Authentication**: OTP-based login system
- 📋 **Medical Records**: Access to personal medical history
- 💊 **Medication Information**: View current and past medications
- 📅 **Appointment Management**: Check upcoming appointments
- 🏥 **Procedure History**: Access to medical procedures
- 📱 **Real-time Notifications**: Appointment reminders, medication alerts

### For Hospital Staff
- 👥 **Patient Search**: Find patients by name or phone number
- 📊 **Patient Information**: Quick access to patient data
- 📅 **Appointment Scheduling**: Schedule appointments via WhatsApp
- 🔒 **Privacy Controls**: Automatic data filtering and masking

### System Features
- 🔄 **Async Processing**: Celery-based message processing
- 📈 **Analytics**: Usage tracking and reporting
- 🛡️ **Security**: Webhook signature validation, rate limiting
- 🗄️ **Data Management**: Automatic cleanup and archiving
- 🔧 **Admin Interface**: Django admin integration

## Installation

### Prerequisites

1. **CARE Platform**: This plugin requires a running CARE instance
2. **WhatsApp Business API**: Access to WhatsApp Business API
3. **Redis**: For caching and Celery task queue
4. **Celery**: For async task processing

### Step 1: Install the Plugin

```bash
# Clone the plugin into your CARE project
cd /path/to/your/care/project
git clone https://github.com/your-org/care_whatsapp_bot.git

# Install dependencies
cd care_whatsapp_bot
pip install -r requirements.txt
```

### Step 2: Configure Django Settings

Add the plugin to your CARE settings:

```python
# settings.py

INSTALLED_APPS = [
    # ... existing apps
    'care_whatsapp_bot',
]

# WhatsApp Configuration
WHATSAPP_ACCESS_TOKEN = 'your_whatsapp_access_token'
WHATSAPP_PHONE_NUMBER_ID = 'your_phone_number_id'
WHATSAPP_APP_SECRET = 'your_app_secret'
WHATSAPP_VERIFY_TOKEN = 'your_verify_token'
WHATSAPP_WEBHOOK_URL = 'https://yourdomain.com/whatsapp/webhook/'

# Celery Configuration (if not already configured)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Cache Configuration (if not already configured)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### Step 3: Update URL Configuration

Add WhatsApp bot URLs to your main `urls.py`:

```python
# urls.py

from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('whatsapp/', include('care_whatsapp_bot.urls')),
]
```

### Step 4: Run Migrations

```bash
python manage.py makemigrations care_whatsapp_bot
python manage.py migrate
```

### Step 5: Set Up WhatsApp Webhook

```bash
# Set up webhook (replace with your actual values)
python manage.py setup_whatsapp_webhook \
    --webhook-url https://yourdomain.com/whatsapp/webhook/ \
    --verify-token your_verify_token \
    --access-token your_access_token \
    --phone-number-id your_phone_number_id

# Test with a message
python manage.py setup_whatsapp_webhook \
    --test-message +1234567890
```

### Step 6: Start Celery Workers

```bash
# Start Celery worker
celery -A care worker -l info

# Start Celery beat (for scheduled tasks)
celery -A care beat -l info
```

## Configuration

### Environment Variables

For production, use environment variables:

```bash
export WHATSAPP_ACCESS_TOKEN="your_access_token"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_number_id"
export WHATSAPP_APP_SECRET="your_app_secret"
export WHATSAPP_VERIFY_TOKEN="your_verify_token"
export WHATSAPP_WEBHOOK_URL="https://yourdomain.com/whatsapp/webhook/"
```

### WhatsApp Business API Setup

1. **Create a WhatsApp Business Account**
2. **Set up a WhatsApp Business API application**
3. **Get your access token and phone number ID**
4. **Configure webhook URL** pointing to your CARE instance

### Development Setup with ngrok

For local development:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Expose local server
ngrok http 8000

# Use the HTTPS URL provided by ngrok as your webhook URL
```

## Usage

### Patient Commands

- `login` - Start authentication process
- `help` - Show available commands
- `menu` - Show main menu
- `get records` - View medical records
- `get medications` - View medications
- `get appointments` - View appointments
- `get procedures` - View procedures
- `logout` - End session

### Staff Commands

- `login` - Start authentication process
- `patient search <name>` - Search for patients
- `patient info <phone>` - Get patient information
- `schedule appointment <details>` - Schedule appointment
- `help` - Show available commands
- `logout` - End session

### Example Conversation

```
User: login
Bot: 🔐 Please enter your phone number to receive an OTP.

User: +1234567890
Bot: 📱 OTP sent to +1234567890. Please enter the 6-digit code.

User: 123456
Bot: ✅ Login successful! Welcome to CARE.

User: get records
Bot: 📋 Your Medical Records:
     • Visit on 2023-12-01: General Checkup
     • Visit on 2023-11-15: Blood Test
     ...
```

## API Endpoints

### Webhook Endpoints

- `GET /whatsapp/webhook/` - Webhook verification
- `POST /whatsapp/webhook/` - Receive WhatsApp messages

### Utility Endpoints

- `GET /whatsapp/health/` - Health check
- `POST /whatsapp/test/send/` - Send test message (debug mode only)

## Administration

### Django Admin

Access the Django admin interface to manage:

- **WhatsApp Sessions**: View and manage user sessions
- **WhatsApp Messages**: Monitor message logs
- **WhatsApp Commands**: Track command usage
- **WhatsApp Notifications**: Manage notifications

### Management Commands

```bash
# Set up webhook
python manage.py setup_whatsapp_webhook --help

# Clean up old data
python manage.py cleanup_whatsapp_data

# Generate analytics
python manage.py generate_whatsapp_analytics
```

### Monitoring

#### Health Check

```bash
curl https://yourdomain.com/whatsapp/health/
```

#### Analytics

View analytics in Django admin or access via cache:

```python
from django.core.cache import cache
analytics = cache.get('whatsapp_analytics')
```

## Security

### Data Privacy

- **PII Filtering**: Automatic filtering of sensitive patient data
- **Phone Number Masking**: Partial masking of phone numbers
- **Access Controls**: Role-based access to patient information

### Security Features

- **Webhook Signature Validation**: Verify WhatsApp webhook authenticity
- **Rate Limiting**: Prevent abuse and spam
- **Session Management**: Secure session handling with expiration
- **OTP Authentication**: Secure login process

### Best Practices

1. **Use HTTPS**: Always use HTTPS for webhook URLs
2. **Secure Secrets**: Store API keys and secrets securely
3. **Regular Cleanup**: Implement regular data cleanup
4. **Monitor Usage**: Track and monitor bot usage
5. **Error Handling**: Implement comprehensive error handling

## Development

### Running Tests

```bash
# Run all tests
python manage.py test care_whatsapp_bot

# Run with coverage
pytest --cov=care_whatsapp_bot

# Run specific test
python manage.py test care_whatsapp_bot.tests.WhatsAppModelTests
```

### Code Structure

```
care_whatsapp_bot/
├── __init__.py
├── apps.py                 # Django app configuration
├── models.py              # Database models
├── admin.py               # Django admin configuration
├── views.py               # Django views
├── urls.py                # URL configuration
├── signals.py             # Django signals
├── tasks.py               # Celery tasks
├── tests.py               # Test cases
├── authentication.py      # Authentication logic
├── message_router.py      # Message routing logic
├── im_wrapper/
│   ├── __init__.py
│   ├── base.py           # Base IM interface
│   └── whatsapp.py       # WhatsApp implementation
├── handlers/
│   ├── __init__.py
│   ├── common_handler.py  # Common commands
│   ├── patient_handler.py # Patient-specific commands
│   └── staff_handler.py   # Staff-specific commands
├── utils/
│   ├── __init__.py
│   ├── privacy_filter.py  # Data privacy utilities
│   └── data_formatter.py  # Message formatting
├── management/
│   └── commands/
│       └── setup_whatsapp_webhook.py
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── requirements.txt       # Dependencies
└── README.md             # This file
```

### Adding New Commands

1. **Add command to router** in `message_router.py`
2. **Implement handler** in appropriate handler file
3. **Add tests** in `tests.py`
4. **Update help text** in `common_handler.py`

### Extending for Other IM Platforms

1. **Create new provider** in `im_wrapper/`
2. **Implement base interface** from `base.py`
3. **Update router** to support new provider
4. **Add configuration** for new platform

## Troubleshooting

### Common Issues

#### Webhook Not Receiving Messages

1. Check webhook URL is accessible
2. Verify webhook signature validation
3. Check WhatsApp Business API configuration
4. Review server logs for errors

#### OTP Not Sending

1. Verify SMS configuration in CARE
2. Check AWS SNS settings
3. Verify phone number format
4. Check rate limiting

#### Messages Not Processing

1. Check Celery worker is running
2. Verify Redis connection
3. Check task queue status
4. Review error logs

### Debugging

```bash
# Check Celery status
celery -A care inspect active

# Monitor Celery logs
celery -A care worker -l debug

# Check Redis
redis-cli ping

# View Django logs
tail -f /path/to/django.log
```

### Support

For issues and support:

1. Check the [CARE documentation](https://care-docs.ohc.network/)
2. Review [WhatsApp Business API documentation](https://developers.facebook.com/docs/whatsapp)
3. Open an issue on the project repository
4. Contact the CARE development team

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v1.0.0
- Initial release
- Patient and staff authentication
- Basic command handling
- WhatsApp Business API integration
- Django admin interface
- Celery task processing
- Comprehensive test suite