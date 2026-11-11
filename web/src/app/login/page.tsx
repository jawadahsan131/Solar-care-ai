"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [errorMessage, setErrorMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setErrorMessage("");
    const values = new FormData(event.currentTarget);
    const { error } = await createClient().auth.signInWithPassword({
      email: String(values.get("email")),
      password: String(values.get("password")),
    });
    if (error) {
      setErrorMessage(error.message);
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
        <p className="eyebrow">WELCOME BACK</p>
        <h1>Sign in to your home</h1>
        <p className="muted">Pick up where you left off with your solar plan.</p>
        <form className="form-stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input autoComplete="email" name="email" required type="email" />
          </label>
          <label>
            Password
            <input
              autoComplete="current-password"
              minLength={6}
              name="password"
              required
              type="password"
            />
          </label>
          {errorMessage && <p className="form-error" role="alert">{errorMessage}</p>}
          <button className="button button-primary full-width" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">
          New to Solar Care AI? <Link href="/signup">Create an account</Link>
        </p>
      </section>
    </main>
  );
}
