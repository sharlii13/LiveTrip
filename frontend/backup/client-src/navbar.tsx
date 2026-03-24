import { Link, useLocation } from "wouter";
import { Heart, User, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import LiveTripLogo from "@/components/LiveTripLogo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function Navbar() {
  const [location] = useLocation();
  const { user, isAuthenticated, login, logout } = useAuth();

  return (
    <header className="bg-background border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" data-testid="link-home">
            <LiveTripLogo size="md" className="cursor-pointer" />
          </Link>
          
          {/* Navigation Menu */}
          <nav className="hidden md:flex space-x-8">
            <Link href="/" data-testid="link-home-nav">
              <span className={`font-medium transition-colors cursor-pointer ${
                location === "/" ? "text-primary" : "text-foreground hover:text-primary"
              }`}>
                Home
              </span>
            </Link>
            <Link href="/search" data-testid="link-search">
              <span className={`font-medium transition-colors cursor-pointer ${
                location === "/search" ? "text-primary" : "text-foreground hover:text-primary"
              }`}>
                Destinations
              </span>
            </Link>
            <a href="#" className="text-foreground hover:text-primary font-medium transition-colors">
              Hotels
            </a>
            <a href="#" className="text-foreground hover:text-primary font-medium transition-colors">
              Restaurants
            </a>
            <a href="#" className="text-foreground hover:text-primary font-medium transition-colors">
              Experiences
            </a>
          </nav>
          
          {/* User Actions */}
          <div className="flex items-center space-x-4">
            <button className="text-foreground hover:text-primary" data-testid="button-favorites">
              <Heart className="w-5 h-5" />
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
                    <Link href={`/profile/${user?.id}`}>
                      <User className="mr-2 h-4 w-4" />
                      <span>Profile</span>
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
