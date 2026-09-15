"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../../lib/api";

type User = { id:number; username:string; first_name:string; last_name:string; email:string; membership_active:boolean; role_assignments:Array<{id:string; role:{name:string}; organization_unit?:{name:string}|null}> };
export default function UsersPage(){
 const [users,setUsers]=useState<User[]>([]); const [error,setError]=useState("");
 useEffect(()=>{apiFetch("/tenant-users/").then(async r=>{const b=await r.json(); if(!r.ok) throw new Error(b.detail??b.message??"خطا"); setUsers(Array.isArray(b)?b:b.results??[])}).catch(e=>setError(e.message))},[]);
 return <main className="adminPage"><div className="pageHead"><div><h1>کاربران Tenant</h1><p>عضویت، نقش و Scope سازمانی</p></div><Link href="/" className="secondaryLink">داشبورد</Link></div>{error&&<div className="message">{error}</div>}<div className="panel"><table><thead><tr><th>کاربر</th><th>نام</th><th>ایمیل</th><th>عضویت</th><th>نقش‌ها</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td>{u.username}</td><td>{u.first_name} {u.last_name}</td><td>{u.email||"—"}</td><td>{u.membership_active?"فعال":"غیرفعال"}</td><td>{u.role_assignments.map(r=><span className="pill" key={r.id}>{r.role.name}{r.organization_unit?` · ${r.organization_unit.name}`:" · کل Tenant"}</span>)}</td></tr>)}</tbody></table></div></main>
}
