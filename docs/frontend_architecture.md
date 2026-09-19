# Dhwani Frontend Architecture

The Dhwani user interface is a unified, cyber-themed dashboard built with **Next.js 16 (Turbopack)**, **React 19**, **TailwindCSS**, **Lucide Icons**, **Recharts**, and **Three.js**.

---

## 1. Directory Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx         # Global fonts, metadata, and root shell
│   │   ├── page.tsx           # Unified page container
│   │   └── globals.css        # Atmospheric dark luxury cyber styling
│   ├── components/
│   │   ├── dashboard/
│   │   │   ├── UnifiedCyberDashboard.tsx  # Central operational control tabs
│   │   │   ├── MetricStrip.tsx            # Live trust & telemetry metrics
│   │   │   ├── LiveAnalysisSection.tsx    # Waveform player & risk gauge
│   │   │   ├── ThreatIntelligence.tsx     # Vector analysis & attack trends
│   │   │   └── VerificationWorkflow.tsx   # Zero-trust caller policy tree
│   │   ├── hero/
│   │   │   ├── DhwaniSphere.tsx           # Interactive 3D Three.js orb
│   │   │   ├── HeroDashboard.tsx          # Editorial cyber header & stats
│   │   │   └── MetricsBar.tsx             # Latency & throughput counters
│   │   └── navigation/
│   │       ├── Navbar.tsx                 # Floating glassmorphic header
│   │       └── Footer.tsx                 # Compliance & footer links
```

---

## 2. Real-Time Telemetry via WebSockets

The dashboard connects to `ws://localhost:8000/ws/dashboard` upon mount.
It handles live events dispatched by the backend:

- `call_started`: Dispatched when an inbound phone call connects.
- `vad_update`: Dispatched on every 4.037s audio window with speech/non-speech energy metrics.
- `risk_update`: Dispatched with multi-model prediction, consensus level, and mitigation policy.
- `security_alert`: Dispatched when a confirmed high-risk incident triggers alerting.
- `call_ended`: Dispatched when the telephony stream disconnects.
