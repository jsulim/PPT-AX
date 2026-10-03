import Link from "next/link";
import { notFound } from "next/navigation";

import { apiBaseUrl, getHwpxFormJob } from "@/lib/api";

type PageProps = {
  params: {
    jobId: string;
  };
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

function itemText(item: Record<string, string>) {
  return Object.entries(item)
    .map(([key, value]) => `${key}: ${value}`)
    .join(" · ");
}

export default async function HwpxFormJobDetailPage({ params }: PageProps) {
  const job = await getHwpxFormJob(params.jobId);
  if (!job) {
    notFound();
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5">
        <Link className="w-fit text-sm font-medium text-slate-600 underline" href="/forms/jobs">
          생성 로그로
        </Link>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-slate-500">HWPX 생성 상세</p>
            <h1 className="break-all text-2xl font-semibold text-slate-950">{job.output_filename}</h1>
          </div>
          <a
            className="w-fit rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white"
            href={`${apiBaseUrl}${job.download_url}`}
          >
            HWPX 다운로드
          </a>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="채운 칸" value={job.filled_count} tone="emerald" />
        <Metric label="누락" value={job.missing_count} tone="amber" />
        <Metric label="스킵" value={job.skipped_count} tone="rose" />
        <Metric label="서식만 추출" value={job.trim_applied ? "완료" : "미적용"} tone="slate" />
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="text-base font-semibold text-slate-950">기본 정보</h2>
        <dl className="mt-4 grid gap-3 text-sm md:grid-cols-2">
          <Info label="생성 시각" value={formatDate(job.created_at)} />
          <Info label="업로드 파일" value={job.source_filename} />
          <Info label="원본 저장명" value={job.original_filename} />
          <Info label="작업 ID" value={job.job_id} />
        </dl>
      </section>

      <LogList title="채운 항목" items={job.filled} empty="채운 항목이 없습니다." tone="emerald" />
      <ObjectList title="누락 항목" items={job.missing} empty="누락 항목이 없습니다." tone="amber" />
      <ObjectList title="스킵 항목" items={job.skipped} empty="스킵 항목이 없습니다." tone="rose" />
      <ObjectList title="자동 매핑 정보" items={job.mappings} empty="매핑 정보가 없습니다." tone="slate" />
    </main>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | number;
  tone: "emerald" | "amber" | "rose" | "slate";
}) {
  const toneClass = {
    emerald: "text-emerald-700",
    amber: "text-amber-700",
    rose: "text-rose-700",
    slate: "text-slate-800",
  }[tone];

  return (
    <article className="rounded border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${toneClass}`}>{value}</p>
    </article>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 break-all font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function LogList({
  title,
  items,
  empty,
  tone,
}: {
  title: string;
  items: string[];
  empty: string;
  tone: "emerald" | "amber" | "rose" | "slate";
}) {
  const toneClass = {
    emerald: "bg-emerald-50",
    amber: "bg-amber-50",
    rose: "bg-rose-50",
    slate: "bg-slate-50",
  }[tone];

  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{empty}</p>
      ) : (
        <ul className="mt-3 max-h-80 space-y-2 overflow-auto text-sm">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className={`break-all rounded ${toneClass} px-3 py-2`}>
              {item}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ObjectList({
  title,
  items,
  empty,
  tone,
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  empty: string;
  tone: "emerald" | "amber" | "rose" | "slate";
}) {
  const toneClass = {
    emerald: "bg-emerald-50",
    amber: "bg-amber-50",
    rose: "bg-rose-50",
    slate: "bg-slate-50",
  }[tone];

  return (
    <section className="rounded border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">{empty}</p>
      ) : (
        <ul className="mt-3 max-h-80 space-y-2 overflow-auto text-sm">
          {items.map((item, index) => (
            <li key={index} className={`break-all rounded ${toneClass} px-3 py-2 text-slate-800`}>
              {itemText(
                Object.fromEntries(Object.entries(item).map(([key, value]) => [key, String(value)])),
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
