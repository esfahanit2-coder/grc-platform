"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "../../../lib/api";
import { Button, FormField, Input, Select, StatusMessage, Textarea } from "../../../components/ui";

type Control = { id: string; code: string; title: string; objective: string; description: string; status: string; is_global: boolean; control_type: string; nature: string };
type Mapping = { id: string; framework_code: string; requirement_code: string; coverage: string; mapping_type: string; approved: boolean };
type Implementation = { id: string; organization_name: string; owner_display: string; implementation_status: string; effectiveness: string; review_date?: string | null };
type Requirement = { id: string; code: string; title: string; framework_code: string; version_code?: string };
type Unit = { id: string; code: string; name: string };
type User = { id: number; username: string; first_name?: string; last_name?: string; membership_active?: boolean };
type MappingForm = { requirement: string; mapping_type: string; coverage: string; rationale: string };
type ImplementationForm = { unit: string; owner: string; description: string };

const initialMapping: MappingForm = { requirement: "", mapping_type: "related", coverage: "100", rationale: "" };
const initialImplementation: ImplementationForm = { unit: "", owner: "", description: "" };

function unpack<T>(value: T[] | { results?: T[] }) {
  return Array.isArray(value) ? value : value.results ?? [];
}

function displayUser(user: User) {
  const name = (String(user.first_name ?? "") + " " + String(user.last_name ?? "")).trim();
  return name ? name + " (" + user.username + ")" : user.username;
}

function message(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") return fallback;
  const items = Object.entries(payload as Record<string, unknown>)
    .flatMap(([key, value]) => (Array.isArray(value) ? value : typeof value === "string" ? [value] : [])
      .map(item => key + ": " + String(item)));
  return items.slice(0, 8).join(" • ") || fallback;
}

