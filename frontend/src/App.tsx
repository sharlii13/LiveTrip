import { BrowserRouter, Routes, Route } from "react-router-dom";
import { useState, useEffect } from "react";
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
import Map from "@/pages/map";
import Feedback from "@/pages/feedback";
import Destination from "@/pages/destination";
import Profile from "@/pages/profile";
import Login from "@/pages/login";
import TripPlanning from "@/pages/trip-planning";
import { Navigate } from "react-router-dom";
import { recentTrips } from "@/lib/livetrip";
import About from "@/pages/about";
import HealthPanel from "@/components/HealthPanel";
import Navbar from "@/components/navbar";
import AssistantBuddy from "@/components/AssistantBuddy";
import IntroAnimation, { shouldPlayIntro } from "@/components/IntroAnimation";
import PermissionRequests from "@/components/PermissionRequests";
import DateSelection from "@/pages/trip-planning/DateSelection";
import CompanySelection from "@/pages/trip-planning/CompanySelection";
import FoodPreferences from "@/pages/trip-planning/FoodPreferences";
import EcoModeSelection from "@/pages/trip-planning/EcoModeSelection";
import EmergencyContact from "@/pages/trip-planning/EmergencyContact";
import LanguagePreference from "@/pages/trip-planning/LanguagePreference";
import TripSummary from "@/pages/trip-planning/TripSummary";
import MultiDayPlanner from "@/components/itinerary/MultiDayPlanner";
import Trips from "@/pages/trips";
import TripDetail from "@/pages/trip-detail";
import Feed from "@/pages/feed";
import Gallery from "@/pages/gallery";
import Rewards from "@/pages/rewards";
import { GroupsList, GroupDetailPage } from "@/pages/groups";
import Wishlist from "@/pages/wishlist";
import TravelHistory from "@/pages/history";
import Assistant from "@/pages/assistant";

/** The old /itinerary link opens the most recent live trip (or the trip list). */
function LatestItinerary() {
  const id = recentTrips()[0] || localStorage.getItem("currentItineraryId");
  return <Navigate to={id ? `/trips/${id}` : "/trips"} replace />;
}

function Router({ ready }: { ready: boolean }) {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/search" element={<Search />} />
        <Route path="/trip-planning" element={<TripPlanning />} />
        <Route path="/itinerary" element={<LatestItinerary />} />
        <Route path="/about" element={<About />} />
        <Route path="/map" element={<Map />} />
        <Route path="/feedback" element={<Feedback />} />
        <Route path="/health" element={<HealthPanel />} />
        <Route path="/destinations/:id" element={<Destination />} />
        <Route
          path="/profile/:userId"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route path="/trip-planning/dates" element={<DateSelection />} />
        <Route path="/trip-planning/company" element={<CompanySelection />} />
        <Route path="/trip-planning/food-preferences" element={<FoodPreferences />} />
        <Route path="/trip-planning/eco-mode" element={<EcoModeSelection />} />
        <Route path="/trip-planning/emergency-contact" element={<EmergencyContact />} />
        <Route path="/trip-planning/language-preference" element={<LanguagePreference />} />
        <Route path="/trip-planning/summary" element={<TripSummary />} />
        <Route path="/multi-day-planner" element={<MultiDayPlanner />} />
        <Route path="/trips" element={<Trips />} />
        <Route path="/trips/:id" element={<TripDetail />} />
        <Route path="/feed" element={<Feed />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/gallery" element={<ProtectedRoute><Gallery /></ProtectedRoute>} />
        <Route path="/rewards" element={<ProtectedRoute><Rewards /></ProtectedRoute>} />
        <Route path="/groups" element={<ProtectedRoute><GroupsList /></ProtectedRoute>} />
        <Route path="/groups/:id" element={<ProtectedRoute><GroupDetailPage /></ProtectedRoute>} />
        <Route path="/wishlist" element={<ProtectedRoute><Wishlist /></ProtectedRoute>} />
        <Route path="/history" element={<ProtectedRoute><TravelHistory /></ProtectedRoute>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
      {ready && <AssistantBuddy />}
    </div>
  );
}

function App() {
  const [showPermissions, setShowPermissions] = useState(false);
  const [intro, setIntro] = useState(shouldPlayIntro);

  useEffect(() => {
    // Ask once, after the intro; the answer is remembered (handlePermissionsComplete sets the flag)
    if (intro || localStorage.getItem('liveTrip-permissions-requested')) return;
    const timer = setTimeout(() => {
      setShowPermissions(true);
    }, 1000);
    return () => clearTimeout(timer);
  }, [intro]);

  const handlePermissionsComplete = () => {
    setShowPermissions(false);
    localStorage.setItem('liveTrip-permissions-requested', 'true');
  };

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <TripPlanningProvider>
            <TooltipProvider>
              <Toaster />
              <Router ready={!intro} />
              {intro && <IntroAnimation onDone={() => setIntro(false)} />}
              {showPermissions && (
                <PermissionRequests onComplete={handlePermissionsComplete} />
              )}
            </TooltipProvider>
          </TripPlanningProvider>
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
}

export default App;
