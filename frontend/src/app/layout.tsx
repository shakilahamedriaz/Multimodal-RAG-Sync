import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Multimodal RAG — Knowledge Base",
  description: "Intelligent multimodal document retrieval and Q&A",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-50 text-gray-900 antialiased`}>
        <nav className="border-b border-gray-200 bg-white shadow-sm">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
            <a href="/" className="flex items-center gap-2 font-semibold text-brand-700">
              <span className="text-xl">⚡</span>
              <span>RAG Knowledge Base</span>
            </a>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
