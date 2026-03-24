import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import { TripPlanningProvider } from "@/contexts/TripPlanningContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";
import Search from "@/pages/search";
import Destination from "@/pages/destination";
import Profile from "@/pages/profile";
import Login from "@/pages/login";
import Navbar from "@/components/navbar";
import DateSelection from "@/pages/trip-planning/DateSelection";
import CompanySelection from "@/pages/trip-planning/CompanySelection";
import FoodPreferences from "@/pages/trip-planning/FoodPreferences";
import InterestsSelection from "@/pages/trip-planning/InterestsSelection";
import EcoModeSelection from "@/pages/trip-planning/EcoModeSelection";
import TripSummary from "@/pages/trip-planning/TripSummary";

function Router() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
          <Switch>
            <Route path="/" component={Home} />
            <Route path="/login" component={Login} />
            <Route path="/search" component={Search} />
            <Route path="/destinations/:id" component={Destination} />
            <Route path="/profile/:userId">
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            </Route>
            <Route path="/trip-planning/dates" component={DateSelection} />
            <Route path="/trip-planning/company" component={CompanySelection} />
            <Route path="/trip-planning/food-preferences" component={FoodPreferences} />
            <Route path="/trip-planning/interests" component={InterestsSelection} />
            <Route path="/trip-planning/eco-mode" component={EcoModeSelection} />
            <Route path="/trip-planning/summary" component={TripSummary} />
            <Route component={NotFound} />
          </Switch>
    </div>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TripPlanningProvider>
          <TooltipProvider>
            <Toaster />
            <Router />
          </TooltipProvider>
        </TripPlanningProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
