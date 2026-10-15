import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  ScrollText,
  Swords,
  Cpu,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useUiStore } from '@/store/uiStore';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: <LayoutDashboard className="w-4 h-4 shrink-0" /> },
  { to: '/agent', label: 'Live Agent', icon: <Bot className="w-4 h-4 shrink-0" /> },
  { to: '/audit', label: 'Audit Log', icon: <ScrollText className="w-4 h-4 shrink-0" /> },
  { to: '/scenarios', label: 'Scenarios', icon: <Swords className="w-4 h-4 shrink-0" /> },
  { to: '/runtime', label: 'Runtime', icon: <Cpu className="w-4 h-4 shrink-0" /> },
  { to: '/policy', label: 'Policy Rules', icon: <ShieldCheck className="w-4 h-4 shrink-0" /> },
];

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUiStore();

  return (
    <aside
      className={`shrink-0 border-r border-line bg-surface flex flex-col justify-between transition-all duration-300 z-20 ${
        sidebarCollapsed ? 'w-16' : 'w-60'
      }`}
    >
      <div className="p-3 space-y-6">
        {/* Navigation list */}
        <nav className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={sidebarCollapsed ? item.label : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors select-none ${
                  isActive
                    ? 'bg-accent text-on-accent font-semibold shadow-sm'
                    : 'text-muted hover:text-ink hover:bg-raised'
                } ${sidebarCollapsed ? 'justify-center px-0' : ''}`
              }
            >
              {item.icon}
              {!sidebarCollapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Collapse footer button */}
      <div className="p-3 border-t border-line">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={`w-full flex items-center gap-2 p-2 rounded-xl text-xs text-muted hover:text-ink hover:bg-raised transition-colors ${
            sidebarCollapsed ? 'justify-center' : ''
          }`}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span>Collapse Sidebar</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
