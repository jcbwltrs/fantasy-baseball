import { useQuery } from '@tanstack/react-query';
import { getStatus, getRoster, getAvailablePlayers, getDropCandidates, getRunSupportRankings, triggerRefresh } from '../api/client';
import RunSupportBadge from '../components/RunSupportBadge';
import TrendArrow from '../components/TrendArrow';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { TIER_COLORS } from '../utils/scoring';
import { useState } from 'react';

export default function Dashboard() {
  const [refreshing, setRefreshing] = useState(false);

  const statusQ = useQuery({ queryKey: ['status'], queryFn: getStatus });
  const rosterQ = useQuery({ queryKey: ['roster', 1], queryFn: () => getRoster(1) });
  const pickupsQ = useQuery({ queryKey: ['pickups'], queryFn: () => getAvailablePlayers({ window: '30d', limit: 3, sort: 'pts_per_game' }) });
  const dropsQ = useQuery({ queryKey: ['drops'], queryFn: () => getDropCandidates('30d') });
  const hotBattersQ = useQuery({ queryKey: ['hotBatters'], queryFn: () => getAvailablePlayers({ window: '3d', limit: 5, sort: 'pts_per_game', position: 'batter' }) });
  const hotPitchersQ = useQuery({ queryKey: ['hotPitchers'], queryFn: () => getAvailablePlayers({ window: '3d', limit: 5, sort: 'pts_per_game', position: 'pitcher' }) });
  const rsQ = useQuery({ queryKey: ['runSupport'], queryFn: getRunSupportRankings });

  const handleRefresh = async () => {
    setRefreshing(true);
    try { await triggerRefresh(); } finally { setRefreshing(false); }
  };

  const roster = rosterQ.data?.roster || [];
  const rosterPPG = roster.length > 0
    ? roster.reduce((sum, p) => sum + (p.pts_per_game || 0), 0)
    : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#2d2d3d]">Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {statusQ.data?.player_count || 0} players cached
          </span>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-3 py-1.5 rounded-lg text-sm bg-[#AACBF5] text-[#2d2d3d] font-medium hover:bg-[#AACBF5]/80 disabled:opacity-50 transition shadow-sm"
          >
            {refreshing ? 'Refreshing...' : 'Refresh Data'}
          </button>
        </div>
      </div>

      {/* Top Row Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Roster Health */}
        <Card title="Roster Health (7D)">
          {rosterQ.isLoading ? <LoadingSkeleton rows={2} cols={2} /> : (
            <div>
              <div className="text-3xl font-bold text-[#2d2d3d]">{rosterPPG.toFixed(1)}</div>
              <div className="text-sm text-slate-500">Total Pts/Game (last 7 days)</div>
              <div className="text-sm text-slate-400 mt-1">{roster.length} players on roster</div>
            </div>
          )}
        </Card>

        {/* Top Pickups */}
        <Card title="Top Pickup Suggestions">
          {pickupsQ.isLoading ? <LoadingSkeleton rows={3} cols={3} /> : (
            <div className="space-y-2">
              {(pickupsQ.data?.players || []).map((p, i) => (
                <div key={p.player_id} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="text-slate-400 mr-2">{i + 1}.</span>
                    <span className="text-[#2d2d3d] font-medium">{p.player_name}</span>
                    <span className="text-slate-400 ml-1">{p.team}</span>
                    {p.is_pitcher && p.run_support_tier && (
                      <RunSupportBadge tier={p.run_support_tier} compact className="ml-1" />
                    )}
                  </div>
                  <span className="text-emerald-700 font-mono font-medium">{p.pts_per_game} ppg</span>
                </div>
              ))}
              {(pickupsQ.data?.players || []).length === 0 && (
                <div className="text-slate-400 text-sm">No data — refresh to load players</div>
              )}
            </div>
          )}
        </Card>

        {/* Drop Candidates */}
        <Card title="Top Drop Candidates">
          {dropsQ.isLoading ? <LoadingSkeleton rows={3} cols={3} /> : (
            <div className="space-y-2">
              {(dropsQ.data?.candidates || []).slice(0, 3).map((c, i) => (
                <div key={c.player_id} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="text-slate-400 mr-2">{i + 1}.</span>
                    <span className="text-[#2d2d3d] font-medium">{c.player_name}</span>
                    {c.is_pitcher && c.run_support_tier && (
                      <RunSupportBadge tier={c.run_support_tier} compact className="ml-1" />
                    )}
                  </div>
                  <span className={c.recommendation === 'drop' ? 'text-red-500 font-medium' : 'text-amber-600 font-medium'}>
                    {c.recommendation}
                  </span>
                </div>
              ))}
              {(dropsQ.data?.candidates || []).length === 0 && (
                <div className="text-slate-400 text-sm">Add players to your roster first</div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Hot Players — Batters & Pitchers */}
        <Card title="Hot Players (3D) - Available">
          <div className="space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-[#4a6fa5] uppercase tracking-wider mb-2">Batters</h4>
              {hotBattersQ.isLoading ? <LoadingSkeleton rows={3} cols={3} /> : (
                <div className="space-y-1.5">
                  {(hotBattersQ.data?.players || []).map((p) => (
                    <div key={p.player_id} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-[#2d2d3d] font-medium">{p.player_name}</span>
                        <span className="text-slate-400">{p.team} · {p.positions}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-emerald-700 font-mono font-medium">{p.pts_per_game} ppg</span>
                        <TrendArrow trend={p.trend} />
                      </div>
                    </div>
                  ))}
                  {(hotBattersQ.data?.players || []).length === 0 && (
                    <div className="text-slate-400 text-xs">No batter data</div>
                  )}
                </div>
              )}
            </div>
            <div className="border-t border-[#A9B8E2]/40 pt-3">
              <h4 className="text-xs font-semibold text-[#9b6fb0] uppercase tracking-wider mb-2">Pitchers</h4>
              {hotPitchersQ.isLoading ? <LoadingSkeleton rows={3} cols={3} /> : (
                <div className="space-y-1.5">
                  {(hotPitchersQ.data?.players || []).map((p) => (
                    <div key={p.player_id} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-[#2d2d3d] font-medium">{p.player_name}</span>
                        <span className="text-slate-400">{p.team}</span>
                        {p.run_support_tier && (
                          <RunSupportBadge tier={p.run_support_tier} compact />
                        )}
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-emerald-700 font-mono font-medium">{p.pts_per_game} ppg</span>
                        <TrendArrow trend={p.trend} />
                      </div>
                    </div>
                  ))}
                  {(hotPitchersQ.data?.players || []).length === 0 && (
                    <div className="text-slate-400 text-xs">No pitcher data</div>
                  )}
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Run Support Leaderboard */}
        <Card title="MLB Run Support Rankings">
          {rsQ.isLoading ? <LoadingSkeleton rows={10} cols={5} /> : (
            <div className="max-h-80 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-white">
                  <tr className="text-slate-500 text-xs">
                    <th className="text-left py-1">#</th>
                    <th className="text-left">Team</th>
                    <th className="text-left">Tier</th>
                    <th className="text-right">R/G</th>
                    <th className="text-right">Diff</th>
                  </tr>
                </thead>
                <tbody>
                  {(rsQ.data?.teams || []).map((t, i) => {
                    const colors = TIER_COLORS[t.tier] || TIER_COLORS.B;
                    return (
                      <tr key={t.team_id} className="border-t border-[#A9B8E2]/20 hover:bg-[#AACBF5]/10">
                        <td className="py-1 text-slate-400">{i + 1}</td>
                        <td className="font-medium text-[#2d2d3d]">{t.team_abbrev}</td>
                        <td>
                          <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${colors.bg} ${colors.text}`}>
                            {t.tier}
                          </span>
                        </td>
                        <td className="text-right font-mono">{t.games_played > 0 ? (t.runs_scored / t.games_played).toFixed(2) : '—'}</td>
                        <td className={`text-right font-mono ${t.run_differential > 0 ? 'text-emerald-700' : t.run_differential < 0 ? 'text-red-500' : ''}`}>
                          {t.run_differential > 0 ? '+' : ''}{t.run_differential}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-500 mb-3">{title}</h3>
      {children}
    </div>
  );
}
