"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";
import { Button, FormField, Input, Select, StatusMessage, Textarea } from "../../../components/ui";

type RiskEvaluation = { score: string; level: string; methodology_name?: string; likelihood: string; impact: string };
type Risk = { id: string; code: string; title: string; scenario: string; cause: string; consequence: string; status: string; owner_display: string; organization_name?: string; asset_title?: string; latest_evaluations: Record<string, RiskEvaluation> };
type Methodology = { id: string; name: string; status: string; is_default?: boolean };
type Member = { id: number; username: string; first_name?: string; last_name?: string; membership_active?: boolean };
type TreatmentAction = { id: string; title: string; progress: number; status: string };
type Treatment = { id: string; strategy: string; description: string; owner_display: string; target_date?: string; status: string; approval_status: string; actions: TreatmentAction[] };
type EvaluationForm = { methodology: string; kind: string; likelihood: string; impact: string; rationale: string };
type TreatmentForm = { strategy: string; owner: string; description: string; target_date: string };
type ActionForm = { treatmentId: string; owner: string; title: string; due_date: string };

const evalKinds = [
  { id: "inherent", title: "ذاتی" },
  { id: "current", title: "جاری" },
  { id: "residual", title: "باقیمانده" },
  { id: "target", title: "هدف" },
];

function unpack<T>(data: T[] | { results?: T[] }) {
  return Array.isArray(data) ? data : data.results ?? [];
}

function userLabel(u: Member) {
  const full = (String(u.first_name ?? "") + " " + String(u.last_name ?? "")).trim();
  return full ? full + " (" + u.username + ")" : u.username;
}

function errorMessage(body: unknown, fallback: string) {
  if (!body || typeof body !== "object") return fallback;
  const items = Object.entries(body as Record<string, unknown>)
    .flatMap(([key, value]) => (Array.isArray(value) ? value : typeof value === "string" ? [value] : [])
      .map(item => key + ": " + String(item)));
  return items.slice(0, 6).join(" • ") || fallback;
}

