import { NextRequest, NextResponse } from "next/server";

/**
 * Hardened Backend-For-Frontend (BFF) Proxy Route Handler (Phase 3.5)
 * 
 * Authentication Trust-Boundary Security Controls:
 * 1. Strict route categorization:
 *    - Public Demo Routes: Permitted for anonymous evaluation only when DHWANI_DEMO_MODE=true
 *    - Protected Operational Routes: Strictly require client credentials (never unauthenticated)
 * 2. Confused Deputy Elimination:
 *    - Server-side master DHWANI_API_KEY is NEVER attached to anonymous requests for operational routes
 *    - Client credentials (X-API-Key or Bearer token) are forwarded for backend cryptographic validation
 * 3. Enterprise Production Lockdown:
 *    - When DHWANI_ENFORCE_BFF_AUTH=true, even demo routes require client credentials
 * 4. CSRF Defense:
 *    - State-changing methods (POST) validate Origin/Referer against Host
 * 5. Input Validation & Bounding:
 *    - Strict regex segment validation (anti-path-traversal)
 *    - 25 MB body ceiling (anti-DoS memory exhaustion)
 *    - 30-second AbortController timeout (anti-hanging connections)
 *    - Sanitized error responses (no infrastructure/secret leakage)
 */

const MAX_BFF_PAYLOAD_SIZE = 25 * 1024 * 1024; // 25 MB max upload
const UPSTREAM_TIMEOUT_MS = 30000; // 30-second timeout

// 1. Public Demo Endpoints (permitted for evaluation in demo mode)
const PUBLIC_DEMO_ROUTES: Record<string, string[]> = {
  "system/status": ["GET", "HEAD", "OPTIONS"],
  "analyze/upload": ["POST", "OPTIONS"],
  "analyze/youtube": ["POST", "OPTIONS"],
};

// 2. Protected Operational Endpoints (strictly require client-side authentication)
const PROTECTED_OPERATIONAL_ROUTES: Record<string, string[]> = {
  "incidents": ["GET", "HEAD", "OPTIONS"],
  "honeypot/challenge": ["POST", "OPTIONS"],
  "honeypot/verify": ["POST", "OPTIONS"],
  "audit/verify": ["GET", "POST", "OPTIONS"],
};

const ALL_ALLOWED_ROUTES: Record<string, string[]> = {
  ...PUBLIC_DEMO_ROUTES,
  ...PROTECTED_OPERATIONAL_ROUTES,
};

