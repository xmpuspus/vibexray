import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import { authOptions } from "@/lib/auth";
import Link from "next/link";
import { SignOutButton } from "@/components/sign-out-button";
import { LayoutDashboard, MessagesSquare, Ticket, BookOpen, ExternalLink } from "lucide-react";

const NAV = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/conversations", label: "Conversations", icon: MessagesSquare },
  { href: "/admin/tickets", label: "Tickets", icon: Ticket },
  { href: "/admin/knowledge-base", label: "Knowledge Base", icon: BookOpen },
];

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  if (!session?.user) redirect("/admin/login");

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 flex-col border-r border-[hsl(var(--border))] bg-white p-4 sm:flex">
        <span className="mb-6 px-2 text-lg font-semibold">SupportCo</span>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-muted-foreground hover:bg-[hsl(var(--muted))] hover:text-foreground"
            >
              <item.icon className="h-4 w-4" /> {item.label}
            </Link>
          ))}
        </nav>
        <Link
          href="/chat"
          target="_blank"
          className="mb-2 flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-muted-foreground hover:bg-[hsl(var(--muted))]"
        >
          <ExternalLink className="h-4 w-4" /> Customer Chat
        </Link>
        <div className="border-t border-[hsl(var(--border))] pt-3">
          <p className="px-2 text-xs text-muted-foreground">{session.user.email}</p>
          <SignOutButton />
        </div>
      </aside>
      <div className="flex-1 bg-[hsl(var(--muted))]/30">
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </div>
    </div>
  );
}
