import { useQuery, useMutation } from '@tanstack/react-query';
import { optimizeLineup } from '../api/client';
import RunSupportBadge from '../components/RunSupportBadge';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useState } from 'react';

const SLOT_LABELS = {
  C: 'C', '1B': '1B', '2B': '2B', '3B': '3B', SS: 'SS',
  OF_1: 'OF', OF_2: 'OF', OF_3: 'OF', Util: 'Util',
  SP: 'SP', RP: 'RP', P_1: 'P', P_2: 'P', P_3: 'P',
};

export default function LineupOptimizer() {
  const [window, setWindow] = useState('14d');
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - today.getDay() + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const [weekStart, setWeekStart] = useState(monday.toISOString().split('T')[0]);
  const [weekEnd, setWeekEnd] = useState(sunday.toISOString().split('T')[0]);

  const optimizeMutation = useMutation({
    mutationFn: optimizeLineup,
  });

  const handleOptimize = () => {
    optimizeMutation.mutate({ window, week_start: weekStart, week_end: weekEnd });
  };

  const result = optimizeMutation.data;
  const lineup = result?.optimal_lineup || {};
  const bench = result?.bench || [];
  const notes = result?.notes || [];

  // Separate batter and pitcher slots
  const batterSlots = ['C', '1B', '2B', '3B', 'SS', 'OF_1', 'OF_2', 'OF_3', 'Util'];
  const pitcherSlots = ['SP', 'RP', 'P_1', 'P_2', 'P_3'];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <h1 className="text-2xl font-bold text-[#2d2d3d]">Lineup Optimizer</h1>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Performance Window</label>
          <select value={window} onChange={e => setWindow(e.target.value)}
            className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm">
            <option value="7d">7 Days</option>
            <option value="14d">14 Days</option>
            <option value="30d">30 Days</option>
            <option value="season">Season</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Week Start</label>
          <input type="date" value={weekStart} onChange={e => setWeekStart(e.target.value)}
            className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm" />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Week End</label>
          <input type="date" value={weekEnd} onChange={e => setWeekEnd(e.target.value)}
            className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm" />
        </div>
        <button onClick={handleOptimize} disabled={optimizeMutation.isPending}
          className="px-4 py-1.5 rounded-lg text-sm bg-[#AACBF5] text-[#2d2d3d] font-semibold hover:bg-[#AACBF5]/80 disabled:opacity-50 transition shadow-sm">
          {optimizeMutation.isPending ? 'Optimizing...' : 'Optimize Lineup'}
        </button>
      </div>

      {optimizeMutation.isPending && <LoadingSkeleton rows={14} cols={6} />}

      {result && !result.error && (
        <div className="space-y-4">
          {/* Total */}
          <div className="bg-white rounded-xl border border-[#A3DFC4] p-4 flex items-center justify-between shadow-sm">
            <div>
              <div className="text-sm text-slate-500">Total Projected Points</div>
              <div className="text-3xl font-bold text-emerald-700">{result.total_projected_pts}</div>
            </div>
            <div className="text-sm text-slate-400">
              {weekStart} → {weekEnd}
            </div>
          </div>

          {/* Batters */}
          <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-[#4a6fa5] mb-3">Batters</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-xs">
                  <th className="text-left py-1">Slot</th>
                  <th className="text-left">Player</th>
                  <th className="text-left">Team</th>
                  <th className="text-right">Games</th>
                  <th className="text-right">PPG</th>
                  <th className="text-right">Proj Pts</th>
                </tr>
              </thead>
              <tbody>
                {batterSlots.map(slot => {
                  const p = lineup[slot];
                  return (
                    <tr key={slot} className="border-t border-[#A9B8E2]/15 hover:bg-[#AACBF5]/10">
                      <td className="py-2 font-mono text-xs text-slate-400">{SLOT_LABELS[slot]}</td>
                      <td className="font-medium text-[#2d2d3d]">{p?.player_name || '—'}</td>
                      <td className="text-slate-500">{p?.team || ''}</td>
                      <td className="text-right">{p?.games_this_week ?? ''}</td>
                      <td className="text-right font-mono">{p?.projected_pts_per_game ?? ''}</td>
                      <td className="text-right font-mono text-emerald-700 font-medium">{p?.projected_total ?? ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pitchers */}
          <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-[#9b6fb0] mb-3">Pitchers</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 text-xs">
                  <th className="text-left py-1">Slot</th>
                  <th className="text-left">Player</th>
                  <th className="text-left">Team</th>
                  <th className="text-center">RS</th>
                  <th className="text-right">Games</th>
                  <th className="text-right">PPG</th>
                  <th className="text-right">Proj Pts</th>
                </tr>
              </thead>
              <tbody>
                {pitcherSlots.map(slot => {
                  const p = lineup[slot];
                  return (
                    <tr key={slot} className="border-t border-[#A9B8E2]/15 hover:bg-[#AACBF5]/10">
                      <td className="py-2 font-mono text-xs text-slate-400">{SLOT_LABELS[slot]}</td>
                      <td className="font-medium text-[#2d2d3d]">{p?.player_name || '—'}</td>
                      <td className="text-slate-500">{p?.team || ''}</td>
                      <td className="text-center">
                        {p?.run_support_tier ? <RunSupportBadge tier={p.run_support_tier} compact /> : ''}
                      </td>
                      <td className="text-right">{p?.games_this_week ?? ''}</td>
                      <td className="text-right font-mono">{p?.projected_pts_per_game ?? ''}</td>
                      <td className="text-right font-mono text-emerald-700 font-medium">{p?.projected_total ?? ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Bench */}
          {bench.length > 0 && (
            <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-500 mb-3">Bench</h3>
              <div className="space-y-1 text-sm">
                {bench.map(p => (
                  <div key={p.player_id} className="flex items-center justify-between py-1">
                    <div className="flex items-center gap-2">
                      <span className="text-[#2d2d3d]">{p.player_name}</span>
                      <span className="text-slate-400">{p.team} · {p.positions}</span>
                      {p.run_support_tier && <RunSupportBadge tier={p.run_support_tier} compact />}
                    </div>
                    <span className="font-mono text-slate-400">{p.projected_total} proj</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notes */}
          {notes.length > 0 && (
            <div className="bg-[#FAEDAE]/50 border border-[#EFC965] rounded-xl p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-amber-700 mb-2">Notes</h3>
              <ul className="space-y-1 text-sm text-amber-800">
                {notes.map((n, i) => <li key={i}>{n}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {result?.error && (
        <div className="bg-[#FFB8BF]/20 border border-[#FFB8BF] rounded-xl p-4 text-red-600 shadow-sm">
          {result.error}
        </div>
      )}
    </div>
  );
}
