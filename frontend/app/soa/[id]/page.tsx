"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";

type Choice = "undecided" | "included" | "excluded";
type Kind = "annex_a" | "additional";
type Decision = {
  id: string; control: string; control_code: string; reference_kind: Kind;
  source_identifier: string; decision: Choice; rationale: string;
  control_implementation: string | null; risk_treatment: string | null;
  approval_status: "draft_unapproved";
};
type Register = {
  id: string; title: string; revision: number; status: "draft";
  framework_version: string; organization_unit: string; notice: string;
  is_formal_statement_of_applicability: false; decisions: Decision[];
};
type Control = { id: string; code: string; title: string; status: string; is_global: boolean };
type Implementation = {
  id: string; organization_unit: string; control: string;
  control_code: string; implementation_status: string; effectiveness: string;
};
type Treatment = { id: string; risk: string; description: string; approval_status: string; status: string };
type RiskControl = { id: string; risk: string; control_implementation: string };
type Finding = { decision_id: string; source_identifier: string; reference_kind: Kind; codes: string[] };
type Readiness = {
  register_id: string; formal_attestation_allowed: false; is_formal_statement_of_applicability: false;
  status: string; approval_workflow: string; source_control_inventory_coverage: string;
  locked_framework_content_integrity: "unlocked" | "checksum_missing" | "checksum_mismatch" | "checksum_unverifiable" | "internal_checksum_matches";
  integrity_scope: string; evidence_sufficiency: string;
  counts: { decisions: number; included: number; excluded: number; undecided: number; decisions_with_findings: number };
  findings: Finding[]; register_findings: string[]; blocking_external_prerequisites: string[];
};
type NumericDiff = {
  comparison_type: "numeric_structure_only_non_attesting";
  reference: string; formal_attestation_allowed: false;
  source_rights_review: "not_verified";
  comparison_summary: {
    reference_numeric_ids: number; matched_numeric_identifiers: number;
    missing_numeric_identifiers: number; unrecognized_annex_a_identifiers: number;
    undecided_numeric_identifiers: number; additional_organizational_control_decisions: number;
  };
  missing_numeric_ids: string[];
  unrecognized_annex_a_ids: string[];
  undecided_numeric_ids: string[];
  notice: string;
};

type EditForm = {
  control: string; reference_kind: Kind; source_identifier: string;
  decision: Choice; rationale: string; control_implementation: string; risk_treatment: string;
};
const EMPTY: EditForm = {
  control: "", reference_kind: "annex_a", source_identifier: "",
  decision: "undecided", rationale: "", control_implementation: "", risk_treatment: "",
};
const statuses: Record<Choice, string> = {
  included: "انتخاب شده", excluded: "مستثنا شده", undecided: "نیازمند تصمیم",
};
const issueLabels: Record<string, string> = {
  decision_undecided: "تصمیم هنوز ثبت نشده است",
  decision_rationale_missing: "دلیل انتخاب یا استثنا ثبت نشده",
  control_reference_invalid: "مرجع کنترل حذف‌شده یا خارج از محدوده است",
  implementation_not_linked: "برای کنترل انتخاب‌شده، پیاده‌سازی مرتبط نشده",
  implementation_scope_invalid: "محدوده یا مالکیت پیاده‌سازی کنترل معتبر نیست",
  implementation_not_completed: "پیاده‌سازی کنترل تکمیل نشده",
  implementation_effectiveness_not_assessed: "اثربخشی کنترل ارزیابی نشده",
  no_current_scoped_evidence_link: "شاهد غیرمنقضی در همان واحد و مشتری مرتبط نشده",
  excluded_control_has_conflicting_links: "کنترل مستثنا پیوند متعارض دارد",
  risk_treatment_scope_invalid: "درمان ریسک خارج از محدوده است",
  missing_risk_control_link: "درمان ریسک به همین پیاده‌سازی کنترل متصل نیست",
  risk_treatment_not_approved: "درمان ریسک تأیید نشده",
  empty_control_decision_register: "این پرونده هیچ تصمیم کنترلی ندارد",
  source_control_inventory_not_verified: "فهرست کامل کنترل‌های مرجع راستی‌آزمایی نشده",
  rights_and_content_review_not_verified: "حقوق استفاده و اعتبار محتوای مرجع بررسی نشده",
  human_approval_snapshot_not_available: "تصویب انسانی و نسخه قفل‌شده SoA موجود نیست",
  framework_content_unlocked: "قفل نسخه چارچوب برداشته شده؛ اعتبار داخلی نسخه برقرار نیست",
  framework_content_checksum_missing: "نسخه قفل شده اما Checksum داخلی ثبت نشده است",
  framework_content_checksum_mismatch: "Checksum محتوای چارچوب با نسخه قفل‌شده تطبیق ندارد؛ نیازمند بررسی",
  framework_content_checksum_unverifiable: "بازمحاسبه Checksum داخلی چارچوب ممکن نشد",
};

