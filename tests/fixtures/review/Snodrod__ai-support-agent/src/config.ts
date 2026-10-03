try {
  process.loadEnvFile();
} catch {
  // No .env file: rely on the real environment.
}

const num = (value: string | undefined, fallback: number) => {
  const n = Number(value);
  return Number.isFinite(n) && value !== undefined && value !== '' ? n : fallback;
};

export const config = {
  port: num(process.env.PORT, 3000),
  apiKey: process.env.ANTHROPIC_API_KEY ?? '',
  // Any Anthropic-compatible endpoint works: the official API, a proxy or a gateway.
  baseURL: process.env.ANTHROPIC_BASE_URL || undefined,
  model: process.env.MODEL || 'claude-sonnet-5',
  maxTokens: num(process.env.MAX_TOKENS, 2048),
  // Hard stop for the tool loop, so a confused model cannot spin forever.
  maxSteps: num(process.env.MAX_STEPS, 8),
  // USD per million tokens, used only for the cost counter in the UI.
  priceInPerMTok: num(process.env.PRICE_IN_PER_MTOK, 3),
  priceOutPerMTok: num(process.env.PRICE_OUT_PER_MTOK, 15),
  // Fixed "today" keeps the demo data (return windows, callback slots) deterministic.
  today: process.env.DEMO_TODAY || '2026-09-25',
};
