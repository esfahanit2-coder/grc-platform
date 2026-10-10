"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";
import { EmptyState, PageHeader, StatusMessage } from "../../../components/ui";

type Unit = { id: string; name: string };
type TenantUser = { id: number; username: string; membership_active?: boolean };
type Risk = {
  id: string; code: string; title: string; organization_name?: string;
  latest_evaluations?: Record<string, { id: string; score: string; level: string }>;
};
type Appetite = {
  id: string; code: string; version: number; title: string;
  organization_unit: string | null; status: string;
  effective_from: string; effective_until: string | null;
  owner: number; approved_by: number | null;
};
type Tolerance = { id: string; statement: string; evaluation_type: string; maximum_score: string };
type Acceptance = {
  id: string; risk: string; status: string; requested_by: number;
  score_snapshot: string; tolerance_max_snapshot: string; exceeds_tolerance: boolean;
  rationale: string; review_on: string; expires_on: string;
  evaluation_type_snapshot: string; is_current: boolean; exception_justification: string;
};
type PolicyForm = {
  unit: string; code: string; version: string; title: string; owner: string;
  from: string; until: string; maximum: string;
};
type AcceptanceForm = {
  risk: string; appetite: string; rationale: string; review: string; expires: string;
  exception: string; supersedes: string;
};
const emptyPolicy: PolicyForm = { unit: "", code: "", version: "1", title: "", owner: "", from: "", until: "", maximum: "" };
const emptyAcceptance: AcceptanceForm = { risk: "", appetite: "", rationale: "", review: "", expires: "", exception: "", supersedes: "" };

function unpack<T>(body: T[] | { results?: T[] }): T[] {
  return Array.isArray(body) ? body : body.results ?? [];
}

function errorText(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload) return payload;
  if (!payload || typeof payload !== "object") return fallback;
  const entries = Object.entries(payload as Record<string, unknown>);
  return entries.map(([key, value]) => key + ": " + (Array.isArray(value) ? value.join("، ") : String(value))).join(" | ") || fallback;
}

async function loadList<T>(route: string): Promise<T[]> {
  const response = await apiFetch(route);
  if (!response.ok) throw new Error("بارگذاری " + route + " ناموفق بود (" + response.status + ")");
  return unpack((await response.json()) as T[] | { results?: T[] });
}

