import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-dvh overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden bg-surface-800">
        {children}
      </main>
    </div>
  );
}
