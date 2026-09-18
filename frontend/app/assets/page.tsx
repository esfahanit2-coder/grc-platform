"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiFetch } from "../../lib/api";

type Asset = {
  id:string; code:string; title:string; asset_type:string; organization_name:string;
  owner_display:string; custodian_display?:string|null; confidentiality:number; integrity:number;
  availability:number; criticality:string; status:string;
};
type OptionUnit={id:string;code:string;name:string};
type OptionUser={id:number;username:string;display:string};
type SelectorOptions={organization_units:OptionUnit[];users:OptionUser[]};

const typeLabels:Record<string,string>={
  information:"اطلاعات",hardware:"سخت‌افزار",software:"نرم‌افزار",application:"کاربرد",
  database:"پایگاه داده",cloud_service:"سرویس ابری",service:"سرویس",process:"فرآیند",
  person:"فرد",site:"سایت",other:"سایر",
};
const statusLabels:Record<string,string>={active:"فعال",retired:"بازنشسته",archived:"آرشیو"};

const emptyForm={code:"",title:"",asset_type:"application",organization_unit:"",owner:"",custodian:"",description:"",confidentiality:"3",integrity:"3",availability:"3",criticality:"3",status:"active"};

async function responseError(response:Response){
  const body=await response.json().catch(()=>({}));
  if(typeof body?.detail==="string") return body.detail;
  return "عملیات ناموفق بود. مجوزها و مقادیر ورودی را بررسی کنید.";
}

