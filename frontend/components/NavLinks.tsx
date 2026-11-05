"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Applications" },
  { href: "/resume", label: "Resume" },
];

export function NavLinks() {
  const path = usePathname();
  return (
    <nav className="flex gap-5 text-sm">
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" || path.startsWith("/applications") : path.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={
              active
                ? "font-medium text-ink underline decoration-marker decoration-[3px] underline-offset-[6px]"
                : "text-graphite hover:text-ink"
            }
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
