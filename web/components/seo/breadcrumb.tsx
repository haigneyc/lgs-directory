import Link from "next/link";
import { JsonLd } from "./json-ld";

export interface BreadcrumbItem {
  name: string;
  href: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  baseUrl?: string;
}

const MAX_BREADCRUMB_ITEMS = 10;
const DEFAULT_BASE_URL = "https://lgs-directory.com";

export function Breadcrumb({ items, baseUrl = DEFAULT_BASE_URL }: BreadcrumbProps) {
  console.assert(Array.isArray(items), "Breadcrumb: items must be an array");
  console.assert(items.length > 0, "Breadcrumb: items must not be empty");

  const capped = items.slice(0, MAX_BREADCRUMB_ITEMS);

  const ldItems = capped.map((item, idx) => ({
    "@type": "ListItem",
    position: idx + 1,
    name: item.name,
    item: `${baseUrl}${item.href}`,
  }));

  const ldData = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: ldItems,
  };

  return (
    <>
      <JsonLd data={ldData} />
      <nav aria-label="Breadcrumb">
        <ol className="flex items-center gap-2">
          {capped.map((item, idx) => {
            const isLast = idx === capped.length - 1;
            return (
              <li key={item.href} className="flex items-center gap-2">
                {idx > 0 && (
                  <span className="text-sm text-zinc-600" aria-hidden="true">
                    →
                  </span>
                )}
                {isLast ? (
                  <span className="text-sm text-zinc-300">{item.name}</span>
                ) : (
                  <Link
                    href={item.href}
                    className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {item.name}
                  </Link>
                )}
              </li>
            );
          })}
        </ol>
      </nav>
    </>
  );
}
