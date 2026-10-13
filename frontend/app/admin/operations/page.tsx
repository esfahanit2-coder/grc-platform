"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "../../../lib/api";

type StatusValue = "ok" | "warning" | "critical" | "unknown";
type Component = {
  label: string;
  status: StatusValue;
  observed_at?: string | null;
  age_seconds?: number | null;
  details?: Record<string, string | number | boolean | null>;
};
type OperationalStatus = {
  schema_version: number;
  overall_status: "healthy" | "degraded" | "critical";
  observed_at: string;
  environment: string;
  components: Record<string, Component>;
};

const componentLabels: Record<string, string> = {
  database: "پایگاه داده",
  redis: "ردیس و واسط صف",
  object_storage: "ذخیره‌سازی شواهد",
  queue: "صف پردازش سلری",
  async_pipeline: "زنجیره زمان‌بند، صف و پردازشگر",
  backup: "آخرین پشتیبان",
};

const detailLabels: Record<string, string> = {
  database_version: "نسخه پایگاه داده",
  pgvector_version: "نسخه افزونه برداری",
  queue_name: "نام صف پردازش",
  queue_depth: "تعداد پیام‌های صف",
  depth: "عمق صف",
  warning_threshold: "آستانه هشدار",
  error_type: "نوع خطا",
  reason: "دلیل وضعیت",
  source: "منبع سیگنال",
  backup_name: "شناسه نسخه پشتیبان",
  duration_seconds: "مدت عملیات (ثانیه)",
};
const detailValues: Record<string, string> = {
  not_recorded: "سیگنال ثبت نشده است",
  broker_unreachable: "اتصال به واسط پیام برقرار نیست",
  queue_depth_not_available: "عمق صف در دسترس نیست",
  stale: "سیگنال قدیمی است",
};

const statusLabels: Record<string, string> = {
  ok: "سالم",
  warning: "هشدار",
  critical: "بحرانی",
  unknown: "نامشخص",
  healthy: "سالم",
  degraded: "نیازمند توجه",
};

function formatAge(value?: number | null) {
  if (value == null) return "—";
  if (value < 60) return `${value} ثانیه`;
  if (value < 3600) return `${Math.floor(value / 60)} دقیقه`;
  return `${Math.floor(value / 3600)} ساعت`;
}

function formatDetail(key: string, value: string | number | boolean | null) {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "بله" : "خیر";
  if (key === "depth" || key === "queue_depth" || key === "warning_threshold")
    return new Intl.NumberFormat("fa-IR").format(Number(value));
  return typeof value === "string" ? (detailValues[value] ?? value) : String(value);
}

export default function OperationsPage() {
  const [data, setData] = useState<OperationalStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/operations/status/");
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(response.status === 403
          ? "برای مشاهده وضعیت استقرار، مجوز سراسری security.view لازم است."
          : "دریافت وضعیت عملیاتی ناموفق بود.");
      }
      setData(body as OperationalStatus);
    } catch (exception) {
      setData(null);
      setError(exception instanceof Error ? exception.message : "دریافت وضعیت عملیاتی ناموفق بود.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const components = data ? Object.entries(data.components) : [];

  return (
    <main className="adminPage" dir="rtl">
      <div className="pageHead">
        <div>
          <Link href="/">بازگشت به داشبورد</Link>
          <h1>عملیات و سلامت سامانه</h1>
          <p>نمای وضعیت خدمات، صف پردازش، سیگنال‌های دوره‌ای و تازگی پشتیبان؛ بدون افشای اطلاعات محرمانه</p>
        </div>
        <div className="headActions">
          <button type="button" onClick={() => void load()} disabled={loading}>
            {loading ? "در حال بررسی…" : "بررسی مجدد"}
          </button>
        </div>
      </div>

      {error && <div className="message">{error}</div>}

      {data && (
        <>
          <div className="kpis" style={{ marginBottom: 18 }}>
            <article className={`kpi ${data.overall_status === "healthy" ? "good" : "warn"}`}>
              <span>وضعیت کل</span>
              <strong>{statusLabels[data.overall_status] ?? data.overall_status}</strong>
              <small>محاسبه‌شده از مؤلفه‌های عملیاتی</small>
            </article>
            <article className="kpi">
              <span>محیط</span>
              <strong dir="ltr">{data.environment}</strong>
              <small>بدون نمایش تنظیمات محرمانه</small>
            </article>
            <article className="kpi">
              <span>مؤلفه‌های بحرانی</span>
              <strong>{components.filter(([, item]) => item.status === "critical").length}</strong>
              <small>قابل استفاده برای اعلام هشدار</small>
            </article>
            <article className="kpi">
              <span>هشدار / نامشخص</span>
              <strong>{components.filter(([, item]) => ["warning", "unknown"].includes(item.status)).length}</strong>
              <small>نیازمند بررسی عملیاتی</small>
            </article>
          </div>

          <div className="cardsList">
            {components.map(([key, item]) => (
              <article className="panel" key={key}>
                <div className="roleTitle">
                  <h2>{componentLabels[key] ?? item.label}</h2>
                  <span className="pill">{statusLabels[item.status] ?? item.status}</span>
                </div>
                {item.observed_at && (
                  <p className="muted">
                    آخرین سیگنال: {new Date(item.observed_at).toLocaleString("fa-IR")} · سن: {formatAge(item.age_seconds)}
                  </p>
                )}
                {item.details && (
                  <dl>
                    {Object.entries(item.details).map(([detailKey, value]) => (
                      <div key={detailKey} style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                        <dt title={detailKey}>{detailLabels[detailKey] ?? detailKey}</dt>
                        <dd style={{ margin: 0 }} dir="auto">{formatDetail(detailKey, value)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </article>
            ))}
          </div>

          <section className="panel" style={{ marginTop: 18 }}>
            <h2>مرز این وضعیت</h2>
            <p className="muted">
              این صفحه جایگزین پایش مستقل، تمرین بازیابی، سنجش RPO/RTO یا آزمون نفوذ نیست. وضعیت‌ها فقط بر اساس سیگنال‌های واقعی سامانه نمایش داده می‌شوند.
            </p>
          </section>
        </>
      )}

      {!data && !loading && !error && <div className="panel"><p className="muted">وضعیتی برای نمایش وجود ندارد.</p></div>}
    </main>
  );
}
