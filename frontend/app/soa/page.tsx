"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api";

type Register = {
  id: string; title: string; revision: number; status: "draft";
  organization_unit: string; framework_version: string;
  is_formal_statement_of_applicability: false; notice: string;
};
type Unit = { id: string; name: string; code: string };
type Version = {
  id: string; framework: string; framework_name: string; version_code: string;
  is_locked: boolean; status: string;
};
type Framework = { id: string; name: string; is_global: boolean };

function rows<T>(data: T[] | { results?: T[] }): T[] {
  return Array.isArray(data) ? data : data.results ?? [];
}

function errorMessage(body: unknown): string {
  if (typeof body === "string") return body;
  if (!body || typeof body !== "object") return "خطا در دریافت یا ذخیره پرونده.";
  return Object.entries(body as Record<string, unknown>)
    .flatMap(([key, value]) => Array.isArray(value) ? value.map(x => key + ": " + String(x)) :
      typeof value === "string" ? [key + ": " + value] : [])
    .join(" • ") || "ثبت اطلاعات ممکن نشد؛ مجوز و داده‌ها را بررسی کنید.";
}

export default function SoAListPage() {
  const router = useRouter();
  const [registers, setRegisters] = useState<Register[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [frameworks, setFrameworks] = useState<Framework[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingRefs, setLoadingRefs] = useState(false);
  const [error, setError] = useState("");
  const [refError, setRefError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [unit, setUnit] = useState("");
  const [version, setVersion] = useState("");
  const [revision, setRevision] = useState("1");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/soa/registers/");
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(data));
      setRegisters(rows<Register>(data));
    } catch (e) {
      setError(e instanceof Error ? e.message : "امکان دریافت دفتر SoA وجود ندارد.");
      setRegisters([]);
    } finally {
      setLoading(false);
    }
  }

  async function loadReferences() {
    setLoadingRefs(true);
    setRefError("");
    try {
      const [ur, vr, fr] = await Promise.all([
        apiFetch("/organization-units/?page_size=200"),
        apiFetch("/framework-versions/?page_size=200"),
        apiFetch("/frameworks/?page_size=200"),
      ]);
      if (!ur.ok || !vr.ok || !fr.ok) throw new Error("برای ایجاد پرونده باید به واحدها و چارچوب‌های مجاز دسترسی داشته باشید.");
      setUnits(rows<Unit>(await ur.json()));
      setVersions(rows<Version>(await vr.json()));
      setFrameworks(rows<Framework>(await fr.json()));
    } catch (e) {
      setRefError(e instanceof Error ? e.message : "داده‌های مرجع قابل دریافت نیستند.");
      setUnits([]); setVersions([]); setFrameworks([]);
    } finally { setLoadingRefs(false); }
  }

  useEffect(() => {
    void load();
    void loadReferences();
    // Load only for the selected authenticated tenant. Server enforces scoping.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const names = useMemo(() => new Map(units.map(x => [x.id, x.name])), [units]);
  const owned = useMemo(
    () => new Set(frameworks.filter(x => !x.is_global).map(x => x.id)),
    [frameworks],
  );
  const locked = versions.filter(x => x.is_locked && owned.has(x.framework) && x.status !== "retired");

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveError("");
    const n = Number(revision);
    if (!title.trim() || !unit || !version || !Number.isSafeInteger(n) || n < 1) {
      setSaveError("عنوان، واحد، نسخه قفل‌شده و شماره بازنگری معتبر الزامی‌اند.");
      return;
    }
    if (!locked.some(x => x.id === version) || !units.some(x => x.id === unit)) {
      setSaveError("داده مرجع انتخاب‌شده معتبر یا مجاز نیست.");
      return;
    }
    setSaving(true);
    try {
      const response = await apiFetch("/soa/registers/", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(), organization_unit: unit, framework_version: version, revision: n,
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(errorMessage(body));
      await load();
      router.push("/soa/" + encodeURIComponent(String(body.id)));
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "ایجاد پرونده ناموفق بود.");
    } finally { setSaving(false); }
  }

  return <main className="adminPage" dir="rtl">
    <div className="pageHead">
      <div>
        <Link href="/">← داشبورد</Link>
        <h1>دفتر پیش‌نویس SoA</h1>
        <p>ثبت انتخاب یا استثنای کنترل‌ها با توجیه کارشناسی. این بخش صدور یا تأیید رسمی ISO نیست.</p>
      </div>
      <div className="headActions">
        <button type="button" className="secondaryButton" onClick={() => void load()} disabled={loading}>بروزرسانی</button>
        <button type="button" className="primary" onClick={() => {
          setShowCreate(x => !x);
          if (!showCreate && refError) void loadReferences();
        }}>{showCreate ? "بستن فرم" : "+ پرونده پیش‌نویس"}</button>
      </div>
    </div>

    <section className="adminCard" aria-label="هشدار وضعیت پرونده‌ها">
      <p role="status"><strong>پیش‌نویس — تأییدنشده:</strong> هیچ پرونده‌ای در این بخش بیانیه کاربردپذیری نهایی، گواهی استاندارد یا مجوز انتشار محسوب نمی‌شود.</p>
    </section>

    {showCreate && <section className="adminCard">
      <h2>ایجاد پرونده پیش‌نویس</h2>
      {loadingRefs && <p>دریافت واحدهای سازمانی و نسخه‌های مجاز…</p>}
      {refError && <p className="errorText" role="alert">{refError}</p>}
      <form className="settingsForm" onSubmit={create}>
        <label>عنوان پرونده *
          <input required maxLength={255} value={title} onChange={e => setTitle(e.target.value)} placeholder="مثلاً SoA حوزه فناوری اطلاعات" />
        </label>
        <label>واحد سازمانی *
          <select required value={unit} onChange={e => setUnit(e.target.value)}>
            <option value="">انتخاب واحد</option>
            {units.map(x => <option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}
          </select>
        </label>
        <label>نسخه چارچوب قفل‌شده و متعلق به همین مشتری *
          <select required value={version} onChange={e => setVersion(e.target.value)}>
            <option value="">انتخاب نسخه</option>
            {locked.map(x => <option key={x.id} value={x.id}>{x.framework_name} — {x.version_code}</option>)}
          </select>
        </label>
        <label>شماره بازنگری *
          <input type="number" min={1} step={1} value={revision} onChange={e => setRevision(e.target.value)} required />
        </label>
        {!loadingRefs && !refError && locked.length === 0 && <p role="status">نسخه قفل‌شده مجاز پیدا نشد. ابتدا چارچوب اختصاصی مشتری را تکمیل و قفل کنید.</p>}
        {saveError && <p className="errorText" role="alert">{saveError}</p>}
        <button className="primary" type="submit" disabled={saving || loadingRefs || Boolean(refError) || !locked.length}>
          {saving ? "در حال ذخیره…" : "ساخت پیش‌نویس"}
        </button>
      </form>
    </section>}

    <section className="adminCard">
      <h2>پرونده‌های قابل مشاهده در محدوده مجاز</h2>
      {loading && <p>در حال دریافت پرونده‌ها…</p>}
      {error && <p className="errorText" role="alert">{error}</p>}
      {!loading && !error && registers.length === 0 && <p className="emptyState">در این محدوده هنوز پرونده‌ای ثبت نشده است.</p>}
      {!loading && !error && registers.length > 0 && <div className="tableWrap"><table>
        <thead><tr><th>پرونده</th><th>واحد</th><th>بازنگری</th><th>وضعیت</th><th>اقدام</th></tr></thead>
        <tbody>{registers.map(row => <tr key={row.id}>
          <td>{row.title}</td><td>{names.get(row.organization_unit) ?? row.organization_unit}</td>
          <td>{row.revision}</td><td>پیش‌نویس — تأییدنشده</td>
          <td><Link href={"/soa/" + encodeURIComponent(row.id)}>بررسی پرونده</Link></td>
        </tr>)}</tbody>
      </table></div>}
      {registers.length === 200 && <p>در حال حاضر فقط ۲۰۰ پرونده اخیر در API فهرست می‌شود؛ این فهرست کامل بایگانی نیست.</p>}
    </section>
  </main>;
}
