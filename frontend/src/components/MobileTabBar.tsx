import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Bot, Calendar, Camera, Heart, History, Home, Images, Info, Map, Menu, MessageSquare, Route, Trophy, Users } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import InstallAppButton from "@/components/InstallAppButton";

const TABS = [
  { to: "/", label: "Home", icon: Home },
  { to: "/trips", label: "Trips", icon: Calendar },
  { to: "/map", label: "Map", icon: Map },
  { to: "/feed", label: "Photos", icon: Camera },
];
const MORE = [
  { to: "/rewards", label: "Rewards", icon: Trophy },
  { to: "/groups", label: "Groups", icon: Users },
  { to: "/wishlist", label: "Saved places", icon: Heart },
  { to: "/gallery", label: "My gallery", icon: Images },
  { to: "/history", label: "Travel history", icon: History },
  { to: "/assistant", label: "Travel buddy", icon: Bot },
  { to: "/multi-day-planner", label: "Multi-day planner", icon: Route },
  { to: "/feedback", label: "Feedback", icon: MessageSquare },
  { to: "/about", label: "About", icon: Info },
];

/** Phones and small tablets: the main sections as bottom tabs, everything else under More. */
export default function MobileTabBar() {
  const { pathname } = useLocation();
  const [more, setMore] = useState(false);
  useEffect(() => setMore(false), [pathname]);
  const active = (to: string) => (to === "/" ? pathname === "/" : pathname.startsWith(to));
  const moreActive = MORE.some((m) => active(m.to));
  const tab = (on: boolean) =>
    `flex-1 flex flex-col items-center justify-center gap-0.5 h-14 text-[11px] font-medium ${on ? "text-primary" : "text-muted-foreground"}`;

  return (
    <>
      <nav aria-label="Main" className="lg:hidden fixed bottom-0 inset-x-0 z-40 flex bg-background border-t border-border pb-[env(safe-area-inset-bottom)]">
        {TABS.map((t) => (
          <Link key={t.to} to={t.to} className={tab(active(t.to))} aria-current={active(t.to) ? "page" : undefined}>
            <t.icon className="w-5 h-5" />{t.label}
          </Link>
        ))}
        <button type="button" onClick={() => setMore(true)} className={tab(moreActive)} aria-haspopup="dialog">
          <Menu className="w-5 h-5" />More
        </button>
      </nav>
      <Sheet open={more} onOpenChange={setMore}>
        <SheetContent side="bottom" className="rounded-t-3xl max-h-[80vh] overflow-y-auto">
          <SheetHeader><SheetTitle>More</SheetTitle></SheetHeader>
          <div className="grid grid-cols-3 gap-2 pt-4">
            {MORE.map((m) => (
              <Link key={m.to} to={m.to} onClick={() => setMore(false)}
                    className={`flex flex-col items-center gap-2 rounded-2xl p-3 text-center text-xs font-medium hover:bg-accent ${active(m.to) ? "text-primary" : ""}`}>
                <m.icon className="w-6 h-6 text-primary" />{m.label}
              </Link>
            ))}
            <InstallAppButton tile />
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
