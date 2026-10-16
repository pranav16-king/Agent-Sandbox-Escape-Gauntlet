import { create } from 'zustand';

interface UiState {
  selectedAuditId: number | null;
  isDrawerOpen: boolean;
  sidebarCollapsed: boolean;
  filterKind: 'all' | 'allow' | 'block' | 'ask';
  filterTool: string;
  searchQuery: string;
  showSandboxConfirm: boolean;
  
  openDrawer: (id: number) => void;
  closeDrawer: () => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (v: boolean) => void;
  setFilterKind: (k: 'all' | 'allow' | 'block' | 'ask') => void;
  setFilterTool: (t: string) => void;
  setSearchQuery: (q: string) => void;
  setShowSandboxConfirm: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  selectedAuditId: null,
  isDrawerOpen: false,
  sidebarCollapsed: false,
  filterKind: 'all',
  filterTool: 'all',
  searchQuery: '',
  showSandboxConfirm: false,

  openDrawer: (id: number) => set({ selectedAuditId: id, isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false, selectedAuditId: null }),
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: (v: boolean) => set({ sidebarCollapsed: v }),
  setFilterKind: (filterKind) => set({ filterKind }),
  setFilterTool: (filterTool) => set({ filterTool }),
  setSearchQuery: (searchQuery) => set({ searchQuery }),
  setShowSandboxConfirm: (showSandboxConfirm) => set({ showSandboxConfirm }),
}));
