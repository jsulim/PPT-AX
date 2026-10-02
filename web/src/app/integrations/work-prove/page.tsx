"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const samplePayload = {
  bid: {
    no: "20261001001",
    ord: "00",
    name: "지역 관광 활성화 운영 용역",
    noticeOrg: "공고기관",
    demandOrg: "수요기관",
    method: "협상에 의한 계약",
    budget: 100000000,
  },
  notice: {
    bodyText: "과업지시서 또는 제안요청서 본문을 넣습니다.",
    requirements: [{ req_id: "R1", title: "운영계획 수립", scoring_item_key: "S1" }],
    scoringItems: [{ key: "S1", name: "수행계획", points: 30 }],
    forms: [],
    qualifications: [],
  },
  company: { name: "인트윈" },
  selectedPersonnel: [],
  selectedTrackRecords: [],
  outlineItems: [{ scoring_item_key: "S1", slide_type_key: "method_detail", slide_count: 2 }],
};

type ImportResult = {
  project: {
    id: string;
    name: string;
    agency?: string | null;
  };
  notice_context_id: string;
  bid_context_id: string;
  outline_id: string;
};

export default function WorkProveIntegrationPage() {
  const [payload, setPayload] = useState(JSON.stringify(samplePayload, null, 2));
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState("");
  const [statusText, setStatusText] = useState("대기 중입니다.");
  const [loading, setLoading] = useState(false);
  const apiBaseUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
    [],
  );

  const submitImportedPayload = useCallback(
    async (nextPayload: string) => {
      setLoading(true);
      setError("");
      setResult(null);
      setStatusText("PPT_AX로 가져오는 중입니다.");

      try {
        const parsed = JSON.parse(nextPayload) as unknown;
        const response = await fetch(`${apiBaseUrl}/integrations/work-prove/import`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(parsed),
        });
        const data = (await response.json()) as ImportResult | { detail?: string };
        if (!response.ok) {
          throw new Error(
            "detail" in data && data.detail ? data.detail : "가져오기에 실패했습니다.",
          );
        }
        setResult(data as ImportResult);
        setStatusText("가져오기가 완료되었습니다.");
      } catch (caught) {
        setStatusText("가져오기에 실패했습니다.");
        setError(caught instanceof Error ? caught.message : "JSON 형식을 확인해주세요.");
      } finally {
        setLoading(false);
      }
    },
    [apiBaseUrl],
  );

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const hashPayload = hash.get("payload");
    if (!hashPayload) {
      return;
    }

    try {
      const decoded = decodeURIComponent(hashPayload);
      const pretty = JSON.stringify(JSON.parse(decoded), null, 2);
      setPayload(pretty);
      setStatusText("입찰자동화에서 받은 데이터를 읽었습니다.");
      if (hash.get("auto") === "1") {
        window.setTimeout(() => {
          void submitImportedPayload(pretty);
        }, 100);
      }
    } catch (caught) {
      setStatusText("전달 데이터를 읽지 못했습니다.");
      setError(caught instanceof Error ? caught.message : "전달받은 JSON 형식을 확인해주세요.");
    }
  }, [submitImportedPayload]);

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-slate-500">연동</p>
        <h1 className="text-2xl font-semibold text-slate-950">입찰자동화 데이터 가져오기</h1>
        <p className="text-sm text-slate-600">{statusText}</p>
      </header>

      <section className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-3">
          <textarea
            className="min-h-[560px] resize-y rounded border border-slate-300 bg-white p-4 font-mono text-sm leading-6 text-slate-900 outline-none focus:border-slate-500"
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
            spellCheck={false}
          />
          <div className="flex justify-end">
            <button
              className="rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={loading}
              onClick={() => void submitImportedPayload(payload)}
              type="button"
            >
              {loading ? "가져오는 중" : "가져오기"}
            </button>
          </div>
        </div>

        <aside className="flex flex-col gap-3 rounded border border-slate-200 bg-white p-4">
          <h2 className="text-base font-semibold text-slate-900">결과</h2>
          {error ? <p className="text-sm leading-5 text-rose-700">{error}</p> : null}
          {result ? (
            <>
              <dl className="grid gap-3 text-sm">
                <div>
                  <dt className="text-slate-500">사업명</dt>
                  <dd className="mt-1 font-medium text-slate-950">{result.project.name}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">사업 ID</dt>
                  <dd className="mt-1 break-all font-mono text-xs text-slate-700">
                    {result.project.id}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">notice_context</dt>
                  <dd className="mt-1 break-all font-mono text-xs text-slate-700">
                    {result.notice_context_id}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">bid_context</dt>
                  <dd className="mt-1 break-all font-mono text-xs text-slate-700">
                    {result.bid_context_id}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">outline</dt>
                  <dd className="mt-1 break-all font-mono text-xs text-slate-700">
                    {result.outline_id}
                  </dd>
                </div>
              </dl>
              <a
                className="mt-2 inline-flex justify-center rounded bg-slate-950 px-4 py-2 text-sm font-medium text-white"
                href={`/projects/${result.project.id}/build`}
              >
                PPTX 생성으로 이동
              </a>
            </>
          ) : (
            <p className="text-sm leading-5 text-slate-600">
              입찰자동화에서 보낸 JSON을 가져오면 사업 카드와 입력 컨텍스트가 생성됩니다.
            </p>
          )}
        </aside>
      </section>
    </main>
  );
}
