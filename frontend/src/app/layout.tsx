import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Boxes } from "lucide-react";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

const inter = Inter({ subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "Multimodal RAG — Knowledge Base",
  description: "Intelligent multimodal document retrieval and Q&A",
};

// Applied before paint to avoid a flash of the wrong theme.
const themeScript = `
(function () {
  try {
    var t = localStorage.getItem('theme') || 'dark';
    document.documentElement.dataset.theme = t;
  } catch (e) {
    document.documentElement.dataset.theme = 'dark';
  }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${inter.className} ${jetbrainsMono.variable} antialiased`}>
        <nav className="sticky top-0 z-40 border-b bg-bg/80 backdrop-blur-md" style={{ borderColor: "var(--line)" }}>
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
            <a href="/" className="flex items-center gap-2.5">
              <span
                className="grid h-8 w-8 place-items-center rounded-lg text-accent-fg"
                style={{ background: "linear-gradient(135deg, rgb(var(--accent)), rgb(var(--accent-2)))" }}
              >
                <Boxes className="h-4 w-4" />
              </span>
              <div className="leading-none">
                <span className="block text-sm font-bold tracking-tight text-fg">NeuralDocs</span>
                <span className="block font-mono text-[10px] text-fg-subtle">RAG · Multimodal</span>
              </div>
            </a>

            <div className="ml-auto flex items-center gap-2">
              <a
                href="/#knowledge-bases"
                className="hidden rounded-lg px-3 py-1.5 text-xs text-fg-muted transition hover:bg-surface-2 hover:text-fg sm:block"
              >
                Workspace
              </a>
              <ThemeToggle />
            </div>
          </div>
        </nav>
        <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
