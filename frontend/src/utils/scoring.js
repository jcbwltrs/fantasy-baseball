/** Run support tier badge colors */
export const TIER_COLORS = {
  S: { bg: 'bg-emerald-600', text: 'text-white', label: 'Elite' },
  A: { bg: 'bg-emerald-500/80', text: 'text-white', label: 'Good' },
  B: { bg: 'bg-slate-400', text: 'text-white', label: 'Avg' },
  C: { bg: 'bg-orange-400', text: 'text-white', label: 'Below Avg' },
  D: { bg: 'bg-red-400', text: 'text-white', label: 'Poor' },
};

/** Format trend arrow */
export function trendIndicator(trend) {
  if (trend > 1) return { symbol: '\u2191', color: 'text-emerald-700', label: 'Hot' };
  if (trend > 0) return { symbol: '\u2197', color: 'text-emerald-600', label: 'Rising' };
  if (trend < -1) return { symbol: '\u2193', color: 'text-red-500', label: 'Cold' };
  if (trend < 0) return { symbol: '\u2198', color: 'text-red-400', label: 'Cooling' };
  return { symbol: '\u2192', color: 'text-slate-400', label: 'Steady' };
}

/** Recommendation badge colors */
export const REC_COLORS = {
  drop: { bg: 'bg-[#FFB8BF]/30', text: 'text-red-600', border: 'border-[#FFB8BF]' },
  consider: { bg: 'bg-[#EFC965]/30', text: 'text-amber-700', border: 'border-[#EFC965]' },
  hold: { bg: 'bg-[#A3DFC4]/30', text: 'text-emerald-700', border: 'border-[#A3DFC4]' },
};
