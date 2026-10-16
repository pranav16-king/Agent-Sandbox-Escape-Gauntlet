import React, { useMemo, useRef, useState } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Search, Download, Filter, Trash2 } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { useUiStore } from '@/store/uiStore';
import { api } from '@/api/rest';
import { DecisionBadge } from '@/components/DecisionBadge';
import { HashChip } from '@/components/HashChip';
import { Decision } from '@/api/types';

export const LogTable: React.FC<{ maxHeight?: string }> = ({ maxHeight = 'h-[360px]' }) => {
  const auditLogs = useLiveStore((s) => s.auditLogs);
  const clearLogs = useLiveStore((s) => s.clearLogs);
  const [isClearing, setIsClearing] = useState(false);
  const {
    filterKind,
    setFilterKind,
    filterTool,
    setFilterTool,
    searchQuery,
    setSearchQuery,
    openDrawer,
    selectedAuditId,
  } = useUiStore();

  const handleClear = async () => {
    if (!window.confirm('Are you sure you want to clear all audit records and reset the ledger?')) {
      return;
    }
    setIsClearing(true);
    try {
      await api.clearAuditLogs();
      clearLogs();
    } catch (err) {
      console.error('Failed to clear audit ledger:', err);
    } finally {
      setIsClearing(false);
    }
  };

  const parentRef = useRef<HTMLDivElement>(null);

  // Filter logs based on kind, tool, search
  const filteredLogs = useMemo(() => {
    return auditLogs.filter((entry) => {
      if (filterKind !== 'all' && entry.decision !== filterKind) return false;
      if (filterTool !== 'all' && entry.tool !== filterTool) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesArgs = entry.args?.toLowerCase().includes(q);
        const matchesReason = entry.reason?.toLowerCase().includes(q);
        const matchesRule = entry.rule_id?.toLowerCase().includes(q);
        const matchesSource = entry.source?.toLowerCase().includes(q);
        if (!matchesArgs && !matchesReason && !matchesRule && !matchesSource) return false;
      }
      return true;
    });
  }, [auditLogs, filterKind, filterTool, searchQuery]);

  const rowVirtualizer = useVirtualizer({
    count: filteredLogs.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 10,
  });

  const exportCsv = () => {
    if (filteredLogs.length === 0) return;
    const headers = ['id', 'ts', 'tool', 'source', 'decision', 'rule_id', 'args', 'reason', 'hash', 'prev_hash'];
    const rows = filteredLogs.map((e) => [
      e.id,
      `"${e.ts}"`,
      e.tool,
      e.source,
      e.decision,
      `"${e.rule_id}"`,
      `"${(e.args || '').replace(/"/g, '""')}"`,
      `"${(e.reason || '').replace(/"/g, '""')}"`,
      `"${e.hash}"`,
      `"${e.prev_hash}"`,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `sandboxx_audit_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const chips: { id: 'all' | Decision; label: string }[] = [
    { id: 'all', label: 'All Events' },
    { id: 'allow', label: 'Allowed' },
    { id: 'block', label: 'Blocked' },
    { id: 'ask', label: 'Human-in-the-Loop' },
  ];

  return (
    <div className="flex flex-col h-full rounded-card border border-line bg-surface overflow-hidden">
      {/* Controls Bar */}
      <div className="p-3 border-b border-line flex flex-wrap items-center justify-between gap-3 bg-raised/30">
        <div className="flex items-center gap-1.5 flex-wrap">
          {chips.map((chip) => {
            const active = filterKind === chip.id;
            return (
              <button
                key={chip.id}
                type="button"
                onClick={() => setFilterKind(chip.id)}
                className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors select-none ${
                  active
                    ? 'bg-accent text-on-accent font-semibold shadow-sm'
                    : 'bg-surface hover:bg-raised text-muted hover:text-ink border border-line'
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2 flex-1 justify-end min-w-[280px]">
          {/* Tool selector */}
          <div className="relative">
            <select
              value={filterTool}
              onChange={(e) => setFilterTool(e.target.value)}
              aria-label="Filter by tool"
              className="text-xs bg-surface border border-line rounded-lg px-2.5 py-1.5 text-ink focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
            >
              <option value="all">All Tools</option>
              <option value="shell">Shell</option>
              <option value="file">File</option>
              <option value="http">HTTP</option>
            </select>
          </div>

          {/* Search box */}
          <div className="relative flex-1 max-w-xs">
            <Search className="w-3.5 h-3.5 text-muted absolute left-2.5 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Search command, rule, or reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-surface border border-line rounded-lg text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
            />
          </div>

          {/* Export CSV */}
          <button
            type="button"
            onClick={exportCsv}
            disabled={filteredLogs.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-line bg-surface hover:bg-raised text-ink transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Export filtered logs to CSV"
          >
            <Download className="w-3.5 h-3.5 text-muted" />
            <span className="hidden sm:inline">Export</span>
          </button>

          {/* Clear Logs */}
          <button
            type="button"
            onClick={handleClear}
            disabled={isClearing || auditLogs.length === 0}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-line bg-surface hover:bg-block-bg/20 text-muted hover:text-block transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Clear all audit logs from database and reset ledger"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{isClearing ? 'Clearing...' : 'Clear'}</span>
          </button>
        </div>
      </div>

      {/* Accessible live region for screen readers */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {filteredLogs.length > 0 && `Showing ${filteredLogs.length} audit entries.`}
      </div>

      {/* Table Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 px-3 py-2 border-b border-line bg-raised/50 text-[11px] font-semibold text-muted tracking-wider uppercase select-none">
          <div className="col-span-1">ID</div>
          <div className="col-span-2">Time</div>
          <div className="col-span-2">Decision</div>
          <div className="col-span-1">Tool</div>
          <div className="col-span-3">Command / Args</div>
          <div className="col-span-2">Rule / Reason</div>
          <div className="col-span-1 text-right">Hash</div>
        </div>

        {/* Virtualized Body */}
        <div ref={parentRef} className={`flex-1 overflow-auto ${maxHeight}`}>
          {filteredLogs.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center text-muted text-xs">
              <Filter className="w-8 h-8 mb-2 opacity-40" />
              <span>No tool calls match current filter criteria.</span>
            </div>
          ) : (
            <div
              style={{
                height: `${rowVirtualizer.getTotalSize()}px`,
                width: '100%',
                position: 'relative',
              }}
            >
              {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                const entry = filteredLogs[virtualRow.index];
                const isSelected = selectedAuditId === entry.id;

                const rowBg = entry.decision === 'block'
                  ? 'bg-block-bg/40 hover:bg-block-bg/70'
                  : entry.decision === 'ask'
                  ? 'bg-ask-bg/40 hover:bg-ask-bg/70'
                  : 'hover:bg-raised/60';

                return (
                  <div
                    key={entry.id}
                    onClick={() => openDrawer(entry.id)}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${virtualRow.size}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                    }}
                    className={`grid grid-cols-12 gap-2 px-3 items-center text-xs font-mono border-b border-line/50 cursor-pointer transition-colors ${rowBg} ${
                      isSelected ? 'ring-1 ring-accent bg-raised' : ''
                    }`}
                  >
                    <div className="col-span-1 text-muted font-bold truncate">#{entry.id}</div>
                    <div className="col-span-2 text-muted truncate">
                      {new Date(entry.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </div>
                    <div className="col-span-2">
                      <DecisionBadge decision={entry.decision} size="sm" />
                    </div>
                    <div className="col-span-1 uppercase text-ink font-semibold truncate">{entry.tool}</div>
                    <div className="col-span-3 text-ink truncate font-mono" title={entry.args}>
                      {entry.args || '—'}
                    </div>
                    <div className="col-span-2 text-muted truncate" title={entry.reason}>
                      <span className="text-accent mr-1 font-semibold">{entry.rule_id}</span>
                      {entry.reason}
                    </div>
                    <div className="col-span-1 flex justify-end">
                      <HashChip hash={entry.hash} truncateLength={4} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
