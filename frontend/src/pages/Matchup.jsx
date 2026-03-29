import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectMatchup, searchPlayers, getMatchupSchedule, saveMatchupSchedule, getLeagueTeams } from '../api/client';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useState, useCallback } from 'react';

// Season weeks: Week 1 is short (Wed 3/25 - Sun 3/29), then Mon-Sun
const SEASON_WEEKS = generateSeasonWeeks();

function generateSeasonWeeks() {
  const weeks = [];

  // Week 1: Short week — Wed 3/25/26 through Sun 3/29/26
  weeks.push({
    week_number: 1,
    week_label: 'Week 1',
    week_start: '2026-03-25',
    week_end: '2026-03-29',
  });

  // Weeks 2-26: Monday through Sunday
  let start = new Date('2026-03-30'); // Monday after Week 1
  for (let i = 2; i <= 26; i++) {
    const end = new Date(start);
    end.setDate(start.getDate() + 6); // Sunday
    weeks.push({
      week_number: i,
      week_label: `Week ${i}`,
      week_start: start.toISOString().split('T')[0],
      week_end: end.toISOString().split('T')[0],
    });
    start = new Date(end);
    start.setDate(end.getDate() + 1); // Next Monday
  }
  return weeks;
}

export default function Matchup() {
  const [tab, setTab] = useState('schedule'); // schedule | project
  const queryClient = useQueryClient();

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-4">
      <h1 className="text-2xl font-bold text-[#2d2d3d]">Matchups</h1>

      <div className="flex gap-2">
        {[
          { id: 'schedule', label: 'Season Schedule' },
          { id: 'project', label: 'Project Matchup' },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition shadow-sm ${
              tab === t.id ? 'bg-[#AACBF5] text-[#2d2d3d]' : 'bg-white text-slate-500 hover:text-[#2d2d3d] border border-[#A9B8E2]/30'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'schedule' && <ScheduleTab />}
      {tab === 'project' && <ProjectTab />}
    </div>
  );
}


function ScheduleTab() {
  const queryClient = useQueryClient();
  const scheduleQ = useQuery({ queryKey: ['matchupSchedule'], queryFn: getMatchupSchedule });
  const teamsQ = useQuery({ queryKey: ['leagueTeams'], queryFn: getLeagueTeams });

  const teams = teamsQ.data?.teams || [];
  const existingWeeks = scheduleQ.data?.weeks || [];

  // Build local schedule state from existing data or blank
  const [localSchedule, setLocalSchedule] = useState(null);
  const [saving, setSaving] = useState(false);

  // Initialize local schedule from server data
  const schedule = localSchedule || buildScheduleFromServer(existingWeeks);

  const saveMutation = useMutation({
    mutationFn: saveMatchupSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matchupSchedule'] });
      setSaving(false);
    },
  });

  const setMatchup = (weekNumber, teamAId, teamBId) => {
    const updated = { ...schedule };
    if (!updated[weekNumber]) {
      const wk = SEASON_WEEKS.find(w => w.week_number === weekNumber);
      updated[weekNumber] = { ...wk, matchups: {} };
    }
    updated[weekNumber].matchups[teamAId] = teamBId;
    setLocalSchedule(updated);
  };

  const handleSave = () => {
    setSaving(true);
    const matchups = [];
    for (const [weekNum, week] of Object.entries(schedule)) {
      for (const [teamAId, teamBId] of Object.entries(week.matchups)) {
        if (teamBId && teamBId !== '0') {
          const wk = SEASON_WEEKS.find(w => w.week_number === parseInt(weekNum));
          matchups.push({
            week_number: parseInt(weekNum),
            week_label: wk?.week_label || `Week ${weekNum}`,
            week_start: wk?.week_start || '',
            week_end: wk?.week_end || '',
            team_a_id: parseInt(teamAId),
            team_b_id: parseInt(teamBId),
          });
        }
      }
    }
    saveMutation.mutate(matchups);
  };

  const myTeam = teams.find(t => t.is_mine);

  // Format date for display: "Mar 25" style
  const fmtDate = (d) => {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Set your opponent for each week of the season. Only your matchups (Team 1) are needed for projections.
        </p>
        <button onClick={handleSave} disabled={saving}
          className="px-4 py-1.5 rounded-lg text-sm bg-[#A3DFC4] text-[#2d2d3d] font-semibold hover:bg-[#A3DFC4]/80 disabled:opacity-50 transition shadow-sm">
          {saving ? 'Saving...' : 'Save Schedule'}
        </button>
      </div>

      {scheduleQ.isLoading ? <LoadingSkeleton rows={10} cols={4} /> : (
        <div className="bg-white rounded-xl border border-[#A9B8E2]/30 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="text-slate-500 text-xs border-b border-[#A9B8E2]/30">
                  <th className="text-left py-2 px-3 w-24">Week</th>
                  <th className="text-left px-3 w-48">Dates</th>
                  <th className="text-left px-3">Your Opponent</th>
                </tr>
              </thead>
              <tbody>
                {SEASON_WEEKS.map(week => {
                  const weekData = schedule[week.week_number];
                  const myMatchup = weekData?.matchups?.[1] || 0; // team 1's opponent

                  return (
                    <tr key={week.week_number} className="border-b border-[#A9B8E2]/15 hover:bg-[#AACBF5]/10">
                      <td className="py-2 px-3">
                        <span className="text-[#2d2d3d] font-medium">{week.week_label}</span>
                      </td>
                      <td className="px-3 text-slate-500 text-xs">
                        {fmtDate(week.week_start)} — {fmtDate(week.week_end)}
                        {week.week_number === 1 && (
                          <span className="ml-1 text-[10px] text-[#EFC965] font-medium">(short week)</span>
                        )}
                      </td>
                      <td className="px-3">
                        <select
                          value={myMatchup}
                          onChange={e => setMatchup(week.week_number, 1, parseInt(e.target.value))}
                          className="bg-white border border-[#A9B8E2]/50 rounded px-2 py-1 text-sm text-[#2d2d3d] focus:outline-none focus:border-[#AACBF5] w-48 shadow-sm"
                        >
                          <option value={0}>-- Select --</option>
                          {teams.filter(t => !t.is_mine).map(t => (
                            <option key={t.team_id} value={t.team_id}>{t.team_name}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}


function buildScheduleFromServer(weeks) {
  const schedule = {};
  for (const week of weeks) {
    if (!schedule[week.week_number]) {
      schedule[week.week_number] = {
        week_number: week.week_number,
        week_label: week.week_label,
        week_start: week.week_start,
        week_end: week.week_end,
        matchups: {},
      };
    }
    for (const m of week.matchups) {
      schedule[week.week_number].matchups[m.team_a_id] = m.team_b_id;
    }
  }
  return schedule;
}


function ProjectTab() {
  const [window, setWindow] = useState('14d');
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - today.getDay() + 1);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);

  const [weekStart, setWeekStart] = useState(monday.toISOString().split('T')[0]);
  const [weekEnd, setWeekEnd] = useState(sunday.toISOString().split('T')[0]);

  const [oppPlayers, setOppPlayers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);

  const handleSearch = useCallback(async (q) => {
    setSearchQuery(q);
    if (q.length < 2) { setSearchResults([]); return; }
    setSearching(true);
    try {
      const res = await searchPlayers(q);
      setSearchResults(res.players || []);
    } finally {
      setSearching(false);
    }
  }, []);

  const addOppPlayer = (player) => {
    if (!oppPlayers.find(p => p.player_id === player.player_id)) {
      setOppPlayers([...oppPlayers, player]);
    }
    setSearchQuery('');
    setSearchResults([]);
  };

  const removeOppPlayer = (id) => {
    setOppPlayers(oppPlayers.filter(p => p.player_id !== id));
  };

  const projectMutation = useMutation({ mutationFn: projectMatchup });

  const handleProject = () => {
    projectMutation.mutate({
      opponent_roster: oppPlayers.map(p => p.player_id),
      window,
      week_start: weekStart,
      week_end: weekEnd,
    });
  };

  const result = projectMutation.data;
  const wpColor = result?.win_probability >= 0.6 ? '#059669'
    : result?.win_probability >= 0.45 ? '#d97706' : '#dc2626';

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Window</label>
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
      </div>

      {/* Opponent Roster */}
      <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 space-y-3 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-500">Opponent Roster</h3>
        <div className="relative">
          <input type="text" value={searchQuery} onChange={e => handleSearch(e.target.value)}
            placeholder="Search opponent's players..."
            className="w-full max-w-md bg-white border border-[#A9B8E2]/50 rounded-lg px-4 py-2 text-[#2d2d3d] placeholder-slate-400 focus:outline-none focus:border-[#AACBF5] shadow-sm" />
          {searchResults.length > 0 && (
            <div className="absolute top-full left-0 mt-1 w-full max-w-md bg-white border border-[#A9B8E2] rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto">
              {searchResults.map(p => (
                <button key={p.player_id} onClick={() => addOppPlayer(p)}
                  className="w-full text-left px-4 py-2 hover:bg-[#AACBF5]/15 text-sm flex justify-between">
                  <span className="text-[#2d2d3d]">{p.player_name}</span>
                  <span className="text-slate-400">{p.team} · {p.position}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {oppPlayers.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {oppPlayers.map(p => (
              <span key={p.player_id}
                className="inline-flex items-center gap-1 bg-[#AACBF5]/30 text-[#4a6fa5] text-sm px-2 py-1 rounded-lg font-medium">
                {p.player_name}
                <button onClick={() => removeOppPlayer(p.player_id)} className="text-[#4a6fa5]/60 hover:text-[#4a6fa5] ml-1">×</button>
              </span>
            ))}
          </div>
        )}

        <button onClick={handleProject} disabled={oppPlayers.length === 0 || projectMutation.isPending}
          className="px-4 py-1.5 rounded-lg text-sm bg-[#AACBF5] text-[#2d2d3d] font-semibold hover:bg-[#AACBF5]/80 disabled:opacity-50 transition shadow-sm">
          {projectMutation.isPending ? 'Projecting...' : 'Project Matchup'}
        </button>
      </div>

      {projectMutation.isPending && <LoadingSkeleton rows={6} cols={4} />}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-[#A3DFC4] p-4 text-center shadow-sm">
              <div className="text-sm text-slate-500">My Projection</div>
              <div className="text-3xl font-bold text-emerald-700">{result.my_projected_pts}</div>
            </div>
            <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 text-center shadow-sm">
              <div className="text-sm text-slate-500">Win Probability</div>
              <div className="text-3xl font-bold" style={{ color: wpColor }}>
                {(result.win_probability * 100).toFixed(0)}%
              </div>
              <div className="w-full bg-[#A9B8E2]/20 rounded-full h-2 mt-2">
                <div className="h-2 rounded-full transition-all" style={{
                  width: `${result.win_probability * 100}%`,
                  backgroundColor: wpColor,
                }} />
              </div>
            </div>
            <div className="bg-white rounded-xl border border-[#FFB8BF] p-4 text-center shadow-sm">
              <div className="text-sm text-slate-500">Opponent Projection</div>
              <div className="text-3xl font-bold text-red-500">{result.opponent_projected_pts}</div>
            </div>
          </div>

          {result.my_projected_pts > result.opponent_projected_pts ? (
            <div className="bg-[#A3DFC4]/20 border border-[#A3DFC4] rounded-xl p-3 text-sm text-emerald-800 shadow-sm">
              Key Advantage: You're projected to win by {(result.my_projected_pts - result.opponent_projected_pts).toFixed(1)} points
            </div>
          ) : (
            <div className="bg-[#FFB8BF]/20 border border-[#FFB8BF] rounded-xl p-3 text-sm text-red-700 shadow-sm">
              Key Risk: Opponent projected ahead by {(result.opponent_projected_pts - result.my_projected_pts).toFixed(1)} points
            </div>
          )}
        </div>
      )}
    </div>
  );
}
