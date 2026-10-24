import { Link, useLocation } from "react-router-dom";
import {
  Heart, User, LogOut, Sun, Moon, Calendar, MapPin, Camera, Trophy, Users, Images, History, Bot, Languages,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import LiveTripLogo from "@/components/LiveTripLogo";
import { LANGUAGES, currentLanguage, setLanguage } from "@/lib/translate";
import { useState, useEffect } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/trips", label: "My Trips", live: true },
  { to: "/feed", label: "Photo feed" },
  { to: "/rewards", label: "Rewards" },
  { to: "/groups", label: "Groups" },
  { to: "/map", label: "Map" },
  { to: "/feedback", label: "Feedback" },
];

const MENU = [
  { to: "/trips", label: "My trips", icon: Calendar },
  { to: "/gallery", label: "My gallery", icon: Images },
  { to: "/wishlist", label: "Saved places", icon: Heart },
  { to: "/history", label: "Travel history", icon: History },
  { to: "/assistant", label: "Travel assistant", icon: Bot },
  { to: "/rewards", label: "Rewards", icon: Trophy },
  { to: "/groups", label: "Trip groups", icon: Users },
  { to: "/multi-day-planner", label: "Multi-day planner", icon: MapPin },
];

export default function Navbar() {
  const location = useLocation();
  const { user, isAuthenticated, login, logout } = useAuth();
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [language, setLanguageState] = useState(currentLanguage());
  useEffect(() => {
    const sync = () => setLanguageState(currentLanguage());
    window.addEventListener("livetrip-language", sync);
    return () => window.removeEventListener("livetrip-language", sync);
  }, []);

  useEffect(() => {
    // light unless the traveller picked dark with the moon button (the computer's setting no longer decides)
    const shouldBeDark = localStorage.getItem('theme') === 'dark';

    setIsDarkMode(shouldBeDark);
    if (shouldBeDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    const newMode = !isDarkMode;
    setIsDarkMode(newMode);
    localStorage.setItem('theme', newMode ? 'dark' : 'light');
    if (newMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const active = (to: string) => (to === "/" ? location.pathname === "/" : location.pathname.startsWith(to));

  return (
    <header className="bg-background border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          {/* Logo */}
          <Link to="/" data-testid="link-home">
            <LiveTripLogo size="lg" className="cursor-pointer" />
          </Link>

          {/* Navigation Menu */}
          <nav className="hidden lg:flex space-x-6">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} data-testid={`link-nav-${n.label.toLowerCase().replace(/\s/g, "-")}`}>
                <span className={`font-medium transition-colors cursor-pointer flex items-center space-x-2 ${
                  active(n.to) ? "text-primary" : "text-foreground hover:text-primary"
                }`}>
                  <span>{n.label}</span>
                  {n.live && <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>}
                </span>
              </Link>
            ))}
          </nav>

          {/* Mobile Navigation */}
          <nav className="lg:hidden flex space-x-4">
            <Link to="/trips">
              <span className="flex items-center space-x-1 text-sm font-medium text-foreground hover:text-primary transition-colors cursor-pointer">
                <Calendar className="w-4 h-4" /><span>Trips</span>
              </span>
            </Link>
            <Link to="/feed">
              <span className="flex items-center space-x-1 text-sm font-medium text-foreground hover:text-primary transition-colors cursor-pointer">
                <Camera className="w-4 h-4" /><span>Photo feed</span>
              </span>
            </Link>
          </nav>

          {/* User Actions */}
          <div className="flex items-center space-x-4">
            <Link to="/trips" title="My trips" data-testid="button-itinerary-quick">
              <span className="text-foreground hover:text-primary transition-colors duration-200 hover:scale-110 relative inline-block">
                <Calendar className="w-5 h-5" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              </span>
            </Link>

            <Link to="/wishlist" title="Saved places" data-testid="button-favorites">
              <Heart className="w-5 h-5 text-foreground hover:text-primary transition-colors duration-200 hover:scale-110" />
            </Link>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="text-foreground hover:text-primary transition-colors flex items-center gap-1 text-xs font-medium uppercase"
                        title="Language" aria-label="Change language" translate="no">
                  <Languages className="w-5 h-5" />{language === "en" ? "" : language.split("-")[0]}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="max-h-80 overflow-y-auto" translate="no">
                {LANGUAGES.map((l) => (
                  <DropdownMenuItem key={l.code} onClick={() => setLanguage(l.code)} className={l.code === language ? "font-semibold" : ""}>
                    {l.flag} {l.native}{l.native !== l.name ? ` · ${l.name}` : ""}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <button
              onClick={toggleDarkMode}
              className="text-foreground hover:text-primary transition-colors duration-200 hover:scale-110"
              title={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>

            {isAuthenticated ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full" aria-label="Account menu">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user?.avatar || ""} alt={user?.name || ""} />
                      <AvatarFallback>
                        {user?.name?.charAt(0) || "U"}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <div className="flex flex-col space-y-1 p-2">
                    <p className="text-sm font-medium leading-none">{user?.name}</p>
                    <p className="text-xs leading-none text-muted-foreground">
                      {user?.email}
                    </p>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to={`/profile/${user?.id}`}>
                      <User className="mr-2 h-4 w-4" />
                      <span>Profile</span>
                    </Link>
                  </DropdownMenuItem>
                  {MENU.map((m) => (
                    <DropdownMenuItem key={m.to} asChild>
                      <Link to={m.to}>
                        <m.icon className="mr-2 h-4 w-4" />
                        <span>{m.label}</span>
                      </Link>
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={logout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Log out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button
                onClick={login}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
                data-testid="button-signin"
              >
                Sign In
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
