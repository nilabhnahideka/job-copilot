"use client";

/**
 * The top bar's links. Logged in: Applications, Profile, "Analyse a job", your
 * email and Log out. Logged out: Log in and Sign up. The current section is underlined.
 */
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

const LINKS = [
  { href: "/", label: "Applications" },
  { href: "/profile", label: "Profile" },
];

export function NavLinks() {
  const path = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();

  if (loading) return null;

  if (!user) {
    return (
      <div className="ml-auto flex items-center gap-4 text-sm">
        <Link href="/login" className={path === "/login" ? "font-medium" : "text-graphite hover:text-ink"}>
          Log in
        </Link>
        <Link href="/signup" className="rounded-sm bg-ink px-3.5 py-1.5 font-medium text-sheet hover:bg-ink/90">
          Sign up
        </Link>
      </div>
    );
  }

  return (
    <>
      <nav className="flex gap-5 text-sm">
        {LINKS.map((l) => {
          const active =
            l.href === "/" ? path === "/" || path.startsWith("/applications") : path.startsWith(l.href);
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
      <div className="ml-auto flex items-center gap-4 text-sm">
        <span className="hidden text-graphite md:inline">{user.email}</span>
        <button
          type="button"
          onClick={() => {
            logout();
            router.push("/login");
          }}
          className="text-graphite hover:text-ink"
        >
          Log out
        </button>
        <Link href="/new" className="rounded-sm bg-ink px-3.5 py-1.5 font-medium text-sheet hover:bg-ink/90">
          Analyse a job
        </Link>
      </div>
    </>
  );
}
