import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-24 text-center">
      <h1 className="text-6xl font-bold text-zinc-300 mb-4">404</h1>
      <p className="text-lg text-zinc-400 mb-8">
        The page you&apos;re looking for doesn&apos;t exist.
      </p>
      <Link
        href="/"
        className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
      >
        &larr; Back to browse
      </Link>
    </div>
  );
}
