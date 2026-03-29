const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// Status
export const getHealth = () => request('/health');
export const getStatus = () => request('/status');
export const triggerRefresh = () => request('/refresh', { method: 'POST' });

// Players
export const getAvailablePlayers = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return request(`/players/available?${qs}`);
};
export const searchPlayers = (q) => request(`/players/search?q=${encodeURIComponent(q)}`);
export const getPlayerDetail = (id) => request(`/players/${id}`);
export const getRunSupportRankings = () => request('/players/run-support/rankings');

// Roster — multi-team
export const getLeagueTeams = () => request('/roster/teams');
export const renameLeagueTeam = (teamId, name) => request(`/roster/teams/${teamId}`, { method: 'PUT', body: JSON.stringify({ team_name: name }) });
export const getRoster = (leagueTeamId = 1) => request(`/roster/?league_team_id=${leagueTeamId}`);
export const addToRoster = (data) => request('/roster/add', { method: 'POST', body: JSON.stringify(data) });
export const bulkAddToRoster = (data) => request('/roster/bulk-add', { method: 'POST', body: JSON.stringify(data) });
export const dropFromRoster = (data) => request('/roster/drop', { method: 'POST', body: JSON.stringify(data) });
export const moveRosterSlot = (data) => request('/roster/move', { method: 'POST', body: JSON.stringify(data) });
export const getAvailableSlots = (leagueTeamId = 1) => request(`/roster/available-slots?league_team_id=${leagueTeamId}`);
export const uploadRosterCsv = async (file, leagueTeamId = 1) => {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/roster/upload-csv?league_team_id=${leagueTeamId}`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload error: ${res.status}`);
  return res.json();
};
export const confirmCsvUpload = (players, leagueTeamId = 1) => request(`/roster/upload-csv/confirm?league_team_id=${leagueTeamId}`, { method: 'POST', body: JSON.stringify(players) });
export const getDropCandidates = (window = '14d', leagueTeamId = 1) => request(`/roster/drop-candidates?window=${window}&league_team_id=${leagueTeamId}`);

// Lineup
export const optimizeLineup = (data) => request('/lineup/optimize', { method: 'POST', body: JSON.stringify(data) });

// Matchup
export const projectMatchup = (data) => request('/matchup/project', { method: 'POST', body: JSON.stringify(data) });
export const getMatchupSchedule = () => request('/matchup/schedule');
export const saveMatchupSchedule = (matchups) => request('/matchup/schedule', { method: 'POST', body: JSON.stringify({ matchups }) });
export const getMyWeekMatchup = (weekNumber) => request(`/matchup/schedule/my-week?week_number=${weekNumber}`);