export default function ControlDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [control, setControl] = useState<Control | null>(null);
  const [mappings, setMappings] = useState<Mapping[]>([]);
  const [implementations, setImplementations] = useState<Implementation[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [busy, setBusy] = useState(false);
  const [mappingEditor, setMappingEditor] = useState(false);
  const [implementationEditor, setImplementationEditor] = useState(false);
  const [mappingForm, setMappingForm] = useState<MappingForm>(initialMapping);
  const [implementationForm, setImplementationForm] = useState<ImplementationForm>(initialImplementation);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadingOptions(true);
    setError("");
    try {
      const [a, b, c, d, e, f] = await Promise.all([
        apiFetch("/controls/" + encodeURIComponent(id) + "/"),
        apiFetch("/control-requirements/?control=" + encodeURIComponent(id)),
        apiFetch("/control-implementations/?control=" + encodeURIComponent(id)),
        apiFetch("/requirements/?page_size=200"),
        apiFetch("/organization-units/?page_size=200"),
        apiFetch("/tenant-users/"),
      ]);
      if (!a.ok) throw new Error(a.status === 403 ? "مجوز مشاهده کنترل را ندارید." : "جزئیات کنترل قابل دریافت نیست.");
      const nextControl = await a.json() as Control;
      setControl(nextControl);
      const primary = [b, c];
      const primaryNames = ["نگاشت‌ها", "پیاده‌سازی‌ها"];
      for (let index = 0; index < primary.length; index++) {
        if (!primary[index].ok) throw new Error("دریافت " + primaryNames[index] + " مجاز یا ممکن نیست.");
      }
      setMappings(unpack(await b.json() as Mapping[] | { results?: Mapping[] }));
      setImplementations(unpack(await c.json() as Implementation[] | { results?: Implementation[] }));

      // Do not infer that an empty selector is a complete inventory when any API has failed.
      const failed = [d, e, f].some(response => !response.ok);
      if (failed) {
        setError("دریافت همه گزینه‌های مرجع ممکن نیست؛ ثبت نگاشت یا پیاده‌سازی غیرفعال است. مجوزها و دسترسی API را بررسی کنید.");
        setRequirements([]);
        setUnits([]);
        setUsers([]);
      } else {
        const [reqBody, unitBody, userBody] = await Promise.all([d.json(), e.json(), f.json()]);
        setRequirements(unpack(reqBody as Requirement[] | { results?: Requirement[] }));
        setUnits(unpack(unitBody as Unit[] | { results?: Unit[] }));
        setUsers(unpack(userBody as User[] | { results?: User[] }).filter(item => item.membership_active !== false));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "ارتباط با سامانه برقرار نشد.");
      setControl(null);
      setMappings([]);
      setImplementations([]);
    } finally {
      setLoading(false);
      setLoadingOptions(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  async function saveMapping(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (busy || loading || loadingOptions || error || !control || !mappingForm.requirement) {
      setNotice("الزام مرجع را صریحاً انتخاب کنید و ابتدا بارگذاری داده‌ها را کامل کنید.");
      return;
    }
    const coverage = Number(mappingForm.coverage);
    if (!Number.isFinite(coverage) || coverage < 0 || coverage > 100) {
      setNotice("پوشش باید عددی بین صفر تا صد باشد.");
      return;
    }
    setBusy(true);
    try {
      const response = await apiFetch("/control-requirements/", {
        method: "POST",
        body: JSON.stringify({
          control: id,
          requirement: mappingForm.requirement,
          mapping_type: mappingForm.mapping_type,
          coverage: coverage.toFixed(2),
          rationale: mappingForm.rationale.trim(),
          source: "manual",
        }),
      });
      if (!response.ok) throw new Error(message(await response.json().catch(() => null), "ثبت نگاشت ناموفق بود."));
      setMappingForm(initialMapping);
      setMappingEditor(false);
      await load();
      setNotice("نگاشت به‌صورت تأییدنشده ثبت شد. این عملیات تأیید انطباق یا تصویب مستقل نیست.");
    } catch (err) {
      setNotice("خطا: " + (err instanceof Error ? err.message : "ثبت انجام نشد."));
    } finally { setBusy(false); }
  }

  async function saveImplementation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    if (busy || loading || loadingOptions || error || !control ||
        !implementationForm.unit || !implementationForm.owner) {
      setNotice("واحد سازمانی و مالک فعال باید به‌صورت صریح انتخاب شوند.");
      return;
    }
    setBusy(true);
    try {
      const response = await apiFetch("/control-implementations/", {
        method: "POST",
        body: JSON.stringify({
          control: id,
          organization_unit: implementationForm.unit,
          owner: Number(implementationForm.owner),
          implementation_description: implementationForm.description.trim(),
          implementation_status: "planned",
          effectiveness: "not_assessed",
          metadata: {},
        }),
      });
      if (!response.ok) throw new Error(message(await response.json().catch(() => null), "ثبت پیاده‌سازی ناموفق بود."));
      setImplementationForm(initialImplementation);
      setImplementationEditor(false);
      await load();
      setNotice("برنامه پیاده‌سازی ثبت شد؛ وضعیت آن «برنامه‌ریزی‌شده» است، نه «اجراشده».");
    } catch (err) {
      setNotice("خطا: " + (err instanceof Error ? err.message : "ثبت انجام نشد."));
    } finally { setBusy(false); }
  }

  const canEdit = !loading && !loadingOptions && !error && Boolean(control);
  const noticeIsError = notice.startsWith("خطا:") || notice.includes("باید") || notice.includes("الزام");
  return (
    <main className="adminPage">
      <div className="pageHead">
        <div>
          <Link href="/controls">← کنترل‌ها</Link>
          <h1>{control ? control.code + " — " + control.title : "جزئیات کنترل"}</h1>
          <p>{control?.objective || "هدف کنترل ثبت نشده است."}</p>
        </div>
        <div className="headActions">
          <Button variant="secondary" onClick={() => { setNotice(""); setMappingEditor(value => !value); }} disabled={!canEdit || control?.is_global}>
            {mappingEditor ? "بستن نگاشت" : "+ نگاشت الزام"}
          </Button>
          <Button onClick={() => { setNotice(""); setImplementationEditor(value => !value); }} disabled={!canEdit}>
            {implementationEditor ? "بستن فرم" : "+ برنامه پیاده‌سازی"}
          </Button>
        </div>
      </div>
      {notice && <StatusMessage tone={noticeIsError ? "danger" : "success"}>{notice}</StatusMessage>}
      {error && <StatusMessage tone="danger">{error}</StatusMessage>}
      {loading && <p role="status">در حال دریافت اطلاعات کنترل…</p>}
      {!loading && !control && !error && <p role="status">کنترل در محدوده فعلی پیدا نشد.</p>}
      {control && (
        <>
          <div className="productControlStats">
            <div className="productControlStat"><span>وضعیت کنترل</span><strong>{control.status}</strong></div>
            <div className="productControlStat"><span>نگاشت‌های قابل مشاهده</span><strong>{mappings.length}</strong></div>
            <div className="productControlStat"><span>پیاده‌سازی‌های مجاز</span><strong>{implementations.length}</strong></div>
          </div>
          {mappingEditor && !control.is_global && (
            <form className="panel productControlForm" onSubmit={saveMapping}>
              <h2>نگاشت الزام (پیش‌نویس تأییدنشده)</h2>
              <p className="muted">ثبت نگاشت، تأیید مستقل یا تصدیق استاندارد نیست. گزینه‌ها از الزامات قابل مشاهده در حساب شما گرفته می‌شوند.</p>
              <div className="productControlFormGrid">
                <FormField label="الزام مرجع" required>
                  <Select required value={mappingForm.requirement} onChange={event => setMappingForm(x => ({ ...x, requirement: event.target.value }))}>
                    <option value="">الزام را انتخاب کنید</option>
                    {requirements.map(req => <option key={req.id} value={req.id}>{req.framework_code} {req.version_code ?? ""} — {req.code} — {req.title}</option>)}
                  </Select>
                </FormField>
                <FormField label="نوع ارتباط" required>
                  <Select value={mappingForm.mapping_type} onChange={event => setMappingForm(x => ({ ...x, mapping_type: event.target.value }))}>
                    <option value="related">مرتبط</option><option value="partial">جزئی</option>
                    <option value="strong">قوی</option><option value="exact">دقیق</option>
                  </Select>
                </FormField>
                <FormField label="درصد پوشش (۰ تا ۱۰۰)" required>
                  <Input type="number" min={0} max={100} step="0.01" required value={mappingForm.coverage} onChange={event => setMappingForm(x => ({ ...x, coverage: event.target.value }))} />
                </FormField>
                <FormField label="توضیح کارشناسی" className="productFullField">
                  <Textarea value={mappingForm.rationale} onChange={event => setMappingForm(x => ({ ...x, rationale: event.target.value }))} placeholder="چرایی ارتباط و محدودیت‌های پوشش" />
                </FormField>
              </div>
              <Button type="submit" busy={busy} disabled={!canEdit || !requirements.length}>ثبت نگاشت تأییدنشده</Button>
            </form>
          )}
          {implementationEditor && (
            <form className="panel productControlForm" onSubmit={saveImplementation}>
              <h2>برنامه پیاده‌سازی کنترل</h2>
              <p className="muted">به‌منظور جلوگیری از ادعای نادرست، وضعیت اولیه «برنامه‌ریزی‌شده» و اثربخشی «ارزیابی‌نشده» است.</p>
              <div className="productControlFormGrid">
                <FormField label="واحد سازمانی" required>
                  <Select required value={implementationForm.unit} onChange={event => setImplementationForm(x => ({ ...x, unit: event.target.value }))}>
                    <option value="">واحد را انتخاب کنید</option>
                    {units.map(unit => <option value={unit.id} key={unit.id}>{unit.name} ({unit.code})</option>)}
                  </Select>
                </FormField>
                <FormField label="مالک پیاده‌سازی" required>
                  <Select required value={implementationForm.owner} onChange={event => setImplementationForm(x => ({ ...x, owner: event.target.value }))}>
                    <option value="">مالک فعال را انتخاب کنید</option>
                    {users.map(user => <option key={user.id} value={String(user.id)}>{displayUser(user)}</option>)}
                  </Select>
                </FormField>
                <FormField label="توضیح برنامه" className="productFullField">
                  <Textarea value={implementationForm.description} onChange={event => setImplementationForm(x => ({ ...x, description: event.target.value }))} />
                </FormField>
              </div>
              <Button type="submit" busy={busy} disabled={!canEdit || !units.length || !users.length}>ثبت برنامه</Button>
            </form>
          )}
          <div className="grid">
            <section className="panel">
              <h2>پوشش چارچوب‌ها</h2>
              {mappings.length === 0 ? <p className="muted">نگاشتی در محدوده فعلی وجود ندارد.</p> :
                <div className="productControlTableWrap"><table className="dataTable">
                  <thead><tr><th>چارچوب</th><th>الزام</th><th>پوشش</th><th>نوع</th><th>تأیید مستقل</th></tr></thead>
                  <tbody>{mappings.map(m => <tr key={m.id}>
                    <td>{m.framework_code}</td><td>{m.requirement_code}</td><td>{m.coverage}٪</td>
                    <td>{m.mapping_type}</td><td><span className="pill">{m.approved ? "تأییدشده" : "در انتظار تأیید"}</span></td>
                  </tr>)}</tbody>
                </table></div>}
            </section>
            <section className="panel">
              <h2>پیاده‌سازی در سازمان</h2>
              {implementations.length === 0 ? <p className="muted">پیاده‌سازی قابل مشاهده‌ای ثبت نشده است.</p> :
                <div className="productControlTableWrap"><table className="dataTable">
                  <thead><tr><th>واحد</th><th>مالک</th><th>وضعیت</th><th>اثربخشی</th></tr></thead>
                  <tbody>{implementations.map(item => <tr key={item.id}>
                    <td>{item.organization_name}</td><td>{item.owner_display}</td>
                    <td><span className="pill">{item.implementation_status}</span></td>
                    <td>{item.effectiveness}</td>
                  </tr>)}</tbody>
                </table></div>}
            </section>
          </div>
        </>
      )}
    </main>
  );
}
