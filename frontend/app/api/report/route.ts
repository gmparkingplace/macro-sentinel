import { NextResponse } from "next/server";

export async function GET() {
  try {
    const url = "https://raw.githubusercontent.com/gmparkingplace/macro-sentinel/main/data/report.json";
    const res = await fetch(url, { next: { revalidate: 3600 } });
    if (!res.ok) throw new Error("fetch failed");
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "report.json not found" }, { status: 404 });
  }
}
