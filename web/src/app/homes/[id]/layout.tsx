import Link from "next/link";
import { Suspense } from "react";
import HomeTabs from "./home-tabs";

export default function HomeLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <main className="app-shell home-app-shell">
      <header className="topbar home-topbar">
        <Link className="brand-lockup" href="/dashboard">
          <span className="brand-mark">S</span> Solar Care AI
        </Link>
        <Link className="button button-quiet" href="/dashboard">All homes</Link>
      </header>
      <Suspense fallback={<div className="loading-panel">Loading navigation…</div>}>
        <HomeTabs />
      </Suspense>
      {children}
    </main>
  );
}
