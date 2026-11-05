// Word-level diff (LCS) so the UI can highlight words the agent added to a bullet.

export type Token = { text: string; added: boolean };

const norm = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}+#.]/gu, "");

export function diffWords(original: string, rewritten: string): Token[] {
  const a = original.split(/\s+/).filter(Boolean);
  const b = rewritten.split(/\s+/).filter(Boolean);
  const na = a.map(norm);
  const nb = b.map(norm);

  // dp[i][j] = LCS length of a[i:] and b[j:]
  const dp = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      dp[i][j] = na[i] === nb[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const out: Token[] = [];
  let i = 0;
  let j = 0;
  while (j < b.length) {
    if (i < a.length && na[i] === nb[j]) {
      out.push({ text: b[j], added: false });
      i++;
      j++;
    } else if (i < a.length && dp[i + 1][j] >= dp[i][j + 1]) {
      i++;
    } else {
      out.push({ text: b[j], added: true });
      j++;
    }
  }
  return out;
}

/** Merge consecutive tokens with the same `added` flag into runs, for cleaner highlighting. */
export function diffRuns(original: string, rewritten: string): Token[] {
  const runs: Token[] = [];
  for (const t of diffWords(original, rewritten)) {
    const last = runs[runs.length - 1];
    if (last && last.added === t.added) last.text += " " + t.text;
    else runs.push({ ...t });
  }
  return runs;
}