export default function RiskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [risk, setRisk] = useState<Risk | null>(null);
  const [methodologies, setMethodologies] = useState<Methodology[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [referenceError, setReferenceError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeTone, setNoticeTone] = useState<"success" | "danger">("success");
  const [busy, setBusy] = useState(false);
  const [evaluationOpen, setEvaluationOpen] = useState(false);
  const [treatmentOpen, setTreatmentOpen] = useState(false);
  const [evaluation, setEvaluation] = useState<EvaluationForm>({ methodology: "", kind: "residual", likelihood: "", impact: "", rationale: "" });
  const [treatment, setTreatment] = useState<TreatmentForm>({ strategy: "reduce", owner: "", description: "", target_date: "" });
  const [action, setAction] = useState<ActionForm>({ treatmentId: "", owner: "", title: "", due_date: "" });

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    setReferenceError("");
    try {
      const [a, b, c, d] = await Promise.all([
        apiFetch("/risks/" + encodeURIComponent(id) + "/"),
        apiFetch("/risk-methodologies/"),
        apiFetch("/risk-treatments/?risk=" + encodeURIComponent(id)),
        apiFetch("/tenant-users/"),
      ]);
      if (!a.ok) throw new Error(a.status === 403 ? "مجوز مشاهده ریسک وجود ندارد." : "دریافت ریسک ممکن نیست.");
      setRisk(await a.json() as Risk);
      if (!c.ok) throw new Error("برنامه‌های درمان ریسک قابل دریافت نیستند.");
      const body = await c.json() as Treatment[] | { results?: Treatment[] };
      setTreatments(unpack(body));
      if (!b.ok || !d.ok) {
        setMethodologies([]); setMembers([]);
        setReferenceError("داده مرجع روش ارزیابی یا کاربران فعال در دسترس نیست؛ فرم‌های تغییر غیرفعال هستند.");
      } else {
        const [methodBody, memberBody] = await Promise.all([b.json(), d.json()]);
        setMethodologies(unpack(methodBody as Methodology[] | { results?: Methodology[] })
          .filter(item => item.status === "active"));
        setMembers(unpack(memberBody as Member[] | { results?: Member[] })
          .filter(item => item.membership_active !== false));
      }
    } catch (error) {
      setRisk(null); setTreatments([]); setMethodologies([]); setMembers([]);
      setLoadError(error instanceof Error ? error.message : "ارتباط با سامانه برقرار نیست.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  function fail(text: string) { setNoticeTone("danger"); setNotice(text); }
  function pass(text: string) { setNoticeTone("success"); setNotice(text); }
  const canWrite = !loading && !busy && !loadError && !referenceError && Boolean(risk);

  async function submitEvaluation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (!canWrite || !evaluation.methodology || !evaluation.likelihood || !evaluation.impact) {
      fail("روش ارزیابی، احتمال و اثر را به‌صورت صریح انتخاب یا وارد کنید."); return;
    }
    const chance = Number(evaluation.likelihood);
    const impact = Number(evaluation.impact);
    if (!Number.isFinite(chance) || !Number.isFinite(impact) || chance <= 0 || impact <= 0) {
      fail("احتمال و اثر باید اعداد مثبت مطابق مقیاس روش انتخابی باشند."); return;
    }
    setBusy(true);
    try {
      const response = await apiFetch("/risks/" + encodeURIComponent(id) + "/evaluate/", {
        method: "POST",
        body: JSON.stringify({
          methodology: evaluation.methodology,
          evaluation_type: evaluation.kind,
          likelihood: evaluation.likelihood,
          impact: evaluation.impact,
          rationale: evaluation.rationale.trim(),
        }),
      });
      if (!response.ok) throw new Error(errorMessage(await response.json().catch(() => null), "ثبت ارزیابی ریسک ناموفق بود."));
      setEvaluation({ methodology: "", kind: "residual", likelihood: "", impact: "", rationale: "" });
      setEvaluationOpen(false);
      await load();
      pass("ارزیابی با مقیاس روش انتخابی توسط سرور محاسبه و ثبت شد.");
    } catch (error) {
      fail(error instanceof Error ? error.message : "ارزیابی انجام نشد.");
    } finally { setBusy(false); }
  }

  async function submitTreatment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (!canWrite || !treatment.owner || !treatment.description.trim()) {
      fail("مالک فعال و شرح اقدام درمانی باید صریحاً ثبت شوند."); return;
    }
    setBusy(true);
    try {
      const response = await apiFetch("/risk-treatments/", {
        method: "POST",
        body: JSON.stringify({
          risk: id, owner: Number(treatment.owner), strategy: treatment.strategy,
          description: treatment.description.trim(), target_date: treatment.target_date || null,
          approval_status: "not_submitted", status: "planned",
        }),
      });
      if (!response.ok) throw new Error(errorMessage(await response.json().catch(() => null), "ثبت درمان ریسک ناموفق بود."));
      setTreatment({ strategy: "reduce", owner: "", description: "", target_date: "" });
      setTreatmentOpen(false);
      await load();
      pass("درمان ریسک در وضعیت «برنامه‌ریزی‌شده / ارسال‌نشده برای تصویب» ثبت شد.");
    } catch (error) { fail(error instanceof Error ? error.message : "درمان ریسک ثبت نشد."); }
    finally { setBusy(false); }
  }

  async function submitAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (!canWrite || !action.treatmentId || !action.owner || !action.title.trim()) {
      fail("اقدام، مالک و برنامه درمان مرتبط باید صریحاً انتخاب شوند."); return;
    }
    setBusy(true);
    try {
      const response = await apiFetch("/risk-treatments/" + encodeURIComponent(action.treatmentId) + "/actions/", {
        method: "POST",
        body: JSON.stringify({
          title: action.title.trim(), owner: Number(action.owner),
          due_date: action.due_date || null, description: "", priority: "medium",
          progress: 0, status: "todo",
        }),
      });
      if (!response.ok) throw new Error(errorMessage(await response.json().catch(() => null), "ثبت اقدام ناموفق بود."));
      setAction({ treatmentId: "", owner: "", title: "", due_date: "" });
      await load();
      pass("اقدام مرتبط با درمان ریسک، در وضعیت «در انتظار» ثبت شد.");
    } catch (error) { fail(error instanceof Error ? error.message : "ثبت اقدام انجام نشد."); }
    finally { setBusy(false); }
  }

  async function downloadRtp() {
    if (!risk || busy) return;
    setBusy(true); setNotice("");
    try {
      const response = await apiFetch("/risks/" + encodeURIComponent(id) + "/rtp/?format=docx");
      if (!response.ok) throw new Error("خروجی RTP مجاز یا در دسترس نیست.");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url; anchor.download = "RTP-" + risk.code + ".docx";
      document.body.appendChild(anchor); anchor.click(); anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      pass("فایل RTP دریافت شد؛ محتوای آن همچنان نیازمند بررسی و تأیید مسئول مربوط است.");
    } catch (error) { fail(error instanceof Error ? error.message : "ساخت RTP ناموفق بود."); }
    finally { setBusy(false); }
  }

  return (
    <main className="adminPage">
      <div className="pageHead">
        <div>
          <Link href="/risks">← فهرست ریسک‌ها</Link>
          <h1>{risk ? risk.code + " — " + risk.title : "جزئیات ریسک"}</h1>
          <p>{risk?.organization_name || "کل سازمان"} · مالک: {risk?.owner_display || "—"}</p>
        </div>
        <div className="headActions">
          <Button variant="secondary" disabled={!canWrite} onClick={() => { setNotice(""); setEvaluationOpen(open => !open); }}>{evaluationOpen ? "بستن ارزیابی" : "+ ارزیابی ریسک"}</Button>
          <Button variant="secondary" disabled={!canWrite} onClick={() => { setNotice(""); setTreatmentOpen(open => !open); }}>{treatmentOpen ? "بستن درمان" : "+ برنامه درمان"}</Button>
          <Button onClick={() => void downloadRtp()} disabled={!risk || busy}>دریافت RTP (DOCX)</Button>
        </div>
      </div>

      {notice && <StatusMessage tone={noticeTone}>{notice}</StatusMessage>}
      {loadError && <StatusMessage tone="danger">{loadError}</StatusMessage>}
      {referenceError && <StatusMessage tone="warning">{referenceError}</StatusMessage>}
      {loading && <p role="status">در حال بارگذاری ریسک و برنامه‌ها…</p>}

      {risk && (
        <>
          <section className="productControlStats" aria-label="ارزیابی‌های ثبت‌شده">
            {evalKinds.map(item => (
              <div className="productControlStat" key={item.id}>
                <span>ریسک {item.title}</span>
                <strong>{risk.latest_evaluations?.[item.id]?.score ?? "—"}</strong>
                <small>{risk.latest_evaluations?.[item.id]?.level ?? "ارزیابی نشده"}</small>
              </div>
            ))}
          </section>

          {evaluationOpen && (
            <form className="panel productControlForm" onSubmit={submitEvaluation}>
              <h2>ثبت ارزیابی با روش انتخاب‌شده</h2>
              <p className="muted">مقیاس و نتیجه توسط Backend اعتبارسنجی می‌شود؛ هیچ مقدار پیش‌فرضی به‌جای تصمیم ارزیاب ثبت نمی‌شود.</p>
              <div className="productControlFormGrid">
                <FormField label="روش ارزیابی" required>
                  <Select required value={evaluation.methodology} onChange={event => setEvaluation(x => ({ ...x, methodology: event.target.value }))}>
                    <option value="">روش را انتخاب کنید</option>
                    {methodologies.map(m => <option value={m.id} key={m.id}>{m.name}{m.is_default ? " (پیشنهادی سازمان)" : ""}</option>)}
                  </Select>
                </FormField>
                <FormField label="نوع ارزیابی" required>
                  <Select value={evaluation.kind} onChange={event => setEvaluation(x => ({ ...x, kind: event.target.value }))}>
                    {evalKinds.map(k => <option value={k.id} key={k.id}>{k.title}</option>)}
                  </Select>
                </FormField>
                <FormField label="احتمال وقوع" required hint="مطابق مقیاس تعریف‌شده روش">
                  <Input type="number" step="0.01" min="0.01" required value={evaluation.likelihood} onChange={event => setEvaluation(x => ({ ...x, likelihood: event.target.value }))} />
                </FormField>
                <FormField label="اثر" required hint="مطابق مقیاس تعریف‌شده روش">
                  <Input type="number" step="0.01" min="0.01" required value={evaluation.impact} onChange={event => setEvaluation(x => ({ ...x, impact: event.target.value }))} />
                </FormField>
                <FormField className="productFullField" label="دلایل ارزیابی">
                  <Textarea value={evaluation.rationale} onChange={event => setEvaluation(x => ({ ...x, rationale: event.target.value }))} />
                </FormField>
              </div>
              <Button busy={busy} type="submit" disabled={!canWrite || !methodologies.length}>ثبت ارزیابی</Button>
            </form>
          )}

          {treatmentOpen && (
            <form className="panel productControlForm" onSubmit={submitTreatment}>
              <h2>طرح درمان ریسک</h2>
              <div className="productControlFormGrid">
                <FormField label="استراتژی" required>
                  <Select value={treatment.strategy} onChange={event => setTreatment(x => ({ ...x, strategy: event.target.value }))}>
                    <option value="reduce">کاهش</option><option value="avoid">اجتناب</option>
                    <option value="transfer">انتقال</option><option value="accept">پذیرش پیشنهادی</option>
                  </Select>
                </FormField>
                <FormField label="مالک برنامه" required>
                  <Select required value={treatment.owner} onChange={event => setTreatment(x => ({ ...x, owner: event.target.value }))}>
                    <option value="">مالک فعال را انتخاب کنید</option>
                    {members.map(member => <option key={member.id} value={String(member.id)}>{userLabel(member)}</option>)}
                  </Select>
                </FormField>
                <FormField label="تاریخ هدف">
                  <Input type="date" dir="ltr" value={treatment.target_date} onChange={event => setTreatment(x => ({ ...x, target_date: event.target.value }))} />
                </FormField>
                <FormField label="شرح درمان" required className="productFullField">
                  <Textarea required value={treatment.description} onChange={event => setTreatment(x => ({ ...x, description: event.target.value }))} />
                </FormField>
              </div>
              <Button type="submit" busy={busy} disabled={!canWrite || !members.length}>ثبت پیش‌نویس درمان</Button>
            </form>
          )}

          <div className="grid">
            <section className="panel">
              <h2>سناریو و عوامل ریسک</h2>
              <h3>سناریو</h3><p>{risk.scenario || "ثبت نشده"}</p>
              <h3>علت</h3><p>{risk.cause || "ثبت نشده"}</p>
              <h3>پیامد</h3><p>{risk.consequence || "ثبت نشده"}</p>
              <p className="muted">دارایی مرتبط: {risk.asset_title || "بدون دارایی مشخص"} · وضعیت: {risk.status}</p>
            </section>
            <section className="panel">
              <h2>طرح‌های درمان و اقدامات</h2>
              {treatments.length === 0 ? <p className="muted">برنامه درمانی قابل مشاهده‌ای وجود ندارد.</p> :
                treatments.map(row => (
                  <div className="treatmentCard" key={row.id}>
                    <strong>{row.strategy} · {row.owner_display}</strong>
                    <p>{row.description || "شرحی ثبت نشده است."}</p>
                    <small>وضعیت: {row.status} · تصویب: {row.approval_status}</small>
                    {row.actions?.map(item => <p className="actionMini" key={item.id}>{item.title} · {item.progress}٪ · {item.status}</p>)}
                    <Button size="sm" variant="secondary" disabled={!canWrite} onClick={() => setAction({ treatmentId: row.id, owner: "", title: "", due_date: "" })}>+ اقدام مرتبط</Button>
                  </div>
                ))}
            </section>
          </div>

          {action.treatmentId && (
            <form className="panel productControlForm" onSubmit={submitAction}>
              <h2>ثبت اقدام برای برنامه درمان انتخاب‌شده</h2>
              <div className="productControlFormGrid">
                <FormField label="عنوان اقدام" required>
                  <Input required value={action.title} onChange={event => setAction(x => ({ ...x, title: event.target.value }))} />
                </FormField>
                <FormField label="مسئول اقدام" required>
                  <Select required value={action.owner} onChange={event => setAction(x => ({ ...x, owner: event.target.value }))}>
                    <option value="">انتخاب مسئول فعال</option>
                    {members.map(member => <option key={member.id} value={String(member.id)}>{userLabel(member)}</option>)}
                  </Select>
                </FormField>
                <FormField label="سررسید">
                  <Input type="date" dir="ltr" value={action.due_date} onChange={event => setAction(x => ({ ...x, due_date: event.target.value }))} />
                </FormField>
              </div>
              <div className="productControlFormActions">
                <Button type="submit" busy={busy} disabled={!canWrite || !members.length}>ثبت اقدام در انتظار</Button>
                <Button type="button" variant="secondary" onClick={() => setAction({ treatmentId: "", owner: "", title: "", due_date: "" })}>انصراف</Button>
              </div>
            </form>
          )}
        </>
      )}
    </main>
  );
}
