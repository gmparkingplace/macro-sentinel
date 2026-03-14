import { NextResponse } from "next/server";
import { readFileSync } from "fs";
import { join } from "path";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    const filePath = join(process.cwd(), "..", "data", "history.json");
    const raw = readFileSync(filePath, "utf-8");
    const data = JSON.parse(raw);
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" }
    });
  } catch (e) {
    console.error("history.json 로드 실패:", e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }
}
