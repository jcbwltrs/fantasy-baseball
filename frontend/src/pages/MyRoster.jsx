import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getRoster, dropFromRoster, getDropCandidates, uploadRosterCsv,
  confirmCsvUpload, searchPlayers, addToRoster, moveRosterSlot,
  getLeagueTeams, renameLeagueTeam, getAvailableSlots,
} from '../api/client';
import RunSupportBadge from '../components/RunSupportBadge';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { REC_COLORS } from '../utils/scoring';
import { useState, useRef } from 'react';

const WINDOWS = ['3d', '7d', '14d', '30d', 'season'];

const SLOT_ORDER = ['C', '1B', '2B', '3B', 'SS', 'OF', 'Util', 'SP', 'RP', 'P', 'BN', 'IL'];

const SLOT_GROUPS = [
  { label: 'Batters', slots: ['C', '1B', '2B', '3B', 'SS', 'OF', 'Util'], color: '#4a6fa5' },
  { label: 'Pitchers', slots: ['SP', 'RP', 'P'], color: '#9b6fb0' },
  { label: 'Bench & IL', slots: ['BN', 'IL'], color: '#7a8a9e' },
];

export default function MyRoster() {
  const [tab, setTab] = useState('roster');
  const [dropWindow, setDropWindow] = useState('14d');
  const [searchQuery, setSearchQuery] = useState('');
  const [csvResult, setCsvResult] = useState(null);
  const [selectedTeam, setSelectedTeam] = useState(1);
  const [movingPlayer, setMovingPlayer] = useState(null);
  const [editingTeamName, setEditingTeamName] = useState(null);
  const [newTeamName, setNewTeamName] = useState('');
  const fileRef = useRef(null);
  const queryClient = useQueryClient();

  const teamsQ = useQuery({ queryKey: ['leagueTeams'], queryFn: getLeagueTeams });
  const rosterQ = useQuery({ queryKey: ['roster', selectedTeam], queryFn: () => getRoster(selectedTeam) });
  const slotsQ = useQuery({ queryKey: ['slots', selectedTeam], queryFn: () => getAvailableSlots(selectedTeam) });
  const dropsQ = useQuery({
    queryKey: ['dropCandidates', dropWindow, selectedTeam],
    queryFn: () => getDropCandidates(dropWindow, selectedTeam),
    enabled: tab === 'drops',
  });
  const searchQ = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => searchPlayers(searchQuery),
    enabled: searchQuery.length >= 2 && tab === 'add',
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['roster', selectedTeam] });
    queryClient.invalidateQueries({ queryKey: ['slots', selectedTeam] });
    queryClient.invalidateQueries({ queryKey: ['available'] });
    queryClient.invalidateQueries({ queryKey: ['pickups'] });
    queryClient.invalidateQueries({ queryKey: ['hot'] });
    queryClient.invalidateQueries({ queryKey: ['drops'] });
  };

  const dropMutation = useMutation({
    mutationFn: (playerId) => dropFromRoster({ player_id: playerId, league_team_id: selectedTeam }),
    onSuccess: invalidateAll,
  });

  const addMutation = useMutation({
    mutationFn: addToRoster,
    onSuccess: () => {
      invalidateAll();
      setSearchQuery('');
    },
  });

  const moveMutation = useMutation({
    mutationFn: moveRosterSlot,
    onSuccess: () => {
      invalidateAll();
      setMovingPlayer(null);
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ teamId, name }) => renameLeagueTeam(teamId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leagueTeams'] });
      setEditingTeamName(null);
    },
  });

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const result = await uploadRosterCsv(file, selectedTeam);
    setCsvResult(result);
  };

  const handleConfirmCsv = async () => {
    if (!csvResult?.matched) return;
    await confirmCsvUpload(csvResult.matched, selectedTeam);
    setCsvResult(null);
    invalidateAll();
  };

  const roster = rosterQ.data?.roster || [];
  const slotLimits = rosterQ.data?.slot_limits || {};
  const slotCounts = rosterQ.data?.slot_counts || {};
  const teams = teamsQ.data?.teams || [];
  const selectedTeamName = teams.find(t => t.team_id === selectedTeam)?.team_name || `Team ${selectedTeam}`;

  // Group roster by slot
  const rosterBySlot = {};
  for (const p of roster) {
    const slot = p.roster_slot || 'BN';
    if (!rosterBySlot[slot]) rosterBySlot[slot] = [];
    rosterBySlot[slot].push(p);
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      {/* Header + Team Selector */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-bold text-[#2d2d3d]">League Rosters</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-500">{roster.length}/20 players</span>
        </div>
      </div>

      {/* Team Tabs */}
      <div className="flex gap-1 flex-wrap items-center">
        {teams.map(t => (
          <div key={t.team_id} className="flex items-center">
            {editingTeamName === t.team_id ? (
              <div className="flex items-center gap-1">
                <input
                  value={newTeamName}
                  onChange={e => setNewTeamName(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') renameMutation.mutate({ teamId: t.team_id, name: newTeamName });
                    if (e.key === 'Escape') setEditingTeamName(null);
                  }}
                  className="bg-white border border-[#AACBF5] rounded px-2 py-1 text-xs text-[#2d2d3d] focus:outline-none w-28 shadow-sm"
                  autoFocus
                />
                <button onClick={() => renameMutation.mutate({ teamId: t.team_id, name: newTeamName })}
                  className="px-1.5 py-1 rounded text-[10px] bg-[#A3DFC4] text-[#2d2d3d] font-medium">OK</button>
                <button onClick={() => setEditingTeamName(null)}
                  className="px-1 py-1 text-[10px] text-slate-400">×</button>
              </div>
            ) : (
              <button
                onClick={() => setSelectedTeam(t.team_id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1 shadow-sm ${
                  selectedTeam === t.team_id
                    ? t.is_mine ? 'bg-[#A3DFC4] text-[#2d2d3d] ring-1 ring-[#A3DFC4]' : 'bg-[#AACBF5] text-[#2d2d3d] ring-1 ring-[#AACBF5]'
                    : 'bg-white text-slate-500 hover:text-[#2d2d3d] hover:bg-[#AACBF5]/20 border border-[#A9B8E2]/30'
                }`}
              >
                {t.team_name}
                {selectedTeam === t.team_id && (
                  <span
                    onClick={e => { e.stopPropagation(); setEditingTeamName(t.team_id); setNewTeamName(t.team_name); }}
                    className="ml-1 text-[10px] opacity-60 hover:opacity-100 cursor-pointer"
                    title="Rename team"
                  >&#9998;</span>
                )}
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Action Tabs */}
      <div className="flex gap-2">
        {[
          { id: 'roster', label: 'Roster' },
          { id: 'drops', label: 'Drop Candidates' },
          { id: 'add', label: 'Add Player' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm ${
              tab === t.id ? 'bg-[#AACBF5] text-[#2d2d3d]' : 'bg-white text-slate-500 hover:text-[#2d2d3d] border border-[#A9B8E2]/30'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ========== ROSTER TAB ========== */}
      {tab === 'roster' && (
        <>
          {/* CSV Upload */}
          <div className="flex items-center gap-3">
            <input ref={fileRef} type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
            <button onClick={() => fileRef.current?.click()}
              className="px-3 py-1.5 rounded-lg text-sm bg-[#A9B8E2] text-[#2d2d3d] font-medium hover:bg-[#A9B8E2]/80 transition shadow-sm">
              Upload Yahoo CSV
            </button>
            <span className="text-xs text-slate-500">for {selectedTeamName}</span>
          </div>

          {/* CSV Confirmation */}
          {csvResult && (
            <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 space-y-3 shadow-sm">
              <div className="text-sm text-[#2d2d3d] font-semibold">CSV Import Results</div>
              <div className="text-sm text-slate-500">
                Matched: {csvResult.matched?.length || 0} | Unmatched: {csvResult.unmatched?.length || 0}
              </div>
              {csvResult.matched?.map(p => (
                <div key={p.player_id} className="flex items-center gap-2 text-sm">
                  <span className="text-slate-400">{p.input_name}</span>
                  <span className="text-slate-300">→</span>
                  <span className="text-[#2d2d3d]">{p.matched_name}</span>
                  <span className="text-slate-400">({(p.confidence * 100).toFixed(0)}%)</span>
                </div>
              ))}
              {csvResult.unmatched?.map((p, i) => (
                <div key={i} className="text-sm text-red-500">Not found: {p.input_name}</div>
              ))}
              <button onClick={handleConfirmCsv}
                className="px-4 py-2 rounded-lg text-sm bg-[#A3DFC4] text-[#2d2d3d] font-medium hover:bg-[#A3DFC4]/80 shadow-sm">
                Confirm & Add All Matched Players
              </button>
            </div>
          )}

          {/* Slot-Based Roster View */}
          {rosterQ.isLoading ? <LoadingSkeleton rows={10} cols={7} /> : (
            <div className="space-y-4">
              {SLOT_GROUPS.map(group => (
                <div key={group.label} className="bg-white rounded-xl border border-[#A9B8E2]/30 overflow-hidden shadow-sm">
                  <div className="px-4 py-2 border-b border-[#A9B8E2]/20" style={{ backgroundColor: group.color + '15' }}>
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: group.color }}>{group.label}</span>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-slate-500 text-xs border-b border-[#A9B8E2]/20">
                        <th className="text-left py-2 px-3 w-16">Slot</th>
                        <th className="text-left px-2">Player</th>
                        <th className="text-left px-2 w-16">Team</th>
                        <th className="text-left px-2 w-16">Pos</th>
                        <th className="text-right px-2 w-14">GP</th>
                        <th className="text-right px-2 w-20">FPts</th>
                        <th className="text-right px-2 w-16">PPG</th>
                        <th className="px-2 w-24"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.slots.flatMap(slot => {
                        const playersInSlot = rosterBySlot[slot] || [];
                        const limit = slotLimits[slot] || 1;
                        const rows = [];

                        for (let i = 0; i < Math.max(playersInSlot.length, limit); i++) {
                          const p = playersInSlot[i];
                          rows.push(
                            <tr key={`${slot}-${i}`}
                              className="border-b border-[#A9B8E2]/10 hover:bg-[#AACBF5]/10">
                              <td className="py-2 px-3">
                                <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-[#A9B8E2]/20 text-slate-600 font-medium">
                                  {slot}
                                </span>
                              </td>
                              {p ? (
                                <>
                                  <td className="px-2 font-medium text-[#2d2d3d]">{p.player_name}</td>
                                  <td className="px-2 text-slate-500">{p.team}</td>
                                  <td className="px-2 text-slate-500">{p.positions}</td>
                                  <td className="px-2 text-right text-slate-600">{p.games_played}</td>
                                  <td className="px-2 text-right font-mono text-slate-600">{p.fantasy_points}</td>
                                  <td className="px-2 text-right font-mono text-[#2d2d3d] font-medium">{p.pts_per_game}</td>
                                  <td className="px-2">
                                    <div className="flex gap-1 justify-end">
                                      <button onClick={() => setMovingPlayer(movingPlayer === p.player_id ? null : p.player_id)}
                                        className="px-2 py-0.5 rounded text-xs bg-[#AACBF5]/30 text-[#4a6fa5] hover:bg-[#AACBF5]/50 transition font-medium"
                                        title="Move to different slot">
                                        Move
                                      </button>
                                      <button onClick={() => dropMutation.mutate(p.player_id)}
                                        className="px-2 py-0.5 rounded text-xs bg-[#FFB8BF]/30 text-red-600 hover:bg-[#FFB8BF]/50 transition font-medium">
                                        Drop
                                      </button>
                                    </div>
                                    {movingPlayer === p.player_id && (
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {SLOT_ORDER.filter(s => s !== p.roster_slot).map(s => (
                                          <button key={s}
                                            onClick={() => moveMutation.mutate({
                                              player_id: p.player_id,
                                              league_team_id: selectedTeam,
                                              new_slot: s,
                                            })}
                                            className="px-1.5 py-0.5 rounded text-[10px] bg-[#A9B8E2]/20 text-slate-600 hover:bg-[#A9B8E2]/40 transition font-medium">
                                            {s}
                                          </button>
                                        ))}
                                      </div>
                                    )}
                                  </td>
                                </>
                              ) : (
                                <>
                                  <td className="px-2 text-slate-300 italic" colSpan={6}>Empty</td>
                                  <td></td>
                                </>
                              )}
                            </tr>
                          );
                        }
                        return rows;
                      })}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* ========== DROP CANDIDATES TAB ========== */}
      {tab === 'drops' && (
        <>
          <div className="flex rounded-lg overflow-hidden border border-[#A9B8E2]/50 bg-white w-fit shadow-sm">
            {WINDOWS.map(w => (
              <button key={w} onClick={() => setDropWindow(w)}
                className={`px-3 py-1.5 text-sm font-medium transition ${
                  dropWindow === w ? 'bg-[#AACBF5] text-[#2d2d3d]' : 'text-slate-500 hover:text-[#2d2d3d]'
                }`}>
                {w.toUpperCase()}
              </button>
            ))}
          </div>

          {dropsQ.isLoading ? <LoadingSkeleton rows={6} cols={8} /> : (
            <div className="space-y-3">
              {(dropsQ.data?.candidates || []).map(c => {
                const rec = REC_COLORS[c.recommendation] || REC_COLORS.hold;
                return (
                  <div key={c.player_id} className={`bg-white rounded-xl border ${rec.border} p-4 shadow-sm`}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[#2d2d3d] font-medium">{c.player_name}</span>
                        <span className="text-slate-400">{c.team} · {c.positions}</span>
                        {c.is_pitcher && c.run_support_tier && (
                          <RunSupportBadge tier={c.run_support_tier} compact />
                        )}
                      </div>
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${rec.bg} ${rec.text}`}>
                        {c.recommendation.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <div className="text-slate-400">Window PPG</div>
                        <div className="text-[#2d2d3d] font-mono font-medium">{c.pts_per_game}</div>
                      </div>
                      <div>
                        <div className="text-slate-400">Season PPG</div>
                        <div className="text-[#2d2d3d] font-mono font-medium">{c.season_ppg}</div>
                      </div>
                      <div>
                        <div className="text-slate-400">Upgrade Potential</div>
                        <div className={`font-mono font-medium ${c.upgrade_potential > 0 ? 'text-emerald-700' : 'text-slate-400'}`}>
                          {c.upgrade_potential > 0 ? '+' : ''}{c.upgrade_potential}
                        </div>
                      </div>
                      {c.replacement && (
                        <div>
                          <div className="text-slate-400">Best Replacement</div>
                          <div className="text-[#4a6fa5] font-medium">{c.replacement.player_name} ({c.replacement.ppg} ppg)</div>
                        </div>
                      )}
                    </div>
                    {c.reason && <div className="text-xs text-slate-400 mt-2">{c.reason}</div>}
                  </div>
                );
              })}
              {(dropsQ.data?.candidates || []).length === 0 && (
                <div className="text-slate-400 text-sm">No players on this roster to analyze</div>
              )}
            </div>
          )}
        </>
      )}

      {/* ========== ADD PLAYER TAB ========== */}
      {tab === 'add' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search player name..."
              className="w-full max-w-md bg-white border border-[#A9B8E2]/50 rounded-lg px-4 py-2 text-[#2d2d3d] placeholder-slate-400 focus:outline-none focus:border-[#AACBF5] shadow-sm"
            />
            <span className="text-xs text-slate-500">Adding to: {selectedTeamName}</span>
          </div>
          {searchQ.isLoading && <LoadingSkeleton rows={3} cols={4} />}
          {searchQ.data?.players?.map(p => (
            <div key={p.player_id} className="flex items-center justify-between bg-white rounded-lg border border-[#A9B8E2]/30 p-3 shadow-sm">
              <div>
                <span className="text-[#2d2d3d] font-medium">{p.player_name}</span>
                <span className="text-slate-400 ml-2">{p.team} · {p.position}</span>
              </div>
              <div className="flex items-center gap-2">
                <SlotPicker
                  position={p.position}
                  onSelect={(slot) => addMutation.mutate({
                    player_id: p.player_id,
                    player_name: p.player_name,
                    team: p.team,
                    positions: p.position,
                    roster_slot: slot,
                    league_team_id: selectedTeam,
                  })}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Small slot picker for adding players */
function SlotPicker({ position, onSelect }) {
  const [open, setOpen] = useState(false);

  const pitcherSlots = ['SP', 'RP', 'P', 'BN'];
  const batterSlots = ['C', '1B', '2B', '3B', 'SS', 'OF', 'Util', 'BN'];
  const isPitcher = ['SP', 'RP', 'P'].includes(position);
  const slots = isPitcher ? pitcherSlots : batterSlots;

  if (!open) {
    return (
      <button onClick={() => setOpen(true)}
        className="px-3 py-1 rounded text-sm bg-[#A3DFC4] text-[#2d2d3d] font-medium hover:bg-[#A3DFC4]/80 transition shadow-sm">
        Add
      </button>
    );
  }

  return (
    <div className="flex items-center gap-1 flex-wrap">
      <span className="text-xs text-slate-400 mr-1">Slot:</span>
      {slots.map(s => (
        <button key={s}
          onClick={() => { onSelect(s); setOpen(false); }}
          className="px-2 py-0.5 rounded text-xs bg-[#A3DFC4]/30 text-emerald-700 hover:bg-[#A3DFC4]/50 transition font-medium">
          {s}
        </button>
      ))}
      <button onClick={() => setOpen(false)} className="px-1 text-xs text-slate-400">×</button>
    </div>
  );
}
