import type { Metadata } from "next";
import { Cinzel, DM_Sans } from "next/font/google";
import Link from "next/link";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SITE_URL } from "@/lib/site";
import {
  MapPin,
  Sword,
  BookOpen,
  Gamepad2,
  Shield,
  Menu,
} from "lucide-react";
import "./globals.css";

const displayFont = Cinzel({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
});

const bodyFont = DM_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
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

const NAV_LINKS = [
  { href: "/", label: "Game Stores", icon: Sword },
  { href: "/comics", label: "Comics", icon: BookOpen },
  { href: "/retro-games", label: "Retro Games", icon: Gamepad2 },
  { href: "/warhammer", label: "Warhammer", icon: Shield },
  { href: "/near-me", label: "Near Me", icon: MapPin },
] as const;

const NAV_LINKS_LENGTH = 5;
const EBAY_STOREFRONT_URL = "https://www.ebay.com/inf/rollforstore";

/* Google Analytics ID -- hardcoded, no user input */
const GA_ID = "G-WD7RC5SPMY";
const GA_BOOTSTRAP_SCRIPT = [
  "window.dataLayer = window.dataLayer || [];",
  "function gtag(){dataLayer.push(arguments);}",
  "gtag('js', new Date());",
  `gtag('config', '${GA_ID}');`,
].join("\n");

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  console.assert(children !== undefined, "RootLayout: children must be defined");
  console.assert(NAV_LINKS.length === NAV_LINKS_LENGTH, "RootLayout: NAV_LINKS count mismatch");

  return (
    <html
      lang="en"
      className={`${displayFont.variable} ${bodyFont.variable} h-full dark`}
    >
      <head>
        <meta name="impact-site-verification" content="a353081c-3a4d-42f0-a3d7-b95126dbf90a" />
        <script async src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}></script>
        <script dangerouslySetInnerHTML={{ __html: GA_BOOTSTRAP_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-50 antialiased font-body">
        <header className="border-b border-amber-900/20 bg-zinc-950/90 backdrop-blur-md sticky top-0 z-50">
          <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 lg:px-6">
            <Link
              href="/"
              className="font-display font-bold text-xl tracking-tight flex items-center gap-2 group"
            >
              <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-yellow-600/15 text-yellow-500 group-hover:bg-yellow-600/25 transition-colors">
                <Sword className="w-4 h-4" />
              </span>
              <span className="bg-gradient-to-r from-stone-100 via-amber-100 to-stone-300 bg-clip-text text-transparent">
                Roll For Store
              </span>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {NAV_LINKS.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-50 hover:bg-zinc-800/60 transition-all duration-200"
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {link.label}
                  </Link>
                );
              })}
              <a
                href={EBAY_STOREFRONT_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-yellow-500 hover:text-yellow-400 hover:bg-yellow-600/10 transition-all duration-200"
              >
                Shop Cards
              </a>
            </div>

            {/* Mobile nav toggle */}
            <MobileNav />
          </nav>
        </header>
        <TooltipProvider>
          <main className="flex-1">{children}</main>
        </TooltipProvider>
        <footer className="border-t border-amber-900/20 bg-zinc-950">
          <div className="mx-auto max-w-7xl px-4 lg:px-6 py-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              <div>
                <h3 className="font-display font-semibold text-sm text-zinc-300 mb-3">Store Types</h3>
                <ul className="space-y-2">
                  <li><Link href="/" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">Game Stores</Link></li>
                  <li><Link href="/comics" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">Comic Shops</Link></li>
                  <li><Link href="/retro-games" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">Retro Games</Link></li>
                  <li><Link href="/warhammer" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">Warhammer</Link></li>
                </ul>
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm text-zinc-300 mb-3">Discover</h3>
                <ul className="space-y-2">
                  <li><Link href="/near-me" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">Near Me</Link></li>
                  <li><Link href="/?category=lgs" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">All Game Stores</Link></li>
                </ul>
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm text-zinc-300 mb-3">Resources</h3>
                <ul className="space-y-2">
                  <li>
                    <a href={EBAY_STOREFRONT_URL} target="_blank" rel="noopener noreferrer" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
                      Shop Cards on eBay
                    </a>
                  </li>
                </ul>
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm text-zinc-300 mb-3">Roll For Store</h3>
                <p className="text-sm text-zinc-600 leading-relaxed">
                  The most comprehensive directory of local game stores, comic shops, and hobby stores in the US.
                </p>
              </div>
            </div>
            <div className="mt-10 pt-6 border-t border-zinc-800/60 text-center text-xs text-zinc-600">
              Roll For Store
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

/** Mobile nav using details/summary for progressive enhancement (no JS required) */
function MobileNav() {
  console.assert(NAV_LINKS.length > 0, "MobileNav: NAV_LINKS must not be empty");
  console.assert(NAV_LINKS.length === NAV_LINKS_LENGTH, "MobileNav: NAV_LINKS count mismatch");

  return (
    <details className="md:hidden relative group">
      <summary aria-label="Open navigation menu" className="list-none cursor-pointer p-2 rounded-lg hover:bg-zinc-800/60 transition-colors [&::-webkit-details-marker]:hidden">
        <Menu className="w-5 h-5 text-zinc-400" />
      </summary>
      <div className="absolute right-0 top-full mt-2 w-56 rounded-xl border border-zinc-800 bg-zinc-900/95 backdrop-blur-lg shadow-xl p-2 z-50">
        {NAV_LINKS.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-zinc-300 hover:text-zinc-50 hover:bg-zinc-800/60 transition-colors"
            >
              <Icon className="w-4 h-4 text-zinc-500" />
              {link.label}
            </Link>
          );
        })}
        <div className="border-t border-zinc-800 mt-1 pt-1">
          <a
            href={EBAY_STOREFRONT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-amber-400 hover:bg-yellow-600/10 transition-colors"
          >
            Shop Cards
          </a>
        </div>
      </div>
    </details>
  );
}
