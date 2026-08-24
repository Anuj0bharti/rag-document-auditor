import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "RAG Document Auditor", description: "Evidence-first document analysis" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
