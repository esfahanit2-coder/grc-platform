"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";
import { EmptyState, PageHeader, StatusMessage } from "../../../components/ui";

type Template = { id: string; code: string; title: string; organization_unit: string | null; owner: number };
type Version = { id: string; template: string; version_code: string; status: string };
type Criterion = { id: string; version: string; code: string; title: string; response_type: string; required: boolean; choices: string[] };
type Run = { id: string; title: string; template_version: string; organization_unit: string | null; status: string };
type Answer = { value: string | number | boolean };
type RunItem = {
  id: string; run: string; criterion_code_snapshot: string; criterion_title_snapshot: string;
  response_type_snapshot: string; options_snapshot: string[]; answer: Answer | null;
  applicability_mode_snapshot: string; required_snapshot: boolean; score_percent: string | null;
};
type Decision = {
  id: string; generic_item: string | null; decision: string; rationale: string;
  reviewed_by: number | null; reviewed_at: string | null;
};
type Member = { id: number; username: string; membership_active?: boolean };
type Unit = { id: string; name: string };
type Summary = {
  items_count: number; answered_count: number; required_unanswered: number;
  applicability_reviews_missing: number; scored_count: number; score_percent: string | null;
  is_partial_score: boolean;
};
function unpack<T>(v: T[] | { results?: T[] }): T[] { return Array.isArray(v) ? v : v.results ?? []; }
function messageOf(raw: unknown, fallback: string): string {
  if (!raw || typeof raw !== "object") return fallback;
  return Object.entries(raw as Record<string, unknown>).map(([k, v]) =>
    k + ": " + (Array.isArray(v) ? v.join("، ") : String(v))).join(" | ") || fallback;
}
async function list<T>(route: string): Promise<T[]> {
  const r = await apiFetch(route);
  if (!r.ok) throw new Error("دریافت " + route + " ناموفق بود (" + r.status + ")");
  return unpack((await r.json()) as T[] | { results?: T[] });
}

