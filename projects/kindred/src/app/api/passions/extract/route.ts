import { config } from "@/lib/config";

/**
 * POST /api/passions/extract
 *
 * Takes free-text responses from onboarding and extracts structured passion data
 * using LLM analysis. Returns passion categories with inferred intensity and confidence.
 *
 * Body: { responses: string[] }
 * Returns: { passions: ExtractedPassion[] }
 */

interface ExtractedPassion {
  categoryPath: string;
  inferredIntensity: number;
  confidence: number;
  sourcePhrase: string;
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || !Array.isArray(body.responses) || body.responses.length === 0) {
    return Response.json({ error: "responses array is required" }, { status: 400 });
  }

  const responses = body.responses.filter(
    (r: unknown) => typeof r === "string" && r.trim().length > 0,
  ) as string[];

  if (responses.length === 0) {
    return Response.json({ passions: [] });
  }

  const systemPrompt = `You are analyzing free-text responses to extract passion/interest signals for a social matching application.

For each response, identify specific interests with hierarchical depth. The deeper the specificity, the higher the match quality.

Examples of depth:
- Depth 1: "Music" (too broad)
- Depth 2: "Jazz" (genre level)
- Depth 3: "Bebop Jazz" (subgenre)
- Depth 4: "Thelonious Monk" (specific artist — highest signal)

For each passion found, estimate:
- inferredIntensity (0.0-1.0): How passionate they seem based on language, detail, and enthusiasm
- confidence (0.0-1.0): How confident you are in this extraction
- sourcePhrase: The exact phrase that signals this passion

Return ONLY a JSON array of objects with: categoryPath (string, "/" separated hierarchy), inferredIntensity, confidence, sourcePhrase.

Example output:
[
  {"categoryPath": "Music/Jazz/Bebop/Thelonious Monk", "inferredIntensity": 0.9, "confidence": 0.95, "sourcePhrase": "I could listen to Monk's solo stuff for days"},
  {"categoryPath": "Cooking/Fermentation/Sourdough", "inferredIntensity": 0.7, "confidence": 0.8, "sourcePhrase": "maintaining a sourdough starter"}
]`;

  const userContent = responses
    .map((r, i) => `Response ${i + 1}: "${r}"`)
    .join("\n\n");

  try {
    const resp = await fetch(`${config.litellmUrl}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.litellmKey}`,
      },
      signal: AbortSignal.timeout(30_000),
      body: JSON.stringify({
        model: "reasoning",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userContent },
        ],
        max_tokens: 2000,
        temperature: 0.3,
        stream: false,
      }),
    });

    if (!resp.ok) {
      return Response.json({ error: "LLM extraction failed" }, { status: 502 });
    }

    const data = await resp.json();
    let content = data.choices?.[0]?.message?.content ?? "";

    // Strip think blocks
    content = content.replace(/<think>[\s\S]*?<\/think>/g, "").trim();

    // Extract JSON array
    const jsonMatch = content.match(/\[[\s\S]*\]/);
    if (!jsonMatch) {
      return Response.json({ passions: [] });
    }

    const passions: ExtractedPassion[] = JSON.parse(jsonMatch[0]);
    return Response.json({ passions });
  } catch (err) {
    console.error("Passion extraction failed:", err);
    return Response.json({ error: "Extraction failed" }, { status: 500 });
  }
}
