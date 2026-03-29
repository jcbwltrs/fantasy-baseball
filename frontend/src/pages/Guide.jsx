export default function Guide() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold text-[#2d2d3d]">How to Use This Tool</h1>
      <p className="text-slate-500 text-sm">
        A step-by-step guide to getting the most out of the Fantasy Baseball Optimizer for your 10-team Yahoo H2H Points league.
      </p>

      {/* Getting Started */}
      <Section title="1. Initial Setup">
        <ol className="list-decimal list-inside space-y-2 text-slate-600 text-sm">
          <li>
            <strong className="text-[#2d2d3d]">Refresh Data</strong> — Click the <Pill>Refresh Data</Pill> button on the
            Dashboard. This pulls all MLB player stats, game logs, and team run support data from the MLB Stats API.
            The initial load takes a few minutes (780+ players).
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Name Your Teams</strong> — Go to <Pill>My Roster</Pill> and click the pencil
            icon on each team tab to rename them to match your Yahoo league (e.g. "My Team", "Josh's Squad", etc.).
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Load Your Roster</strong> — For your team (Team 1), either:
            <ul className="list-disc list-inside ml-4 mt-1 space-y-1 text-slate-500">
              <li>Upload a Yahoo CSV export via <Pill>Upload Yahoo CSV</Pill></li>
              <li>Use the <Pill>Add Player</Pill> tab to search and add players one-by-one, picking the correct roster slot</li>
            </ul>
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Load Opponent Rosters</strong> — Switch to each opponent's team tab (Team 2-10)
            and add their players the same way. This enables accurate waiver wire analysis since rostered players across
            ALL teams are excluded from the available player pool.
          </li>
        </ol>
      </Section>

      {/* Roster Management */}
      <Section title="2. Managing Your Roster">
        <div className="space-y-3 text-sm text-slate-600">
          <Item label="Slot Assignment">
            When adding a player, click <Pill>Add</Pill> to see available roster slots (C, 1B, 2B, etc.).
            Pick the correct slot — the system enforces slot limits (e.g. 3 OF spots, 5 BN spots).
          </Item>
          <Item label="Moving Players">
            Click <Pill>Move</Pill> next to any player to see available slots. Click a slot to reassign them.
            Use this to move players between starting positions and bench.
          </Item>
          <Item label="Dropping Players">
            Click <Pill>Drop</Pill> to remove a player. They'll return to the waiver wire pool.
          </Item>
          <Item label="Weekly Acquisition Limit">
            During the season, you're limited to 6 adds per week (resets Monday). This limit is not enforced
            while building your initial roster (under 20 players).
          </Item>
          <Item label="Shohei Ohtani">
            Ohtani appears as two separate entries — "Shohei Ohtani (B)" for batting and "Shohei Ohtani (P)" for
            pitching. Each can be on a different team's roster.
          </Item>
        </div>
      </Section>

      {/* Waiver Wire */}
      <Section title="3. Waiver Wire">
        <div className="space-y-3 text-sm text-slate-600">
          <Item label="Time Windows">
            Use 3D/7D/14D/30D/Season to see player performance over different periods. Short windows (3D, 7D)
            surface hot streaks; longer windows (30D, Season) show consistency.
          </Item>
          <Item label="Pitcher Win-Adjusted PPG">
            Pitchers are automatically ranked by win-adjusted points per game. Pitchers on teams with elite run
            support (S/A tier) get a boost because the 10-point Win bonus is more likely.
          </Item>
          <Item label="Run Support Badges">
            Colored badges (S, A, B, C, D) next to pitcher names indicate their team's offensive support tier.
            S-tier (green) = elite, D-tier (red) = poor. Hover for details.
          </Item>
          <Item label="A+ Run Support Filter">
            Check the "A+ RS only" box to filter to pitchers on S or A-tier run support teams — these have
            the highest Win upside.
          </Item>
          <Item label="Position Filter">
            Filter by position to find specific needs. "ALL" shows all available players.
          </Item>
        </div>
      </Section>

      {/* Drop Candidates */}
      <Section title="4. Drop Candidates">
        <div className="space-y-3 text-sm text-slate-600">
          <p>
            The Drop Candidates tab on My Roster analyzes your roster and finds your weakest players compared to
            what's available on waivers.
          </p>
          <Item label="Recommendations">
            <span className="text-red-500 font-medium">DROP</span> = a significantly better replacement exists (2+ PPG upgrade).{' '}
            <span className="text-amber-600 font-medium">CONSIDER</span> = marginal upgrade available.{' '}
            <span className="text-emerald-700 font-medium">HOLD</span> = no better option or pitcher has strong run support.
          </Item>
          <Item label="Run Support Override">
            Pitchers with S or A-tier run support will be marked HOLD even if a replacement scores more raw points,
            because Win premium (10 pts) makes them more valuable than stats alone suggest.
          </Item>
        </div>
      </Section>

      {/* Matchup */}
      <Section title="5. Matchup Schedule & Projections">
        <div className="space-y-3 text-sm text-slate-600">
          <Item label="Season Schedule">
            Go to <Pill>Matchups → Season Schedule</Pill> and set your opponent for each of the 26 weeks. Week 1
            is a short week (Wed-Sun), then all following weeks run Monday through Sunday.
            Use the dropdown to pick which team you're playing. Click <Pill>Save Schedule</Pill> when done.
          </Item>
          <Item label="Project Matchup">
            Switch to <Pill>Project Matchup</Pill>, set the week dates, add your opponent's players, and click
            Project. You'll see point projections and a win probability percentage.
          </Item>
          <Item label="Win Probability">
            Uses a normal CDF model with 18% standard deviation to estimate your chance of winning.
            Green (60%+) = favorable, Yellow (45-60%) = toss-up, Red (&lt;45%) = underdog.
          </Item>
        </div>
      </Section>

      {/* Lineup Optimizer */}
      <Section title="6. Lineup Optimizer">
        <div className="space-y-3 text-sm text-slate-600">
          <p>
            The Lineup Optimizer picks your best starting lineup for a given week based on recent performance,
            the MLB schedule (games per team that week), and pitcher win projections.
          </p>
          <Item label="How It Works">
            It uses a greedy algorithm: assigns your best players to their most valuable eligible slots,
            prioritizing specific positions first (C, 1B, etc.), then flex slots (OF, Util, P).
            Pitchers get WPPS-adjusted projections that account for run support.
          </Item>
          <Item label="Performance Window">
            Choose how far back to look for player performance. 14D is a good default balance between
            recency and sample size.
          </Item>
        </div>
      </Section>

      {/* Scoring Reference */}
      <Section title="7. Scoring Reference">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-[#2d2d3d] font-medium text-sm mb-2">Batter Scoring</h4>
            <table className="w-full text-xs">
              <tbody className="text-slate-600">
                {[
                  ['Run (R)', '+1'], ['Single (1B)', '+1'], ['Double (2B)', '+2'],
                  ['Triple (3B)', '+3'], ['Home Run (HR)', '+4'], ['RBI', '+1'],
                  ['Sac Bunt (SH)', '+0.25'], ['Stolen Base (SB)', '+1'], ['Caught Stealing (CS)', '-0.5'],
                  ['Walk (BB)', '+1'], ['Hit by Pitch (HBP)', '+1'], ['Strikeout (K)', '-0.5'],
                  ['GIDP', '-1'], ['Cycle', '+2'], ['Grand Slam Bonus', '+1'],
                ].map(([stat, pts]) => (
                  <tr key={stat} className="border-b border-[#A9B8E2]/15">
                    <td className="py-1 px-2">{stat}</td>
                    <td className={`py-1 px-2 text-right font-mono ${pts.startsWith('+') ? 'text-emerald-700' : 'text-red-500'}`}>{pts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <h4 className="text-[#2d2d3d] font-medium text-sm mb-2">Pitcher Scoring</h4>
            <table className="w-full text-xs">
              <tbody className="text-slate-600">
                {[
                  ['Appearance (APP)', '+0.5'], ['Inning Pitched (IP)', '+1.3'], ['Win (W)', '+10'],
                  ['Loss (L)', '-5'], ['Complete Game (CG)', '+2'], ['Save (SV)', '+8'],
                  ['Hit Allowed (H)', '-0.25'], ['Earned Run (ER)', '-1'], ['HR Allowed', '-0.25'],
                  ['Walk Allowed (BB)', '-0.25'], ['HBP Allowed', '-0.25'], ['Strikeout (K)', '+1.4'],
                  ['GIDP Induced', '+0.5'], ['Hold (HLD)', '+6'], ['Blown Save (BSV)', '-3'],
                ].map(([stat, pts]) => (
                  <tr key={stat} className="border-b border-[#A9B8E2]/15">
                    <td className="py-1 px-2">{stat}</td>
                    <td className={`py-1 px-2 text-right font-mono ${pts.startsWith('+') ? 'text-emerald-700' : 'text-red-500'}`}>{pts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </Section>

      {/* Roster Slots */}
      <Section title="8. Roster Positions">
        <div className="text-sm text-slate-600">
          <p className="mb-2">20 roster spots per team:</p>
          <div className="flex flex-wrap gap-2">
            {['C', '1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'Util', 'SP', 'RP', 'P', 'P', 'P', 'BN', 'BN', 'BN', 'BN', 'BN', 'IL'].map((s, i) => (
              <span key={`${s}-${i}`} className="px-2 py-1 rounded bg-[#A9B8E2]/20 text-slate-600 text-xs font-mono font-medium">{s}</span>
            ))}
          </div>
          <p className="mt-2 text-slate-400 text-xs">
            Batters: C, 1B, 2B, 3B, SS, 3×OF, Util. Pitchers: SP, RP, 3×P. Bench: 5×BN. Injured: 1×IL.
          </p>
        </div>
      </Section>

      {/* Tips */}
      <Section title="9. Pro Tips">
        <ul className="list-disc list-inside space-y-2 text-sm text-slate-600">
          <li>
            <strong className="text-[#2d2d3d]">Pitcher Wins are king</strong> — At 10 points each, a pitcher on an
            S-tier offense (NYY, LAD) who gets 1 extra win per month is worth ~2.5 PPG more than their raw stats suggest.
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Check the Hot Players widget daily</strong> — The 3-day window on the
            Dashboard surfaces streaking players before everyone else notices.
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Don't roster D-tier pitchers unless elite</strong> — A pitcher on a
            bottom-5 offense needs to be exceptional (top-10 K rate, sub-3.00 ERA) to overcome the Win drought.
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Data refreshes every 6 hours</strong> — Or click Refresh Data manually.
            Stats come from the MLB Stats API and include all 2026 regular season data.
          </li>
          <li>
            <strong className="text-[#2d2d3d]">Load all 10 rosters</strong> — The tool works best when all rosters are
            entered. The waiver wire becomes truly accurate when it knows which players are actually available.
          </li>
        </ul>
      </Section>
    </div>
  );
}


function Section({ title, children }) {
  return (
    <div className="bg-white rounded-xl border border-[#A9B8E2]/30 p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-[#2d2d3d] mb-3">{title}</h2>
      {children}
    </div>
  );
}

function Item({ label, children }) {
  return (
    <div>
      <span className="text-[#2d2d3d] font-medium">{label}:</span>{' '}
      <span className="text-slate-500">{children}</span>
    </div>
  );
}

function Pill({ children }) {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded bg-[#AACBF5]/30 text-[#4a6fa5] text-xs font-mono font-medium">
      {children}
    </span>
  );
}
