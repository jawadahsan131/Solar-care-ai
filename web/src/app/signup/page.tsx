"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const [errorMessage, setErrorMessage] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setErrorMessage("");
    setNotice("");
    const values = new FormData(event.currentTarget);
    const { data, error } = await createClient().auth.signUp({
      email: String(values.get("email")),
      password: String(values.get("password")),
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) {
      setErrorMessage(error.message);
      setBusy(false);
      return;
    }
    if (!data.session) {
      setNotice("Check your email to confirm your account, then sign in.");
      setBusy(false);
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="auth-page">
      <Link className="brand-lockup" href="/">
        <span className="brand-mark">S</span> Solar Care AI
      </Link>
      <section className="auth-card">
        <p className="eyebrow">GET STARTED</p>
        <h1>Create your account</h1>
        <p className="muted">Your appliance list and estimates stay with you.</p>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input autoComplete="email" name="email" required type="email" />
          </label>
          <label>
            Password
            <input
              autoComplete="new-password"
              minLength={8}
              name="password"
              required
              type="password"
            />
          </label>
          {errorMessage && <p className="form-error" role="alert">{errorMessage}</p>}
          {notice && <p className="form-notice" role="status">{notice}</p>}
          <button className="button button-primary full-width" disabled={busy}>
            {busy ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="auth-switch">
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </section>
    </main>
  );
}
