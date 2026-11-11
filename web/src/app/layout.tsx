import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Solar Care AI | Plan solar for your home",
  description:
    "List your home appliances, review your energy estimate, and compare solar system options.",
  manifest: "/manifest.webmanifest",
  applicationName: "Solar Care AI",
};

export const viewport: Viewport = {
  themeColor: "#176b4d",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
