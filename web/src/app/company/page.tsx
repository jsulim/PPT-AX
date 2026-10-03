import Link from "next/link";

import { apiBaseUrl, getCompanyDataSnapshot, getHwpxFormJobs } from "@/lib/api";

const companyFields = [
  ["name", "상호"],
  ["business_no", "사업자등록번호"],
  ["corporate_no", "법인등록번호"],
  ["ceo_name", "대표자"],
  ["phone", "전화"],
  ["email", "이메일"],
  ["address", "주소"],
] as const;

const requiredCompanyFields = ["name", "business_no", "ceo_name", "phone", "email", "address"];

function valueText(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  if (Array.isArray(value)) {
    return `${value.length}건`;
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Asia/Seoul",
  }).format(new Date(value));
}

export default async function CompanyPage() {
  const [snapshot, jobs] = await Promise.all([getCompanyDataSnapshot(), getHwpxFormJobs(8)]);
  const missingCompanyFields = requiredCompanyFields.filter((key) => !snapshot.company[key]);
  const latestJob = jobs[0];

  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 px-6 py-8">
      <header className="flex flex-col gap-3 border-b border-slate-200 pb-5">
        <Link className="w-fit text-sm font-medium text-slate-600 underline" href="/">
          처음으로
        </Link>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-medium text-slate-500">회사 데이터 관리</p>
            <h1 className="text-2xl font-semibold text-slate-950">인력·실적·서식 생성 현황</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-900"
              href="/forms/jobs"
            >
              생성 결과 보기
            </Link>
            {latestJob ? (
              <a
                className="rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white"
                href={`${apiBaseUrl}${latestJob.download_url}`}
              >
                최근 서식 다운로드
              </a>
            ) : null}
          </div>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-4">
        <Metric label="등록 인력" value={snapshot.personnel.length} />
        <Metric label="인력 경력" value={snapshot.personnel_careers.length} />
        <Metric label="수행실적" value={snapshot.track_records.length} />
        <Metric label="최근 생성 서식" value={jobs.length} />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <section className="rounded border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-slate-950">회사 기본정보</h2>
            <span
              className={`rounded px-2 py-1 text-xs font-medium ${
                missingCompanyFields.length
                  ? "bg-amber-50 text-amber-700"
                  : "bg-emerald-50 text-emerald-700"
              }`}
            >
              {missingCompanyFields.length ? `${missingCompanyFields.length}개 보충 필요` : "완료"}
            </span>
          </div>
          <dl className="mt-4 grid gap-3 text-sm">
            {companyFields.map(([key, label]) => (
              <div key={key} className="grid grid-cols-[120px_1fr] gap-3 border-b border-slate-100 pb-2">
                <dt className="text-slate-500">{label}</dt>
                <dd className="break-all font-medium text-slate-900">{valueText(snapshot.company[key])}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-950">최근 생성 서식</h2>
          {jobs.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">아직 생성된 HWPX 서식이 없습니다.</p>
          ) : (
            <div className="mt-4 divide-y divide-slate-100">
              {jobs.map((job) => (
                <article key={job.job_id} className="grid gap-3 py-3 text-sm md:grid-cols-[1fr_auto]">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-900" title={job.source_filename}>
                      {job.source_filename}
                    </p>
                    <p className="mt-1 text-slate-500">
                      {formatDate(job.created_at)} · 채움 {job.filled_count} · 누락 {job.missing_count}
                    </p>
                  </div>
                  <div className="flex gap-3">
                    <Link className="font-medium text-slate-800 underline" href={`/forms/jobs/${job.job_id}`}>
                      상세
                    </Link>
                    <a className="font-medium text-slate-800 underline" href={`${apiBaseUrl}${job.download_url}`}>
                      다운로드
                    </a>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <DataTable
          title="인력 목록"
          rows={snapshot.personnel}
          columns={[
            ["name", "성명"],
            ["department", "소속"],
            ["position", "직위"],
            ["role", "참여 업무"],
          ]}
          empty="동기화된 인력 데이터가 없습니다."
        />
        <DataTable
          title="수행실적"
          rows={snapshot.track_records}
          columns={[
            ["project_name", "사업명"],
            ["client_name", "발주처"],
            ["period", "기간"],
            ["amount_krw", "금액"],
          ]}
          empty="동기화된 수행실적 데이터가 없습니다."
        />
      </section>

      <DataTable
        title="인력별 경력"
        rows={snapshot.personnel_careers}
        columns={[
          ["personnel_name", "성명"],
          ["project_name", "사업명"],
          ["client_name", "근무처"],
          ["period", "참여기간"],
          ["role", "담당업무"],
        ]}
        empty="동기화된 인력 경력 데이터가 없습니다."
      />
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <article className="rounded border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value.toLocaleString("ko-KR")}</p>
    </article>
  );
}

function DataTable({
  title,
  rows,
  columns,
  empty,
}: {
  title: string;
  rows: Array<Record<string, unknown>>;
  columns: Array<readonly [string, string]>;
  empty: string;
}) {
  return (
    <section className="overflow-hidden rounded border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">{title}</h2>
      </div>
      {rows.length === 0 ? (
        <p className="px-4 py-10 text-sm text-slate-500">{empty}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                {columns.map(([key, label]) => (
                  <th key={key} className="whitespace-nowrap px-4 py-3 font-medium">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.slice(0, 50).map((row, index) => (
                <tr key={String(row.source_key ?? index)}>
                  {columns.map(([key]) => (
                    <td key={key} className="max-w-[280px] truncate px-4 py-3 text-slate-800">
                      {valueText(row[key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
