"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../../lib/api";
type Role={id:string;code:string;name:string;is_system:boolean;permissions:Array<{code:string}>};
export default function RolesPage(){const[roles,setRoles]=useState<Role[]>([]);const[error,setError]=useState("");useEffect(()=>{apiFetch("/roles/").then(async r=>{const b=await r.json();if(!r.ok)throw new Error(b.detail??"خطا");setRoles(Array.isArray(b)?b:b.results??[])}).catch(e=>setError(e.message))},[]);return <main className="adminPage"><div className="pageHead"><div><h1>نقش‌ها و مجوزها</h1><p>RBAC و Scope سازمانی</p></div><Link href="/" className="secondaryLink">داشبورد</Link></div>{error&&<div className="message">{error}</div>}<div className="cardsList">{roles.map(r=><article className="panel" key={r.id}><div className="roleTitle"><h2>{r.name}</h2>{r.is_system&&<span className="pill">System</span>}</div><code>{r.code}</code><div className="permissionCloud">{r.permissions.map(p=><span className="pill" key={p.code}>{p.code}</span>)}</div></article>)}</div></main>}
