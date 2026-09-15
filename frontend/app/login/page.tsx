"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { API_BASE, persistSession } from "../../lib/api";

type Step = "password" | "otp" | "enroll" | "enroll_verify" | "done";

export default function LoginPage() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<Step>("password");
  const [challenge, setChallenge] = useState("");
  const [deviceId, setDeviceId] = useState("");
  const [secret, setSecret] = useState("");
  const [otpUri, setOtpUri] = useState("");

  async function completeLogin(body: { access?: string; refresh?: string; cookie_auth?: boolean }) {
    await persistSession(body);
    setStep("done");
    setMessage("ورود موفق بود. Tenant فعال نیز برای نشست انتخاب شد.");
  }

  async function submitPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await fetch(`${API_BASE}/auth/token`, {
        method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include",
        body: JSON.stringify({ username: data.get("username"), password: data.get("password") }),
      });
      const body = await response.json();
      if (response.status === 202 && body.code === "MFA_REQUIRED") { setChallenge(body.challenge); setStep("otp"); return; }
      if (response.status === 428 && body.code === "MFA_SETUP_REQUIRED") {
        const enroll = await fetch(`${API_BASE}/auth/mfa/enroll`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify({ challenge: body.challenge }) });
        const enrollment = await enroll.json();
        if (!enroll.ok) throw new Error(enrollment.message ?? "راه‌اندازی MFA ناموفق بود");
        setChallenge(enrollment.challenge); setDeviceId(enrollment.device_id); setSecret(enrollment.secret); setOtpUri(enrollment.otpauth_uri); setStep("enroll_verify"); return;
      }
      if (!response.ok) throw new Error(body.message ?? body.detail ?? "ورود ناموفق بود");
      await completeLogin(body);
    } catch (error) { setMessage(error instanceof Error ? error.message : "خطای نامشخص"); }
    finally { setLoading(false); }
  }

  async function submitOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const endpoint = step === "otp" ? "/auth/mfa/verify-login" : "/auth/mfa/enroll/verify";
      const payload: Record<string, unknown> = { challenge, otp: data.get("otp") };
      if (step === "enroll_verify") payload.device_id = deviceId;
      const response = await fetch(`${API_BASE}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "include", body: JSON.stringify(payload) });
      const body = await response.json();
      if (!response.ok) throw new Error(body.message ?? "کد تأیید معتبر نیست");
      await completeLogin(body);
    } catch (error) { setMessage(error instanceof Error ? error.message : "خطای نامشخص"); }
    finally { setLoading(false); }
  }

  return (
    <main className="loginPage">
      <div className="loginCard">
        <div className="brandMark large">G</div><h1>ورود به GRC Platform</h1>
        {step === "password" && <form className="stack" onSubmit={submitPassword}><p>احراز هویت و MFA — GRC Platform</p><label>نام کاربری<input name="username" autoComplete="username" required /></label><label>رمز عبور<input name="password" type="password" autoComplete="current-password" required /></label><button className="primary" disabled={loading}>{loading ? "در حال ورود..." : "ورود"}</button></form>}
        {step === "otp" && <form className="stack" onSubmit={submitOtp}><p>کد شش‌رقمی برنامه Authenticator را وارد کنید.</p><label>کد MFA<input name="otp" inputMode="numeric" autoComplete="one-time-code" required /></label><button className="primary" disabled={loading}>تأیید و ورود</button></form>}
        {step === "enroll_verify" && <form className="stack" onSubmit={submitOtp}><p>سازمان شما MFA را اجباری کرده است. Secret زیر را در Authenticator ثبت کنید و سپس کد را وارد کنید.</p><code className="secretBox">{secret}</code><details><summary>نمایش URI فنی</summary><small className="breakText">{otpUri}</small></details><label>کد MFA<input name="otp" inputMode="numeric" autoComplete="one-time-code" required /></label><button className="primary" disabled={loading}>فعال‌سازی MFA و ورود</button></form>}
        {step === "done" && <Link className="primary linkButton" href="/">ورود به داشبورد</Link>}
        {message && <div className="message">{message}</div>}<Link href="/">بازگشت</Link>
      </div>
    </main>
  );
}
