import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SITE_URL } from "@/lib/site";
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
  description:
    "Find local game stores, comic shops, retro video game stores, and Warhammer hobby shops near you across the US.",
  openGraph: {
    title: "Roll For Store",
    description:
      "Find local game stores, comic shops, retro video game stores, and Warhammer hobby shops near you across the US.",
    type: "website",
    url: SITE_URL,
  },
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
        {/* Google Analytics - hardcoded gtag snippet, no user input, safe for inline script */}
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-WD7RC5SPMY"></script>
        <script dangerouslySetInnerHTML={{ __html: `
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', 'G-WD7RC5SPMY');
        `}} />
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
                Game Stores
              </Link>
              <Link href="/comics" className="hover:text-zinc-50 transition-colors">
                Comics
              </Link>
              <Link href="/retro-games" className="hover:text-zinc-50 transition-colors">
                Retro Games
              </Link>
              <Link href="/warhammer" className="hover:text-zinc-50 transition-colors">
                Warhammer
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
