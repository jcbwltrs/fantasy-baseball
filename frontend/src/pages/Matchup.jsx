import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectMatchup, getMatchupSchedule, saveMatchupSchedule, getLeagueTeams } from '../api/client';
import LoadingSkeleton from '../components/LoadingSkeleton';
import { useState } from 'react';

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

  const [localSchedule, setLocalSchedule] = useState(null);
  const [saving, setSaving] = useState(false);

  const schedule = localSchedule || buildScheduleFromServer(existingWeeks);

  const [saveError, setSaveError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const saveMutation = useMutation({
    mutationFn: saveMatchupSchedule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matchupSchedule'] });
      setSaving(false);
      setSaveError(null);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    },
    onError: (err) => {
      setSaving(false);
      setSaveError(err.message || 'Failed to save schedule');
      setSaveSuccess(false);
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

  const fmtDate = (d) => {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Set your opponent for each week. Projections will auto-pull both rosters from the My Roster tab.
        </p>
        <div className="flex items-center gap-3">
          <button onClick={handleSave} disabled={saving}
            className="px-4 py-1.5 rounded-lg text-sm bg-[#A3DFC4] text-[#2d2d3d] font-semibold hover:bg-[#A3DFC4]/80 disabled:opacity-50 transition shadow-sm">
            {saving ? 'Saving...' : 'Save Schedule'}
          </button>
          {saveSuccess && <span className="text-sm text-emerald-600 font-medium">Saved!</span>}
          {saveError && <span className="text-sm text-red-500">{saveError}</span>}
        </div>
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
                  const myMatchup = weekData?.matchups?.[1] || 0;

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
  const [selectedWeek, setSelectedWeek] = useState(1);
  const [window, setWindow] = useState('14d');

  const scheduleQ = useQuery({ queryKey: ['matchupSchedule'], queryFn: getMatchupSchedule });
  const teamsQ = useQuery({ queryKey: ['leagueTeams'], queryFn: getLeagueTeams });

  const teams = teamsQ.data?.teams || [];
  const existingWeeks = scheduleQ.data?.weeks || [];
  const schedule = buildScheduleFromServer(existingWeeks);

  // Find opponent for selected week
  const weekData = schedule[selectedWeek];
  const opponentId = weekData?.matchups?.[1] || 0;
  const opponentName = teams.find(t => t.team_id === opponentId)?.team_name || 'No opponent set';
  const weekInfo = SEASON_WEEKS.find(w => w.week_number === selectedWeek);

  const projectMutation = useMutation({ mutationFn: projectMatchup });

  const handleProject = () => {
    if (!weekInfo || !opponentId) return;
    projectMutation.mutate({
      week_number: selectedWeek,
      window,
      week_start: weekInfo.week_start,
      week_end: weekInfo.week_end,
    });
  };

  const result = projectMutation.data;
  const wpColor = result?.win_probability >= 0.6 ? '#059669'
    : result?.win_probability >= 0.45 ? '#d97706' : '#dc2626';

  const fmtDate = (d) => {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Week</label>
          <select value={selectedWeek} onChange={e => setSelectedWeek(parseInt(e.target.value))}
            className="bg-white border border-[#A9B8E2]/50 rounded-lg px-3 py-1.5 text-sm text-[#2d2d3d] shadow-sm">
            {SEASON_WEEKS.map(w => (
              <option key={w.week_number} value={w.week_number}>
                {w.week_label} ({fmtDate(w.week_start)} — {fmtDate(w.week_end)})
              </option>
            ))}
          </select>
        </div>
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
        <div className="flex items-center gap-3">
          <div className="text-sm">
            <span className="text-slate-400">vs </span>
            <span className={`font-semibold ${opponentId ? 'text-[#2d2d3d]' : 'text-red-400'}`}>
              {opponentId ? opponentName : 'No opponent set — save your schedule first'}
            </span>
          </div>
        </div>
        <button onClick={handleProject}
          disabled={!opponentId || projectMutation.isPending}
          className="px-4 py-1.5 rounded-lg text-sm bg-[#AACBF5] text-[#2d2d3d] font-semibold hover:bg-[#AACBF5]/80 disabled:opacity-50 transition shadow-sm">
          {projectMutation.isPending ? 'Projecting...' : 'Project Matchup'}
        </button>
      </div>

      {projectMutation.isPending && <LoadingSkeleton rows={8} cols={4} />}

      {projectMutation.isError && (
        <div className="bg-[#FFB8BF]/20 border border-[#FFB8BF] rounded-xl p-4 text-red-600 shadow-sm">
          API Error: {projectMutation.error?.message || 'Unknown error'}
        </div>
      )}

      {result?.error && (
        <div className="bg-[#FFB8BF]/20 border border-[#FFB8BF] rounded-xl p-4 text-red-600 shadow-sm">
          {result.error}
        </div>
      )}

      {/* Results */}
      {result && !result.error && (
        <div className="space-y-4">
          {/* Score cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-[#A3DFC4] p-4 text-center shadow-sm">
              <div className="text-sm text-slate-500">My Team</div>
              <div className="text-3xl font-bold text-emerald-700">{result.my_projected_pts}</div>
              <div className="text-xs text-slate-400 mt-1">{result.my_roster_count} players</div>
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
              <div className="text-sm text-slate-500">{result.opponent_name}</div>
              <div className="text-3xl font-bold text-red-500">{result.opponent_projected_pts}</div>
              <div className="text-xs text-slate-400 mt-1">{result.opp_roster_count} players</div>
            </div>
          </div>

          {/* Debug info (temporary) */}
          {result._debug && (
            <div className="bg-slate-100 rounded-xl p-3 text-xs font-mono text-slate-600 space-y-1">
              <div>ref_date: {result._debug.ref_date} | window: {result._debug.start_date} → {result._debug.end_date}</div>
              <div>MLB schedule games found: {result._debug.total_games_found} teams</div>
              <div>team_games sample: {JSON.stringify(result._debug.team_games_sample)}</div>
              <div>roster team abbrevs: {JSON.stringify(result._debug.sample_roster_teams)}</div>
            </div>
          )}

          {/* Advantage/Risk banner */}
          {result.my_projected_pts > result.opponent_projected_pts ? (
            <div className="bg-[#A3DFC4]/20 border border-[#A3DFC4] rounded-xl p-3 text-sm text-emerald-800 shadow-sm">
              Projected to win by {(result.my_projected_pts - result.opponent_projected_pts).toFixed(1)} points
            </div>
          ) : (
            <div className="bg-[#FFB8BF]/20 border border-[#FFB8BF] rounded-xl p-3 text-sm text-red-700 shadow-sm">
              Opponent projected ahead by {(result.opponent_projected_pts - result.my_projected_pts).toFixed(1)} points
            </div>
          )}

          {/* Side-by-side roster breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <RosterBreakdown title="My Team" players={result.my_players} colorClass="text-emerald-700" />
            <RosterBreakdown title={result.opponent_name} players={result.opp_players} colorClass="text-red-500" />
          </div>
        </div>
      )}
    </div>
  );
}


function RosterBreakdown({ title, players, colorClass }) {
  if (!players || players.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-slate-500 mb-2">{title}</h3>
        <div className="text-sm text-slate-400">No roster loaded. Add players in the My Roster tab.</div>
      </div>
    );
  }

  const starters = players.filter(p => p.slot !== 'BN' && p.slot !== 'IL');
  const bench = players.filter(p => p.slot === 'BN');
  const il = players.filter(p => p.slot === 'IL');

  return (
    <div className="bg-white rounded-xl border border-[#A9B8E2]/30 overflow-hidden shadow-sm">
      <div className="px-4 py-2 border-b border-[#A9B8E2]/20 bg-[#AACBF5]/10">
        <span className="text-sm font-semibold text-[#2d2d3d]">{title}</span>
        <span className="text-xs text-slate-400 ml-2">
          {starters.reduce((sum, p) => sum + p.projected, 0).toFixed(1)} projected pts
        </span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-slate-400 border-b border-[#A9B8E2]/15">
            <th className="text-left py-1 px-3 w-12">Slot</th>
            <th className="text-left px-2">Player</th>
            <th className="text-left px-2 w-10">Tm</th>
            <th className="text-right px-2 w-12">PPG</th>
            <th className="text-right px-2 w-10">G</th>
            <th className="text-right px-2 w-14">Proj</th>
          </tr>
        </thead>
        <tbody>
          {starters.map((p, i) => (
            <tr key={p.player_id} className="border-b border-[#A9B8E2]/10 hover:bg-[#AACBF5]/5">
              <td className="py-1 px-3">
                <span className="font-mono text-[10px] px-1 py-0.5 rounded bg-[#A9B8E2]/20 text-slate-500">{p.slot}</span>
              </td>
              <td className="px-2 text-[#2d2d3d] font-medium truncate max-w-[120px]">{p.player_name}</td>
              <td className="px-2 text-slate-400">{p.team}</td>
              <td className="px-2 text-right font-mono text-slate-500">{p.ppg}</td>
              <td className="px-2 text-right text-slate-400">{p.games}</td>
              <td className={`px-2 text-right font-mono font-medium ${colorClass}`}>{p.projected}</td>
            </tr>
          ))}
          {bench.length > 0 && (
            <>
              <tr><td colSpan={6} className="px-3 pt-2 pb-1 text-[10px] font-semibold text-slate-400 uppercase">Bench</td></tr>
              {bench.map(p => (
                <tr key={p.player_id} className="border-b border-[#A9B8E2]/10">
                  <td className="py-1 px-3">
                    <span className="font-mono text-[10px] px-1 py-0.5 rounded bg-slate-100 text-slate-400">BN</span>
                  </td>
                  <td className="px-2 text-slate-400">{p.player_name}</td>
                  <td className="px-2 text-slate-300">{p.team}</td>
                  <td className="px-2 text-right font-mono text-slate-300">{p.ppg}</td>
                  <td className="px-2 text-right text-slate-300">{p.games}</td>
                  <td className="px-2 text-right font-mono text-slate-300">—</td>
                </tr>
              ))}
            </>
          )}
        </tbody>
      </table>
    </div>
  );
}
