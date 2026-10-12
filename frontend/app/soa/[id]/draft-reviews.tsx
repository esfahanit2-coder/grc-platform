"use client";

import { useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";

type ReviewEvent = {
  id: string; round: number;
  kind: "requested" | "feedback_recorded" | "changes_requested" | "superseded";
  actor_id: string; assigned_reviewer_id: string; created_at: string;
  note: string; snapshot_stale: boolean; can_respond?: boolean;
  formal_attestation_allowed: false;
};
type Candidate = { id: string; display: string };
type Candidates = { results: Candidate[]; truncated: boolean };
type ReviewList = { results: ReviewEvent[]; truncated: boolean };

const labels: Record<ReviewEvent["kind"], string> = {
  requested: "ارسال برای نظر بازبین مستقل",
  feedback_recorded: "نظر بازبین ثبت شد (نه تصویب)",
  changes_requested: "بازبین درخواست اصلاح کرده",
  superseded: "درخواست قبلی پس از تغییر پیش‌نویس منسوخ شد",
};

function errorMessage(input: unknown): string {
  if (!input || typeof input !== "object") return "درخواست قابل انجام نبود.";
  return Object.entries(input as Record<string, unknown>)
    .flatMap(([key, value]) => typeof value === "string" ? [key + ": " + value] :
      Array.isArray(value) ? value.map(item => key + ": " + String(item)) : [])
    .join(" • ") || "خطا در مجوز یا اعتبار اطلاعات.";
}

export default function DraftSoAReviews({ registerId }: { registerId: string }) {
  const path = "/soa/registers/" + encodeURIComponent(registerId) + "/";
  const [events, setEvents] = useState<ReviewEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [requestOpen, setRequestOpen] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [candidateError, setCandidateError] = useState("");
  const [candidateLoading, setCandidateLoading] = useState(false);
  const [reviewer, setReviewer] = useState("");
  const [requestNote, setRequestNote] = useState("");
  const [responseTarget, setResponseTarget] = useState<string | null>(null);
  const [responseKind, setResponseKind] = useState<"feedback_recorded" | "changes_requested">("changes_requested");
  const [responseNote, setResponseNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const response = await apiFetch(path + "review-requests/");
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(payload));
      setEvents((payload as ReviewList).results ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "سوابق بازبینی دریافت نشد.");
      setEvents([]);
    } finally { setLoading(false); }
  }
  useEffect(() => {
    void load();
    // Scope is determined and checked by the server for every request.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registerId]);

  async function openRequest() {
    setRequestOpen(true); setResponseTarget(null); setFormError("");
    setCandidateLoading(true); setCandidateError("");
    try {
      const response = await apiFetch(path + "reviewers/");
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(payload));
      const values = (payload as Candidates).results ?? [];
      setCandidates(values);
      if (values.length) setReviewer(values[0].id);
    } catch (err) {
      setCandidates([]);
      setCandidateError(err instanceof Error ? err.message : "فهرست بازبینان قابل دریافت نیست.");
    } finally { setCandidateLoading(false); }
  }
  async function submitRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFormError("");
    if (!reviewer) { setFormError("انتخاب بازبین مستقل الزامی است."); return; }
    setSaving(true);
    try {
      const response = await apiFetch(path + "review-requests/", {
        method: "POST", body: JSON.stringify({ reviewer, note: requestNote.trim() }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(payload));
      setRequestOpen(false); setRequestNote(""); setReviewer("");
      await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "ثبت درخواست ناموفق بود."); }
    finally { setSaving(false); }
  }
  async function submitResponse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setFormError("");
    if (!responseTarget || !responseNote.trim()) {
      setFormError("نوع نظر و متن بازخورد الزامی‌اند."); return;
    }
    setSaving(true);
    try {
      const response = await apiFetch(
        path + "review-requests/" + encodeURIComponent(responseTarget) + "/respond/",
        { method: "POST", body: JSON.stringify({ kind: responseKind, note: responseNote.trim() }) },
      );
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(payload));
      setResponseTarget(null); setResponseNote("");
      await load();
    } catch (err) { setFormError(err instanceof Error ? err.message : "ثبت نظر ممکن نشد."); }
    finally { setSaving(false); }
  }

  return <section className="adminCard" dir="rtl" aria-label="بازبینی انسانی پیش‌نویس">
    <div className="pageHead">
      <div>
        <h2>بازبینی انسانی پیش‌نویس</h2>
        <p>ثبت نظر یا درخواست اصلاح توسط شخص مستقل. این مرحله <strong>هیچ تصویب، امضا یا صدور SoA</strong> انجام نمی‌دهد.</p>
      </div>
      <div className="headActions">
        <button type="button" className="secondaryButton" onClick={() => void load()} disabled={loading}>به‌روزرسانی سوابق</button>
        <button type="button" className="primary" onClick={() => void openRequest()}>+ درخواست نظر مستقل</button>
      </div>
    </div>
    {loading && <p>در حال دریافت سوابق بازبینی…</p>}
    {error && <p role="alert" className="errorText">{error}</p>}
    {!loading && !error && events.length === 0 && <p className="emptyState">هنوز درخواست بازبینی ثبت نشده است.</p>}
    {!loading && !error && events.length > 0 && <div className="tableWrap"><table>
      <thead><tr><th>دور</th><th>رخداد</th><th>یادداشت</th><th>وضعیت نسخه</th><th>اقدام</th></tr></thead>
      <tbody>{events.map(item => <tr key={item.id}>
        <td>{item.round}</td><td>{labels[item.kind]}</td>
        <td>{item.note || "—"}</td><td>{item.snapshot_stale ? "پیش‌نویس از زمان درخواست تغییر کرده" : "نسخه رویداد بدون تغییر شناسایی‌شده"}</td>
        <td>{item.can_respond ?
          <button type="button" className="secondaryButton" onClick={() => {
            setRequestOpen(false); setResponseTarget(item.id); setFormError(""); setResponseNote("");
          }}>ثبت نظر بازبین</button> :
          "بدون اقدام یا خارج از اختیار"}</td>
      </tr>)}</tbody>
    </table></div>}
    <p>سوابق فقط برای مشاهده‌اند و تغییرات بعدی پیش‌نویس، اعتبار نظر ثبت‌شده روی نسخه قبلی را از بین می‌برد.</p>

    {requestOpen && <form className="settingsForm" onSubmit={submitRequest}>
      <h3>درخواست نظر بازبین مستقل</h3>
      {candidateLoading && <p>در حال دریافت بازبینان دارای مجوز…</p>}
      {candidateError && <p className="errorText" role="alert">{candidateError}</p>}
      {!candidateLoading && !candidateError && !candidates.length && <p>بازبین مستقلی با مجوز لازم در این محدوده یافت نشد.</p>}
      <label>بازبین *
        <select required value={reviewer} onChange={e => setReviewer(e.target.value)}>
          <option value="">انتخاب بازبین</option>
          {candidates.map(x => <option key={x.id} value={x.id}>{x.display}</option>)}
        </select>
      </label>
      <label>توضیح درخواست (اختیاری)
        <textarea rows={2} maxLength={2000} value={requestNote} onChange={e => setRequestNote(e.target.value)} />
      </label>
      {formError && <p role="alert" className="errorText">{formError}</p>}
      <div className="buttonRow">
        <button className="primary" type="submit" disabled={saving || candidateLoading || !!candidateError || !candidates.length}>
          {saving ? "در حال ثبت…" : "ارسال برای دریافت نظر"}
        </button>
        <button type="button" className="secondaryButton" onClick={() => { setRequestOpen(false); setFormError(""); }}>انصراف</button>
      </div>
    </form>}

    {responseTarget && <form className="settingsForm" onSubmit={submitResponse}>
      <h3>ثبت نظر بازبین — بدون تأیید رسمی</h3>
      <label>نتیجه بازبینی *
        <select value={responseKind} onChange={e => setResponseKind(e.target.value as "feedback_recorded" | "changes_requested")}>
          <option value="changes_requested">درخواست اصلاح پیش‌نویس</option>
          <option value="feedback_recorded">ثبت نظر کارشناسی (نه تصویب)</option>
        </select>
      </label>
      <label>شرح نظر انسانی *
        <textarea required rows={3} maxLength={4000} value={responseNote} onChange={e => setResponseNote(e.target.value)} />
      </label>
      {formError && <p role="alert" className="errorText">{formError}</p>}
      <div className="buttonRow">
        <button className="primary" type="submit" disabled={saving || !responseNote.trim()}>
          {saving ? "در حال ثبت…" : "ثبت بازخورد غیررسمی"}
        </button>
        <button type="button" className="secondaryButton" onClick={() => { setResponseTarget(null); setFormError(""); }}>انصراف</button>
      </div>
    </form>}
  </section>;
}