export default function GenericAssessmentsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [criteria, setCriteria] = useState<Criterion[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [items, setItems] = useState<RunItem[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [users, setUsers] = useState<Member[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [selected, setSelected] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [draftCode, setDraftCode] = useState("");
  const [draftTitle, setDraftTitle] = useState("");
  const [draftUnit, setDraftUnit] = useState("");
  const [draftOwner, setDraftOwner] = useState("");
  const [versionTemplate, setVersionTemplate] = useState("");
  const [versionCode, setVersionCode] = useState("1");
  const [criterionVersion, setCriterionVersion] = useState("");
  const [criterionCode, setCriterionCode] = useState("");
  const [criterionTitle, setCriterionTitle] = useState("");
  const [criterionType, setCriterionType] = useState("boolean");
  const [criterionChoices, setCriterionChoices] = useState("");
  const [publishVersion, setPublishVersion] = useState("");
  const [runVersion, setRunVersion] = useState("");
  const [runUnit, setRunUnit] = useState("");
  const [runOwner, setRunOwner] = useState("");
  const [runTitle, setRunTitle] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [reason, setReason] = useState<Record<string, string>>({});
  const [decision, setDecision] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    setLoading(true);
    const paths = [
      "/assessment-templates/?page_size=200", "/assessment-template-versions/?page_size=200",
      "/assessment-criteria/?page_size=200", "/generic-assessments/?page_size=200",
      "/tenant-users/?page_size=200", "/organization-units/?page_size=200",
      "/assessment-applicability-decisions/?page_size=200",
    ];
    const r = await Promise.allSettled(paths.map(path => list<unknown>(path)));
    const value = (i: number): unknown[] => {
      const result = r[i];
      return result?.status === "fulfilled" ? result.value : [];
    };
    setTemplates(value(0) as Template[]);
    setVersions(value(1) as Version[]);
    setCriteria(value(2) as Criterion[]);
    setRuns(value(3) as Run[]);
    setUsers((value(4) as Member[]).filter(x => x.membership_active !== false));
    setUnits(value(5) as Unit[]);
    setDecisions(value(6) as Decision[]);
    const failures = r.flatMap((res, i) => res.status === "rejected" ? [paths[i]] : []);
    setError(failures.length ? "برخی داده‌ها یا مجوزها در دسترس نیستند: " + failures.join("، ") : "");
    setLoading(false);
  }

  async function loadRun(id: string) {
    if (!id) { setItems([]); setSummary(null); return; }
    const [a, b] = await Promise.all([
      apiFetch("/generic-assessment-items/?page_size=200&run=" + encodeURIComponent(id)),
      apiFetch("/generic-assessments/" + encodeURIComponent(id) + "/summary/"),
    ]);
    if (!a.ok || !b.ok) {
      setError("دریافت پاسخ‌های ارزیابی یا خلاصه آن ناموفق بود.");
      return;
    }
    setItems(unpack((await a.json()) as RunItem[] | {results?: RunItem[]}));
    setSummary(await b.json() as Summary);
  }

  useEffect(() => { void loadAll(); }, []);

  const versionsByTemplate = useMemo(() => new Map(templates.map(t => [t.id, t])), [templates]);
  const current = runs.find(r => r.id === selected);
  const pendingDecisions = decisions.filter(d => items.some(i => i.id === d.generic_item) && !d.reviewed_at);
  const published = versions.filter(v => v.status === "published");
  const draftVersions = versions.filter(v => v.status === "draft");

  async function post(path: string, payload: Record<string, unknown>, success: string) {
    setBusy(true); setInfo("");
    try {
      const r = await apiFetch(path, { method: "POST", body: JSON.stringify(payload) });
      if (!r.ok) {
        const data = await r.json().catch(() => null) as unknown;
        setInfo(messageOf(data, "ثبت ناموفق بود (" + r.status + ")"));
        return null;
      }
      const obj = await r.json().catch(() => ({})) as {id?: string};
      setInfo(success);
      await loadAll();
      if (selected) await loadRun(selected);
      return obj;
    } catch {
      setInfo("ارتباط با سرور برقرار نشد.");
      return null;
    } finally { setBusy(false); }
  }

  function createTemplate(e: FormEvent) {
    e.preventDefault();
    void post("/assessment-templates/", {
      code: draftCode, title: draftTitle, organization_unit: draftUnit || null,
      owner: Number(draftOwner),
    }, "قالب جدید ایجاد شد.");
  }

  function createVersion(e: FormEvent) {
    e.preventDefault();
    void post("/assessment-template-versions/", {
      template: versionTemplate, version_code: versionCode,
    }, "نسخه پیش‌نویس ایجاد شد.");
  }

  function createCriterion(e: FormEvent) {
    e.preventDefault();
    void post("/assessment-criteria/", {
      version: criterionVersion, code: criterionCode, title: criterionTitle,
      response_type: criterionType, choices: criterionType === "choice"
        ? criterionChoices.split("،").map(x => x.trim()).filter(Boolean) : [],
      required: true, weight: "1.000", applicability_mode: "review",
    }, "معیار ارزیابی ثبت شد.");
  }

  function createRun(e: FormEvent) {
    e.preventDefault();
    void post("/generic-assessments/", {
      template_version: runVersion, title: runTitle,
      owner: Number(runOwner), organization_unit: runUnit || null,
    }, "ارزیابی جدید بر اساس نسخه منتشرشده ایجاد شد.");
  }

  function saveAnswer(item: RunItem) {
    let value: string | boolean | number = answers[item.id] ?? "";
    if (item.response_type_snapshot === "boolean") {
      if (value !== "true" && value !== "false") { setInfo("پاسخ بله/خیر را انتخاب کنید."); return; }
      value = value === "true";
    }
    if (item.response_type_snapshot === "number") {
      if (value === "" || !Number.isFinite(Number(value))) { setInfo("یک مقدار عددی معتبر وارد کنید."); return; }
      value = Number(value);
    }
    void post("/generic-assessment-items/" + item.id + "/answer/", { value }, "پاسخ ثبت شد.");
  }

  async function complete() {
    if (!selected) return;
    const r = await post("/generic-assessments/" + selected + "/complete/", {}, "ارزیابی تکمیل و قفل شد.");
    if (r) await loadRun(selected);
  }

  return (
    <main className="adminPage">
      <PageHeader
        eyebrow={<Link href="/assessments">← ارزیابی و انطباق</Link>}
        title="موتور ارزیابی عمومی"
        description="قالب‌های نسخه‌دار، معیارهای قابل تنظیم و پاسخ‌های تاریخی مستقل از استاندارد"
      />
      {error && <StatusMessage tone="warning">{error}</StatusMessage>}
      {info && <StatusMessage>{info}</StatusMessage>}
      {loading && <p className="muted">در حال دریافت اطلاعات…</p>}
      <div className="grid">
        <section className="panel">
          <h2>۱. ایجاد قالب</h2>
          <form className="settingsForm" onSubmit={createTemplate}>
            <label>کد *<input dir="ltr" required value={draftCode} onChange={e => setDraftCode(e.target.value)} /></label>
            <label>عنوان *<input required value={draftTitle} onChange={e => setDraftTitle(e.target.value)} /></label>
            <label>مالک *<select required value={draftOwner} onChange={e => setDraftOwner(e.target.value)}>
              <option value="">انتخاب مالک</option>{users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
            </select></label>
            <label>دامنه سازمانی<select value={draftUnit} onChange={e => setDraftUnit(e.target.value)}>
              <option value="">کل سازمان (نیازمند اختیار سراسری)</option>
              {units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select></label>
            <button className="primary" type="submit" disabled={busy}>ثبت قالب</button>
          </form>
        </section>
        <section className="panel">
          <h2>۲. ایجاد نسخه پیش‌نویس</h2>
          <form className="settingsForm" onSubmit={createVersion}>
            <label>قالب *<select required value={versionTemplate} onChange={e => setVersionTemplate(e.target.value)}>
              <option value="">انتخاب قالب</option>{templates.map(t => <option key={t.id} value={t.id}>{t.code} — {t.title}</option>)}
            </select></label>
            <label>نسخه *<input required dir="ltr" value={versionCode} onChange={e => setVersionCode(e.target.value)} /></label>
            <button className="primary" type="submit" disabled={busy}>ثبت نسخه</button>
          </form>
          <p className="muted">نسخه منتشرشده و معیارهای آن قابل تغییر نیستند.</p>
        </section>
        <section className="panel">
          <h2>۳. تعریف معیار</h2>
          <form className="settingsForm" onSubmit={createCriterion}>
            <label>نسخه پیش‌نویس *<select required value={criterionVersion} onChange={e => setCriterionVersion(e.target.value)}>
              <option value="">انتخاب نسخه</option>{draftVersions.map(v => <option key={v.id} value={v.id}>{versionsByTemplate.get(v.template)?.code} / {v.version_code}</option>)}
            </select></label>
            <label>کد معیار *<input dir="ltr" required value={criterionCode} onChange={e => setCriterionCode(e.target.value)} /></label>
            <label>شرح معیار *<input required value={criterionTitle} onChange={e => setCriterionTitle(e.target.value)} /></label>
            <label>نوع پاسخ<select value={criterionType} onChange={e => setCriterionType(e.target.value)}>
              <option value="boolean">بله / خیر</option><option value="number">عدد بین ۰ و ۱۰۰</option>
              <option value="choice">انتخاب از فهرست</option><option value="text">متن</option>
            </select></label>
            {criterionType === "choice" && <label>گزینه‌ها (جداشده با «،»)<input required value={criterionChoices} onChange={e => setCriterionChoices(e.target.value)} /></label>}
            <button className="primary" type="submit" disabled={busy}>ثبت معیار</button>
          </form>
        </section>
        <section className="panel">
          <h2>۴. انتشار نسخه</h2>
          <p className="muted">مالک قالب نمی‌تواند همان نسخه را منتشر کند؛ مجوز بازبینی مستقل لازم است.</p>
          <label>نسخه<select value={publishVersion} onChange={e => setPublishVersion(e.target.value)}>
            <option value="">انتخاب نسخه</option>{draftVersions.map(v => <option key={v.id} value={v.id}>{versionsByTemplate.get(v.template)?.title} / {v.version_code}</option>)}
          </select></label>
          <button className="primary" disabled={busy || !publishVersion} onClick={() => void post(
            "/assessment-template-versions/" + publishVersion + "/publish/", {}, "نسخه ارزیابی منتشر و قفل شد.",
          )}>انتشار با تأیید مستقل</button>
        </section>
      </div>

      <section className="panel">
        <h2>۵. شروع ارزیابی</h2>
        <form className="settingsForm" onSubmit={createRun}>
          <label>نسخه منتشرشده<select required value={runVersion} onChange={e => setRunVersion(e.target.value)}>
            <option value="">انتخاب نسخه</option>{published.map(v => <option key={v.id} value={v.id}>{versionsByTemplate.get(v.template)?.title} / {v.version_code}</option>)}
          </select></label>
          <label>عنوان ارزیابی<input required value={runTitle} onChange={e => setRunTitle(e.target.value)} /></label>
          <label>مالک<select required value={runOwner} onChange={e => setRunOwner(e.target.value)}>
            <option value="">انتخاب مالک</option>{users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
          </select></label>
          <label>واحد سازمانی<select value={runUnit} onChange={e => setRunUnit(e.target.value)}>
            <option value="">کل سازمان</option>{units.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
          </select></label>
          <button className="primary" type="submit" disabled={busy}>ایجاد ارزیابی با نسخه ثابت</button>
        </form>
      </section>

      <section className="panel">
        <h2>۶. اجرا و پاسخ به معیارها</h2>
        <label>ارزیابی<select value={selected} onChange={e => { setSelected(e.target.value); void loadRun(e.target.value); }}>
          <option value="">انتخاب ارزیابی</option>{runs.map(r => <option key={r.id} value={r.id}>{r.title} ({r.status})</option>)}
        </select></label>
        {summary && <p className="muted">پاسخ‌ها: {summary.answered_count}/{summary.items_count} ·
          امتیاز: {summary.score_percent ?? "بدون امتیاز عددی"} ·
          بررسی کاربردپذیری باقی‌مانده: {summary.applicability_reviews_missing}
          {summary.is_partial_score && " — امتیاز فقط معیارهای عددی و بله/خیر را پوشش می‌دهد"}</p>}
        {!items.length ? <EmptyState title="معیاری برای نمایش انتخاب نشده است." /> :
          <div className="grid">
            {items.map(item => {
              const existing = item.answer?.value;
              const answer = answers[item.id] ?? (existing === undefined ? "" : String(existing));
              const itemDecisions = decisions.filter(d => d.generic_item === item.id);
              const reviewed = itemDecisions.find(d => d.reviewed_at);
              return <section key={item.id} className="panel">
                <h3>{item.criterion_code_snapshot} — {item.criterion_title_snapshot}</h3>
                <p className="muted">نوع پاسخ: {item.response_type_snapshot} · {item.required_snapshot ? "الزامی" : "اختیاری"}</p>
                {item.response_type_snapshot === "boolean" || item.response_type_snapshot === "choice" ?
                  <select disabled={busy || current?.status === "completed"} value={answer} onChange={e => setAnswers(p => ({ ...p, [item.id]: e.target.value }))}>
                    <option value="">انتخاب پاسخ</option>
                    {(item.response_type_snapshot === "boolean" ? ["true", "false"] : item.options_snapshot).map(v =>
                      <option key={v} value={v}>{v === "true" ? "بله" : v === "false" ? "خیر" : v}</option>)}
                  </select> : item.response_type_snapshot === "number" ?
                  <input type="number" min="0" max="100" step="0.001" disabled={busy || current?.status === "completed"} value={answer} onChange={e => setAnswers(p => ({ ...p, [item.id]: e.target.value }))} /> :
                  <textarea disabled={busy || current?.status === "completed"} value={answer} onChange={e => setAnswers(p => ({ ...p, [item.id]: e.target.value }))} />
                }
                <button className="secondaryLink" disabled={busy || current?.status === "completed"} onClick={() => saveAnswer(item)}>ثبت پاسخ</button>
                {item.applicability_mode_snapshot === "review" && (
                  <div>
                    <p className="muted">کاربردپذیری: {reviewed ? reviewed.decision + " (بازبینی‌شده)" : "نیازمند بررسی مستقل"}</p>
                    <select disabled={busy || current?.status === "completed"} value={decision[item.id] ?? "applicable"} onChange={e => setDecision(p => ({ ...p, [item.id]: e.target.value }))}>
                      <option value="applicable">کاربرد دارد</option><option value="not_applicable">کاربرد ندارد</option>
                    </select>
                    <textarea disabled={busy || current?.status === "completed"} placeholder="دلیل کاربردپذیری/عدم کاربردپذیری" value={reason[item.id] ?? ""} onChange={e => setReason(p => ({ ...p, [item.id]: e.target.value }))} />
                    <button className="secondaryLink" disabled={busy || !reason[item.id]?.trim() || current?.status === "completed"}
                      onClick={() => void post("/assessment-applicability-decisions/", {
                        generic_item: item.id, decision: decision[item.id] ?? "applicable",
                        rationale: reason[item.id],
                      }, "پیشنهاد کاربردپذیری ثبت شد؛ بازبینی مستقل لازم است.")}>ثبت پیشنهاد</button>
                  </div>
                )}
              </section>;
            })}
          </div>
        }
        {pendingDecisions.length > 0 && <div className="panel">
          <h3>تصمیمات نیازمند بازبینی مستقل</h3>
          {pendingDecisions.map(d => <div key={d.id}>
            <p>{d.decision} — {d.rationale}</p>
            <button className="secondaryLink" disabled={busy} onClick={() => void post(
              "/assessment-applicability-decisions/" + d.id + "/review/", {},
              "تصمیم کاربردپذیری بازبینی و قفل شد.",
            )}>ثبت بازبینی مستقل</button>
          </div>)}
        </div>}
        <button className="primary" disabled={busy || !selected || current?.status === "completed"} onClick={() => void complete()}>
          تکمیل و قفل‌کردن ارزیابی
        </button>
      </section>
      <section className="panel">
        <h2>قالب‌ها و سوابق ارزیابی</h2>
        <p className="muted">نسخه‌های منتشرشده غیرقابل ویرایش‌اند. سوابق ارزیابی و انطباق موجود نیز بدون تغییر باقی می‌مانند.</p>
        <table className="dataTable"><thead><tr><th>قالب</th><th>نسخه‌ها</th><th>معیارها</th></tr></thead><tbody>
          {templates.map(t => <tr key={t.id}>
            <td>{t.code} — {t.title}</td><td>{versions.filter(v => v.template === t.id).length}</td>
            <td>{criteria.filter(c => versions.some(v => v.template === t.id && v.id === c.version)).length}</td>
          </tr>)}
        </tbody></table>
      </section>
    </main>
  );
}
