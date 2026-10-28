import { NextResponse } from "next/server";

export async function GET() {
  const backendBase = (process.env.DHWANI_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
  try {
    const res = await fetch(`${backendBase}/health`);
    const data = await res.json();
    return NextResponse.json({
      status: "ok",
      frontend: "operational",
      backend: data,
    });
  } catch (e: any) {
    return NextResponse.json(
      {
        status: "degraded",
        frontend: "operational",
        backend: "unreachable",
      },
      { status: 503 }
    );
  }
}