function list<T>(payload: T[] | { results?: T[] }): T[] {
  return Array.isArray(payload) ? payload : payload.results ?? [];
}
function message(body: unknown): string {
  if (typeof body === "string") return body;
  if (!body || typeof body !== "object") return "درخواست ناموفق بود.";
  return Object.entries(body as Record<string, unknown>)
    .flatMap(([key, value]) => Array.isArray(value) ? value.map(v => key + ": " + String(v)) :
      typeof value === "string" ? [key + ": " + value] : [])
    .join(" • ") || "درخواست ناموفق بود؛ داده‌ها و مجوزها را بررسی کنید.";
}

export default function SoADraftDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [register, setRegister] = useState<Register | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [numericDiff, setNumericDiff] = useState<NumericDiff | null>(null);
  const [numericDiffLoading, setNumericDiffLoading] = useState(false);
  const [numericDiffError, setNumericDiffError] = useState("");
  const [controls, setControls] = useState<Control[]>([]);
  const [implementations, setImplementations] = useState<Implementation[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [riskLinks, setRiskLinks] = useState<RiskControl[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingOptions, setLoadingOptions] = useState(false);
  const [optionsError, setOptionsError] = useState("");
  const [optionsNotice, setOptionsNotice] = useState("");
  const [error, setError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showEditor, setShowEditor] = useState(false);
  const [form, setForm] = useState<EditForm>(EMPTY);

  async function load() {
    setLoading(true); setError("");
    try {
      const [a, b] = await Promise.all([
        apiFetch("/soa/registers/" + encodeURIComponent(id) + "/"),
        apiFetch("/soa/registers/" + encodeURIComponent(id) + "/readiness/"),
      ]);
      const data = await a.json().catch(() => ({}));
      if (!a.ok) throw new Error(message(data));
      const summary = await b.json().catch(() => ({}));
      if (!b.ok) throw new Error(message(summary));
      setRegister(data as Register);
      setReadiness(summary as Readiness);
    } catch (e) {
      setError(e instanceof Error ? e.message : "امکان دریافت پرونده وجود ندارد.");
      setRegister(null); setReadiness(null);
    } finally { setLoading(false); }
  }

  async function loadNumericDiff() {
    setNumericDiffLoading(true);
    setNumericDiffError("");
    try {
      const response = await apiFetch(
        "/soa/registers/" + encodeURIComponent(id) +
        "/reference-diff/?reference=iso-iec-27001-2022-annex-a-structure-only",
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(message(payload));
      setNumericDiff(payload as NumericDiff);
    } catch (e) {
      setNumericDiffError(e instanceof Error ? e.message : "مقایسه شناسه‌های عددی ممکن نشد.");
      setNumericDiff(null);
    } finally { setNumericDiffLoading(false); }
  }

  async function loadOptions() {
    setLoadingOptions(true); setOptionsError(""); setOptionsNotice("");
    try {
      const [a, b, c, d] = await Promise.all([
        apiFetch("/controls/?page_size=200"),
        apiFetch("/control-implementations/?page_size=200"),
        apiFetch("/risk-treatments/?page_size=200"),
        apiFetch("/risk-controls/?page_size=200"),
      ]);
      if (!a.ok) {
        throw new Error("فهرست کنترل‌های مجاز قابل دریافت نیست و بدون تعیین کنترل نمی‌توان تصمیم جدید ثبت کرد.");
      }
      setControls(list<Control>(await a.json()));
      setImplementations(b.ok ? list<Implementation>(await b.json()) : []);
      setTreatments(c.ok ? list<Treatment>(await c.json()) : []);
      setRiskLinks(d.ok ? list<RiskControl>(await d.json()) : []);
      if (!b.ok || !c.ok || !d.ok) {
        setOptionsNotice("برخی داده‌های اختیاری پیاده‌سازی و ریسک در دسترس نیستند. ثبت تصمیم بدون این پیوندها ممکن است؛ مجوزها را از مدیر بخواهید.");
      }
    } catch (e) {
      setOptionsError(e instanceof Error ? e.message : "داده‌های مرجع در دسترس نیستند.");
      setControls([]); setImplementations([]); setTreatments([]); setRiskLinks([]);
    } finally { setLoadingOptions(false); }
  }

  useEffect(() => {
    void load();
    // API always enforces tenant and unit permissions on the requested UUID.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const existingControls = useMemo(() => new Set(register?.decisions.map(x => x.control) ?? []), [register]);
  const allowedControls = controls.filter(x => (
    (x.status === "active" || !x.is_global) &&
    (editingId ? true : !existingControls.has(x.id))
  ));
  const implementationsForDecision = implementations.filter(x =>
    register && x.organization_unit === register.organization_unit && x.control === form.control
  );
  const selectedImplementation = form.decision === "included" ? form.control_implementation : "";
  const linkedRiskIds = new Set(riskLinks.filter(x => x.control_implementation === selectedImplementation).map(x => x.risk));
  const treatmentsForDecision = treatments.filter(x => linkedRiskIds.has(x.risk));
  const issueById = useMemo(
    () => new Map((readiness?.findings ?? []).map(x => [x.decision_id, x.codes])),
    [readiness],
  );

  function update<K extends keyof EditForm>(key: K, value: EditForm[K]) {
    setForm(current => ({ ...current, [key]: value }));
  }
  function openNew() {
    setForm(EMPTY); setEditingId(null); setShowEditor(true); setSaveError("");
    void loadOptions();
  }
  function openEdit(decision: Decision) {
    setEditingId(decision.id); setShowEditor(true); setSaveError("");
    setForm({
      control: decision.control,
      reference_kind: decision.reference_kind,
      source_identifier: decision.source_identifier,
      decision: decision.decision,
      rationale: decision.rationale,
      control_implementation: decision.control_implementation ?? "",
      risk_treatment: decision.risk_treatment ?? "",
    });
    void loadOptions();
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaveError("");
    if (!register || !form.control || !form.source_identifier.trim()) {
      setSaveError("کنترل و شناسه مرجع باید مشخص شوند."); return;
    }
    if (form.decision !== "undecided" && !form.rationale.trim()) {
      setSaveError("برای انتخاب یا استثنای کنترل باید دلیل کارشناسی ثبت شود."); return;
    }
    if (form.risk_treatment && (!form.control_implementation || !treatmentsForDecision.some(x => x.id === form.risk_treatment))) {
      setSaveError("درمان ریسک باید با پیاده‌سازی انتخاب‌شده رابطه ثبت‌شده داشته باشد."); return;
    }
    if (!editingId && !allowedControls.some(x => x.id === form.control)) {
      setSaveError("کنترل انتخاب‌شده قبلاً در این پرونده ثبت شده یا در فهرست مجاز نیست."); return;
    }
    setSaving(true);
    try {
      const base = "/soa/registers/" + encodeURIComponent(register.id) + "/decisions/";
      const isPatch = Boolean(editingId);
      const response = await apiFetch(isPatch ? base + encodeURIComponent(editingId as string) + "/" : base, {
        method: isPatch ? "PATCH" : "POST",
        body: JSON.stringify({
          ...(!isPatch ? {
            control: form.control, reference_kind: form.reference_kind, source_identifier: form.source_identifier.trim(),
          } : {}),
          decision: form.decision,
          rationale: form.rationale.trim(),
          control_implementation: form.decision === "included" ? form.control_implementation || null : null,
          risk_treatment: form.decision === "included" ? form.risk_treatment || null : null,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(message(result));
      setShowEditor(false); setEditingId(null); setForm(EMPTY);
      // Numeric comparison is opt-in and may be stale after decisions change.
      setNumericDiff(null);
      await load();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "ذخیره تصمیم ناموفق بود.");
    } finally { setSaving(false); }
  }

  return <main className="adminPage" dir="rtl">
    <div className="pageHead">
      <div>
        <Link href="/soa">← دفتر پیش‌نویس‌ها</Link>
        <h1>{register?.title ?? "پرونده SoA"}</h1>
        <p>ثبت تصمیم و بازبینی نواقص کنترل‌ها؛ هیچ خروجی رسمی یا تأیید استاندارد از این صفحه صادر نمی‌شود.</p>
      </div>
      <button type="button" className="secondaryButton" onClick={() => void load()} disabled={loading}>بازبینی مجدد</button>
    </div>
    <section className="adminCard">
      <p role="status"><strong>DRAFT / NOT APPROVED — پیش‌نویس تأییدنشده.</strong> ارتباط کنترل، ریسک یا شاهد، اثبات انطباق نیست.</p>
      {register && <p>بازنگری {register.revision} · نسخه چارچوب: <code dir="ltr">{register.framework_version}</code> · وضعیت: پیش‌نویس</p>}
    </section>
    {loading && <p>در حال بارگذاری اطلاعات پرونده…</p>}
    {error && <p className="errorText" role="alert">{error}</p>}

    {register && readiness && <section className="adminCard">
      <h2>پیش‌بررسی نواقص و آمادگی داده‌ها</h2>
      <p>این بررسی فقط مشکلات قابل مشاهده را نشان می‌دهد و در هیچ حالتی مجوز تأیید SoA صادر نمی‌کند.</p>
      <div className="formGrid">
        <p>کل تصمیم‌ها: <strong>{readiness.counts.decisions}</strong></p>
        <p>انتخاب شده: <strong>{readiness.counts.included}</strong></p>
        <p>مستثنا: <strong>{readiness.counts.excluded}</strong></p>
        <p>بدون تصمیم: <strong>{readiness.counts.undecided}</strong></p>
        <p>دارای نقص: <strong>{readiness.counts.decisions_with_findings}</strong></p>
      </div>
      <p><strong>یکپارچگی داخلی محتوای نسخه قفل‌شده:</strong> {
        readiness.locked_framework_content_integrity === "internal_checksum_matches" ?
          "Checksum داخلی با محتوای نسخه مطابقت دارد (صرفاً یکپارچگی داخلی، نه اصالت استاندارد)" :
        readiness.locked_framework_content_integrity === "checksum_missing" ?
          "Checksum داخلی ثبت نشده" :
        readiness.locked_framework_content_integrity === "checksum_mismatch" ?
          "هشدار: محتوای نسخه با Checksum قفل‌شده متفاوت است" :
        readiness.locked_framework_content_integrity === "unlocked" ?
          "نسخه قفل نیست" : "بازمحاسبه یکپارچگی ممکن نشد"
      }</p>
      <p>این کنترل نه اصالت PDF استاندارد و نه حق قانونی استفاده از آن را تأیید می‌کند.</p>
      <h3>موانع عمومی که همچنان باز هستند</h3>
      <ul>{readiness.register_findings.map(code => <li key={code}>{issueLabels[code] ?? code}</li>)}</ul>
      <p><strong>اعتبار کامل فهرست کنترل‌های مرجع:</strong> بررسی نشده · <strong>ارزش شواهد:</strong> نیازمند بازبینی انسانی</p>
      <p><strong>گردش تأیید رسمی:</strong> موجود نیست.</p>
    </section>}

    {register && <section className="adminCard">
      <h2>مقایسه اختیاری شناسه‌های عددی Annex A نسخه ۲۰۲۲</h2>
      <p>این مقایسه فقط ساختار عددی ۹۳ شناسه مرجع را بررسی می‌کند؛ هویت چارچوب این پرونده، مجوز متن استاندارد، ضرورت انتخاب کنترل‌ها و انطباق سازمان را تأیید نمی‌کند. همه ۹۳ کنترل لزوماً برای این سازمان لازم نیستند.</p>
      <button type="button" className="secondaryButton" onClick={() => void loadNumericDiff()} disabled={numericDiffLoading}>
        {numericDiffLoading ? "در حال مقایسه…" : "مقایسه عددی شناسه‌های ثبت‌شده"}
      </button>
      {numericDiffError && <p role="alert" className="errorText">{numericDiffError}</p>}
      {numericDiff && <div>
        <p role="status"><strong>صرفاً مقایسه ساختاری؛ نه گواهی یا تأیید SoA.</strong></p>
        <div className="formGrid">
          <p>شناسه‌های مرجع: <strong>{numericDiff.comparison_summary.reference_numeric_ids}</strong></p>
          <p>دارای شناسه عددی منطبق: <strong>{numericDiff.comparison_summary.matched_numeric_identifiers}</strong></p>
          <p>شناسه‌های بدون تصمیم ثبت‌شده: <strong>{numericDiff.comparison_summary.missing_numeric_identifiers}</strong></p>
          <p>شناسه‌های ناشناخته: <strong>{numericDiff.comparison_summary.unrecognized_annex_a_identifiers}</strong></p>
          <p>شناسه‌های دارای تصمیم نامشخص: <strong>{numericDiff.comparison_summary.undecided_numeric_identifiers}</strong></p>
          <p>تصمیم‌های کنترل افزوده سازمانی: <strong>{numericDiff.comparison_summary.additional_organizational_control_decisions}</strong></p>
        </div>
        {numericDiff.missing_numeric_ids.length > 0 && <details>
          <summary>شناسه‌های عددی فاقد تصمیم ({numericDiff.missing_numeric_ids.length})</summary>
          <p dir="ltr">{numericDiff.missing_numeric_ids.join(" · ")}</p>
        </details>}
        {numericDiff.unrecognized_annex_a_ids.length > 0 && <details>
          <summary>شناسه‌های Annex A ناشناخته</summary>
          <p dir="ltr">{numericDiff.unrecognized_annex_a_ids.join(" · ")}</p>
        </details>}
        {numericDiff.undecided_numeric_ids.length > 0 && <details>
          <summary>شناسه‌های دارای تصمیم نامشخص</summary>
          <p dir="ltr">{numericDiff.undecided_numeric_ids.join(" · ")}</p>
        </details>}
        <p><strong>حق استفاده از استاندارد:</strong> بررسی نشده · <strong>تأیید انسانی:</strong> انجام نشده</p>
      </div>}
    </section>}

    {register && <section className="adminCard">
      <div className="pageHead"><div><h2>تصمیم‌های کنترلی</h2><p>ثبت شناسه عددی به معنی تأیید تطابق آن با منبع استاندارد نیست.</p></div>
        <button type="button" className="primary" onClick={openNew}>+ تصمیم پیش‌نویس</button>
      </div>
      {register.decisions.length === 0 && <p className="emptyState">هنوز هیچ تصمیمی ثبت نشده است؛ این پرونده آماده تأیید نیست.</p>}
      {register.decisions.length > 0 && <div className="tableWrap"><table>
        <thead><tr><th>شناسه مرجع</th><th>کنترل</th><th>وضعیت</th><th>نواقص</th><th>اقدام</th></tr></thead>
        <tbody>{register.decisions.map(row => <tr key={row.id}>
          <td><code dir="ltr">{row.source_identifier}</code>{row.reference_kind === "additional" && " (کنترل افزوده)"}</td>
          <td>{row.control_code}</td><td>{statuses[row.decision]}</td>
          <td>{(issueById.get(row.id) ?? []).length ?
            <ul>{(issueById.get(row.id) ?? []).map(code => <li key={code}>{issueLabels[code] ?? code}</li>)}</ul> :
            "نقص ردیفی شناسایی نشد؛ بازبینی انسانی همچنان الزامی است"}</td>
          <td><button className="secondaryButton" type="button" onClick={() => openEdit(row)}>ویرایش</button></td>
        </tr>)}</tbody>
      </table></div>}
    </section>}

    {register && showEditor && <section className="adminCard">
      <h2>{editingId ? "ویرایش تصمیم پیش‌نویس" : "ثبت تصمیم جدید"}</h2>
      <p>کنترل انتخاب‌شده و شناسه مرجع پس از ایجاد تغییرناپذیرند. در صورت نیاز به اصلاح منبع، به مدیر سامانه اطلاع دهید.</p>
      {loadingOptions && <p>دریافت کنترل‌ها و ارتباط‌های ریسک…</p>}
      {optionsError && <p className="errorText" role="alert">{optionsError}</p>}
      {optionsNotice && <p role="status">{optionsNotice}</p>}
      <form className="settingsForm" onSubmit={save}>
        <label>کنترل *
          <select required disabled={Boolean(editingId)} value={form.control} onChange={e => {
            setForm(current => ({ ...current, control: e.target.value, control_implementation: "", risk_treatment: "" }));
          }}>
            <option value="">انتخاب کنترل قابل مشاهده</option>
            {allowedControls.map(x => <option key={x.id} value={x.id}>{x.code} — {x.title}</option>)}
            {editingId && !allowedControls.some(x => x.id === form.control) &&
              <option value={form.control}>کنترل ثبت‌شده قبلی</option>}
          </select>
        </label>
        <label>نوع مرجع *
          <select disabled={Boolean(editingId)} value={form.reference_kind} onChange={e => update("reference_kind", e.target.value as Kind)}>
            <option value="annex_a">شناسه ارجاعی Annex A</option>
            <option value="additional">کنترل افزوده سازمانی</option>
          </select>
        </label>
        <label>شناسه منبع *
          <input required maxLength={120} disabled={Boolean(editingId)} dir="ltr" value={form.source_identifier}
            onChange={e => update("source_identifier", e.target.value)}
            placeholder="برای مثال A.5.1 — باید با مرجع مجاز کنترل شود" />
        </label>
        <label>تصمیم *
          <select value={form.decision} onChange={e => {
            const value = e.target.value as Choice;
            setForm(current => ({
              ...current, decision: value,
              control_implementation: value === "included" ? current.control_implementation : "",
              risk_treatment: value === "included" ? current.risk_treatment : "",
            }));
          }}>
            <option value="undecided">بدون تصمیم</option><option value="included">انتخاب شود</option>
            <option value="excluded">مستثنا شود</option>
          </select>
        </label>
        <label>دلیل کارشناسی {form.decision === "undecided" ? "(اختیاری)" : "*"}
          <textarea rows={3} required={form.decision !== "undecided"} value={form.rationale}
            onChange={e => update("rationale", e.target.value)} placeholder="دلیل واقعی انتخاب یا استثنا را بنویسید؛ متن استاندارد را کپی نکنید." />
        </label>
        {form.decision === "included" && <label>پیاده‌سازی کنترل (اختیاری)
          <select value={form.control_implementation} onChange={e =>
            setForm(current => ({ ...current, control_implementation: e.target.value, risk_treatment: "" }))}>
            <option value="">بدون پیوند</option>
            {implementationsForDecision.map(x => <option key={x.id} value={x.id}>
              {x.control_code} — {x.implementation_status} / {x.effectiveness}
            </option>)}
          </select>
        </label>}
        {form.decision === "included" && form.control_implementation && <label>درمان ریسک دارای ارتباط با همین پیاده‌سازی (اختیاری)
          <select value={form.risk_treatment} onChange={e => update("risk_treatment", e.target.value)}>
            <option value="">بدون پیوند</option>
            {treatmentsForDecision.map(x => <option key={x.id} value={x.id}>
              {x.description || x.id} — {x.approval_status} / {x.status}
            </option>)}
          </select>
        </label>}
        {saveError && <p className="errorText" role="alert">{saveError}</p>}
        <div className="buttonRow">
          <button type="submit" className="primary" disabled={saving || loadingOptions || Boolean(optionsError)}>
            {saving ? "در حال ذخیره…" : "ذخیره پیش‌نویس"}
          </button>
          <button type="button" className="secondaryButton" onClick={() => setShowEditor(false)}>انصراف</button>
        </div>
      </form>
    </section>}
  </main>;
}
