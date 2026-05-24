"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/search",    icon: "🔍", label: "Search"        },
  { href: "/library",   icon: "📚", label: "Library"       },
  { href: "/fetch",     icon: "📄", label: "Fetch Text"    },
  { href: "/citations", icon: "🔖", label: "Citations"     },
  { href: "/analyze",   icon: "🔬", label: "Analyze"       },
  { href: "/graph",     icon: "🕸",  label: "Graph"         },
  { href: "/agent",     icon: "🤖", label: "Agent"         },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside
      className="flex flex-col w-52 shrink-0 border-r py-6 px-3 gap-1"
      style={{ backgroundColor: "var(--color-surface)", borderColor: "var(--color-border)" }}
    >
      <div className="px-3 mb-6">
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: "var(--color-muted)" }}>
          Research Agent
        </span>
      </div>
      {NAV.map(({ href, icon, label }) => {
        const active = path.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              backgroundColor: active ? "rgba(138,180,248,0.12)" : "transparent",
              color: active ? "var(--color-accent)" : "var(--color-muted)",
            }}
          >
            <span className="text-base leading-none">{icon}</span>
            {label}
          </Link>
        );
      })}
    </aside>
  );
}
