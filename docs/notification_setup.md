# Multi-Channel Emergency Notification Guide

Dhwani implements an abstracted, pluggable notification subsystem supporting SMS, WhatsApp, Email, and Dashboard alerts with configurable cooldowns and deduplication.

---

## 1. Notification Priority & Fallback Order

```
[Confirmed High-Risk Incident]
            │
            ▼
    [1. Twilio SMS]
     (if configured & enabled)
            │ fails or unconfigured
            ▼
   [2. Twilio WhatsApp]
(only if verified & supported)
            │ fails or unconfigured
            ▼
      [3. SMTP Email]
     (tertiary fallback)
            │ always
            ▼
   [4. Dashboard Alert]
(WebSocket real-time broadcast)
```

---

## 2. Configuration & Dry-Run Mode

### Safe Testing (Dry Run Mode)
By default, Dhwani operates in dry-run mode:
```env
DHWANI_ALERT_DRY_RUN=true
```
In this mode, security alerts are logged to the console and recorded in the audit ledger without sending external SMS or consuming Twilio account balances.

### Production SMS Delivery
To enable live SMS delivery, provide the following in `.env`:
```env
DHWANI_ALERT_DRY_RUN=false
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
DHWANI_ALERT_PHONE_NUMBER=+1987654321
```

### Production WhatsApp Delivery
WhatsApp is enabled **only** when explicitly configured with verified WhatsApp sender addresses:
```env
DHWANI_WHATSAPP_ENABLED=true
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
DHWANI_WHATSAPP_ALERT_NUMBER=whatsapp:+1234567890
```

### SMTP Email Fallback
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@example.com
SMTP_PASSWORD=app_password_here
DHWANI_ALERT_EMAIL=security_team@example.com
```

---

## 3. Anti-Spam & Deduplication Policies

- **Cooldown**: Default 60-second cooldown per session prevents flooding security personnel with repeat alerts during active calls.
- **Incident Deduplication**: Each security event is bound to a unique `incident_id`. Identical incidents are never re-dispatched.
