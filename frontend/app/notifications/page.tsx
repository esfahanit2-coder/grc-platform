"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button, EmptyState, PageHeader, StatusMessage, Surface } from "../../components/ui";
import { apiFetch } from "../../lib/api";
import styles from "./notifications.module.css";

type Notification = {
  id: string;
  title: string;
  body: string;
  category: string;
  severity: string;
  read_at: string | null;
  created_at: string;
};

type NotificationPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Notification[];
};

type ReadFilter = "all" | "unread";

const categoryLabels: Record<string, string> = {
  general: "عمومی",
  action_assigned: "تخصیص اقدام",
  action_due_soon: "نزدیک سررسید",
  action_overdue: "اقدام معوق",
  assessment: "ارزیابی",
  workflow: "گردش کار",
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("fa-IR");
}

function severityClass(value: string): string {
  if (value === "critical" || value === "high" || value === "error") return styles.danger;
  if (value === "warning") return styles.warning;
  return styles.info;
}

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [filter, setFilter] = useState<ReadFilter>("all");
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState("");
  const [confirmAll, setConfirmAll] = useState(false);
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const suffix = filter === "unread" ? "&unread=1" : "";
        const [listResponse, summaryResponse] = await Promise.all([
          apiFetch("/notifications/?page=" + page + suffix),
          apiFetch("/notifications/summary/"),
        ]);
        if (!listResponse.ok) {
          throw new Error(listResponse.status === 403
            ? "مجوز مشاهده اعلان‌های این حساب وجود ندارد."
            : "دریافت اعلان‌ها ناموفق بود. لطفاً دوباره تلاش کنید.");
        }
        const body: NotificationPage | Notification[] = await listResponse.json();
        const rows = Array.isArray(body) ? body : body.results;
        if (!Array.isArray(rows)) throw new Error("پاسخ فهرست اعلان‌ها معتبر نیست.");

        let unread: number | null = null;
        if (summaryResponse.ok) {
          const summary: { unread?: unknown } = await summaryResponse.json().catch(() => ({}));
          if (typeof summary.unread === "number" && Number.isFinite(summary.unread)) {
            unread = summary.unread;
          }
        }
        if (active) {
          setItems(rows);
          setCount(Array.isArray(body) ? rows.length : body.count);
          setHasNext(!Array.isArray(body) && Boolean(body.next));
          setHasPrevious(!Array.isArray(body) && Boolean(body.previous));
          setUnreadCount(unread);
        }
      } catch (exception) {
        if (active) {
          setItems([]);
          setCount(0);
          setHasNext(false);
          setHasPrevious(false);
          setUnreadCount(null);
          setError(exception instanceof Error ? exception.message : "دریافت اعلان‌ها ناموفق بود.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [filter, page, reload]);

  function changeFilter(value: ReadFilter) {
    setFilter(value);
    setPage(1);
    setConfirmAll(false);
    setNotice("");
  }

  async function markRead(id: string) {
    setWorking(id);
    setError("");
    setNotice("");
    try {
      const response = await apiFetch("/notifications/" + encodeURIComponent(id) + "/read/", { method: "POST" });
      if (!response.ok) throw new Error("ثبت وضعیت خوانده‌شده انجام نشد. لطفاً دوباره تلاش کنید.");
      setNotice("وضعیت اعلان با موفقیت ثبت شد.");
      if (filter === "unread" && items.length === 1 && page > 1) {
        setPage(value => value - 1);
      } else {
        setReload(value => value + 1);
      }
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "ثبت وضعیت اعلان ناموفق بود.");
    } finally {
      setWorking("");
    }
  }

  async function markAllRead() {
    setWorking("all");
    setError("");
    setNotice("");
    try {
      const response = await apiFetch("/notifications/read-all/", { method: "POST" });
      if (!response.ok) throw new Error("ثبت گروهی اعلان‌ها ناموفق بود. هیچ موفقیتی تأیید نشده است.");
      const result: { updated?: number } = await response.json();
      setNotice(
        typeof result.updated === "number"
          ? new Intl.NumberFormat("fa-IR").format(result.updated) + " اعلان به‌عنوان خوانده‌شده ثبت شد."
          : "درخواست ثبت گروهی انجام شد.",
      );
      setConfirmAll(false);
      setPage(1);
      setReload(value => value + 1);
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : "ثبت گروهی اعلان‌ها ناموفق بود.");
    } finally {
      setWorking("");
    }
  }

  const busy = Boolean(working);
  const countLabel = new Intl.NumberFormat("fa-IR").format(count);
  const unreadLabel = unreadCount === null ? "نامشخص" : new Intl.NumberFormat("fa-IR").format(unreadCount);

  return (
    <main className="adminPage" dir="rtl">
      <div className={styles.container}>
        <PageHeader
          eyebrow={<Link href="/">بازگشت به داشبورد</Link>}
          title="صندوق اعلان‌ها"
          description="پیگیری اعلان‌های مربوط به اقدامات، ارزیابی‌ها و گردش کار در Tenant انتخاب‌شده"
          actions={
            <div className={styles.actions}>
              <Link className="secondaryLink" href="/work">کارهای من</Link>
              <Button variant="secondary" onClick={() => { setNotice(""); setReload(value => value + 1); }} disabled={loading || busy}>
                {loading ? "در حال بارگذاری…" : "بازخوانی"}
              </Button>
            </div>
          }
        />

        <Surface>
          <div className={styles.toolbar}>
            <div className={styles.filters} aria-label="فیلتر اعلان‌ها">
              <Button variant={filter === "all" ? "primary" : "secondary"} disabled={loading || busy}
                aria-pressed={filter === "all"} onClick={() => changeFilter("all")}>
                همه اعلان‌ها
              </Button>
              <Button variant={filter === "unread" ? "primary" : "secondary"} disabled={loading || busy}
                aria-pressed={filter === "unread"} onClick={() => changeFilter("unread")}>
                خوانده‌نشده ({unreadLabel})
              </Button>
            </div>
            <div className={styles.bulk}>
              <span className={styles.muted}>تعداد در فیلتر: {countLabel}</span>
              <Button variant="ghost" disabled={loading || busy || unreadCount === null || unreadCount === 0}
                onClick={() => setConfirmAll(value => !value)}>
                علامت‌گذاری همه به‌عنوان خوانده‌شده
              </Button>
            </div>
          </div>
          {confirmAll && (
            <div className={styles.confirm} role="group" aria-label="تأیید تغییر وضعیت گروهی">
              <p>همه اعلان‌های خوانده‌نشده حساب شما در Tenant فعلی، نه فقط این صفحه، خوانده‌شده خواهند شد.</p>
              <div className={styles.actions}>
                <Button variant="secondary" disabled={busy} onClick={() => setConfirmAll(false)}>انصراف</Button>
                <Button variant="primary" busy={working === "all"} disabled={busy} onClick={() => void markAllRead()}>
                  تأیید ثبت گروهی
                </Button>
              </div>
            </div>
          )}
        </Surface>

        {error && <StatusMessage tone="danger" title="خطا">{error}</StatusMessage>}
        {notice && <StatusMessage tone="success">{notice}</StatusMessage>}

        {loading ? (
          <Surface><p className={styles.muted} role="status">در حال دریافت اعلان‌های مجاز…</p></Surface>
        ) : !error && items.length === 0 ? (
          <Surface>
            <EmptyState
              title={filter === "unread" ? "اعلان خوانده‌نشده‌ای در این صفحه وجود ندارد." : "هنوز اعلانی ثبت نشده است."}
              description="فقط اعلان‌های مربوط به حساب شما در Tenant فعال نمایش داده می‌شوند."
              action={filter === "unread" ? <Button variant="secondary" onClick={() => changeFilter("all")}>نمایش همه</Button> : undefined}
            />
          </Surface>
        ) : (
          <div className={styles.list} aria-label="فهرست اعلان‌ها">
            {items.map(item => (
              <article key={item.id} className={[styles.item, item.read_at ? styles.read : styles.unread].join(" ")}>
                <div className={styles.itemHeader}>
                  <div className={styles.itemTitle}>
                    {!item.read_at && <span className={styles.unreadDot} aria-label="خوانده‌نشده" />}
                    <h2>{item.title}</h2>
                  </div>
                  <div className={styles.tags}>
                    <span className={styles.tag}>{categoryLabels[item.category] ?? item.category}</span>
                    <span className={[styles.tag, severityClass(item.severity)].join(" ")}>{item.severity || "info"}</span>
                  </div>
                </div>
                {item.body && <p className={styles.body}>{item.body}</p>}
                <div className={styles.itemFooter}>
                  <time dateTime={item.created_at} className={styles.muted}>{formatDate(item.created_at)}</time>
                  {item.read_at ? (
                    <span className={styles.muted}>خوانده‌شده</span>
                  ) : (
                    <Button variant="secondary" size="sm" busy={working === item.id} disabled={busy || loading}
                      onClick={() => void markRead(item.id)}>علامت‌گذاری به‌عنوان خوانده‌شده</Button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}

        {!loading && !error && (hasPrevious || hasNext) && (
          <nav className={styles.pagination} aria-label="صفحه‌بندی اعلان‌ها">
            <Button variant="secondary" disabled={!hasPrevious || busy} onClick={() => setPage(value => Math.max(1, value - 1))}>
              صفحه قبل
            </Button>
            <span>صفحه {new Intl.NumberFormat("fa-IR").format(page)}</span>
            <Button variant="secondary" disabled={!hasNext || busy} onClick={() => setPage(value => value + 1)}>
              صفحه بعد
            </Button>
          </nav>
        )}
      </div>
    </main>
  );
}
