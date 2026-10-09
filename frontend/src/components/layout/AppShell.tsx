import { Sidebar } from "@/components/layout/Sidebar";

interface AppShellProps {
  children: React.ReactNode;
  /** When provided, "新研究" resets the session instead of a no-op link. */
  onNewResearch?: () => void;
  /** Changing this value (e.g. a finished reportId) reloads the history list. */
  historyRefreshKey?: string | null;
}

export function AppShell({ children, onNewResearch, historyRefreshKey }: AppShellProps) {
  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar onNewResearch={onNewResearch} refreshKey={historyRefreshKey} />
      <main className="flex-1 flex flex-col overflow-hidden bg-surface-800">
        {children}
      </main>
    </div>
  );
}
