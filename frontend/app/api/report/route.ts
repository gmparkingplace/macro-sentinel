import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const url = "https://raw.githubusercontent.com/gmparkingplace/macro-sentinel/main/data/report.json";
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`fetch failed: ${res.status}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: "report.json not found" }, { status: 404 });
  }
}
