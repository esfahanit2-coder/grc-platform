"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/api";

const menu = [
  { label: "داشبورد", href: "/" },
  { label: "سازمان", href: "/organization" },
  { label: "کاربران", href: "/admin/users" },
  { label: "نقش‌ها و مجوزها", href: "/admin/roles" },
  { label: "چارچوب‌ها", href: "/frameworks" },
  { label: "کنترل‌ها", href: "/controls" },
  { label: "دارایی‌ها", href: "/assets" },
  { label: "ریسک", href: "/risks" },
  { label: "انطباق و ارزیابی", href: "/assessments" },
  { label: "شواهد", href: "/evidence" },
  { label: "یافته‌ها", href: "/findings" },
  { label: "اقدامات", href: "/actions" },
  { label: "ممیزی", href: "/audits" },
  { label: "آزمون کنترل‌ها", href: "/control-tests" },
  { label: "مستندات", href: "/documents" },
  { label: "اتصال‌ها", href: "/connectors" },
  { label: "هوش مصنوعی", href: "/ai" },
  { label: "گردش‌کار", href: "/workflows" },
  { label: "اعلان‌ها", href: "/notifications" },
  { label: "تنظیمات امنیتی", href: "/settings/security" },
];

type Finding = {
  id: string;
  title: string;
  severity?: string;
  due_date?: string | null;
};

type Dashboard = {
  compliance_score: number | null;
  high_critical_residual_risks: number;
  open_findings: number;
  overdue_actions: number;
  control_effectiveness: Record<string, number>;
  assessments_due: number;
  top_findings: Finding[];
};

function metricTone(value: number | null) {
  if (value === null) return "neutral";
  if (value >= 80) return "good";
  if (value >= 60) return "warn";
  return "bad";
}

function formatSeverity(value?: string) {
  const labels: Record<string, string> = {
    critical: "بحرانی",
    high: "بالا",
    medium: "متوسط",
    low: "پایین",
  };
  return labels[value ?? ""] ?? value ?? "—";
}

export default function Home() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/dashboard/management/");
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || body.message || `HTTP ${response.status}`);
      }
      setData(await response.json());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "دریافت داشبورد ناموفق بود.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const effectiveness = useMemo(
    () => Object.entries(data?.control_effectiveness ?? {}).sort((a, b) => b[1] - a[1]),
    [data],
  );

  const cards = [
    {
      label: "امتیاز انطباق",
      value: data?.compliance_score == null ? "—" : `${data.compliance_score}%`,
      tone: metricTone(data?.compliance_score ?? null),
    },
    {
      label: "ریسک‌های Residual بالا/بحرانی",
      value: data ? String(data.high_critical_residual_risks) : "—",
      tone: data && data.high_critical_residual_risks > 0 ? "bad" : "good",
    },
    {
      label: "یافته‌های باز",
      value: data ? String(data.open_findings) : "—",
      tone: "neutral",
    },
    {
      label: "اقدامات معوق",
      value: data ? String(data.overdue_actions) : "—",
      tone: data && data.overdue_actions > 0 ? "warn" : "good",
    },
  ];

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">G</div>
          <div>
            <strong>GRC Platform</strong>
            <small>Governance · Risk · Compliance</small>
          </div>
        </div>
        <nav>
          {menu.map((item, index) => (
            <Link key={item.href} href={item.href} className={index === 0 ? "active" : ""}>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="liveStatus">
            <strong>داشبورد عملیاتی</strong>
            <small>داده‌های tenant جاری</small>
          </div>
          <div className="topbarLinks">
            <Link className="secondaryLink" href="/connectors">عملیات اتصال‌ها</Link>
            <Link className="ai" href="/ai">دستیار هوشمند ✦</Link>
          </div>
        </header>

        <div className="content">
          <div className="titleRow">
            <div>
              <h1>داشبورد</h1>
              <p>نمای واقعی وضعیت حاکمیت، ریسک و انطباق بر اساس داده‌های قابل دسترسی شما</p>
            </div>
            <button className="primary" onClick={load} disabled={loading}>
              {loading ? "در حال بروزرسانی…" : "بروزرسانی"}
            </button>
          </div>

          {error && (
            <div className="errorBanner" role="alert">
              <strong>دریافت داشبورد ناموفق بود.</strong>
              <span>{error}</span>
            </div>
          )}

          <div className="kpis">
            {cards.map((card) => (
              <article key={card.label} className={`kpi ${card.tone}`}>
                <span>{card.label}</span>
                <strong>{loading ? "…" : card.value}</strong>
                <small>محاسبه‌شده از داده‌های جاری</small>
              </article>
            ))}
          </div>

          <div className="grid">
            <article className="panel">
              <div className="panelHead">
                <h2>اثربخشی کنترل‌ها</h2>
                <span className="pill">{effectiveness.reduce((sum, [, count]) => sum + count, 0)} کنترل</span>
              </div>
              {!loading && effectiveness.length === 0 ? (
                <p className="emptyState">هنوز داده‌ای برای اثربخشی کنترل‌ها ثبت نشده است.</p>
              ) : (
                <div className="statusList">
                  {effectiveness.map(([status, count]) => (
                    <div key={status} className="statusRow">
                      <span>{status || "نامشخص"}</span>
                      <strong>{count}</strong>
                    </div>
                  ))}
                </div>
              )}
            </article>

            <article className="panel">
              <div className="panelHead">
                <h2>ارزیابی‌های سررسیددار</h2>
                <Link href="/assessments">مشاهده ارزیابی‌ها</Link>
              </div>
              <div className="bigOperationalMetric">{loading ? "…" : data?.assessments_due ?? "—"}</div>
              <p className="muted">ارزیابی‌های تکمیل‌نشده‌ای که تاریخ سررسید برای آن‌ها ثبت شده است.</p>
            </article>

            <article className="panel wide">
              <div className="panelHead">
                <h2>یافته‌های باز با اولویت نمایش</h2>
                <Link href="/findings">همه یافته‌ها</Link>
              </div>
              {!loading && (data?.top_findings?.length ?? 0) === 0 ? (
                <p className="emptyState">یافته بازی در محدوده دسترسی فعلی وجود ندارد.</p>
              ) : (
                <table>
                  <thead>
                    <tr>
                      <th>یافته</th>
                      <th>شدت</th>
                      <th>سررسید</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data?.top_findings ?? []).map((finding) => (
                      <tr key={finding.id}>
                        <td><Link href={`/findings/${finding.id}`}>{finding.title}</Link></td>
                        <td><span className={`riskLevel ${finding.severity ?? ""}`}>{formatSeverity(finding.severity)}</span></td>
                        <td>{finding.due_date || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </article>

            <article className="panel wide">
              <h2>عملیات Pilot / RC</h2>
              <div className="operationsLinks">
                <Link href="/connectors">Connector Health & Sync</Link>
                <Link href="/reports">گزارش مدیریتی</Link>
                <Link href="/control-tests">آزمون کنترل‌ها</Link>
                <Link href="/frameworks/crosswalk">Crosswalk چارچوب‌ها</Link>
              </div>
            </article>
          </div>
        </div>
      </section>
    </main>
  );
}
