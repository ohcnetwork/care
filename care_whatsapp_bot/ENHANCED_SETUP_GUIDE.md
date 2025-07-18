# 🏥 CARE WhatsApp Bot - Enhanced Setup & Troubleshooting Guide

## 🚀 Quick Start

### 1. **Configuration Validation**
Before starting, validate your WhatsApp configuration:

```bash
python manage.py whatsapp_health_check
```

### 2. **Fix Common Issues**
Run auto-fix for common problems:

```bash
python manage.py whatsapp_health_check --fix
```

## 🔧 **Configuration Management**

### Required Environment Variables
```bash
# Essential settings
WHATSAPP_ACCESS_TOKEN=EAAxxxxx...        # From Facebook Developers
WHATSAPP_PHONE_NUMBER_ID=123456789       # Your WhatsApp Business phone number ID
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_token # Custom verification token

# Optional but recommended
WHATSAPP_APP_SECRET=your_app_secret      # For webhook signature validation
WHATSAPP_WEBHOOK_URL=https://your-domain.com/webhook/
```

### 🔍 **Troubleshooting Common Issues**

#### ❌ **Error: "Object with ID 'messages' does not exist"**
**Cause**: Invalid or expired access token, or missing phone number ID

**Solutions**:
1. **Get a new access token**:
   - Go to [Facebook Developers Console](https://developers.facebook.com/)
   - Select your WhatsApp Business app
   - Navigate to WhatsApp > API Setup
   - Generate a new temporary token
   - Update `WHATSAPP_ACCESS_TOKEN` in your `.env` file

2. **Verify phone number ID**:
   - In the same API Setup page, copy the Phone Number ID
   - Update `WHATSAPP_PHONE_NUMBER_ID` in your `.env` file

3. **Check permissions**:
   - Ensure your app has `whatsapp_business_messaging` permission
   - Verify the phone number is verified in your WhatsApp Business account

#### ❌ **Error: "Rate limited"**
**Cause**: Too many API requests in a short time

**Solutions**:
1. **Clear rate limiting**:
   ```bash
   python manage.py whatsapp_health_check --fix
   ```

2. **Implement exponential backoff** (already included in enhanced provider)

#### ❌ **Error: "Webhook verification failed"**
**Cause**: Incorrect verify token or webhook URL

**Solutions**:
1. **Check verify token**:
   - Ensure `WHATSAPP_WEBHOOK_VERIFY_TOKEN` matches what you set in Facebook
   
2. **Verify webhook URL**:
   - Should be publicly accessible
   - Must use HTTPS in production
   - Should end with `/webhook/`

## 🧪 **Testing**

### Run Enhanced Tests
```bash
# Run all WhatsApp bot tests
python manage.py test care_whatsapp_bot.tests_enhanced

# Run specific test
python manage.py test care_whatsapp_bot.tests_enhanced.WhatsAppBotTestCase.test_registration_flow
```

### Manual Testing
```bash
# Test registration
curl -X POST "http://localhost:8000/webhook/" \\
  -H "Content-Type: application/json" \\
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "919876543210",
            "text": {"body": "register"},
            "type": "text"
          }]
        }
      }]
    }]
  }'
```

## 📊 **Monitoring & Health Checks**

### Daily Health Check
```bash
# Basic health check
python manage.py whatsapp_health_check

# Detailed analysis
python manage.py whatsapp_health_check --detailed

# Auto-fix issues
python manage.py whatsapp_health_check --fix
```

### Key Metrics to Monitor
- **Configuration validity**: All required settings present
- **API connectivity**: Can reach WhatsApp Graph API
- **Database health**: Sessions and messages being stored
- **Recent activity**: Messages processed in last 24 hours
- **Error rates**: Failed message sends
- **Rate limiting**: Current API usage status

## 🔒 **Security Best Practices**

### 1. **Environment Variables**
- Never commit `.env` files to version control
- Use different tokens for development/production
- Rotate access tokens regularly

### 2. **Webhook Security**
- Always validate webhook signatures in production
- Use HTTPS for webhook URLs
- Implement rate limiting on webhook endpoint

### 3. **User Data Protection**
- Log minimal user information
- Implement data retention policies
- Follow GDPR/privacy regulations

## 🚀 **Performance Optimization**

### 1. **Caching Strategy**
```python
# Cache user sessions
cache.set(f'whatsapp_session_{phone_number}', session_data, 3600)

# Cache rate limiting status
cache.set('whatsapp_rate_limit', True, 300)
```

### 2. **Database Optimization**
- Index frequently queried fields
- Archive old messages periodically
- Use database connection pooling

### 3. **API Optimization**
- Implement retry logic with exponential backoff
- Batch API requests when possible
- Monitor API usage quotas

## 📈 **Scaling Considerations**

### 1. **High Volume Handling**
- Use Celery for async message processing
- Implement message queuing
- Load balance webhook endpoints

### 2. **Multi-tenant Support**
- Separate configurations per tenant
- Isolate user data
- Scale database accordingly

## 🐛 **Debugging Tips**

### 1. **Enable Debug Logging**
```python
LOGGING = {
    'loggers': {
        'care_whatsapp_bot': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

### 2. **Common Debug Commands**
```bash
# Check recent messages
python manage.py shell -c "
from care_whatsapp_bot.models import WhatsAppMessage;
print(WhatsAppMessage.objects.order_by('-created_at')[:5])
"

# Check user sessions
python manage.py shell -c "
from care_whatsapp_bot.models import WhatsAppSession;
print(WhatsAppSession.objects.filter(is_authenticated=True).count())
"
```

## 🔄 **Deployment Checklist**

### Pre-deployment
- [ ] Run health check: `python manage.py whatsapp_health_check`
- [ ] Run tests: `python manage.py test care_whatsapp_bot`
- [ ] Verify environment variables
- [ ] Test webhook connectivity

### Post-deployment
- [ ] Verify webhook is receiving requests
- [ ] Test registration flow
- [ ] Test login flow
- [ ] Monitor error logs
- [ ] Check API rate limits

## 📞 **Support & Maintenance**

### Regular Maintenance Tasks
1. **Weekly**: Run health checks and review logs
2. **Monthly**: Rotate access tokens
3. **Quarterly**: Review and archive old data
4. **As needed**: Update WhatsApp API version

### Getting Help
1. Check logs: `tail -f logs/whatsapp_bot.log`
2. Run diagnostics: `python manage.py whatsapp_health_check --detailed`
3. Review Facebook Developer Console for API issues
4. Check CARE community forums for known issues

---

## 🎯 **Next Steps for Your Setup**

Based on the error you encountered, here's what you should do:

1. **Immediate Fix**:
   ```bash
   # Check your current configuration
   python manage.py whatsapp_health_check
   ```

2. **Update Access Token**:
   - Go to Facebook Developers Console
   - Generate a new access token
   - Update your `.env` file

3. **Test the Fix**:
   ```bash
   # Test with the health check
   python manage.py whatsapp_health_check --detailed
   ```

Your registration functionality is working perfectly - it's just the WhatsApp API credentials that need updating! 🎉