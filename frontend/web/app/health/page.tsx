export default function HealthPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">
        Frontend Health Check
      </h1>

      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
        <p className="text-sm font-semibold text-emerald-800">Status: ONLINE</p>
        <p className="mt-2 text-sm text-emerald-700">
          Next.js UI is running successfully.
        </p>
      </div>
    </section>
  );
}
