// LiteLLM client for report generation
// Routes through VAULT LiteLLM proxy — cloud models for client-facing quality

function ensureOpenAiBaseUrl(url: string): string {
  const normalized = url.replace(/\/+$/, "");
  return normalized.endsWith("/v1") ? normalized : `${normalized}/v1`;
}

const LITELLM_BASE_URL = ensureOpenAiBaseUrl(
  process.env.ATHANOR_LITELLM_URL ||
    process.env.LITELLM_BASE_URL ||
    "http://192.168.1.203:4000"
);
const LITELLM_API_KEY =
  process.env.ATHANOR_LITELLM_API_KEY ||
  process.env.LITELLM_API_KEY ||
  process.env.OPENAI_API_KEY ||
  "";

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ChatCompletionResponse {
  id: string;
  choices: {
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }[];
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export async function chatCompletion(
  messages: ChatMessage[],
  options: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
  } = {}
): Promise<ChatCompletionResponse> {
  const {
    model = "reasoning", // LiteLLM slot — routes to best available cloud model
    temperature = 0.3,
    max_tokens = 4096,
  } = options;

  const response = await fetch(`${LITELLM_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${LITELLM_API_KEY}`,
    },
    body: JSON.stringify({
      model,
      messages,
      temperature,
      max_tokens,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `LiteLLM request failed (${response.status}): ${errorBody}`
    );
  }

  return response.json();
}

export async function generateReportNarrative(
  inspectionData: Record<string, unknown>
): Promise<string> {
  const systemPrompt = `You are an energy auditing report writer for Ulrich Energy, a RESNET-certified HERS Rating business in the Twin Cities.

Write professional, homeowner-friendly energy audit reports. Include:
- Clear explanation of test results and what they mean
- Comparison to code requirements and typical homes
- Recommended improvements ranked by cost-effectiveness
- Professional but approachable tone

Use specific numbers from the inspection data. Do not fabricate data.`;

  const userPrompt = `Generate an energy audit report narrative for the following inspection data:

${JSON.stringify(inspectionData, null, 2)}

Include sections for:
1. Executive Summary
2. Building Envelope Assessment
3. Air Leakage Results (Blower Door Test)
4. Duct Leakage Results
5. Insulation Assessment
6. Window Performance
7. HVAC System Evaluation
8. Recommendations (ranked by cost-effectiveness)
9. Compliance Summary`;

  const result = await chatCompletion(
    [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt },
    ],
    {
      model: "reasoning", // Cloud model for client-facing quality
      temperature: 0.3,
      max_tokens: 4096,
    }
  );

  return result.choices[0].message.content;
}
