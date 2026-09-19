export interface SecurityEvent {
  id: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  type: string;
  timestamp: string;
  source: string;
  status: "FLAGGED" | "BLOCKED" | "VERIFIED" | "INVESTIGATING";
  confidence: number;
}

export interface MetricData {
  label: string;
  value: string;
  change?: string;
  isPositive?: boolean;
  description: string;
}

export interface ThreatDataPoint {
  time: string;
  genuine: number;
  synthetic: number;
  suspicious: number;
}

export const initialMetrics: MetricData[] = [
  {
    label: "VOICE INTERACTIONS",
    value: "12,584",
    change: "+14.2%",
    isPositive: true,
    description: "Real-time acoustic sessions analyzed",
  },
  {
    label: "DETECTION CONFIDENCE",
    value: "98.4%",
    change: "+0.6%",
    isPositive: true,
    description: "Neural acoustic accuracy score",
  },
  {
    label: "AVERAGE LATENCY",
    value: "<120ms",
    change: "-18ms",
    isPositive: true,
    description: "Sub-audible pipeline response",
  },
  {
    label: "THREATS FLAGGED",
    value: "347",
    change: "-4.5%",
    isPositive: true,
    description: "Deepfakes and cloned voices mitigated",
  },
  {
    label: "SYSTEM AVAILABILITY",
    value: "99.1%",
    change: "Operational",
    isPositive: true,
    description: "Global zero-trust edge uptime",
  },
];

export const securityEvents: SecurityEvent[] = [
  {
    id: "evt-01",
    severity: "HIGH",
    type: "Voice Clone Pattern Detected",
    timestamp: "2 min ago",
    source: "Mobile Inbound Stream (SIP:4049)",
    status: "BLOCKED",
    confidence: 99.4,
  },
  {
    id: "evt-02",
    severity: "MEDIUM",
    type: "Unusual Pitch & Phase Discontinuity",
    timestamp: "7 min ago",
    source: "WebRTC Audio Channel #12",
    status: "FLAGGED",
    confidence: 82.1,
  },
  {
    id: "evt-03",
    severity: "LOW",
    type: "Verified Voice Interaction",
    timestamp: "12 min ago",
    source: "Android Guardian SDK v2.4",
    status: "VERIFIED",
    confidence: 98.9,
  },
  {
    id: "evt-04",
    severity: "HIGH",
    type: "Synthetic Vocoder Speech Signature",
    timestamp: "18 min ago",
    source: "API Ingestion Gateway",
    status: "BLOCKED",
    confidence: 99.8,
  },
  {
    id: "evt-05",
    severity: "LOW",
    type: "Biometric Glottal Signature Confirmed",
    timestamp: "24 min ago",
    source: "Mobile Telemetry (SM-S928B)",
    status: "VERIFIED",
    confidence: 99.2,
  },
];

export const threatTimelineData: ThreatDataPoint[] = [
  { time: "00:00", genuine: 420, synthetic: 18, suspicious: 24 },
  { time: "03:00", genuine: 380, synthetic: 14, suspicious: 19 },
  { time: "06:00", genuine: 510, synthetic: 29, suspicious: 35 },
  { time: "09:00", genuine: 890, synthetic: 58, suspicious: 42 },
  { time: "12:00", genuine: 1120, synthetic: 74, suspicious: 51 },
  { time: "15:00", genuine: 1040, synthetic: 62, suspicious: 47 },
  { time: "18:00", genuine: 920, synthetic: 48, suspicious: 38 },
  { time: "21:00", genuine: 680, synthetic: 31, suspicious: 26 },
  { time: "24:00", genuine: 540, synthetic: 22, suspicious: 20 },
];