export default function AssetsPage(){
  const[rows,setRows]=useState<Asset[]>([]);
  const[options,setOptions]=useState<SelectorOptions|null>(null);
  const[search,setSearch]=useState("");
  const[typeFilter,setTypeFilter]=useState("");
  const[statusFilter,setStatusFilter]=useState("");
  const[loading,setLoading]=useState(true);
  const[error,setError]=useState("");
  const[message,setMessage]=useState("");
  const[showCreate,setShowCreate]=useState(false);
  const[form,setForm]=useState(emptyForm);
  const[saving,setSaving]=useState(false);
  const[page,setPage]=useState(1);
  const[count,setCount]=useState(0);

  const load=useCallback(async()=>{
    setLoading(true);setError("");
    const q=new URLSearchParams({page:String(page)});
    if(search.trim()) q.set("search",search.trim());
    if(typeFilter) q.set("asset_type",typeFilter);
    if(statusFilter) q.set("status",statusFilter);
    const response=await apiFetch("/assets/?"+q.toString());
    if(!response.ok){setRows([]);setError(await responseError(response));setLoading(false);return;}
    const body=await response.json();if(Array.isArray(body)){setRows(body);setCount(body.length)}else{setRows(body.results??[]);setCount(body.count??(body.results?.length??0))}setLoading(false);
  },[search,typeFilter,statusFilter,page]);

  useEffect(()=>{void load()},[load]);

  async function openCreate(){
    setMessage("");setError("");
    const response=await apiFetch("/assets/selector-options/");
    if(!response.ok){setError("فرم ایجاد دارایی برای این حساب قابل استفاده نیست یا مجوز asset.manage ندارید.");return;}
    const body=await response.json() as SelectorOptions;
    setOptions(body);
    setForm(emptyForm);
    setShowCreate(true);
  }

  async function create(event:FormEvent){
    event.preventDefault();
    if(!form.organization_unit||!form.owner){setError("واحد سازمانی و مالک را انتخاب کنید.");return;}
    setSaving(true);setError("");setMessage("");
    const payload={
      ...form,
      owner:Number(form.owner),
      custodian:form.custodian?Number(form.custodian):null,
      confidentiality:Number(form.confidentiality),
      integrity:Number(form.integrity),
      availability:Number(form.availability),
      criticality:form.criticality,
      metadata:{},
    };
    const response=await apiFetch("/assets/",{method:"POST",body:JSON.stringify(payload)});
    if(!response.ok){setError(await responseError(response));setSaving(false);return;}
    setMessage("دارایی با موفقیت ثبت شد.");setShowCreate(false);setForm(emptyForm);setSaving(false);if(page===1)await load();else setPage(1);
  }

  const field=(key:keyof typeof emptyForm,value:string)=>setForm(current=>({...current,[key]:value}));
  const pageCount=Math.max(1,Math.ceil(count/50));

  return <main className="adminPage" dir="rtl">
    <div className="pageHead">
      <div><Link href="/">بازگشت به داشبورد</Link><h1>دفتر دارایی‌ها</h1><p>مالکیت، CIA، Criticality و ردیابی وابستگی‌های دارایی</p></div>
      <button className="primary" type="button" onClick={()=>void openCreate()}>+ دارایی جدید</button>
    </div>

    {message&&<div className="message">{message}</div>}
    {error&&<div className="message">{error}</div>}

    {showCreate&&options&&<section className="panel">
      <div className="roleTitle"><h2>دارایی جدید</h2><button type="button" className="secondaryButton" onClick={()=>setShowCreate(false)}>بستن</button></div>
      <form onSubmit={create}>
        <div className="formGrid">
          <label>کد<input dir="ltr" value={form.code} onChange={e=>field("code",e.target.value)} required/></label>
          <label>عنوان<input value={form.title} onChange={e=>field("title",e.target.value)} required/></label>
          <label>نوع<select value={form.asset_type} onChange={e=>field("asset_type",e.target.value)}>{Object.entries(typeLabels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
          <label>واحد سازمانی<select value={form.organization_unit} onChange={e=>field("organization_unit",e.target.value)} required><option value="">انتخاب کنید</option>{options.organization_units.map(u=><option key={u.id} value={u.id}>{u.code} — {u.name}</option>)}</select></label>
          <label>مالک<select value={form.owner} onChange={e=>field("owner",e.target.value)} required><option value="">انتخاب کنید</option>{options.users.map(u=><option key={u.id} value={u.id}>{u.display} ({u.username})</option>)}</select></label>
          <label>متولی<select value={form.custodian} onChange={e=>field("custodian",e.target.value)}><option value="">بدون متولی</option>{options.users.map(u=><option key={u.id} value={u.id}>{u.display} ({u.username})</option>)}</select></label>
          <label>C<select value={form.confidentiality} onChange={e=>field("confidentiality",e.target.value)}>{[1,2,3,4,5].map(v=><option key={v}>{v}</option>)}</select></label>
          <label>I<select value={form.integrity} onChange={e=>field("integrity",e.target.value)}>{[1,2,3,4,5].map(v=><option key={v}>{v}</option>)}</select></label>
          <label>A<select value={form.availability} onChange={e=>field("availability",e.target.value)}>{[1,2,3,4,5].map(v=><option key={v}>{v}</option>)}</select></label>
          <label>Criticality<input type="number" min="0" step="0.01" value={form.criticality} onChange={e=>field("criticality",e.target.value)}/></label>
          <label>وضعیت<select value={form.status} onChange={e=>field("status",e.target.value)}>{Object.entries(statusLabels).filter(([v])=>v!=="archived").map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
        </div>
        <label>توضیحات<textarea value={form.description} onChange={e=>field("description",e.target.value)}/></label>
        <div className="headActions"><button type="submit" disabled={saving}>{saving?"در حال ثبت…":"ثبت دارایی"}</button></div>
      </form>
    </section>}

    <div className="toolbar">
      <input value={search} onChange={e=>{setSearch(e.target.value);setPage(1)}} placeholder="جستجو در کد، عنوان یا توضیحات"/>
      <select value={typeFilter} onChange={e=>{setTypeFilter(e.target.value);setPage(1)}}><option value="">همه انواع</option>{Object.entries(typeLabels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
      <select value={statusFilter} onChange={e=>{setStatusFilter(e.target.value);setPage(1)}}><option value="">همه وضعیت‌ها</option>{Object.entries(statusLabels).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
    </div>

    <section className="panel">
      {loading?<p className="muted">در حال دریافت دارایی‌ها…</p>:rows.length===0?<div className="emptyState">دارایی‌ای مطابق فیلترها یافت نشد.</div>:
      <div className="tableWrap"><table className="dataTable"><thead><tr><th>کد</th><th>دارایی</th><th>نوع</th><th>واحد</th><th>مالک</th><th>C/I/A</th><th>بحرانی‌بودن</th><th>وضعیت</th></tr></thead><tbody>{rows.map(a=><tr key={a.id}><td dir="ltr">{a.code}</td><td><Link href={"/assets/"+a.id}>{a.title}</Link></td><td>{typeLabels[a.asset_type]??a.asset_type}</td><td>{a.organization_name}</td><td>{a.owner_display}</td><td dir="ltr">{a.confidentiality}/{a.integrity}/{a.availability}</td><td dir="ltr">{a.criticality}</td><td>{statusLabels[a.status]??a.status}</td></tr>)}</tbody></table></div>}
      {count>50&&<div className="headActions"><button type="button" className="secondaryButton" disabled={page<=1||loading} onClick={()=>setPage(p=>Math.max(1,p-1))}>صفحه قبل</button><span>صفحه {page} از {pageCount} · {count} رکورد</span><button type="button" className="secondaryButton" disabled={page>=pageCount||loading} onClick={()=>setPage(p=>Math.min(pageCount,p+1))}>صفحه بعد</button></div>}
    </section>
  </main>;
}
