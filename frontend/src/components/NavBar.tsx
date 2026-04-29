"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { signOut } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/projects", label: "Projects" },
  { href: "/jobs", label: "AI Jobs" },
  { href: "/billing", label: "Billing" },
];

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  async function handleLogout() {
    await signOut();
    router.replace("/login");
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/projects" className="text-lg font-bold text-indigo-600">
          CoachX Media AI
        </Link>

        <nav className="flex items-center gap-6">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={`text-sm font-medium transition-colors ${
                pathname.startsWith(href)
                  ? "text-indigo-600"
                  : "text-gray-600 hover:text-indigo-600"
              }`}
            >
              {label}
            </Link>
          ))}
          <button
            onClick={handleLogout}
            className="text-sm font-medium text-gray-600 hover:text-red-500 transition-colors"
          >
            Logout
          </button>
        </nav>
      </div>
    </header>
  );
}
