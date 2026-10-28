# Twilio Telephony & Media Streams Integration Guide

This guide details how to configure Twilio Programmable Voice to fork real-time phone call audio into Dhwani's neural detection pipeline via WebSocket Media Streams.

---

## 1. Architecture Flow

```
[Inbound Caller] 
       │ (Cellular / PSTN Call)
       ▼
[Twilio Phone Number]
       │ HTTP POST /twilio/voice (Webhook)
       ▼
[Dhwani FastAPI Webhook]
       │ Returns TwiML XML (<Connect><Stream url="wss://.../twilio/media" />)
       ▼
[Twilio Media Stream]
       │ WebSocket (G.711 μ-law @ 8000 Hz, 20ms chunks)
       ▼
[Dhwani Telephony Receiver: /twilio/media]
       │ 1. Decode G.711 μ-law → 16-bit linear PCM
       │ 2. Resample 8 kHz → 16 kHz mono float32
       ▼
[Dhwani Live Audio Pipeline]
       │ 1. Rolling 64,600-sample buffer (4.0375s windows, 1.0s hop)
       │ 2. Energy VAD Pre-Filter (-38 dBFS threshold)
       │ 3. 4-Model Ensemble (W2V2-AASIST, AASIST, AASIST-L, Acoustic)
       │ 4. Dynamic Adaptive Reliability Fusion
       │ 5. Inter-Model Consensus & Attack Attribution
       │ 6. Mitigation Policy Evaluation
       ▼
[Frontend Dashboard: /ws/dashboard]
       Real-time updates to connected security analysts
```

---

## 2. Twilio Account Configuration

### Step A: Configure Webhook in Twilio Console
1. Log in to the [Twilio Console](https://console.twilio.com/).
2. Navigate to **Phone Numbers** → **Manage** → **Active numbers**.
3. Select your Dhwani telephone number.
4. Under the **Voice Configuration** section:
   - Configure **A Call Comes In**: Select `Webhook`.
   - **URL**: `https://<YOUR-PUBLIC-DOMAIN>/twilio/voice`
   - **HTTP Method**: `HTTP POST`
5. Click **Save**.

### Step B: Environment Variables
Create or update your `.env` file in the project root:

```env
# Twilio Voice Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Public WSS endpoint where Twilio will stream audio (via ngrok or cloud domain)
TWILIO_STREAM_PUBLIC_URL=wss://<YOUR-PUBLIC-DOMAIN>/twilio/media

# Security Alert Destination
DHWANI_ALERT_PHONE_NUMBER=+1987654321
DHWANI_ALERT_DRY_RUN=true
```

---

## 3. Local Development with ngrok Tunnel

To test Twilio with a local workstation:

1. Start Dhwani backend on port 8000:
   ```powershell
   python -m uvicorn backend.main:app --port 8000
   ```
2. Start ngrok tunnel:
   ```powershell
   ngrok http 8000
   ```
3. Set `TWILIO_STREAM_PUBLIC_URL` in `.env` to:
   ```env
   TWILIO_STREAM_PUBLIC_URL=wss://YOUR-SUBDOMAIN.ngrok-free.app/twilio/media
   ```
4. Set the Twilio Voice Webhook URL in Twilio Console to:
   ```
   https://YOUR-SUBDOMAIN.ngrok-free.app/twilio/voice
   ```

---

## 4. Testing the Telephony Pipeline Manually

1. Dial your Twilio phone number from any mobile device.
2. The gateway will answer and announce: *"Connecting to Dhwani secure voice protection gateway."*
3. The call audio will stream into `/twilio/media`.
4. Open the Dhwani dashboard at `http://localhost:3000` and switch to the **Live Call** tab:
   - Call status will display `STREAMING`.
   - The caller's phone number is privacy-masked (e.g. `+1 (***) ***-2671`).
   - Real-time VAD speech ratio and ensemble risk scores update once per second.
