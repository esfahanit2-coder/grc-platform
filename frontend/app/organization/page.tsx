"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "../../lib/api";
type Node={id:string;code:string;name:string;unit_type:string;children:Node[]};
function Tree({nodes,depth=0}:{nodes:Node[];depth?:number}){return <>{nodes.map(n=><div key={n.id}><div className="treeNode" style={{marginRight:depth*24}}><b>{n.name}</b><span>{n.code} · {n.unit_type}</span></div><Tree nodes={n.children??[]} depth={depth+1}/></div>)}</>}
export default function OrganizationPage(){const[nodes,setNodes]=useState<Node[]>([]);const[error,setError]=useState("");useEffect(()=>{apiFetch("/organization-units/tree/").then(async r=>{const b=await r.json();if(!r.ok)throw new Error(b.detail??"خطا");setNodes(b)}).catch(e=>setError(e.message))},[]);return <main className="adminPage"><div className="pageHead"><div><h1>ساختار سازمانی</h1><p>نمای Scope-aware؛ فقط واحدهای مجاز نمایش داده می‌شوند.</p></div><Link href="/" className="secondaryLink">داشبورد</Link></div>{error&&<div className="message">{error}</div>}<div className="panel"><Tree nodes={nodes}/></div></main>}
