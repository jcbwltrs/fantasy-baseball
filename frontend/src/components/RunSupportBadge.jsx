import { TIER_COLORS } from '../utils/scoring';

export default function RunSupportBadge({ tier, rpg, rank, compact = false }) {
  const colors = TIER_COLORS[tier] || TIER_COLORS.B;

  if (compact) {
    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${colors.bg} ${colors.text}`}
            title={`${colors.label} Run Support${rpg ? ` — ${rpg.toFixed(1)} R/G` : ''}${rank ? ` (#${rank})` : ''}`}>
        {tier}
      </span>
    );
  }

  return (
    <div className="group relative inline-flex items-center gap-1">
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-bold ${colors.bg} ${colors.text}`}>
        {tier}
      </span>
      {rpg != null && (
        <span className="text-xs text-slate-500">{rpg.toFixed(1)} R/G</span>
      )}
      {rank != null && (
        <span className="text-xs text-slate-400">#{rank}</span>
      )}
      {/* Tooltip */}
      <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-50
                      bg-white border border-[#A9B8E2] rounded-lg p-2 text-xs whitespace-nowrap shadow-lg">
        <div className="font-semibold text-[#2d2d3d]">{colors.label} Run Support</div>
        {rpg != null && <div className="text-slate-600">Runs/Game: {rpg.toFixed(2)}</div>}
        {rank != null && <div className="text-slate-600">MLB Rank: #{rank} of 30</div>}
      </div>
    </div>
  );
}
