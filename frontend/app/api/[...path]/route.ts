import { auth } from "@clerk/nextjs/server";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const isDev = process.env.NODE_ENV !== "production";
function debugLog(...args: unknown[]) { if (isDev) console.log(...args); }

async function proxyRequest(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
  method: string
): Promise<NextResponse> {
  debugLog("[Proxy] Starting request");
  debugLog("[Proxy] Request pathname:", request.nextUrl.pathname);
  
  const { userId, getToken } = await auth();

  
  const params = await context.params;


  // Build the path from the dynamic segments
  const pathSegments = params.path || [];

  
  const path = pathSegments.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  // Add trailing slash to match FastAPI route definitions (e.g. @router.get("/"))
  // This avoids a 307 redirect round-trip on every request
  const url = `${BACKEND_URL}/api/${path}/${searchParams ? `?${searchParams}` : ""}`;

  debugLog(`[Proxy] ${method} ${url}`);

  // Get Clerk token
  const token = userId ? await getToken() : null;

  // L-001: Prepare headers — preserve original Content-Type instead of
  // force-overriding to application/json (which blocks file uploads).
  const headers: HeadersInit = {};

  const incomingCT = request.headers.get("Content-Type");
  if (incomingCT) {
    headers["Content-Type"] = incomingCT;
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Prepare request options
  const options: RequestInit = {
    method,
    headers,
    redirect: "manual", // Handle redirects manually to preserve auth headers
  };

  // Add body for POST, PUT, PATCH — use arrayBuffer to preserve binary payloads
  if (["POST", "PUT", "PATCH"].includes(method)) {
    try {
      const body = await request.arrayBuffer();
      if (body.byteLength > 0) {
        options.body = body;
      }
    } catch {
      // No body or error reading body
    }
  }

  try {
    let response = await fetch(url, options);

    // Handle redirects manually to preserve Authorization header
    if (response.status === 307 || response.status === 308) {
      const redirectUrl = response.headers.get("Location");
      if (redirectUrl) {
        const fullRedirectUrl = redirectUrl.startsWith("http")
          ? redirectUrl
          : `${BACKEND_URL}${redirectUrl}`;
        debugLog(`[Proxy] Following redirect to ${fullRedirectUrl}`);
        response = await fetch(fullRedirectUrl, options);
      }
    }

    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    console.error("[Proxy] Error:", error);
    return NextResponse.json(
      { detail: "Failed to connect to backend" },
      { status: 502 }
    );
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  debugLog("[Proxy] GET handler called");
  try {
    return await proxyRequest(request, context, "GET");
  } catch (error) {
    console.error("[Proxy] GET handler error:", error);
    return NextResponse.json(
      { detail: "Proxy handler error", error: String(error) },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, context, "POST");
}

export async function PUT(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, context, "PUT");
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, context, "PATCH");
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> }
) {
  return proxyRequest(request, context, "DELETE");
}
