export function normalizeReaction(reaction: string): string | null {
  if (!reaction || typeof reaction !== "string") return null;

  // Strip Unicode variation selector VS16 (\uFE0F) and trim whitespace
  let norm = reaction.replace(/\uFE0F/g, "").trim();
  if (!norm) return null;

  // Canonical near-miss mappings
  if (norm === "❤️") norm = "❤";
  if (norm === "✍️") norm = "✍";

  // Validate single grapheme cluster
  const segmenter = new Intl.Segmenter();
  const segments = Array.from(segmenter.segment(norm));
  if (segments.length !== 1) {
    return null;
  }

  // Verify that the single grapheme cluster contains an emoji/pictographic character
  if (!/\p{Extended_Pictographic}/u.test(norm)) {
    return null;
  }

  return norm;
}
