import Link from "next/link";
import { Search } from "lucide-react";

export default function NotFound() {
  console.assert(typeof Link === "function", "NotFound: Link component must be defined");
  console.assert(Search !== null && Search !== undefined, "NotFound: Search icon must be defined");

  return (
    <div className="mx-auto max-w-7xl px-4 py-24 text-center">
      <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-zinc-800/50 mb-6">
        <Search className="w-8 h-8 text-zinc-500" />
      </div>
      <h1 className="font-display text-6xl font-bold text-zinc-300 mb-4">404</h1>
      <p className="text-lg text-zinc-400 mb-8">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm text-yellow-500 hover:text-yellow-400 transition-colors"
      >
        &larr; Back to Roll For Store
      </Link>
    </div>
  );
}
