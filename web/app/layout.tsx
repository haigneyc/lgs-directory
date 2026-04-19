import type { Metadata } from "next";
import { Cinzel, DM_Sans } from "next/font/google";
import Link from "next/link";
import Script from "next/script";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SITE_URL, EBAY_URLS } from "@/lib/site";
import { AffiliateClickTracker } from "@/components/affiliate-click-tracker";
import { AffiliateLink } from "@/components/affiliate-link";
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

/**
 * Site-wide title shown on the homepage and used as the suffix template
 * for inner pages (Petra QA 2026-04-08: bare "Roll For Store" was too thin
 * for ranking on the homepage).
 */
// Keep under ~60 chars so Google's SERP doesn't truncate the title.
// Rex review 2026-04-08 flagged the previous 65-char string.
const SITE_TITLE =
  "Roll For Store — Local Game, Comic & Warhammer Stores";
const SITE_DESCRIPTION =
  "Find local game stores, comic shops, retro video game stores, and Warhammer hobby shops near you across the US.";

export const metadata: Metadata = {
  // metadataBase makes relative og:image / twitter:image paths resolve to
  // the canonical www host. Without it, Next.js prints a build warning
  // and falls back to localhost in dev (Petra QA 2026-04-08).
  metadataBase: new URL(SITE_URL),
  title: {
    default: SITE_TITLE,
    template: "%s | Roll For Store",
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
    type: "website",
    url: SITE_URL,
    siteName: "Roll For Store",
  },
  twitter: {
    // summary_large_image upgrades link previews from a small thumbnail
    // to a full-width hero card on Twitter/X (Petra QA 2026-04-08).
    card: "summary_large_image",
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
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
const EBAY_STOREFRONT_URL = EBAY_URLS.storefront;

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
        <Script
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
          strategy="afterInteractive"
        />
        <Script id="ga-bootstrap" strategy="afterInteractive">
          {GA_BOOTSTRAP_SCRIPT}
        </Script>
      </head>
      <body className="min-h-full flex flex-col bg-zinc-950 text-zinc-50 antialiased font-body">
        <AffiliateClickTracker />
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
              <div className="ml-2 flex flex-col items-center">
                <AffiliateLink
                  href={EBAY_STOREFRONT_URL}
                  network="ebay"
                  placement="site-nav-ebay"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-yellow-500 hover:text-yellow-400 hover:bg-yellow-600/10 transition-all duration-200"
                >
                  Shop Cards
                </AffiliateLink>
                <p className="text-[10px] text-zinc-600 italic -mt-1">Affiliate link</p>
              </div>
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
                    <AffiliateLink
                      href={EBAY_STOREFRONT_URL}
                      network="ebay"
                      placement="footer-ebay"
                      className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
                    >
                      Shop Cards on eBay
                    </AffiliateLink>
                    <p className="text-xs text-zinc-600 italic mt-0.5">eBay Partner affiliate link</p>
                  </li>
                  <li>
                    <Link href="/privacy-policy" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
                      Privacy Policy
                    </Link>
                  </li>
                  <li>
                    <Link href="/affiliate-disclosure" className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors">
                      Affiliate Disclosure
                    </Link>
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
            <div className="mt-10 pt-6 border-t border-zinc-800/60 text-center text-xs text-zinc-600 space-y-2">
              <p className="italic">
                As an Amazon Associate, RollForStore earns from qualifying purchases.{" "}
                <Link href="/affiliate-disclosure" className="not-italic underline hover:text-zinc-400 transition-colors">
                  Full disclosure
                </Link>
                .
              </p>
              <div className="flex items-center justify-center gap-3">
                <span>Roll For Store</span>
                <span className="text-zinc-700">|</span>
                <Link href="/privacy-policy" className="hover:text-zinc-400 transition-colors">
                  Privacy Policy
                </Link>
                <span className="text-zinc-700">|</span>
                <Link href="/affiliate-disclosure" className="hover:text-zinc-400 transition-colors">
                  Affiliate Disclosure
                </Link>
              </div>
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
          <AffiliateLink
            href={EBAY_STOREFRONT_URL}
            network="ebay"
            placement="mobile-nav-ebay"
            className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-amber-400 hover:bg-yellow-600/10 transition-colors"
            title="Affiliate link - we earn a commission on purchases"
          >
            Shop Cards
          </AffiliateLink>
          <p className="px-3 text-[10px] text-zinc-600 italic">Affiliate link</p>
        </div>
      </div>
    </details>
  );
}
