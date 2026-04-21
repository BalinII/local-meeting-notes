import { StatusCard } from "./StatusCard";

type Section = {
  title: string;
  description: string;
  status: string;
};

type AppShellProps = {
  sections: Section[];
};

export function AppShell({ sections }: AppShellProps) {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Windows Local-First Desktop Scaffold</p>
        <h1>Local Meeting Notes</h1>
        <p className="hero-copy">
          Phase 1 provides structure only: a Tauri shell, Python backend layout,
          local storage paths, and placeholder workflow modules.
        </p>
      </section>

      <section className="grid">
        {sections.map((section) => (
          <StatusCard key={section.title} {...section} />
        ))}
      </section>
    </main>
  );
}
