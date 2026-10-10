"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";
import { EmptyState, PageHeader, StatusMessage } from "../../../components/ui";

type HistorySource = "all" | "legacy" | "generic";
type HistoryRecord = {
  id: string;
  source: "legacy" | "generic";
  title: string;
  status: string;
  organization_unit: string | null;
  reference_version_id: string;
  overall_score: string | null;
  progress_percent: string | null;
  created_at: string;
};
type HistoryResponse = {
  page: number;
  page_size: number;
  has_more: boolean;
  results: HistoryRecord[];
};
type Unit = { id: string; name: string };

const sourceLabels: Record<HistorySource, string> = {
  all: "همه ارزیابی‌ها",
  legacy: "ارزیابی‌های مبتنی بر استاندارد",
  generic: "ارزیابی‌های عمومی",
};
const statusLabels: Record<string, string> = {
  draft: "پیش‌نویس",
  in_progress: "در حال اجرا",
  in_review: "در حال بازبینی",
  completed: "تکمیل‌شده",
  cancelled: "لغوشده",
};

export default function AssessmentHistoryPage() {
  const [source, setSource] = useState<HistorySource>("all");
  const [unit, setUnit] = useState("");
  const [draftSearch, setDraftSearch] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [units, setUnits] = useState<Unit[]>([]);
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const pageSize = 25;

  useEffect(() => {
    const controller = new AbortController();
    async function getUnits() {
      try {
        const response = await apiFetch("/organization-units/?page_size=200", { signal: controller.signal });
        if (!response.ok) return;
        const body = await response.json() as Unit[] | { results?: Unit[] };
        if (!controller.signal.aborted) setUnits(Array.isArray(body) ? body : body.results ?? []);
      } catch {
        // Unit name resolution is optional; history remains usable by UUID.
      }
    }
    void getUnits();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({
          source, page: String(page), page_size: String(pageSize),
        });
        if (unit) params.set("organization_unit", unit);
        if (search) params.set("search", search);
        const response = await apiFetch("/assessment-history/?" + params.toString(), {
          signal: controller.signal,
        });
        if (!response.ok) {
          setError(response.status === 403
            ? "برای مشاهده سوابق ارزیابی در این دامنه مجوز ندارید."
            : "دریافت سوابق ارزیابی ناموفق بود (" + response.status + ").");
          if (!controller.signal.aborted) setData(null);
          return;
        }
        const payload = await response.json() as HistoryResponse;
        if (!controller.signal.aborted) setData(payload);
      } catch {
        if (!controller.signal.aborted) {
          setError("ارتباط با سامانه برقرار نشد.");
          setData(null);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [source, unit, page, search]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setSearch(draftSearch.trim().slice(0, 120));
  }

  return (
    <main className="adminPage" dir="rtl">
      <PageHeader
        eyebrow={<Link href="/assessments">← بازگشت به ارزیابی و انطباق</Link>}
        title="سوابق یکپارچه ارزیابی‌ها"
        description="نمای فقط‌خواندنی سوابق ارزیابی‌های قبلی و موتور ارزیابی عمومی، بدون تغییر داده‌های تاریخی"
      />
      <section className="panel">
        <form className="settingsForm" onSubmit={submitSearch}>
          <label>نوع ارزیابی
            <select value={source} onChange={event => {
              setSource(event.target.value as HistorySource);
              setPage(1);
            }}>
              <option value="all">{sourceLabels.all}</option>
              <option value="legacy">{sourceLabels.legacy}</option>
              <option value="generic">{sourceLabels.generic}</option>
            </select>
          </label>
          <label>واحد سازمانی
            <select value={unit} onChange={event => { setUnit(event.target.value); setPage(1); }}>
              <option value="">همه واحدهای مجاز</option>
              {units.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}
            </select>
          </label>
          <label>جست‌وجو در عنوان
            <input maxLength={120} value={draftSearch} onChange={event => setDraftSearch(event.target.value)} placeholder="عنوان ارزیابی" />
          </label>
          <button className="primary" type="submit">جست‌وجو</button>
        </form>
      </section>
      {error && <StatusMessage tone="danger">{error}</StatusMessage>}
      {loading ? <p className="muted">در حال دریافت سوابق…</p> :
        data && <section className="panel">
          <h2>دفتر سوابق ارزیابی</h2>
          <p className="muted">نتایج صفحه {data.page}؛ موارد عمومی هنوز در این نمای مشترک امتیاز محاسبه‌شده ندارند و امتیاز قبلی آن‌ها جایگزین نمی‌شود.</p>
          {!data.results.length ? <EmptyState title="ارزیابی‌ای با این شرایط یافت نشد." /> :
            <table className="dataTable">
              <thead><tr>
                <th>عنوان</th><th>منبع</th><th>وضعیت</th>
                <th>واحد</th><th>امتیاز قبلی</th><th>زمان ثبت</th><th>مشاهده</th>
              </tr></thead>
              <tbody>
                {data.results.map(row => <tr key={row.source + ":" + row.id}>
                  <td>{row.title}</td>
                  <td>{row.source === "legacy" ? "ارزیابی استاندارد" : "موتور عمومی"}</td>
                  <td>{statusLabels[row.status] ?? row.status}</td>
                  <td>{units.find(x => x.id === row.organization_unit)?.name ?? (row.organization_unit ? "واحد مجاز" : "کل سازمان")}</td>
                  <td>{row.source === "legacy" ? row.overall_score ?? "—" : "قابل مقایسه نیست"}</td>
                  <td><time dateTime={row.created_at}>{new Date(row.created_at).toLocaleDateString("fa-IR")}</time></td>
                  <td><Link href={row.source === "legacy" ? "/assessments/" + row.id : "/assessments/generic"}>
                    {row.source === "legacy" ? "جزئیات" : "ورود به موتور"}
                  </Link></td>
                </tr>)}
              </tbody>
            </table>}
          <div className="headActions">
            <button className="secondaryLink" type="button" disabled={page <= 1} onClick={() => setPage(v => Math.max(1, v - 1))}>صفحه قبل</button>
            <span>صفحه {page}</span>
            <button className="secondaryLink" type="button" disabled={!data.has_more} onClick={() => setPage(v => v + 1)}>صفحه بعد</button>
          </div>
        </section>}
    </main>
  );
}
