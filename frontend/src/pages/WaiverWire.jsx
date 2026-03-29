import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getAvailablePlayers, addToRoster, getPlayerDetail } from '../api/client';
import RunSupportBadge from '../components/RunSupportBadge';
import TrendArrow from '../components/TrendArrow';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const WINDOWS = ['3d', '7d', '14d', '30d', 'season'];
const POSITIONS = ['ALL', 'C', '1B', '2B', '3B', 'SS', 'OF', 'SP', 'RP'];

export default function WaiverWire() {
  const [window, setWindow] = useState('7d');
  const [position, setPosition] = useState('ALL');
  const [sort, setSort] = useState('pts_per_game');
  const [expanded, setExpanded] = useState(null);
  const [rsFilter, setRsFilter] = useState(false);

  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['available', window, position, sort],
    queryFn: () => getAvailablePlayers({ window, position, sort, limit: 50 }),
  });

  const addMutation = useMutation({
    mutationFn: addToRoster,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roster'] });
      queryClient.invalidateQueries({ queryKey: ['available'] });
      queryClient.invalidateQueries({ queryKey: ['pickups'] });
      queryClient.invalidateQueries({ queryKey: ['hot'] });
    },
  });

  let players = data?.players || [];
  if (rsFilter) {
    players = players.filter(p => !p.is_pitcher || ['S', 'A'].includes(p.run_support_tier));
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <h1 className="text-2xl font-bold text-[#2d2d3d]">Waiver Wire</h1>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-lg overflow-hidden border border-[#A9B8E2]/50 bg-white shadow-sm">
          {WINDOWS.map(w => (
            <button key={w} onClick={() => setWindow(w)}
              className={`px-3 py-1.5 text-sm font-medium transition ${window === w ? 'bg-[#AACBF5] text-[#2d2d3d]' : 'text-slate-500 hover:text-[#2d2d3d] hover:bg-[#AACBF5]/20'}`}>
              {w.toUpperCase()}
            </button>
          ))}
        </div>

        <select value={position} onChange={e => setPosition(e.target.value)}
          className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm">
          {POSITIONS.map(p => <option key={p} value={p}>{p}</option>)}
        </select>

        <select value={sort} onChange={e => setSort(e.target.value)}
          className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm">
          <option value="pts_per_game">Pts/Game</option>
          <option value="total_pts">Total Pts</option>
          <option value="trend">Trend</option>
        </select>

        <label className="flex items-center gap-2 text-sm text-slate-500 cursor-pointer">
          <input type="checkbox" checked={rsFilter} onChange={e => setRsFilter(e.target.checked)}
            className="rounded accent-[#AACBF5]" />
          A+ Run Support Only
        </label>

        <span className="text-xs text-slate-400 ml-auto">{players.length} players</span>
      </div>

      {/* Table */}
      {isLoading ? <LoadingSkeleton rows={10} cols={8} /> : (
        <div className="overflow-x-auto bg-white rounded-xl border border-[#A9B8E2]/30 shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs border-b border-[#A9B8E2]/30 bg-[#AACBF5]/10">
                <th className="text-left py-2 px-2">#</th>
                <th className="text-left px-2">Player</th>
                <th className="text-left px-2">Team</th>
                <th className="text-left px-2">Pos</th>
                <th className="text-right px-2">GP</th>
                <th className="text-right px-2">FPts</th>
                <th className="text-right px-2">FPts/G</th>
                <th className="text-right px-2">Season PPG</th>
                <th className="text-center px-2">Trend</th>
                <th className="text-center px-2">RS</th>
                <th className="text-right px-2">Adj PPG</th>
                <th className="px-2"></th>
              </tr>
            </thead>
            <tbody>
              {players.map((p, i) => (
                <PlayerRow key={p.player_id} player={p} rank={i + 1}
                  expanded={expanded === p.player_id}
                  onToggle={() => setExpanded(expanded === p.player_id ? null : p.player_id)}
                  onAdd={() => addMutation.mutate({
                    player_id: p.player_id, player_name: p.player_name,
                    team: p.team, positions: p.positions, roster_slot: 'BN',
                    league_team_id: 1,
                  })}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PlayerRow({ player: p, rank, expanded, onToggle, onAdd }) {
  const detailQ = useQuery({
    queryKey: ['playerDetail', p.player_id],
    queryFn: () => getPlayerDetail(p.player_id),
    enabled: expanded,
  });

  return (
    <>
      <tr onClick={onToggle}
        className={`border-b border-[#A9B8E2]/15 cursor-pointer transition
          ${rank % 2 === 0 ? 'bg-[#F7F1D1]/30' : ''}
          hover:bg-[#AACBF5]/10`}>
        <td className="py-2 px-2 text-slate-400">{rank}</td>
        <td className="px-2 font-medium text-[#2d2d3d]">{p.player_name}</td>
        <td className="px-2 text-slate-500">{p.team}</td>
        <td className="px-2 text-slate-500">{p.positions}</td>
        <td className="px-2 text-right">{p.games_played}</td>
        <td className="px-2 text-right font-mono">{p.fantasy_points}</td>
        <td className="px-2 text-right font-mono text-[#2d2d3d] font-medium">{p.pts_per_game}</td>
        <td className="px-2 text-right font-mono text-slate-400">{p.season_ppg}</td>
        <td className="px-2 text-center"><TrendArrow trend={p.trend} /></td>
        <td className="px-2 text-center">
          {p.is_pitcher && p.run_support_tier ? (
            <RunSupportBadge tier={p.run_support_tier} rpg={p.team_rpg} rank={p.run_support_rank} />
          ) : <span className="text-slate-300">—</span>}
        </td>
        <td className="px-2 text-right font-mono">
          {p.is_pitcher ? (
            <span className={p.win_adjusted_ppg > p.pts_per_game ? 'text-emerald-700 font-medium' : ''}>
              {p.win_adjusted_ppg}
            </span>
          ) : <span className="text-slate-300">—</span>}
        </td>
        <td className="px-2">
          <button onClick={e => { e.stopPropagation(); onAdd(); }}
            className="px-2 py-1 rounded text-xs bg-[#A3DFC4] text-[#2d2d3d] font-medium hover:bg-[#A3DFC4]/80 transition shadow-sm">
            Add
          </button>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={12} className="bg-[#AACBF5]/10 p-4 border-b border-[#A9B8E2]/30">
            {detailQ.isLoading ? <LoadingSkeleton rows={3} cols={4} /> : (
              <div className="space-y-3">
                {detailQ.data?.recent_game_logs?.length > 0 && (
                  <div>
                    <div className="text-xs text-slate-500 mb-2">Last 14 Days — Fantasy Points per Game</div>
                    <ResponsiveContainer width="100%" height={120}>
                      <LineChart data={detailQ.data.recent_game_logs.map(g => ({
                        date: g.game_date?.slice(5),
                        pts: g.fantasy_points,
                      })).reverse()}>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                        <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={30} />
                        <Tooltip contentStyle={{ background: '#fff', border: '1px solid #A9B8E2', borderRadius: 8 }}
                          labelStyle={{ color: '#64748b' }} />
                        <Line type="monotone" dataKey="pts" stroke="#4a6fa5" strokeWidth={2} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
