import React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Palette, Check, Sun, Moon, Sparkles, Monitor } from 'lucide-react';
import { useTheme, ThemeName } from '@/theme/ThemeProvider';

const THEMES: { id: ThemeName; name: string; icon: React.ReactNode; preview: { surface: string; text: string; accent: string } }[] = [
  {
    id: 'light',
    name: 'Light (Warm)',
    icon: <Sun className="w-4 h-4" />,
    preview: { surface: '#FFFFFF', text: '#1C1B18', accent: '#F2B705' },
  },
  {
    id: 'dark',
    name: 'Dark (Charcoal)',
    icon: <Moon className="w-4 h-4" />,
    preview: { surface: '#1A1D1C', text: '#E8ECE9', accent: '#E3B341' },
  },
  {
    id: 'black',
    name: 'Black (High Contrast)',
    icon: <Sparkles className="w-4 h-4" />,
    preview: { surface: '#0B0B0B', text: '#F5F5F5', accent: '#FFFFFF' },
  },
  {
    id: 'grey',
    name: 'Grey (Low Glare)',
    icon: <Monitor className="w-4 h-4" />,
    preview: { surface: '#ECEEEE', text: '#1F2325', accent: '#2F3437' },
  },
];

export const ThemeSwitcher: React.FC = () => {
  const { theme, setTheme } = useTheme();

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          aria-label="Select color theme"
          className="flex items-center gap-2 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-line bg-surface hover:bg-raised text-ink transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <Palette className="w-3.5 h-3.5 text-muted" />
          <span className="capitalize">{theme}</span>
        </button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="end"
          sideOffset={6}
          className="z-50 w-56 rounded-xl border border-line bg-surface p-1.5 shadow-xl text-ink animate-in fade-in-50 zoom-in-95"
        >
          <div className="px-2 py-1.5 text-[11px] font-semibold text-muted tracking-wider uppercase">
            Color Theme
          </div>

          {THEMES.map((t) => {
            const isSelected = theme === t.id;
            return (
              <DropdownMenu.Item
                key={t.id}
                onSelect={() => setTheme(t.id)}
                className={`flex items-center justify-between px-2.5 py-2 text-xs rounded-lg cursor-pointer outline-none transition-colors select-none ${
                  isSelected ? 'bg-raised font-semibold text-ink' : 'hover:bg-raised/70 text-ink'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-muted">{t.icon}</span>
                  <span>{t.name}</span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-0.5 p-0.5 rounded border border-line" style={{ background: t.preview.surface }}>
                    <div className="w-2 h-2 rounded-full" style={{ background: t.preview.accent }} />
                    <div className="w-2 h-2 rounded-full" style={{ background: t.preview.text }} />
                  </div>
                  {isSelected && <Check className="w-3.5 h-3.5 text-accent" />}
                </div>
              </DropdownMenu.Item>
            );
          })}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};
