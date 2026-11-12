// Jobs at companies where I have a referral (companies.referral) rank
// higher. The model's score in jobs.score stays the pure resume fit; the
// bonus is added wherever the score is shown or sorted on, so changing the
// referral list never needs a re-score.

/** Points added to a referral company's job score, capped at 100. */
export const REFERRAL_SCORE_BONUS = 10;

/**
 * Added to a referral company's job priority (src/lib/scoring/priority.ts),
 * about as much as a junior title, so those jobs reach the model sooner.
 */
export const REFERRAL_PRIORITY_BONUS = 2;

export function displayedScore(score: number | null, referral: boolean): number | null {
  if (score === null || !referral) return score;
  return Math.min(100, score + REFERRAL_SCORE_BONUS);
}
