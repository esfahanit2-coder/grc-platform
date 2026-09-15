import Link from "next/link";

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
  { label: "مستندات", href: "/documents" },
  { label: "هوش مصنوعی", href: "/ai" },
  { label: "گردش‌کار", href: "/workflows" },
  { label: "اعلان‌ها", href: "/notifications" },
  { label: "تنظیمات امنیتی", href: "/settings/security" },
];

const cards = [
  { label: "درصد انطباق کل", value: "72%", tone: "good" },
  { label: "ریسک‌های بحرانی و بالا", value: "12", tone: "bad" },
  { label: "یافته‌های باز", value: "21", tone: "neutral" },
  { label: "اقدامات معوق", value: "17", tone: "warn" },
];

export default function Home() {
  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">G</div>
          <div><strong>GRC Platform</strong><small>Governance · Risk · Compliance</small></div>
        </div>
        <nav>{menu.map((item, i) => <Link key={item.label} href={item.href} className={i === 0 ? "active" : ""}>{item.label}</Link>)}</nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div className="profile"><span className="avatar">ع</span><div><strong>علی محمدی</strong><small>مدیر ریسک</small></div></div>
          <div className="search">جستجو در ریسک‌ها، کنترل‌ها، مستندات ... <kbd>Ctrl K</kbd></div>
          <Link className="ai" href="/ai">دستیار هوشمند ✦</Link>
        </header>

        <div className="content">
          <div className="titleRow"><div><h1>داشبورد</h1><p>نمای کلی وضعیت حاکمیت، ریسک و انطباق سازمان</p></div><button className="primary">+ ایجاد سریع</button></div>
          <div className="filters"><button>همه واحدها⌄</button><button>همه چارچوب‌ها⌄</button><button>۳۰ روز گذشته⌄</button></div>
          <div className="kpis">{cards.map(c => <article key={c.label} className={`kpi ${c.tone}`}><span>{c.label}</span><strong>{c.value}</strong><small>نمونه رابط Sprint 6</small></article>)}</div>
          <div className="grid">
            <article className="panel"><h2>وضعیت انطباق بر اساس چارچوب</h2>{[["ISO/IEC 27001","78%",78],["افتا","64%",64],["COBIT 2019","51%",51],["ISO 9001","73%",73],["ISO 31000","68%",68]].map(([n,v,p]) => <div className="barRow" key={String(n)}><span>{n}</span><div className="bar"><i style={{width:`${p}%`}} /></div><b>{v}</b></div>)}</article>
            <article className="panel"><h2>ریسک‌های برتر</h2><table><tbody><tr><th>شناسه</th><th>ریسک</th><th>سطح</th></tr><tr><td>R-001</td><td>دسترسی غیرمجاز مدیریتی</td><td><em className="critical">بحرانی</em></td></tr><tr><td>R-002</td><td>خرابی سامانه پشتیبان‌گیری</td><td><em className="high">بالا</em></td></tr><tr><td>R-003</td><td>نشت اطلاعات مشتریان</td><td><em className="high">بالا</em></td></tr></tbody></table></article>
            <article className="panel wide"><h2>Foundation status</h2><p className="muted">این رابط عمداً داده نمونه نشان می‌دهد. Sprint 4 ارزیابی انطباق، Evidence قابل استفاده مجدد، Finding و CAPA را به هسته ریسک و کنترل متصل می‌کند.</p><div className="foundation"><span>✓ RTL shell</span><span>✓ API v1</span><span>✓ Scoped RBAC</span><span>✓ PostgreSQL</span><span>✓ Professional audit trail</span><span>✓ Framework Engine</span><span>✓ Version Lock</span><span>✓ Crosswalk</span><span>✓ Common Controls</span><span>✓ Asset Register</span><span>✓ Risk Engine</span><span>✓ RTP</span><span>✓ Compliance Assessment</span><span>✓ Evidence Reuse</span><span>✓ Finding & CAPA</span><span>✓ S3 abstraction</span><span>✓ AI Gateway</span><span>✓ Local AI</span><span>✓ Permission-safe RAG</span><span>✓ Workflow</span><span>✓ Notifications</span><span>✓ PDF Template Engine</span></div></article>
          </div>
        </div>
      </section>
    <section className="panel"><h2>ماژول‌های Sprint 5 و 6</h2><p><Link href="/audits">ممیزی داخلی</Link> · <Link href="/control-tests">آزمون کنترل‌ها</Link> · <Link href="/documents">مستندات</Link> · <Link href="/reports">گزارش مدیریتی</Link> · <Link href="/ai">AI/RAG</Link> · <Link href="/workflows">Workflow</Link></p></section></main>
  );
}
