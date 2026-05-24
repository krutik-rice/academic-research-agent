import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Academic Research Agent",
  description: "AI-powered research tool — search, analyze, and synthesize papers",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full flex overflow-hidden" style={{ backgroundColor: "var(--color-bg)" }}>
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
