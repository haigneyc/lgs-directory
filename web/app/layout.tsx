import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Roll For Store",
  description: "Find local game stores near you",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full dark`}
    >
      <head>
        <meta name="impact-site-verification" content="a353081c-3a4d-42f0-a3d7-b95126dbf90a" />
      </head>
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-50 antialiased">
        <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-sm sticky top-0 z-50">
          <nav className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
            <Link
              href="/"
              className="font-semibold text-lg tracking-tight"
            >
              Roll For Store
            </Link>
            <div className="flex items-center gap-6 text-sm text-zinc-400">
              <Link href="/" className="hover:text-zinc-50 transition-colors">
                Browse
              </Link>
              <Link
                href="/near-me"
                className="hover:text-zinc-50 transition-colors"
              >
                Near Me
              </Link>
              <a
                href="https://hollowhag.tcgplayerpro.com/"
                target="_blank"
                rel="noopener"
                className="text-amber-400 hover:text-amber-300 transition-colors"
              >
                Shop Cards
              </a>
            </div>
          </nav>
        </header>
        <TooltipProvider>
          <main className="flex-1">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
