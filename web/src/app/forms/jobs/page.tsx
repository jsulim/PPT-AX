import Link from "next/link";

import { apiBaseUrl, getHwpxFormJobs } from "@/lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

export default async function HwpxFormJobsPage() {
  const jobs = await getHwpxFormJobs(100);

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5">
        <Link className="w-fit text-sm font-medium text-slate-600 underline" href="/company">
          회사 데이터로
        </Link>
        <div>
          <p className="text-sm font-medium text-slate-500">HWPX 생성 결과</p>
          <h1 className="text-2xl font-semibold text-slate-950">생성 로그</h1>
        </div>
      </header>

      <section className="overflow-hidden rounded border border-slate-200 bg-white">
        <div className="grid grid-cols-[1.4fr_1fr_0.7fr_0.7fr_0.7fr_0.8fr] gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium text-slate-600">
          <span>생성 시각</span>
          <span>파일</span>
          <span>채움</span>
          <span>누락</span>
          <span>스킵</span>
          <span>작업</span>
        </div>
        {jobs.length === 0 ? (
          <p className="px-4 py-10 text-sm text-slate-500">
            아직 생성 로그가 없습니다. HWPX를 생성하면 이곳에 기록됩니다.
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobs.map((job) => (
              <article
                key={job.job_id}
                className="grid grid-cols-[1.4fr_1fr_0.7fr_0.7fr_0.7fr_0.8fr] gap-3 px-4 py-3 text-sm"
              >
                <span className="text-slate-700">{formatDate(job.created_at)}</span>
                <span className="truncate text-slate-900" title={job.source_filename}>
                  {job.source_filename}
                </span>
                <span className="font-medium text-emerald-700">{job.filled_count}</span>
                <span className={job.missing_count ? "font-medium text-amber-700" : "text-slate-500"}>
                  {job.missing_count}
                </span>
                <span className={job.skipped_count ? "font-medium text-rose-700" : "text-slate-500"}>
                  {job.skipped_count}
                </span>
                <span className="flex gap-3">
                  <Link className="font-medium text-slate-900 underline" href={`/forms/jobs/${job.job_id}`}>
                    상세
                  </Link>
                  <a className="font-medium text-slate-700 underline" href={`${apiBaseUrl}${job.download_url}`}>
                    다운로드
                  </a>
                </span>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