export default function RiskGovernancePage() {
  const [policies, setPolicies] = useState<Appetite[]>([]);
  const [tolerances, setTolerances] = useState<Tolerance[]>([]);
  const [acceptances, setAcceptances] = useState<Acceptance[]>([]);
  const [risks, setRisks] = useState<Risk[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [policy, setPolicy] = useState<PolicyForm>(emptyPolicy);
  const [request, setRequest] = useState<AcceptanceForm>(emptyAcceptance);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    const paths = [
      "/risk-appetites/?page_size=200", "/risk-tolerances/?page_size=200",
      "/risk-acceptances/?page_size=200", "/risks/?page_size=200",
      "/organization-units/?page_size=200", "/tenant-users/?page_size=200",
    ];
    const settled = await Promise.allSettled(paths.map(route => loadList<unknown>(route)));
    const failed = settled.flatMap((result, index) =>
      result.status === "rejected" ? [paths[index]] : []);
    const value = (index: number): unknown[] => {
      const result = settled[index];
      return result?.status === "fulfilled" ? result.value : [];
    };
    setPolicies(value(0) as Appetite[]);
    setTolerances(value(1) as Tolerance[]);
    setAcceptances(value(2) as Acceptance[]);
    setRisks(value(3) as Risk[]);
    setUnits(value(4) as Unit[]);
    setUsers((value(5) as TenantUser[]).filter(user => user.membership_active !== false));
    setError(failed.length ? "دسترسی یا دریافت برخی داده‌ها ناموفق بود: " + failed.join("، ") : "");
    setLoading(false);
  }

  useEffect(() => { void load(); }, []);

  const riskById = useMemo(() => new Map(risks.map(row => [row.id, row])), [risks]);
  const toleranceByPolicy = useMemo(() =>
    new Map(tolerances.filter(t => t.evaluation_type === "residual").map(t => [t.statement, t.maximum_score])),
    [tolerances]);
  const selectedRisk = risks.find(row => row.id === request.risk);
  const selectedEvaluation = selectedRisk?.latest_evaluations?.residual ?? selectedRisk?.latest_evaluations?.current;
  const activePolicies = policies.filter(row => row.status === "approved");
  const pending = acceptances.filter(row => row.status === "pending");

  async function submit(route: string, payload: Record<string, unknown>, success: string) {
    setBusy(true);
    setMessage("");
    try {
      const response = await apiFetch(route, { method: "POST", body: JSON.stringify(payload) });
      if (!response.ok) {
        const body = await response.json().catch(() => null) as unknown;
        setMessage(errorText(body, "درخواست ناموفق بود (" + response.status + ")"));
        return null;
      }
      const result = await response.json().catch(() => ({})) as { id?: string };
      setMessage(success);
      await load();
      return result;
    } catch {
      setMessage("ارتباط با سرور برقرار نشد.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function createPolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!policy.owner || !policy.code.trim() || !policy.from || !policy.maximum) {
      setMessage("کد، مالک، تاریخ شروع و حد تحمل الزامی هستند.");
      return;
    }
    const result = await submit("/risk-appetites/", {
      organization_unit: policy.unit || null, code: policy.code.trim(), version: Number(policy.version),
      title: policy.title.trim(), owner: Number(policy.owner), effective_from: policy.from,
      effective_until: policy.until || null,
    }, "نسخه پیش‌نویس اشتهای ریسک ایجاد شد.");
    if (result?.id) {
      const second = await submit("/risk-tolerances/", {
        statement: result.id, evaluation_type: "residual", maximum_score: policy.maximum,
      }, "سیاست و حد تحمل آن ثبت شدند. پیش از استفاده، سیاست باید تأیید شود.");
      if (second) setPolicy(emptyPolicy);
    }
  }

  async function createAcceptance(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEvaluation || !request.appetite || !request.rationale.trim()) {
      setMessage("ریسک دارای ارزیابی فعلی/باقیمانده، سیاست تأییدشده و دلیل مکتوب لازم است.");
      return;
    }
    const result = await submit("/risk-acceptances/", {
      risk: request.risk, evaluation: selectedEvaluation.id, appetite: request.appetite,
      supersedes: request.supersedes || null,
      rationale: request.rationale.trim(), review_on: request.review,
      expires_on: request.expires, exception_justification: request.exception.trim(),
    }, "درخواست پذیرش ثبت شد و در انتظار تصمیم تأییدکننده مستقل است.");
    if (result) setRequest(emptyAcceptance);
  }

  async function decide(id: string, decision: "approve" | "reject") {
    await submit("/risk-acceptances/" + id + "/" + decision + "/", {
      decision_note: (notes[id] ?? "").trim(),
    }, decision === "approve" ? "تصمیم تأیید ثبت شد." : "درخواست با ثبت دلیل رد شد.");
  }

  return (
    <main className="adminPage">
      <PageHeader
        eyebrow={<Link href="/risks">← بازگشت به فهرست ریسک‌ها</Link>}
        title="اشتهای ریسک و پذیرش ریسک"
        description="سیاست‌های نسخه‌دار، حدود تحمل، درخواست پذیرش و تصمیم‌گیری مستقل با ثبت سابقه"
      />
      {error && <StatusMessage tone="warning">{error}</StatusMessage>}
      {message && <StatusMessage>{message}</StatusMessage>}
      {loading && <p className="muted">در حال دریافت داده‌های سازمان…</p>}

      <div className="grid">
        <section className="panel">
          <h2>نسخه جدید سیاست اشتهای ریسک</h2>
          <p className="muted">ابتدا پیش‌نویس و حد تحمل باقیمانده را بسازید؛ مالک سیاست نمی‌تواند همان نسخه را تأیید کند.</p>
          <form className="settingsForm" onSubmit={createPolicy}>
            <label>کد سیاست *<input dir="ltr" required value={policy.code} onChange={e => setPolicy(v => ({ ...v, code: e.target.value }))} /></label>
            <label>عنوان *<input required value={policy.title} onChange={e => setPolicy(v => ({ ...v, title: e.target.value }))} /></label>
            <label>شماره نسخه *<input dir="ltr" type="number" min="1" required value={policy.version} onChange={e => setPolicy(v => ({ ...v, version: e.target.value }))} /></label>
            <label>واحد سازمانی<select value={policy.unit} onChange={e => setPolicy(v => ({ ...v, unit: e.target.value }))}>
              <option value="">کل سازمان (مستلزم مجوز سراسری)</option>
              {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select></label>
            <label>مالک *<select required value={policy.owner} onChange={e => setPolicy(v => ({ ...v, owner: e.target.value }))}>
              <option value="">انتخاب مالک</option>
              {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
            </select></label>
            <label>شروع اعتبار *<input type="date" required value={policy.from} onChange={e => setPolicy(v => ({ ...v, from: e.target.value }))} /></label>
            <label>پایان اعتبار<input type="date" value={policy.until} onChange={e => setPolicy(v => ({ ...v, until: e.target.value }))} /></label>
            <label>حداکثر امتیاز ریسک باقیمانده *<input type="number" min="0" step="0.0001" required value={policy.maximum} onChange={e => setPolicy(v => ({ ...v, maximum: e.target.value }))} /></label>
            <button type="submit" className="primary" disabled={busy || loading}>ثبت سیاست و حد تحمل</button>
          </form>
        </section>
        <section className="panel">
          <h2>درخواست پذیرش ریسک</h2>
          <p className="muted">درخواست به شناسه دقیق ارزیابی متصل می‌شود و امتیاز تاریخی را تغییر نمی‌دهد.</p>
          <form className="settingsForm" onSubmit={createAcceptance}>
            <label>ریسک *<select required value={request.risk} onChange={e => setRequest(v => ({ ...v, risk: e.target.value, appetite: "", supersedes: "" }))}>
              <option value="">انتخاب ریسک</option>
              {risks.map(r => <option key={r.id} value={r.id}>{r.code} — {r.title}</option>)}
            </select></label>
            <p className="muted">آخرین ارزیابی: {selectedEvaluation ? selectedEvaluation.score + " (" + selectedEvaluation.level + ")" : "ثبت نشده"}</p>
            <label>سیاست مصوب *<select required value={request.appetite} onChange={e => setRequest(v => ({ ...v, appetite: e.target.value }))}>
              <option value="">انتخاب نسخه معتبر</option>
              {activePolicies.map(a => <option key={a.id} value={a.id}>{a.code} / نسخه {a.version} — سقف: {toleranceByPolicy.get(a.id) ?? "تعریف نشده"}</option>)}
            </select></label>
            <label>جایگزین‌کردن پذیرش قبلی (در صورت تمدید)<select value={request.supersedes} onChange={e => setRequest(v => ({ ...v, supersedes: e.target.value }))}>
              <option value="">پذیرش جاری وجود ندارد یا انتخاب نشده</option>
              {acceptances.filter(a => a.risk === request.risk && a.is_current).map(a =>
                <option key={a.id} value={a.id}>{a.score_snapshot} — معتبر تا {a.expires_on}</option>)}
            </select></label>
            <label>دلیل پذیرش *<textarea required value={request.rationale} onChange={e => setRequest(v => ({ ...v, rationale: e.target.value }))} /></label>
            <label>تاریخ بازبینی *<input required type="date" value={request.review} onChange={e => setRequest(v => ({ ...v, review: e.target.value }))} /></label>
            <label>تاریخ انقضا *<input required type="date" value={request.expires} onChange={e => setRequest(v => ({ ...v, expires: e.target.value }))} /></label>
            <label>توجیه استثنا (اگر امتیاز فراتر از حد تحمل است)<textarea value={request.exception} onChange={e => setRequest(v => ({ ...v, exception: e.target.value }))} /></label>
            <button type="submit" className="primary" disabled={busy || !selectedEvaluation}>ثبت درخواست برای تأیید</button>
          </form>
        </section>
      </div>

      <section className="panel">
        <h2>نسخه‌های اشتهای ریسک</h2>
        {!policies.length ? <EmptyState title="سیاستی برای این محدوده یافت نشد." /> :
          <table className="dataTable"><thead><tr><th>کد / نسخه</th><th>عنوان</th><th>سقف باقیمانده</th><th>وضعیت</th><th>اعتبار</th><th>تصمیم</th></tr></thead><tbody>
            {policies.map(p => <tr key={p.id}>
              <td>{p.code} / {p.version}</td><td>{p.title}</td>
              <td>{toleranceByPolicy.get(p.id) ?? "—"}</td><td>{p.status}</td>
              <td>{p.effective_from} تا {p.effective_until ?? "نامحدود"}</td>
              <td>{p.status === "draft" ? <button className="secondaryLink" disabled={busy} onClick={() => void submit("/risk-appetites/" + p.id + "/approve/", {}, "نسخه سیاست تأیید شد.")}>تأیید مستقل</button> : "—"}</td>
            </tr>)}
          </tbody></table>
        }
      </section>

      <section className="panel">
        <h2>درخواست‌های در انتظار تصمیم ({pending.length})</h2>
        {!pending.length ? <EmptyState title="درخواستی در انتظار تصمیم نیست." /> :
          <table className="dataTable"><thead><tr><th>ریسک</th><th>امتیاز و حد تحمل</th><th>بازبینی / انقضا</th><th>دلیل درخواست</th><th>تصمیم مستند</th></tr></thead><tbody>
            {pending.map(item => <tr key={item.id}>
              <td>{riskById.get(item.risk)?.code ?? item.risk.slice(0, 8)}</td>
              <td>{item.score_snapshot} / {item.tolerance_max_snapshot}
                {item.exceeds_tolerance && <strong> — خارج از تحمل</strong>}</td>
              <td>{item.review_on} / {item.expires_on}</td>
              <td>{item.rationale}</td>
              <td>
                <textarea aria-label="یادداشت تصمیم" placeholder="دلیل تصمیم را ثبت کنید" value={notes[item.id] ?? ""}
                  onChange={e => setNotes(s => ({ ...s, [item.id]: e.target.value }))} />
                <div className="headActions">
                  <button className="primary" disabled={busy} onClick={() => void decide(item.id, "approve")}>تأیید</button>
                  <button className="secondaryLink" disabled={busy || !notes[item.id]?.trim()} onClick={() => void decide(item.id, "reject")}>رد</button>
                </div>
              </td>
            </tr>)}
          </tbody></table>
        }
      </section>
      <section className="panel">
        <h2>دفتر تصمیمات و سوابق پذیرش</h2>
        {!acceptances.length ? <EmptyState title="تاکنون تصمیمی ثبت نشده است." /> :
          <table className="dataTable"><thead><tr><th>ریسک</th><th>امتیاز ثبت‌شده</th><th>وضعیت</th><th>انقضا</th></tr></thead><tbody>
            {acceptances.map(row => <tr key={row.id}>
              <td>{riskById.get(row.risk)?.code ?? row.risk.slice(0, 8)}</td>
              <td>{row.score_snapshot}</td><td>{row.status}{row.is_current ? " (معتبر)" : ""}</td><td>{row.expires_on}</td>
            </tr>)}
          </tbody></table>
        }
      </section>
    </main>
  );
}
