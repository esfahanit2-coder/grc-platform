"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

type WorkspaceLink = { label: string; href: string; icon: string };
type WorkspaceSection = { label: string; links: WorkspaceLink[] };

const sections: WorkspaceSection[] = [
  {
    label: "حاکمیت و انطباق",
    links: [
      { label: "داشبورد", href: "/", icon: "⌂" },
      { label: "ریسک‌ها", href: "/risks", icon: "△" },
      { label: "کنترل‌ها", href: "/controls", icon: "◇" },
      { label: "شواهد", href: "/evidence", icon: "▤" },
      { label: "پیش‌نویس SoA", href: "/soa", icon: "▧" },
    ],
  },
  {
    label: "اقدامات و ارزیابی",
    links: [
      { label: "کارهای من", href: "/work", icon: "☷" },
      { label: "اقدامات اصلاحی", href: "/actions", icon: "✓" },
      { label: "ارزیابی‌ها", href: "/assessments", icon: "▦" },
      { label: "ممیزی", href: "/audits", icon: "◎" },
      { label: "گزارش‌ها", href: "/reports", icon: "▥" },
    ],
  },
  {
    label: "مدیریت سامانه",
    links: [
      { label: "سلامت و عملیات", href: "/admin/operations", icon: "◉" },
      { label: "اتصال‌ها", href: "/connectors", icon: "↔" },
      { label: "اعلان‌ها", href: "/notifications", icon: "♧" },
    ],
  },
];

const flat = sections.flatMap(section => section.links);

export default function ProductWorkspace({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const selected = flat
    .filter(link => link.href === path || (link.href !== "/" && path.startsWith(link.href + "/")))
    .sort((a, b) => b.href.length - a.href.length)[0];
  const currentTitle = selected?.label ?? "فضای کاری";
  const isSelected = (href: string) =>
    href === path || (href !== "/" && path.startsWith(href + "/"));

  return (
    <div className="productShell" dir="rtl">
      {mobileOpen && (
        <button
          type="button"
          className="productMobileOverlay"
          aria-label="بستن فهرست مسیرها"
          onClick={() => setMobileOpen(false)}
        />
      )}
      <aside
        id="product-navigation"
        className={`productSidebar ${mobileOpen ? "productSidebar--open" : ""}`}
        aria-label="منوی اصلی نرم‌افزار"
      >
        <Link className="productBrand" href="/" onClick={() => setMobileOpen(false)}>
          <span className="productBrandMark" aria-hidden="true">G</span>
          <span>
            <strong>GRC Platform</strong>
            <small>حاکمیت، ریسک و انطباق</small>
          </span>
        </Link>
        <nav className="productNavigation" aria-label="مسیرهای نرم‌افزار">
          {sections.map(section => (
            <section key={section.label} className="productNavGroup" aria-label={section.label}>
              <h2>{section.label}</h2>
              {section.links.map(link => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`productNavLink ${isSelected(link.href) ? "productNavLink--active" : ""}`}
                  aria-current={isSelected(link.href) ? "page" : undefined}
                  onClick={() => setMobileOpen(false)}
                >
                  <span className="productNavIcon" aria-hidden="true">{link.icon}</span>
                  <span>{link.label}</span>
                </Link>
              ))}
            </section>
          ))}
        </nav>
        <p className="productSidebarFoot">نمای پایلوت · اطلاعات از سامانه واقعی</p>
      </aside>
      <div className="productWorkspace">
        <header className="productTopbar">
          <div className="productTopbarLocation">
            <button
              type="button"
              className="productNavToggle"
              aria-label="باز کردن منوی اصلی"
              aria-expanded={mobileOpen}
              aria-controls="product-navigation"
              onClick={() => setMobileOpen(open => !open)}
            >☰</button>
            <Link className="productHomeLink" href="/">خانه</Link>
            <span className="productBreadcrumbSeparator" aria-hidden="true">/</span>
            <strong>{currentTitle}</strong>
          </div>
          <div className="productTopbarLinks">
            <Link href="/work">کارهای من</Link>
            <Link href="/notifications">اعلان‌ها</Link>
          </div>
        </header>
        <div className="productWorkspaceBody">{children}</div>
      </div>
    </div>
  );
}
