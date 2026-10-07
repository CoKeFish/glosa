/** Word-level diff between what the learner wrote and the correction, for highlighting.
 * Words are compared case- and punctuation-insensitively, so "english." matches "English."
 * and only real changes light up. */

export type Piece = { text: string; changed: boolean };

const norm = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}']/gu, "");

function lcs(a: string[], b: string[]): boolean[][] {
  // keep[0][i] / keep[1][j]: whether a[i] / b[j] is part of the longest common subsequence.
  const n = a.length, m = b.length;
  const dp = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = norm(a[i]) === norm(b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const keepA = new Array<boolean>(n).fill(false), keepB = new Array<boolean>(m).fill(false);
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (norm(a[i]) === norm(b[j])) {
      keepA[i] = keepB[j] = true;
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) i++;
    else j++;
  }
  return [keepA, keepB];
}

/** The answer with removed or wrong words marked, and the correction with added ones marked. */
export function diffWords(answer: string, correction: string): { answer: Piece[]; correction: Piece[] } {
  const a = answer.split(/\s+/).filter(Boolean);
  const b = correction.split(/\s+/).filter(Boolean);
  const [keepA, keepB] = lcs(a, b);
  return {
    answer: a.map((text, i) => ({ text, changed: !keepA[i] })),
    correction: b.map((text, i) => ({ text, changed: !keepB[i] })),
  };
}
