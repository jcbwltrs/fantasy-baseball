import { NavLink } from 'react-router-dom';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/waiver-wire', label: 'Waiver Wire' },
  { to: '/roster', label: 'My Roster' },
  { to: '/lineup', label: 'Lineup Optimizer' },
  { to: '/matchup', label: 'Matchup' },
  { to: '/guide', label: 'Guide' },
];

export default function Navbar() {
  return (
    <nav className="bg-[#AACBF5] border-b border-[#A9B8E2] sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center h-14 gap-1 overflow-x-auto">
          <span className="text-[#2d2d3d] font-bold text-lg mr-4 whitespace-nowrap">
            Fantasy Baseball
          </span>
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                  isActive
                    ? 'bg-white/50 text-[#2d2d3d] font-semibold'
                    : 'text-[#2d2d3d]/70 hover:text-[#2d2d3d] hover:bg-white/30'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
