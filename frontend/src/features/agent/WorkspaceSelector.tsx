import React, { useState, useEffect } from 'react';
import { 
  Folder, 
  FolderGit2, 
  CheckCircle2, 
  ShieldAlert, 
  FolderOpen, 
  HardDrive, 
  FileCode, 
  FileText, 
  X, 
  CornerLeftUp,
  FileCheck
} from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { api } from '@/api/rest';
import { WorkspaceBrowseResult } from '@/api/types';

export const WorkspaceSelector: React.FC = () => {
  const workspace = useLiveStore((s) => s.workspace);
  const setWorkspaceInfo = useLiveStore((s) => s.setWorkspaceInfo);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [showFileTree, setShowFileTree] = useState(false);
  const [folderInput, setFolderInput] = useState(workspace?.path || '');
  const [browseData, setBrowseData] = useState<WorkspaceBrowseResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Sync input when workspace changes
  useEffect(() => {
    if (workspace?.path) {
      setFolderInput(workspace.path);
    }
  }, [workspace?.path]);

  const loadBrowsePath = async (targetPath?: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.browseWorkspace(targetPath);
      setBrowseData(data);
      if (targetPath) {
        setFolderInput(data.current_path);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to browse filesystem directory');
    } finally {
      setIsLoading(false);
    }
  };

  const openPickerModal = () => {
    setIsModalOpen(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    loadBrowsePath(workspace?.path || undefined);
  };

  const handleApplyWorkspace = async (targetPathToApply?: string) => {
    const pathToUse = (targetPathToApply || folderInput).trim();
    if (!pathToUse) {
      setErrorMsg('Please specify a valid folder path.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await api.setWorkspace(pathToUse);
      if (res.ok && res.workspace) {
        setWorkspaceInfo(res.workspace);
        setSuccessMsg(`Project workspace locked to: ${res.workspace.name}`);
        setTimeout(() => {
          setIsModalOpen(false);
          setSuccessMsg(null);
        }, 800);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to set active project workspace');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rounded-card border border-line bg-surface overflow-hidden">
      {/* Top Banner Bar */}
      <div className="p-3.5 flex flex-wrap items-center justify-between gap-3 bg-raised/30 border-b border-line">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center shrink-0 text-accent">
            <FolderGit2 className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">
                Active Project Workspace
              </span>
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-allow-bg text-allow border border-allow/30">
                <CheckCircle2 className="w-3 h-3" />
                Confined Boundary
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5 truncate">
              <span className="text-xs font-bold text-ink truncate font-mono">
                {workspace?.name || 'Project Workspace'}
              </span>
              <span className="text-[11px] text-muted truncate font-mono hidden sm:inline" title={workspace?.path}>
                ({workspace?.path || '/workspace'})
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setShowFileTree(!showFileTree)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
              showFileTree
                ? 'bg-accent text-on-accent border-accent'
                : 'bg-surface hover:bg-raised text-ink border-line'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>{showFileTree ? 'Hide Files' : `Files (${workspace?.file_count ?? 0})`}</span>
          </button>

          <button
            type="button"
            onClick={openPickerModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-surface hover:bg-raised text-ink border border-line hover:border-accent transition-colors shadow-sm"
          >
            <FolderOpen className="w-3.5 h-3.5 text-accent" />
            <span>Select Folder</span>
          </button>
        </div>
      </div>

      {/* Expandable Workspace File List */}
      {showFileTree && (
        <div className="p-3 bg-raised/20 border-b border-line text-xs font-mono">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-line/60 text-muted text-[11px]">
            <span>Files allowed for AI agent in this project:</span>
            <span>{workspace?.files?.length || 0} top-level entries</span>
          </div>
          {(!workspace?.files || workspace.files.length === 0) ? (
            <div className="py-4 text-center text-muted">
              No files detected or workspace is empty.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-48 overflow-y-auto pr-1">
              {workspace.files.map((f, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 p-1.5 rounded-md bg-surface border border-line/60 truncate"
                  title={`${f.name} (${f.type})`}
                >
                  {f.type === 'directory' ? (
                    <Folder className="w-3.5 h-3.5 text-accent shrink-0" />
                  ) : (
                    <FileText className="w-3.5 h-3.5 text-muted shrink-0" />
                  )}
                  <span className="truncate text-ink text-[11px]">{f.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Select Project Folder Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-xl rounded-card border border-line bg-surface p-5 shadow-2xl space-y-4 font-sans">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-5 h-5 text-accent" />
                <h3 className="text-sm font-bold text-ink">Select Project Folder for AI Agent</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 text-muted hover:text-ink rounded-lg transition-colors"
                aria-label="Close folder selector modal"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Choose the exact project folder on your machine. The AI agent and Host Security Gateway
              will strictly confine all tool calls (file reading, writing, command execution) to this project directory.
            </p>

            {/* Quick Presets */}
            <div className="space-y-1.5">
              <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">
                Quick Select:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleApplyWorkspace('D:/Agent Sandbox Escape Gauntlet')}
                  className="px-2.5 py-1 text-xs font-mono rounded-lg bg-raised hover:bg-surface border border-line text-ink transition-colors flex items-center gap-1.5"
                >
                  <HardDrive className="w-3 h-3 text-accent" />
                  <span>Agent Sandbox Escape Gauntlet</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyWorkspace('/workspace')}
                  className="px-2.5 py-1 text-xs font-mono rounded-lg bg-raised hover:bg-surface border border-line text-ink transition-colors flex items-center gap-1.5"
                >
                  <HardDrive className="w-3 h-3 text-accent" />
                  <span>Default Container /workspace</span>
                </button>
              </div>
            </div>

            {/* Path Input Form */}
            <div className="space-y-1.5">
              <label htmlFor="folder-input" className="text-[11px] font-semibold text-muted uppercase tracking-wider">
                Custom Folder Path:
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="folder-input"
                  type="text"
                  value={folderInput}
                  onChange={(e) => setFolderInput(e.target.value)}
                  placeholder="e.g. D:/MyProjects/FullstackApp"
                  className="flex-1 px-3 py-2 text-xs font-mono bg-raised/50 border border-line rounded-lg text-ink placeholder:text-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
                />
                <button
                  type="button"
                  onClick={() => handleApplyWorkspace()}
                  disabled={isLoading || !folderInput.trim()}
                  className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-accent text-on-accent hover:opacity-90 transition-opacity disabled:opacity-50 shrink-0"
                >
                  {isLoading ? 'Setting...' : 'Set Active'}
                </button>
              </div>
            </div>

            {/* Directory Navigation Explorer */}
            {browseData && (
              <div className="space-y-2 border border-line rounded-lg p-3 bg-raised/20">
                <div className="flex items-center justify-between text-xs font-mono text-muted">
                  <div className="flex items-center gap-1.5 truncate">
                    <span className="font-semibold text-ink">Browsing:</span>
                    <span className="truncate" title={browseData.current_path}>{browseData.current_path}</span>
                  </div>
                  {browseData.parent_path && (
                    <button
                      type="button"
                      onClick={() => loadBrowsePath(browseData.parent_path!)}
                      className="flex items-center gap-1 text-[11px] text-accent hover:underline shrink-0"
                    >
                      <CornerLeftUp className="w-3 h-3" />
                      <span>Up</span>
                    </button>
                  )}
                </div>

                <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
                  {browseData.directories.length === 0 ? (
                    <div className="text-xs text-muted py-2 text-center">No subdirectories found.</div>
                  ) : (
                    browseData.directories.map((dir, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-1.5 rounded hover:bg-surface border border-transparent hover:border-line text-xs font-mono cursor-pointer transition-colors"
                        onClick={() => loadBrowsePath(dir.path)}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <Folder className="w-3.5 h-3.5 text-accent shrink-0" />
                          <span className="truncate text-ink">{dir.name}</span>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleApplyWorkspace(dir.path);
                          }}
                          className="px-2 py-0.5 text-[10px] font-sans font-semibold rounded bg-accent/20 hover:bg-accent text-accent hover:text-on-accent transition-colors"
                        >
                          Select
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Error or Success notification */}
            {errorMsg && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-block-bg text-block border border-block/30 text-xs font-mono">
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}
            {successMsg && (
              <div className="flex items-center gap-2 p-2.5 rounded-lg bg-allow-bg text-allow border border-allow/30 text-xs font-mono">
                <FileCheck className="w-4 h-4 shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* Security Guarantee Note */}
            <div className="p-2.5 rounded-lg bg-raised/40 border border-line text-[11px] text-muted flex items-start gap-2">
              <span className="text-allow font-bold">🛡️</span>
              <span>
                <strong>Hard Boundary Guarantee:</strong> The Host Gateway policy engine rejects all commands, path traversals (<code>..</code>), and file operations attempting to reach files outside this chosen directory.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
