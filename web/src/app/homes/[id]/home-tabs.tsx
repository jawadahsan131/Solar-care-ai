"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

const tabs = [
  { path: "", label: "Appliances", icon: "⌂" },
  { path: "/add", label: "Add", icon: "+" },
  { path: "/bills", label: "Bills", icon: "▤" },
  { path: "/forecast", label: "Forecast", icon: "☼" },
  { path: "/today", label: "Today", icon: "◷" },
  { path: "/checkin", label: "Check-in", icon: "✓" },
  { path: "/plan", label: "Plan", icon: "↗" },
  { path: "/dashboard", label: "Dashboard", icon: "▦" },
  { path: "/whatif", label: "What-if", icon: "◇" },
  { path: "/report", label: "Report", icon: "↗" },
];

export default function HomeTabs() {
  const { id } = useParams<{ id: string }>();
  const pathname = usePathname();

  return (
    <nav className="home-tabs" aria-label="Home sections">
      {tabs.map((tab) => {
        const href = `/homes/${id}${tab.path}`;
        const active =
          tab.path === ""
            ? pathname === `/homes/${id}`
            : pathname.startsWith(href);
        return (
          <Link
            aria-current={active ? "page" : undefined}
            className={`home-tab${active ? " active" : ""}`}
            href={href}
            key={tab.label}
          >
            <span aria-hidden="true">{tab.icon}</span>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
