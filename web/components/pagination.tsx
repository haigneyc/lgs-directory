"use client";

import Link from "next/link";
import { useSearchParams, usePathname } from "next/navigation";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
}

export function Pagination({ page, pageSize, total }: PaginationProps) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const totalPages = Math.ceil(total / pageSize);

  function buildHref(targetPage: number): string {
    const params = new URLSearchParams(searchParams.toString());
    if (targetPage <= 1) {
      params.delete("page");
    } else {
      params.set("page", String(targetPage));
    }
    const qs = params.toString();
    return qs ? `${pathname}?${qs}` : pathname;
  }

  const btnClass = cn(
    buttonVariants({ variant: "outline", size: "sm" }),
    "border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800"
  );

  const disabledClass = "pointer-events-none opacity-50";

  return (
    <div className="flex items-center justify-between pt-4">
      <p className="text-sm text-zinc-500">
        {total.toLocaleString()} store{total === 1 ? "" : "s"} found
      </p>
      {totalPages > 1 && (
        <div className="flex items-center gap-2">
          {page > 1 ? (
            <Link href={buildHref(page - 1)} className={btnClass}>
              Previous
            </Link>
          ) : (
            <span className={cn(btnClass, disabledClass)}>Previous</span>
          )}
          <span className="text-sm text-zinc-400 px-2">
            {page} / {totalPages}
          </span>
          {page < totalPages ? (
            <Link href={buildHref(page + 1)} className={btnClass}>
              Next
            </Link>
          ) : (
            <span className={cn(btnClass, disabledClass)}>Next</span>
          )}
        </div>
      )}
    </div>
  );
}
