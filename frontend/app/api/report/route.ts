import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const ts = Date.now();
    const url = `https://raw.githubusercontent.com/gmparkingplace/macro-sentinel/main/data/report.json?t=${ts}`;
    const res = await fetch(url, { 
      cache: "no-store",
      headers: { "Cache-Control": "no-cache, no-store, must-revalidate" }
    });
    if (!res.ok) throw new Error(`fetch failed: ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data, {
      headers: {
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache"
      }
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "report.json not found" }, { status: 404 });
  }
}
