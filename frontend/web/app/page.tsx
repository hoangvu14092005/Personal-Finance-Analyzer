export default function Home() {
  return (
    <section className="space-y-8">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-[0.15em] text-teal-700">
          Phase 0.2
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Frontend Foundation Is Ready
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
          This app is initialized with Next.js 15 App Router, TypeScript, and
          Tailwind CSS using pnpm. It is the starting point for the Personal
          Finance Analyzer UI.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Framework</h2>
          <p className="mt-2 text-sm text-slate-600">Next.js 15 App Router</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Language</h2>
          <p className="mt-2 text-sm text-slate-600">TypeScript enabled</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-slate-900">Styling</h2>
          <p className="mt-2 text-sm text-slate-600">Tailwind CSS configured</p>
        </div>
      </div>
    </section>
  );
}
