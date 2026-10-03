import { useState } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

/**
 * User-facing escape hatch when someone suspects they're on a stale build
 * or seeing stale data. Triggers the PWA update check (if registered) and
 * then performs a hard reload that bypasses the HTTP cache.
 */
export function CheckForUpdatesButton({ className }: { className?: string }) {
  const [busy, setBusy] = useState(false);

  const handleClick = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const check = (window as any).__pwaCheckForUpdate as (() => void) | undefined;
      check?.();

      // Give the service worker a moment to detect a new build and surface
      // the update banner. If no update is pending, hard-reload to evict
      // any stale data the user is worried about.
      await new Promise((r) => setTimeout(r, 800));

      toast.success("Refreshing to get the latest version…");
      // Cache-busting reload
      const url = new URL(window.location.href);
      url.searchParams.set("_r", Date.now().toString());
      window.location.replace(url.toString());
    } finally {
      setBusy(false);
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleClick}
      disabled={busy}
      className={className}
      title="Check for updates"
    >
      <RefreshCw className={`h-4 w-4 sm:mr-1.5 ${busy ? "animate-spin" : ""}`} />
      <span className="hidden sm:inline">Check for updates</span>
    </Button>
  );
}
