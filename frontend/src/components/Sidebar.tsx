import React, { useEffect } from 'react';
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
  const { sidebarCollapsed, toggleSidebar, setSidebarCollapsed } = useUiStore();

  useEffect(() => {
    // Auto-collapse below 1280px per design system spec
    if (window.innerWidth < 1280) {
      setSidebarCollapsed(true);
    }
  }, [setSidebarCollapsed]);

  return (
    <>
      {/* Mobile backdrop */}
      {!sidebarCollapsed && (
        <div
          role="presentation"
          aria-hidden="true"
          onClick={() => setSidebarCollapsed(true)}
          className="fixed inset-0 top-14 bg-black/40 backdrop-blur-xs z-30 lg:hidden"
        />
      )}

      <aside
        className={`fixed lg:static top-14 lg:top-auto bottom-0 left-0 z-40 lg:z-20 h-[calc(100vh-3.5rem)] lg:h-full shrink-0 border-r border-line bg-surface flex flex-col justify-between transition-all duration-300 shadow-xl lg:shadow-none ${
          sidebarCollapsed
            ? '-translate-x-full lg:translate-x-0 lg:w-16'
            : 'translate-x-0 w-60'
        }`}
      >
        <div className="p-3 space-y-6 overflow-y-auto min-h-0 flex-1">
          {/* Navigation list */}
          <nav className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                title={sidebarCollapsed ? item.label : undefined}
                onClick={() => {
                  if (window.innerWidth < 1024) {
                    setSidebarCollapsed(true);
                  }
                }}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-colors select-none ${
                    isActive
                      ? 'bg-accent text-on-accent font-semibold shadow-sm'
                      : 'text-muted hover:text-ink hover:bg-raised'
                  } ${sidebarCollapsed ? 'lg:justify-center lg:px-0' : ''}`
                }
              >
                {item.icon}
                <span className={`truncate ${sidebarCollapsed ? 'lg:hidden' : ''}`}>
                  {item.label}
                </span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* Collapse footer button */}
        <div className="p-3 border-t border-line shrink-0">
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
    </>
  );
};
