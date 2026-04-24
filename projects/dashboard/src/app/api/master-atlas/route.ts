import { NextResponse } from "next/server";
import {
  buildFallbackMasterAtlasRelationshipMap,
  pickMasterAtlasRelationshipMap,
  readGeneratedMasterAtlas,
} from "@/lib/master-atlas";

const MASTER_ATLAS_FRESHNESS_BUDGET_MS = 20 * 60 * 1000;

function isStaleGeneratedAt(value: string | null | undefined) {
  if (!value) {
    return true;
  }
  const timestamp = Date.parse(value);
  if (Number.isNaN(timestamp)) {
    return true;
  }
  return Date.now() - timestamp > MASTER_ATLAS_FRESHNESS_BUDGET_MS;
}

export async function GET() {
  try {
    const bundle = await readGeneratedMasterAtlas();
    const map = pickMasterAtlasRelationshipMap(bundle);
    if (!map) {
      return NextResponse.json(
        buildFallbackMasterAtlasRelationshipMap(
          "Master atlas feed is temporarily unavailable from this dashboard runtime.",
          "Master atlas feed is unavailable",
        ),
      );
    }
    if (isStaleGeneratedAt(map.generated_at)) {
      return NextResponse.json(
        buildFallbackMasterAtlasRelationshipMap(
          "Master atlas feed is present but stale in this dashboard runtime.",
          "Master atlas feed is stale",
        ),
      );
    }
    return NextResponse.json(map);
  } catch {
    return NextResponse.json(
      buildFallbackMasterAtlasRelationshipMap(
        "The dashboard runtime failed to load the compiled master atlas feed.",
        "Failed to load master atlas feed",
      ),
    );
  }
}
