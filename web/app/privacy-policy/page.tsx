import type { Metadata } from "next";
import Link from "next/link";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "Privacy policy for Roll For Store, covering data collection, Google Analytics, affiliate programs, and your rights.",
  alternates: { canonical: `${SITE_URL}/privacy-policy` },
  robots: { index: true, follow: true },
  openGraph: {
    title: "Privacy Policy",
    description:
      "Privacy policy for Roll For Store, covering data collection, Google Analytics, affiliate programs, and your rights.",
    type: "website",
    url: `${SITE_URL}/privacy-policy`,
  },
};

/** Last updated date for the privacy policy */
const LAST_UPDATED = "April 6, 2026";

/** Contact email for privacy requests */
const CONTACT_EMAIL = "privacy@rollforstore.com";

/** Sections for the privacy policy -- keeps the JSX clean */
const SECTION_COUNT = 8;

export default function PrivacyPolicyPage() {
  console.assert(
    LAST_UPDATED.length > 0,
    "PrivacyPolicyPage: LAST_UPDATED must not be empty",
  );
  console.assert(
    CONTACT_EMAIL.includes("@"),
    "PrivacyPolicyPage: CONTACT_EMAIL must be a valid email",
  );

  return (
    <div className="mx-auto max-w-3xl px-4 lg:px-6 py-12">
      <header className="mb-10">
        <h1 className="font-display text-3xl font-bold tracking-tight bg-gradient-to-r from-stone-100 via-amber-100 to-stone-300 bg-clip-text text-transparent mb-2">
          Privacy Policy
        </h1>
        <p className="text-sm text-zinc-500">
          Last updated: {LAST_UPDATED}
        </p>
      </header>

      <div className="space-y-10 text-sm text-zinc-300 leading-relaxed">
        {/* Section 1: Introduction */}
        <Section number={1} title="Introduction">
          <p>
            Roll For Store (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;)
            operates the website{" "}
            <Link
              href="/"
              className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
            >
              rollforstore.com
            </Link>
            . This Privacy Policy explains what information we collect, how we
            use it, and your rights regarding that information.
          </p>
          <p className="mt-3">
            Roll For Store is a directory website. We do not require user
            accounts, and we do not collect personal information directly. Our
            data collection is limited to anonymous analytics and cookies set by
            third-party services described below.
          </p>
        </Section>

        {/* Section 2: Information We Collect */}
        <Section number={2} title="Information We Collect">
          <p>We collect the following types of anonymous data through third-party services:</p>
          <ul className="list-disc list-inside mt-3 space-y-1.5 text-zinc-400">
            <li>IP address (anonymized by Google Analytics)</li>
            <li>Browser type and version</li>
            <li>Device type (desktop, mobile, tablet)</li>
            <li>Pages visited, time spent on pages, and navigation paths</li>
            <li>Referring website or search engine</li>
            <li>General geographic location (country/region level)</li>
          </ul>
          <p className="mt-3">
            We do <strong className="text-zinc-200">not</strong> collect names,
            email addresses, payment information, or any other personally
            identifiable information.
          </p>
        </Section>

        {/* Section 3: Google Analytics */}
        <Section number={3} title="Google Analytics">
          <p>
            We use Google Analytics (measurement ID: G-WD7RC5SPMY) to understand
            how visitors use our site. Google Analytics uses cookies -- small
            text files stored on your device -- to collect anonymous usage data.
          </p>
          <p className="mt-3">The primary cookie used is:</p>
          <ul className="list-disc list-inside mt-2 space-y-1.5 text-zinc-400">
            <li>
              <code className="text-xs bg-zinc-800 px-1.5 py-0.5 rounded font-mono">
                _ga
              </code>{" "}
              -- Used to distinguish unique visitors. Expires after 2 years.
            </li>
          </ul>
          <p className="mt-3">
            Google Analytics collects data anonymously and reports website trends
            without identifying individual visitors. We use this data solely to
            analyze site traffic and improve user experience.
          </p>
          <p className="mt-3">
            For more information, see{" "}
            <a
              href="https://policies.google.com/privacy"
              target="_blank"
              rel="noopener noreferrer"
              className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
            >
              Google&apos;s Privacy Policy
            </a>
            . You can opt out of Google Analytics by installing the{" "}
            <a
              href="https://tools.google.com/dlpage/gaoptout"
              target="_blank"
              rel="noopener noreferrer"
              className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
            >
              Google Analytics Opt-out Browser Add-on
            </a>
            .
          </p>
        </Section>

        {/* Section 4: Affiliate Programs */}
        <Section number={4} title="Affiliate Programs">
          <p>
            Roll For Store participates in the following affiliate programs:
          </p>
          <ul className="list-disc list-inside mt-3 space-y-1.5 text-zinc-400">
            <li>
              <strong className="text-zinc-200">eBay Partner Network</strong> --
              When you click an eBay affiliate link on our site, eBay may set
              cookies on your device to track whether you make a purchase. If you
              do, we may earn a small commission at no extra cost to you.
            </li>
          </ul>
          <p className="mt-3">
            These affiliate cookies are set by the respective programs, not by
            Roll For Store. We do not have access to the data collected by these
            cookies. Each program&apos;s privacy policy governs how they handle
            your data.
          </p>
        </Section>

        {/* Section 5: Third-Party Data Sharing */}
        <Section number={5} title="Third-Party Data Sharing">
          <p>
            We do not sell your personal information. Data may be shared with the
            following third parties solely as part of the services described above:
          </p>
          <ul className="list-disc list-inside mt-3 space-y-1.5 text-zinc-400">
            <li>
              <strong className="text-zinc-200">Google</strong> -- Anonymous
              analytics data via Google Analytics
            </li>
            <li>
              <strong className="text-zinc-200">eBay</strong> -- Affiliate
              tracking cookies when you click eBay links
            </li>
          </ul>
        </Section>

        {/* Section 6: Your Rights (CCPA) */}
        <Section number={6} title="Your Rights (California Residents)">
          <p>
            If you are a California resident, the California Consumer Privacy Act
            (CCPA) grants you the following rights:
          </p>
          <ul className="list-disc list-inside mt-3 space-y-1.5 text-zinc-400">
            <li>
              <strong className="text-zinc-200">Right to know</strong> -- You
              may request information about what data we collect and how it is
              used.
            </li>
            <li>
              <strong className="text-zinc-200">Right to delete</strong> -- You
              may request deletion of any personal information we hold about you.
            </li>
            <li>
              <strong className="text-zinc-200">Right to opt out</strong> -- You
              may opt out of the &quot;sale&quot; or &quot;sharing&quot; of
              personal information. As noted above, we do not sell personal
              information. You may opt out of Google Analytics tracking using the{" "}
              <a
                href="https://tools.google.com/dlpage/gaoptout"
                target="_blank"
                rel="noopener noreferrer"
                className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
              >
                Google Analytics Opt-out Add-on
              </a>
              .
            </li>
            <li>
              <strong className="text-zinc-200">
                Right to non-discrimination
              </strong>{" "}
              -- We will not discriminate against you for exercising your privacy
              rights.
            </li>
          </ul>
          <p className="mt-3">
            To exercise any of these rights, contact us at{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>

        {/* Section 7: Cookie Management */}
        <Section number={7} title="Cookie Management">
          <p>
            You can control cookies through your browser settings. Most browsers
            allow you to block or delete cookies. Please note that disabling
            cookies may affect the functionality of some websites.
          </p>
          <p className="mt-3">
            This site uses cookies only for analytics (Google Analytics) and
            affiliate tracking (eBay Partner Network). We do not use cookies for
            advertising, personalization, or user authentication.
          </p>
        </Section>

        {/* Section 8: Changes & Contact */}
        <Section number={8} title="Changes to This Policy">
          <p>
            We may update this Privacy Policy from time to time. Changes will be
            posted on this page with an updated &quot;Last updated&quot; date.
          </p>
          <p className="mt-3">
            If you have questions about this Privacy Policy, contact us at{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="text-yellow-500 hover:text-yellow-400 underline underline-offset-2"
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section helper                                                     */
/* ------------------------------------------------------------------ */

interface SectionProps {
  number: number;
  title: string;
  children: React.ReactNode;
}

function Section({ number, title, children }: SectionProps) {
  console.assert(
    number >= 1 && number <= SECTION_COUNT,
    `Section: number ${number} out of range 1..${SECTION_COUNT}`,
  );
  console.assert(title.length > 0, "Section: title must not be empty");

  return (
    <section>
      <h2 className="font-display text-lg font-semibold tracking-tight text-zinc-100 mb-3">
        {number}. {title}
      </h2>
      {children}
    </section>
  );
}
