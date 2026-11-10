import { anthropic } from "@ai-sdk/anthropic";
import { google } from "@ai-sdk/google";
import { createProviderRegistry } from "ai";

// SCORING_MODEL is "<provider>:<model id>", e.g. "google:gemini-3.5-flash-lite"
// or "anthropic:claude-haiku-5-5". Each provider reads its own API key from
// the environment (GOOGLE_GENERATIVE_AI_API_KEY / ANTHROPIC_API_KEY).
export const DEFAULT_SCORING_MODEL = "google:gemini-3.5-flash-lite";

const registry = createProviderRegistry({ anthropic, google });

export function scoringModelId(): string {
  return process.env.SCORING_MODEL || DEFAULT_SCORING_MODEL;
}

export function scoringModel() {
  return registry.languageModel(scoringModelId() as `${"anthropic" | "google"}:${string}`);
}

// Whether the configured provider's API key is set, so the worker doesn't
// start (and log an error every minute) in a dev setup without one.
export function scoringModelConfigured(): boolean {
  const provider = scoringModelId().split(":")[0];
  if (provider === "google") return Boolean(process.env.GOOGLE_GENERATIVE_AI_API_KEY);
  if (provider === "anthropic") return Boolean(process.env.ANTHROPIC_API_KEY);
  return false;
}