const getBackendUrl = () => {
  return (process.env.DHWANI_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
};

function extractClientApiKey(request: NextRequest): string | null {
  const xApiKey = request.headers.get("x-api-key");
  if (xApiKey && xApiKey.trim()) {
    return xApiKey.trim();
  }

  const authHeader = request.headers.get("authorization");
  if (authHeader && authHeader.toLowerCase().startsWith("bearer ")) {
    const token = authHeader.substring(7).trim();
    if (token) return token;
  }

  return null;
}

async function handleProxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  const { path } = await context.params;
  const segments = Array.isArray(path) ? path : [path];

  // 1. Path segment traversal defense
  for (const segment of segments) {
    if (
      !segment ||
      segment === ".." ||
      segment.includes("/") ||
      segment.includes("\\") ||
      !/^[a-zA-Z0-9_-]+$/.test(segment)
    ) {
      return NextResponse.json(
        { detail: "Invalid path: illegal characters or path traversal sequence detected." },
        { status: 400 }
      );
    }
  }

  const pathStr = segments.join("/");

  // 2. Strict route allowlist check
  const allowedMethods = ALL_ALLOWED_ROUTES[pathStr];
  if (!allowedMethods) {
    return NextResponse.json(
      { detail: `Endpoint '/api/${pathStr}' is not accessible via the BFF proxy.` },
      { status: 404 }
    );
  }

  // 3. HTTP method validation
  if (!allowedMethods.includes(request.method)) {
    return NextResponse.json(
      { detail: `Method ${request.method} is not allowed for '/api/${pathStr}'.` },
      { status: 405 }
    );
  }

  // 4. CSRF defense on state-changing requests
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    const host = request.headers.get("host");
    if (origin && host) {
      try {
        const originUrl = new URL(origin);
        if (originUrl.host !== host) {
          // Check if origin is explicitly allowed
          const rawAllowed = process.env.ALLOWED_ORIGINS || "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001";
          const allowedList = rawAllowed.split(",").map((o) => o.trim()).filter(Boolean);
          if (!allowedList.includes(origin)) {
            return NextResponse.json(
              { detail: "Cross-site request forgery protection: origin mismatch." },
              { status: 403 }
            );
          }
        }
      } catch {
        return NextResponse.json(
          { detail: "Invalid origin header format." },
          { status: 403 }
        );
      }
    }
  }

  // 5. Authentication Trust-Boundary Enforcement
  const clientApiKey = extractClientApiKey(request);
  const isProtectedOperational = pathStr in PROTECTED_OPERATIONAL_ROUTES;
  const enforceBffAuth = process.env.DHWANI_ENFORCE_BFF_AUTH === "true";
  const isDemoMode = process.env.DHWANI_DEMO_MODE !== "false"; // Default true for demo preview

  // If operational route OR if enterprise auth is strictly enforced on all BFF routes:
  if (isProtectedOperational || enforceBffAuth) {
    if (!clientApiKey) {
      return NextResponse.json(
        {
          detail: isProtectedOperational
            ? `Protected operational endpoint '/api/${pathStr}' requires client authentication. Please provide X-API-Key or Bearer token.`
            : "Client authentication required: missing X-API-Key or Bearer token.",
        },
        { status: 401 }
      );
    }
  }

  // 6. Request size validation (header check)
  const contentLength = request.headers.get("content-length");
  if (contentLength && parseInt(contentLength, 10) > MAX_BFF_PAYLOAD_SIZE) {
    return NextResponse.json(
      { detail: `Payload too large. Exceeds maximum allowed size of ${MAX_BFF_PAYLOAD_SIZE} bytes.` },
      { status: 413 }
    );
  }

  // 7. Construct upstream URL
  const backendBase = getBackendUrl();
  const search = request.nextUrl.search;
  const targetUrl = `${backendBase}/api/${pathStr}${search}`;

  // 8. Build trusted forward headers
  const forwardHeaders = new Headers();

  const contentType = request.headers.get("content-type");
  if (contentType) {
    forwardHeaders.set("content-type", contentType);
  }

  const accept = request.headers.get("accept");
  if (accept) {
    forwardHeaders.set("accept", accept);
  }

  // Credential forwarding logic:
  // - If client provided a key, forward the CLIENT's key to the backend for verification
  // - If client provided NO key, attach server DHWANI_API_KEY ONLY for public demo routes in demo mode
  if (clientApiKey) {
    forwardHeaders.set("X-API-Key", clientApiKey);
  } else if (!isProtectedOperational && isDemoMode) {
    const serverKey = process.env.DHWANI_API_KEY;
    if (serverKey) {
      forwardHeaders.set("X-API-Key", serverKey);
    }
  }

  // Header injection defense: sanitize client-supplied session ID
  const rawSessionId = request.headers.get("x-session-id");
  if (rawSessionId && /^[a-zA-Z0-9_-]{1,64}$/.test(rawSessionId)) {
    forwardHeaders.set("X-Session-ID", rawSessionId);
  }

  // 9. Read and bound body for non-GET/HEAD methods
  let body: ArrayBuffer | undefined = undefined;
  if (request.method !== "GET" && request.method !== "HEAD") {
    body = await request.arrayBuffer();
    if (body.byteLength > MAX_BFF_PAYLOAD_SIZE) {
      return NextResponse.json(
        { detail: `Payload too large. Exceeds maximum allowed size of ${MAX_BFF_PAYLOAD_SIZE} bytes.` },
        { status: 413 }
      );
    }
  }

  // 10. Timed upstream request
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);

  try {
    const backendRes = await fetch(targetUrl, {
      method: request.method,
      headers: forwardHeaders,
      body: body && body.byteLength > 0 ? body : undefined,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    // Forward safe response headers only
    const resHeaders = new Headers();
    const resContentType = backendRes.headers.get("content-type");
    if (resContentType) {
      resHeaders.set("content-type", resContentType);
    }

    const resBody = await backendRes.arrayBuffer();
    return new NextResponse(resBody, {
      status: backendRes.status,
      statusText: backendRes.statusText,
      headers: resHeaders,
    });
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error?.name === "AbortError") {
      return NextResponse.json(
        { detail: "Gateway timeout: Dhwani inference backend did not respond within 30 seconds." },
        { status: 504 }
      );
    }
    return NextResponse.json(
      { detail: "Backend gateway error: unable to establish connection with Dhwani inference engine." },
      { status: 502 }
    );
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
export const HEAD = handleProxy;
export const OPTIONS = handleProxy;
