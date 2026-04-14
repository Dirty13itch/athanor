import { NextResponse } from "next/server";
import {
  buildFallbackMasterAtlasRelationshipMap,
  pickMasterAtlasRelationshipMap,
  readGeneratedMasterAtlas,
} from "@/lib/master-atlas";

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
