"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { apiFetch } from "../../lib/api";
import { Button, EmptyState, FormField, Input, StatusMessage, Textarea } from "../../components/ui";

type Control = {
  id: string;
  code: string;
  title: string;
  control_type: string;
  nature: string;
  status: string;
  frameworks_count: number;
  implementations_count: number;
  is_global: boolean;
};

type CreateControl = { code: string; title: string; objective: string; description: string };
const initialForm: CreateControl = { code: "", title: "", objective: "", description: "" };

function errorMessage(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") return fallback;
  const fields = Object.entries(payload as Record<string, unknown>)
    .flatMap(([field, value]) =>
      (Array.isArray(value) ? value : typeof value === "string" ? [value] : [])
        .map(item => field === "detail" ? String(item) : field + ": " + String(item))
    ).slice(0, 5);
  return fields.join(" • ") || fallback;
}

export default function ControlsPage() {
  const [items, setItems] = useState<Control[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [notice, setNotice] = useState("");
  const [noticeTone, setNoticeTone] = useState<"success" | "danger">("success");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateControl>(initialForm);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (query: string) => {
    setLoading(true);
    setLoadError("");
    try {
      const result = await apiFetch("/controls/?search=" + encodeURIComponent(query.trim()));
      if (!result.ok) throw new Error(result.status === 403
        ? "مجوز مشاهده کنترل‌ها در محدوده فعلی وجود ندارد."
        : "دریافت فهرست کنترل‌ها ناموفق بود.");
      const payload = await result.json() as Control[] | { results?: Control[] };
      setItems(Array.isArray(payload) ? payload : payload.results ?? []);
    } catch (error) {
      setItems([]);
      setLoadError(error instanceof Error ? error.message : "ارتباط با سامانه برقرار نشد.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(""); }, [load]);

  function update<K extends keyof CreateControl>(key: K, value: CreateControl[K]) {
    setForm(previous => ({ ...previous, [key]: value }));
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;
    setNotice("");
    const code = form.code.trim();
    const title = form.title.trim();
    if (!code || !title) {
      setNoticeTone("danger");
      setNotice("کد و عنوان کنترل الزامی هستند.");
      return;
    }
    setSaving(true);
    try {
      const response = await apiFetch("/controls/", {
        method: "POST",
        body: JSON.stringify({
          code, title,
          objective: form.objective.trim(),
          description: form.description.trim(),
          control_type: "technical",
          nature: "preventive",
          frequency: "",
          automation_level: "manual",
          status: "draft",
          metadata: {},
        }),
      });
      if (!response.ok) {
        const error = await response.json().catch(() => null) as unknown;
        throw new Error(errorMessage(error, "ثبت کنترل ناموفق بود؛ داده‌ها و سطح دسترسی را بررسی کنید."));
      }
      setForm(initialForm);
      setShowCreate(false);
      setSearch("");
      await load("");
      setNoticeTone("success");
      setNotice("پیش‌نویس کنترل ایجاد شد. ثبت کنترل به معنی اجرای آن یا تأیید انطباق نیست.");
    } catch (error) {
      setNoticeTone("danger");
      setNotice(error instanceof Error ? error.message : "ثبت کنترل انجام نشد.");
    } finally {
      setSaving(false);
    }
  }

  const mapped = items.reduce((count, item) => count + (item.frameworks_count || 0), 0);
  const implemented = items.reduce((count, item) => count + (item.implementations_count || 0), 0);

  return (
    <main className="adminPage">
      <div className="pageHead">
        <div>
          <h1>کتابخانه کنترل‌ها</h1>
          <p>یک کنترل مشترک، چند چارچوب؛ مدیریت نگاشت و پیاده‌سازی در محدوده دسترسی شما</p>
        </div>
        <div className="headActions">
          <Link className="secondaryLink" href="/soa">پیش‌نویس SoA</Link>
          <Button onClick={() => { setNotice(""); setShowCreate(value => !value); }}>
            {showCreate ? "بستن فرم" : "+ ایجاد کنترل"}
          </Button>
        </div>
      </div>

      {notice && (
        <StatusMessage className="productInlineStatus" tone={noticeTone}>
          {notice}
        </StatusMessage>
      )}

      <div className="productControlStats" aria-label="آمار کنترل‌های بارگذاری‌شده">
        <div className="productControlStat">
          <span>کنترل‌های قابل مشاهده</span><strong>{loading ? "…" : items.length}</strong>
        </div>
        <div className="productControlStat">
          <span>نگاشت‌های چارچوب در نتایج فعلی</span><strong>{loading ? "…" : mapped}</strong>
        </div>
        <div className="productControlStat">
          <span>پیاده‌سازی‌های ثبت‌شده در نتایج فعلی</span><strong>{loading ? "…" : implemented}</strong>
        </div>
      </div>

      {showCreate && (
        <form className="panel productControlForm" onSubmit={create} aria-label="ایجاد پیش‌نویس کنترل">
          <div>
            <h2>کنترل جدید</h2>
            <p className="muted">ابتدا یک پیش‌نویس ثبت کنید؛ نگاشت استاندارد و پیاده‌سازی در صفحه جزئیات انجام می‌شود.</p>
          </div>
          <div className="productControlFormGrid">
            <FormField label="شناسه کنترل" required hint="کد یکتا؛ برای مثال CTRL-IAM-001">
              <Input
                dir="ltr" required maxLength={80} autoComplete="off"
                value={form.code} onChange={event => update("code", event.target.value)}
                placeholder="CTRL-IAM-001"
              />
            </FormField>
            <FormField label="عنوان کنترل" required>
              <Input
                required maxLength={255} value={form.title}
                onChange={event => update("title", event.target.value)}
                placeholder="عنوان کنترل را وارد کنید"
              />
            </FormField>
            <FormField className="productFullField" label="هدف کنترل">
              <Textarea
                rows={2} value={form.objective}
                onChange={event => update("objective", event.target.value)}
                placeholder="هدف و نتیجه مورد انتظار کنترل"
              />
            </FormField>
            <FormField className="productFullField" label="شرح کنترل">
              <Textarea
                rows={3} value={form.description}
                onChange={event => update("description", event.target.value)}
                placeholder="شرح قابل اجرا؛ از درج متن استاندارد دارای مجوز نامشخص خودداری کنید"
              />
            </FormField>
          </div>
          <div className="productControlFormActions">
            <Button type="submit" busy={saving} disabled={saving}>ثبت پیش‌نویس</Button>
            <Button type="button" variant="secondary" disabled={saving} onClick={() => setShowCreate(false)}>انصراف</Button>
          </div>
        </form>
      )}

      <form className="toolbar" role="search" onSubmit={event => { event.preventDefault(); void load(search); }}>
        <Input
          type="search" aria-label="جستجو در کد و عنوان کنترل"
          value={search} onChange={event => setSearch(event.target.value)}
          placeholder="جستجو در کد و عنوان کنترل…"
        />
        <Button type="submit" variant="secondary" busy={loading}>جستجو</Button>
      </form>

      <section className="panel">
        {loadError && <StatusMessage tone="danger" title="خطا در دریافت اطلاعات">{loadError}</StatusMessage>}
        {loading ? (
          <p className="muted" role="status">در حال دریافت کنترل‌های مجاز…</p>
        ) : !loadError && items.length === 0 ? (
          <EmptyState
            title="کنترلی در نتایج فعلی وجود ندارد"
            description="ممکن است هنوز کنترلی ثبت نشده باشد یا جستجوی شما نتیجه‌ای نداشته باشد."
          />
        ) : !loadError ? (
          <div className="productControlTableWrap">
            <table className="dataTable">
              <caption style={{ textAlign: "right", paddingBottom: 12, color: "#60758c" }}>
                {items.length} کنترل در نتایج بارگذاری‌شده — آمار کل سازمان از این صفحه استنباط نمی‌شود.
              </caption>
              <thead>
                <tr>
                  <th scope="col">شناسه</th>
                  <th scope="col">کنترل</th>
                  <th scope="col">نوع و ماهیت</th>
                  <th scope="col">نگاشت</th>
                  <th scope="col">پیاده‌سازی</th>
                  <th scope="col">وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {items.map(control => (
                  <tr key={control.id}>
                    <td><Link href={`/controls/${control.id}`} dir="ltr">{control.code}</Link></td>
                    <td>
                      <Link href={`/controls/${control.id}`}>{control.title}</Link>
                      {control.is_global && <span className="pill">مشترک سراسری</span>}
                    </td>
                    <td className="productControlType">{control.control_type} · {control.nature}</td>
                    <td>{control.frameworks_count ?? 0}</td>
                    <td>{control.implementations_count ?? 0}</td>
                    <td><span className="pill">{control.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </main>
  );
}
