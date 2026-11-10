// Runs once when the Next.js server starts. Starts the background job
// scoring worker (src/lib/scoring/worker.ts) in the Node.js runtime; it
// does nothing unless the resume URLs and a model API key are configured.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { startScoringWorker } = await import("./lib/scoring/worker");
    startScoringWorker();
  }
}
