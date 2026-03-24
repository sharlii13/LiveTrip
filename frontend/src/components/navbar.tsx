import { Link, useLocation } from "react-router-dom";
import { Heart, User, LogOut, Sun, Moon, Bell, Calendar, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import LiveTripLogo from "@/components/LiveTripLogo";
import { useState, useEffect } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function Navbar() {
  const location = useLocation();
  const { user, isAuthenticated, login, logout } = useAuth();
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    
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

  return (
    <header className="bg-background border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" data-testid="link-home">
            <LiveTripLogo size="lg" className="cursor-pointer" />
          </Link>
          
              {/* Navigation Menu */}
              <nav className="hidden md:flex space-x-6">
                <Link to="/" data-testid="link-home-nav">
                  <span className={`font-medium transition-colors cursor-pointer ${
                    location.pathname === "/" ? "text-primary" : "text-foreground hover:text-primary"
                  }`}>
                    Home
                  </span>
                </Link>
                <Link to="/map" data-testid="link-map">
                  <span className={`font-medium transition-colors cursor-pointer ${
                    location.pathname === "/map" ? "text-primary" : "text-foreground hover:text-primary"
                  }`}>
                    Map
                  </span>
                </Link>
                <Link to="/itinerary" data-testid="link-itinerary">
                  <span className={`font-medium transition-colors cursor-pointer flex items-center space-x-2 ${
                    location.pathname === "/itinerary" ? "text-primary" : "text-foreground hover:text-primary"
                  }`}>
                    <Calendar className="w-4 h-4" />
                    <span>My Itinerary</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  </span>
                </Link>
                <Link to="/multi-day-planner" data-testid="link-multi-day">
                  <span className={`font-medium transition-colors cursor-pointer flex items-center space-x-2 ${
                    location.pathname === "/multi-day-planner" ? "text-primary" : "text-foreground hover:text-primary"
                  }`}>
                    <MapPin className="w-4 h-4" />
                    <span>Multi-Day Planner</span>
                  </span>
                </Link>
                <Link to="/feedback" data-testid="link-feedback">
                  <span className={`font-medium transition-colors cursor-pointer ${
                    location.pathname === "/feedback" ? "text-primary" : "text-foreground hover:text-primary"
                  }`}>
                    Feedback
                  </span>
                </Link>
              </nav>

              {/* Mobile Navigation */}
              <nav className="md:hidden flex space-x-4">
                <Link to="/itinerary">
                  <span className="flex items-center space-x-2 text-sm font-medium text-foreground hover:text-primary transition-colors cursor-pointer">
                    <Calendar className="w-4 h-4" />
                    <span>Itinerary</span>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  </span>
                </Link>
              </nav>
          
          {/* User Actions */}
          <div className="flex items-center space-x-4">
            <Link to="/itinerary">
              <button 
                className="text-foreground hover:text-primary transition-colors duration-200 hover:scale-110 relative" 
                data-testid="button-itinerary-quick"
                title="My Itinerary"
              >
                <Calendar className="w-5 h-5" />
                <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              </button>
            </Link>
            
            <button 
              className="text-foreground hover:text-primary transition-colors duration-200 hover:scale-110" 
              data-testid="button-favorites"
              title="Favorites"
            >
              <Heart className="w-5 h-5" />
            </button>
            
            <button 
              className="text-foreground hover:text-primary transition-colors duration-200 hover:scale-110" 
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
            </button>
            
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
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
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
                  <DropdownMenuItem asChild>
                    <Link to="/itinerary">
                      <Calendar className="mr-2 h-4 w-4" />
                      <span>My Itinerary</span>
                    </Link>
                  </DropdownMenuItem>
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
