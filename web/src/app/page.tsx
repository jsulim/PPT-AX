import { getHealth } from "@/lib/api";

const labels: Record<string, string> = {
  db: "DB",
  redis: "Redis",
  worker: "Worker",
};

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-slate-500">인트윈 제안 자동화 플랫폼</p>
        <h1 className="text-3xl font-semibold tracking-normal text-slate-950">PPT AX</h1>
      </header>

      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-3">
          <h2 className="text-lg font-semibold text-slate-900">실행 상태</h2>
          <span className="text-sm text-slate-500">
            {health ? (health.status === "ok" ? "정상입니다." : "확인이 필요합니다.") : "API 연결이 필요합니다."}
          </span>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {["db", "redis", "worker"].map((key) => {
            const component = health?.components[key];
            const ok = Boolean(component?.ok);

            return (
              <article key={key} className="rounded border border-slate-200 bg-white p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-base font-medium text-slate-900">{labels[key]}</h3>
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium ${
                      ok ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
                    }`}
                  >
                    {ok ? "정상" : "대기"}
                  </span>
                </div>
                <p className="mt-3 min-h-10 text-sm leading-5 text-slate-600">
                  {component?.detail ?? "상태 정보를 아직 받지 못했습니다."}
                </p>
              </article>
            );
          })}
        </div>
      </section>
    </main>
  );
}
