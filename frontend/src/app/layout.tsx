import type { Metadata } from "next";
import type { ReactNode } from "react";
import AppShell from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "MySEOapp — SEO Operations Dashboard",
  description:
    "Technical audits, on-page optimization, keyword research, rank tracking and white-label reporting in one dashboard.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
