import type { FaqItem } from "@/lib/faq";
import { HelpCircle } from "lucide-react";

interface StoreFaqProps {
  items: FaqItem[];
  storeName: string;
}

const MAX_DISPLAY_ITEMS = 12;

export function StoreFaq({ items, storeName }: StoreFaqProps) {
  console.assert(Array.isArray(items), "StoreFaq: items must be an array");
  console.assert(typeof storeName === "string", "StoreFaq: storeName must be a string");

  if (items.length === 0) {
    return null;
  }

  const displayItems = items.slice(0, MAX_DISPLAY_ITEMS);

  return (
    <section aria-label={`Frequently asked questions about ${storeName}`}>
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle className="w-5 h-5 text-yellow-500" />
        <h2 className="font-display text-lg font-semibold">
          Frequently Asked Questions
        </h2>
      </div>
      <div className="space-y-2">
        {displayItems.map((item) => (
          <details
            key={item.question}
            className="group rounded-xl border border-zinc-800 bg-zinc-900/50 transition-colors hover:bg-zinc-900/80"
          >
            <summary className="flex cursor-pointer items-center justify-between px-5 py-4 text-sm font-medium text-zinc-200 hover:text-zinc-100 transition-colors [&::-webkit-details-marker]:hidden">
              <span>{item.question}</span>
              <span
                className="ml-2 text-zinc-500 transition-transform duration-200 group-open:rotate-45"
                aria-hidden="true"
              >
                +
              </span>
            </summary>
            <div className="px-5 pb-4 text-sm text-zinc-400 leading-relaxed">
              {item.answer}
            </div>
          </details>
        ))}
      </div>
    </section>
  );
}
