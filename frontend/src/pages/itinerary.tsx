import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Calendar, 
  MapPin, 
  Clock, 
  Users, 
  Utensils, 
  Leaf, 
  Heart, 
  Star, 
  Camera, 
  Car, 
  Plane, 
  Train, 
  Bus, 
  Footprints, 
  Bike,
  Phone,
  Globe,
  ChevronLeft,
  ChevronRight,
  Download,
  Share2,
  Bookmark,
  CheckCircle,
  Info,
  Sun,
  Moon,
  Cloud,
  CloudRain,
  AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useTripPlanning } from "@/contexts/TripPlanningContext";
import LiveTripLogo from "@/components/LiveTripLogo";
import { apiService, webSocketService, Itinerary as BackendItinerary, MultiDayPlanResponse } from "@/services/apiService";
import { createCompleteItineraryFromCity, getApiBase } from "@/lib/api";
import { UpdateBanner } from "@/components/itinerary/UpdateBanner";
import { ItineraryCard, type ItineraryBadge } from "@/components/itinerary/ItineraryCard";
import { AnimatePresence } from "framer-motion";

// ---- Enhanced basic itinerary utilities ----
const START_TIME = 9 * 60;  // 9:00 AM
const END_TIME = 19 * 60;   // 7:00 PM

const defaultDurations: Record<string, number> = {
  tourist_attraction: 120,
  museum: 150,
  park: 90,
  temple: 60,
  shopping: 120,
  restaurant: 75,
};

function minutesToTime(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const ampm = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 === 0 ? 12 : hours % 12;
  return `${displayHours}:${minutes.toString().padStart(2, "0")} ${ampm}`;
}

function normalizeType(raw: string): string {
  const t = (raw || '').toLowerCase();
  if (t.includes('museum') || t.includes('historical')) return 'museum';
  if (t.includes('park') || t.includes('garden')) return 'park';
  if (t.includes('temple') || t.includes('religious')) return 'temple';
  if (t.includes('shop')) return 'shopping';
  if (t.includes('restaurant') || t.includes('food')) return 'restaurant';
  if (t.includes('view') || t.includes('scenic')) return 'tourist_attraction';
  return 'tourist_attraction';
}

function generateEnhancedItinerary(places: any[]) {
  let currentTime = START_TIME;
  const itinerary: any[] = [];

  for (const place of places) {
    const visitDuration = defaultDurations[place.type] ?? 90; // minutes
    const endTime = currentTime + visitDuration;

    if (endTime > END_TIME) break; // exceed day end

    itinerary.push({
      ...place,
      startTime: minutesToTime(currentTime),
      endTime: minutesToTime(endTime),
      duration: visitDuration,
    });

    currentTime = endTime + 15; // 15 min buffer
  }

  // Always add Dinner at the end
  const dinnerStart = Math.min(currentTime, END_TIME);
  itinerary.push({
    name: 'Dinner',
    type: 'restaurant',
    startTime: minutesToTime(dinnerStart),
    endTime: minutesToTime(END_TIME),
    duration: Math.max(END_TIME - dinnerStart, 60),
  });

  return itinerary;
}

function typeEmoji(t: string): string {
  switch (t) {
    case 'museum': return '🏛️';
    case 'park': return '🌳';
    case 'temple': return '⛩️';
    case 'shopping': return '🛍️';
    case 'restaurant': return '🍽️';
    default: return '📍';
  }
}

function getActivityEmoji(category: string): string {
  switch (category.toLowerCase()) {
    case 'temple': return '🛕';
    case 'shopping': return '🛍️';
    case 'food': return '🍽️';
    case 'museum': return '🏛️';
    case 'tourist_attraction': return '🏛️';
    case 'park': return '🌳';
    case 'restaurant': return '🍽️';
    default: return '📍';
  }
}
// ---- end utilities ----

export default function Itinerary() {
  const { tripData } = useTripPlanning();
  const navigate = useNavigate();
  const [currentDay, setCurrentDay] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [apiResult, setApiResult] = useState<any | null>(null);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const itineraryId = (typeof window !== 'undefined') ? (localStorage.getItem('currentItineraryId') || null) : null;

  const enhancedItinerary = useMemo(() => {
    try {
      const route = Array.isArray(apiResult?.optimized_route) ? apiResult!.optimized_route : [];
      const mapped = route.map((p: any) => ({ name: p.name, type: normalizeType(p.category || 'tourist_attraction') }));
      return generateEnhancedItinerary(mapped);
    } catch { return []; }
  }, [apiResult]);
  const [daywise, setDaywise] = useState<{ date: string; items: any[] }[]>([]);
  const [debugInfo, setDebugInfo] = useState<string>("");
  const [lastError, setLastError] = useState<string | null>(null);

  // Generate itinerary data based on trip details
  const [itinerary, setItinerary] = useState<any[]>([]);
  const [backendItinerary, setBackendItinerary] = useState<BackendItinerary | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [currentWeather, setCurrentWeather] = useState<any>(null);
  const [multiDayData, setMultiDayData] = useState<MultiDayPlanResponse | null>(null);
  const [isMultiDayTrip, setIsMultiDayTrip] = useState<boolean>(false);

  // Minimal requirement for backend creation is a destination
  const hasDestination = () => {
    return !!tripData.destination && tripData.destination.trim().length > 0;
  };

  useEffect(() => {
    // Check if this is a multi-day trip
    const isMultiDay = localStorage.getItem('isMultiDayTrip') === 'true';
    const storedMultiDayData = localStorage.getItem('multiDayItinerary');
    
    console.log('🔍 Multi-day check:', { isMultiDay, hasStoredData: !!storedMultiDayData });
    
    setIsMultiDayTrip(isMultiDay);
    
    if (isMultiDay && storedMultiDayData) {
      // Load multi-day data from localStorage
      try {
        const parsedData = JSON.parse(storedMultiDayData) as MultiDayPlanResponse;
        console.log('📅 Loaded multi-day data:', parsedData);
        setMultiDayData(parsedData);
        
        // Convert multi-day data to existing itinerary format for display
        const convertedItinerary = convertMultiDayToLocal(parsedData);
        console.log('🔄 Converted itinerary:', convertedItinerary);
        setItinerary(convertedItinerary);
        setIsLoading(false);
        return;
      } catch (error) {
        console.error('Failed to parse multi-day data:', error);
        // Fall through to normal loading
      }
    }
    
    // Require at least a destination to proceed; otherwise stop
    if (!hasDestination()) {
      setIsLoading(false);
      return;
    }

    // Always create a fresh itinerary via backend for the current destination (no GET-by-id path)
    const loadItinerary = async () => {
      try {
        const city = (tripData.destination || '').trim() || 'Mumbai';
        const created = await createCompleteItineraryFromCity(city, 1, { startDate: tripData.startDate || undefined, endDate: tripData.endDate || undefined, startTime: '09:00:00' });
        const newId = created.itinerary_id?.toString?.() || created.itinerary_id || "";
        if (newId) {
          localStorage.setItem('currentItineraryId', newId);
          localStorage.setItem('currentItineraryCity', city);
        }
        setApiResult(created);
        setLastUpdated(new Date());
        try {
          const converted = convertCreatedResponseToLocal(created);
          setItinerary(converted);
        } catch {}
        setIsLoading(false);
      } catch (creationError) {
        console.error('Backend creation failed:', creationError);
        setIsLoading(false);
      }
    };

    // Simulate loading and generate itinerary
    const generateLocalItinerary = () => {
      // Use trip data if available, otherwise use mock data for demo
      const destination = tripData.destination || 'Paris';
      const startDate = tripData.startDate ? new Date(tripData.startDate) : new Date();
      const endDate = tripData.endDate ? new Date(tripData.endDate) : new Date(Date.now() + 3 * 24 * 60 * 60 * 1000); // 3 days from now
      
      const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      
      const generatedItinerary = [];
      
      for (let i = 0; i < days; i++) {
        const currentDate = new Date(startDate);
        currentDate.setDate(startDate.getDate() + i);
        
        generatedItinerary.push({
          day: i + 1,
          date: currentDate,
          weather: getRandomWeather(),
          activities: generateDayActivities(i + 1, days),
          meals: generateMeals(),
          accommodation: generateAccommodation(),
          transportation: generateTransportation(),
          highlights: generateHighlights(i + 1, days),
          tips: generateTips()
        });
      }
      
      setItinerary(generatedItinerary);
      setIsLoading(false);
    };

    loadItinerary();

    // Optionally connect WebSocket for real-time updates if we have an itinerary id
    if (itineraryId) {
      try {
        webSocketService.connect(itineraryId);

        const onAnyMessage = (data: any) => {
          // Show human-readable banner and refresh itinerary when backend updates arrive
          const t = (data?.type || '').toString();
          if (t) {
            const readable =
              t.includes('rain') || t.includes('weather') ? '🔄 Replanned due to weather changes'
              : t.includes('traffic') ? '🔄 Replanned due to traffic delays'
              : t.includes('replan') || t.includes('update') || t.includes('optimized') ? '🔄 Itinerary updated'
              : '🔔 Update received';
            setBannerMessage(data?.message || readable);
          }
          // Try refetching itinerary by id if backend supports it
          (async () => {
            try {
              const fresh = await apiService.getItinerary(itineraryId);
              setApiResult(fresh);
              setLastUpdated(new Date());
            } catch {
              // If GET by id not supported, skip silently
            }
          })();
        };

        webSocketService.on('message', onAnyMessage);
        webSocketService.on('itinerary_updated', onAnyMessage as any);
        webSocketService.on('replan', onAnyMessage as any);

        return () => {
          webSocketService.off('message', onAnyMessage);
          webSocketService.off('itinerary_updated', onAnyMessage as any);
          webSocketService.off('replan', onAnyMessage as any);
          webSocketService.disconnect();
        };
      } catch {
        // ignore socket errors for now
      }
    }

    // Cleanup fallback when no socket
    return () => {
      // no-op: websockets disabled in simplified flow
    };
  }, [tripData]);

  // Group API result into day-wise buckets
  function groupByDayFromApiResult(result: any): { date: string; items: any[] }[] {
    if (!result) return [];
    const daily: { [date: string]: any[] } = {};
    const route = Array.isArray(result?.optimized_route) ? result.optimized_route : [];
    for (const item of route) {
      // Use the correct field names from the API response
      const ts = item?.scheduled_arrival_time || item?.scheduled_departure_time || 
                item?.arrival_time_formatted || item?.departure_time_formatted || '';
      if (!ts) {
        // If no timestamp, use today's date as fallback
        const date = new Date().toISOString().slice(0, 10);
        if (!daily[date]) daily[date] = [];
        daily[date].push(item);
        continue;
      }
      // Handle both full ISO timestamps and time-only formats
      let date: string;
      if (ts.includes('-')) {
        // Full date like "2025-10-05" or "2025-10-05T09:03:00"
        date = ts.slice(0, 10);
      } else {
        // Time-only format like "09:03", use today's date
        date = new Date().toISOString().slice(0, 10);
      }
      if (!daily[date]) daily[date] = [];
      daily[date].push(item);
    }
    // If backend provided daily_schedule keys, ensure we respect that order
    const keys = result?.daily_schedule ? Object.keys(result.daily_schedule) : Object.keys(daily);
    const sorted = keys.sort();
    return sorted.map(date => ({ date, items: (daily[date] || []).slice() }));
  }

  // Convert creation response to local itinerary shape (minimal)
  function convertCreatedResponseToLocal(created: any) {
    const days = groupByDayFromApiResult(created);
    return days.map((d, idx) => ({
      day: idx + 1,
      date: new Date(d.date),
      activities: d.items.map((it: any) => ({
        time: it.arrival_time_formatted || (it.scheduled_arrival_time ? new Date(it.scheduled_arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''),
        title: it.name,
        description: it.optimal_visit_info?.tips?.[0] || '',
        icon: Camera,
        duration: `${(it.stay_duration_hours || it.stay_duration || 2)}h`,
        type: it.category || 'sightseeing',
        location: it.address || '',
        cost: '',
        difficulty: 'Easy'
      }))
    }));
  }

  function hhmm(d: Date) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  const getRandomWeather = () => {
    const weathers = [
      { type: 'sunny', icon: Sun, temp: '28°C', description: 'Sunny' },
      { type: 'cloudy', icon: Cloud, temp: '24°C', description: 'Partly Cloudy' },
      { type: 'rainy', icon: CloudRain, temp: '22°C', description: 'Light Rain' },
      { type: 'clear', icon: Moon, temp: '26°C', description: 'Clear Skies' }
    ];
    return weathers[Math.floor(Math.random() * weathers.length)];
  };

  const generateDayActivities = (day: number, totalDays: number) => {
    const destination = tripData.destination || 'Paris';
    const companyType = tripData.companyType || 'solo';
    const interests = tripData.interests || ['sightseeing'];
    
    // Generate more detailed and personalized activities based on destination and interests
    const activityTemplates = {
      'Paris': [
        { time: '08:30', title: 'Eiffel Tower Sunrise', description: 'Start your day with breathtaking views from the iconic Eiffel Tower. Beat the crowds and capture stunning photos as the city awakens.', icon: Camera, duration: '1.5h', type: 'sightseeing', location: 'Champ de Mars, 7th arrondissement', cost: '€29', difficulty: 'Easy' },
        { time: '10:30', title: 'Louvre Museum Tour', description: 'Explore the world\'s largest art museum, home to the Mona Lisa and thousands of masterpieces. Audio guide included.', icon: Camera, duration: '2.5h', type: 'culture', location: 'Rue de Rivoli, 1st arrondissement', cost: '€17', difficulty: 'Moderate' },
        { time: '13:30', title: 'Seine River Cruise', description: 'Enjoy a leisurely lunch cruise along the Seine with panoramic views of Notre-Dame, Musée d\'Orsay, and more.', icon: Utensils, duration: '2h', type: 'food', location: 'Port de la Bourdonnais', cost: '€45', difficulty: 'Easy' },
        { time: '16:00', title: 'Montmartre Walking Tour', description: 'Discover the bohemian charm of Montmartre, visit Sacré-Cœur, and explore local artists\' studios.', icon: Footprints, duration: '2h', type: 'culture', location: 'Montmartre, 18th arrondissement', cost: 'Free', difficulty: 'Moderate' },
        { time: '18:30', title: 'Champs-Élysées Shopping', description: 'Stroll down the world\'s most beautiful avenue, shop at luxury boutiques, and enjoy café culture.', icon: Star, duration: '1.5h', type: 'leisure', location: 'Champs-Élysées, 8th arrondissement', cost: 'Variable', difficulty: 'Easy' },
        { time: '20:30', title: 'Traditional French Dinner', description: 'Savor authentic French cuisine at a charming bistro with wine pairing and local specialties.', icon: Utensils, duration: '2h', type: 'food', location: 'Le Marais district', cost: '€60-80', difficulty: 'Easy' }
      ],
      'Tokyo': [
        { time: '07:00', title: 'Tsukiji Fish Market', description: 'Experience the world\'s largest fish market, watch the famous tuna auction, and enjoy fresh sushi breakfast.', icon: Utensils, duration: '2h', type: 'food', location: 'Tsukiji, Chuo City', cost: '¥3000-5000', difficulty: 'Easy' },
        { time: '09:30', title: 'Senso-ji Temple', description: 'Visit Tokyo\'s oldest temple, participate in traditional rituals, and explore the bustling Nakamise shopping street.', icon: Camera, duration: '1.5h', type: 'culture', location: 'Asakusa, Taito City', cost: 'Free', difficulty: 'Easy' },
        { time: '11:30', title: 'Tokyo Skytree', description: 'Ascend to the top of Japan\'s tallest structure for panoramic city views and interactive exhibits.', icon: Camera, duration: '1.5h', type: 'sightseeing', location: 'Sumida City', cost: '¥2100', difficulty: 'Easy' },
        { time: '14:00', title: 'Harajuku & Shibuya', description: 'Explore youth culture in Harajuku, visit the famous Shibuya crossing, and shop for unique souvenirs.', icon: Star, duration: '2.5h', type: 'leisure', location: 'Shibuya & Harajuku', cost: 'Variable', difficulty: 'Easy' },
        { time: '17:00', title: 'Traditional Tea Ceremony', description: 'Learn the art of Japanese tea ceremony in a traditional setting with a certified instructor.', icon: Utensils, duration: '1h', type: 'culture', location: 'Urasenke Foundation', cost: '¥3000', difficulty: 'Moderate' },
        { time: '19:00', title: 'Ramen Tasting Tour', description: 'Sample different styles of ramen at local shops, from tonkotsu to miso, with expert guidance.', icon: Utensils, duration: '2h', type: 'food', location: 'Various locations', cost: '¥2000-4000', difficulty: 'Easy' }
      ],
      'New York': [
        { time: '08:00', title: 'Central Park Morning Run', description: 'Start your day with a refreshing jog through Central Park, passing iconic landmarks and beautiful scenery.', icon: Footprints, duration: '1h', type: 'leisure', location: 'Central Park, Manhattan', cost: 'Free', difficulty: 'Moderate' },
        { time: '09:30', title: 'Statue of Liberty & Ellis Island', description: 'Take a ferry to Liberty Island, explore the museum, and learn about American immigration history.', icon: Camera, duration: '3h', type: 'sightseeing', location: 'Battery Park, Manhattan', cost: '$24', difficulty: 'Easy' },
        { time: '13:00', title: 'Broadway Show Matinee', description: 'Experience world-class theater with a matinee performance of a Tony Award-winning musical.', icon: Star, duration: '2.5h', type: 'culture', location: 'Times Square Theater District', cost: '$80-150', difficulty: 'Easy' },
        { time: '16:30', title: 'High Line Park Walk', description: 'Stroll along the elevated park built on a historic freight rail line with stunning city views.', icon: Footprints, duration: '1h', type: 'leisure', location: 'Chelsea, Manhattan', cost: 'Free', difficulty: 'Easy' },
        { time: '18:00', title: 'Brooklyn Bridge Sunset', description: 'Walk across the iconic Brooklyn Bridge during golden hour for spectacular skyline views.', icon: Camera, duration: '1h', type: 'sightseeing', location: 'Brooklyn Bridge', cost: 'Free', difficulty: 'Easy' },
        { time: '19:30', title: 'NYC Food Tour', description: 'Sample diverse cuisines from different neighborhoods, from pizza to bagels to international fare.', icon: Utensils, duration: '2.5h', type: 'food', location: 'Various neighborhoods', cost: '$75', difficulty: 'Easy' }
      ]
    };

    // Get activities for the destination or use a default set
    const activities = activityTemplates[destination as keyof typeof activityTemplates] || activityTemplates['Paris'];
    
    // Select 4-6 activities based on day and interests
    const selectedActivities = activities.slice(0, Math.min(6, 4 + Math.floor(Math.random() * 2)));
    
    // Personalize activities based on user interests
    return selectedActivities.map(activity => ({
      ...activity,
      title: activity.title,
      description: activity.description,
      personalized: interests.includes(activity.type) ? '⭐ Recommended for you' : ''
    }));
  };

  const generateMeals = () => {
    const destination = tripData.destination || 'Paris';
    const foodPreference = tripData.foodPreference || 'both';
    
    const mealTemplates = {
      'Paris': {
        vegetarian: [
          { time: '08:30', type: 'Breakfast', name: 'Croissant & Café au Lait', description: 'Fresh buttery croissants with locally roasted coffee', location: 'Café de Flore, Saint-Germain', rating: 4.6, cost: '€8-12', specialty: 'Traditional French breakfast' },
          { time: '13:00', type: 'Lunch', name: 'Ratatouille Provençale', description: 'Classic vegetable stew with herbs de Provence', location: 'Le Comptoir du Relais, 5th arr.', rating: 4.8, cost: '€18-25', specialty: 'Authentic Provençal cuisine' },
          { time: '20:00', type: 'Dinner', name: 'Vegetarian Tasting Menu', description: '7-course plant-based menu with wine pairing', location: 'L\'Arpège, 7th arr.', rating: 4.9, cost: '€120-180', specialty: 'Michelin-starred vegetarian' }
        ],
        'non-vegetarian': [
          { time: '08:30', type: 'Breakfast', name: 'Full French Breakfast', description: 'Croissants, pain au chocolat, fresh fruit, and café au lait', location: 'Café de Flore, Saint-Germain', rating: 4.6, cost: '€12-18', specialty: 'Classic French breakfast' },
          { time: '13:00', type: 'Lunch', name: 'Coq au Vin', description: 'Traditional chicken braised in red wine with mushrooms', location: 'Le Comptoir du Relais, 5th arr.', rating: 4.8, cost: '€22-30', specialty: 'Signature French dish' },
          { time: '20:00', type: 'Dinner', name: 'Duck Confit & Foie Gras', description: 'Confit duck leg with pan-seared foie gras', location: 'L\'Arpège, 7th arr.', rating: 4.9, cost: '€150-220', specialty: 'Haute cuisine experience' }
        ],
        both: [
          { time: '08:30', type: 'Breakfast', name: 'Continental Breakfast', description: 'Mixed selection of pastries, fruits, and beverages', location: 'Café de Flore, Saint-Germain', rating: 4.6, cost: '€10-15', specialty: 'Flexible dining options' },
          { time: '13:00', type: 'Lunch', name: 'Market Fresh Lunch', description: 'Seasonal ingredients from local markets', location: 'Le Comptoir du Relais, 5th arr.', rating: 4.8, cost: '€20-28', specialty: 'Farm-to-table dining' },
          { time: '20:00', type: 'Dinner', name: 'Chef\'s Choice Menu', description: 'Chef\'s selection of the day with wine recommendations', location: 'L\'Arpège, 7th arr.', rating: 4.9, cost: '€130-200', specialty: 'Personalized dining experience' }
        ]
      },
      'Tokyo': {
        vegetarian: [
          { time: '08:00', type: 'Breakfast', name: 'Traditional Japanese Breakfast', description: 'Miso soup, rice, pickled vegetables, and green tea', location: 'Tsukiji Outer Market', rating: 4.7, cost: '¥800-1200', specialty: 'Authentic Japanese morning meal' },
          { time: '12:30', type: 'Lunch', name: 'Vegetarian Ramen', description: 'Rich vegetable broth with handmade noodles', location: 'Afuri Ramen, Harajuku', rating: 4.8, cost: '¥1200-1800', specialty: 'Plant-based ramen' },
          { time: '19:00', type: 'Dinner', name: 'Kaiseki Vegetarian', description: 'Multi-course traditional Japanese vegetarian cuisine', location: 'Kikunoi, Kyoto', rating: 4.9, cost: '¥8000-12000', specialty: 'Refined vegetarian kaiseki' }
        ],
        'non-vegetarian': [
          { time: '08:00', type: 'Breakfast', name: 'Sushi Breakfast', description: 'Fresh nigiri and sashimi with miso soup', location: 'Tsukiji Outer Market', rating: 4.7, cost: '¥1500-2500', specialty: 'World\'s freshest sushi' },
          { time: '12:30', type: 'Lunch', name: 'Tonkotsu Ramen', description: 'Rich pork bone broth with chashu and soft-boiled egg', location: 'Ichiran Ramen, Shibuya', rating: 4.8, cost: '¥1200-1800', specialty: 'Famous tonkotsu ramen' },
          { time: '19:00', type: 'Dinner', name: 'Wagyu Beef Kaiseki', description: 'Premium A5 wagyu in traditional multi-course meal', location: 'Kikunoi, Kyoto', rating: 4.9, cost: '¥15000-25000', specialty: 'Ultimate Japanese dining' }
        ],
        both: [
          { time: '08:00', type: 'Breakfast', name: 'Mixed Japanese Breakfast', description: 'Combination of traditional and modern Japanese dishes', location: 'Tsukiji Outer Market', rating: 4.7, cost: '¥1000-1800', specialty: 'Diverse Japanese flavors' },
          { time: '12:30', type: 'Lunch', name: 'Bento Box Lunch', description: 'Assorted Japanese dishes in traditional bento format', location: 'Various locations', rating: 4.8, cost: '¥1000-1500', specialty: 'Portable Japanese meal' },
          { time: '19:00', type: 'Dinner', name: 'Omakase Experience', description: 'Chef\'s choice menu with seasonal ingredients', location: 'Sushi Saito, Roppongi', rating: 4.9, cost: '¥10000-20000', specialty: 'Ultimate sushi experience' }
        ]
      },
      'New York': {
        vegetarian: [
          { time: '08:00', type: 'Breakfast', name: 'Avocado Toast & Smoothie', description: 'Artisanal sourdough with smashed avocado and fresh smoothie', location: 'Two Hands, Nolita', rating: 4.5, cost: '$12-18', specialty: 'Trendy NYC breakfast' },
          { time: '13:00', type: 'Lunch', name: 'Plant-based Burger', description: 'Impossible burger with sweet potato fries', location: 'By Chloe, Greenwich Village', rating: 4.6, cost: '$15-22', specialty: 'Popular vegan chain' },
          { time: '19:30', type: 'Dinner', name: 'Vegetarian Tasting Menu', description: 'Innovative plant-based cuisine with wine pairing', location: 'Dirt Candy, Lower East Side', rating: 4.8, cost: '$85-120', specialty: 'Award-winning vegetarian' }
        ],
        'non-vegetarian': [
          { time: '08:00', type: 'Breakfast', name: 'NYC Bagel & Lox', description: 'Fresh bagel with smoked salmon, cream cheese, and capers', location: 'Russ & Daughters, Lower East Side', rating: 4.7, cost: '$15-25', specialty: 'Classic NYC breakfast' },
          { time: '13:00', type: 'Lunch', name: 'Pastrami Sandwich', description: 'Katz\'s famous pastrami on rye with pickles', location: 'Katz\'s Delicatessen, Lower East Side', rating: 4.8, cost: '$18-28', specialty: 'NYC institution' },
          { time: '19:30', type: 'Dinner', name: 'Steakhouse Experience', description: 'Dry-aged steak with classic sides and cocktails', location: 'Peter Luger, Brooklyn', rating: 4.9, cost: '$120-200', specialty: 'Legendary NYC steakhouse' }
        ],
        both: [
          { time: '08:00', type: 'Breakfast', name: 'NYC Brunch', description: 'Mixed selection of NYC brunch classics', location: 'Sarabeth\'s, Upper West Side', rating: 4.6, cost: '$18-30', specialty: 'Quintessential NYC brunch' },
          { time: '13:00', type: 'Lunch', name: 'Food Truck Tour', description: 'Sample diverse cuisines from NYC food trucks', location: 'Various locations', rating: 4.7, cost: '$10-20', specialty: 'NYC street food culture' },
          { time: '19:30', type: 'Dinner', name: 'Multi-cuisine Dinner', description: 'Chef\'s choice from various NYC culinary traditions', location: 'Le Bernardin, Midtown', rating: 4.9, cost: '$150-300', specialty: 'World-class dining' }
        ]
      }
    };

    const destinationMeals = mealTemplates[destination as keyof typeof mealTemplates] || {
      vegetarian: [
        { time: '08:30', type: 'Breakfast', name: 'Healthy Breakfast', description: 'Fresh fruits, oats, and coffee/tea', location: 'Nearby cafe', rating: 4.0, cost: '₹150-300', specialty: 'Light & energetic' },
        { time: '13:00', type: 'Lunch', name: 'Vegetarian Thali', description: 'Balanced local vegetarian meal', location: 'Local restaurant', rating: 4.2, cost: '₹250-400', specialty: 'Regional flavors' },
        { time: '20:00', type: 'Dinner', name: 'Veg Platter', description: 'Assorted vegetarian dishes', location: 'Popular dining spot', rating: 4.3, cost: '₹300-600', specialty: 'Comfort food' }
      ],
      'non-vegetarian': [
        { time: '08:30', type: 'Breakfast', name: 'Classic Breakfast', description: 'Eggs, toast, and coffee/tea', location: 'Nearby cafe', rating: 4.0, cost: '₹150-300', specialty: 'Filling start' },
        { time: '13:00', type: 'Lunch', name: 'Chicken Thali', description: 'Balanced local non-veg meal', location: 'Local restaurant', rating: 4.2, cost: '₹300-500', specialty: 'Regional flavors' },
        { time: '20:00', type: 'Dinner', name: 'Grilled Platter', description: 'Assorted grilled dishes', location: 'Popular dining spot', rating: 4.3, cost: '₹400-800', specialty: 'Hearty dinner' }
      ],
      both: [
        { time: '08:30', type: 'Breakfast', name: 'Continental Breakfast', description: 'Pastries, fruits, and beverages', location: 'Nearby cafe', rating: 4.0, cost: '₹150-300', specialty: 'Quick & easy' },
        { time: '13:00', type: 'Lunch', name: 'Local Lunch Combo', description: 'Popular local dishes', location: 'Local restaurant', rating: 4.2, cost: '₹250-450', specialty: 'Local taste' },
        { time: '20:00', type: 'Dinner', name: 'Chef’s Choice', description: 'Daily selection by the chef', location: 'Popular dining spot', rating: 4.3, cost: '₹400-800', specialty: 'Balanced meal' }
      ]
    } as any;
    return destinationMeals[foodPreference as keyof typeof destinationMeals] || destinationMeals.both;
  };

  // Compute display days for rendering the schedule cards
  const displayDays = useMemo(() => {
    console.log('🔄 Computing displayDays:', { multiDayData, itinerary: itinerary.length });
    
    // helper curation: 3-4 activities + 1 restaurant for a perfect one-day plan
    const curateOneDay = (items: any[]) => {
      const attractions = items.filter((it) => it.categoryTag !== 'restaurant');
      const restaurants = items.filter((it) => it.categoryTag === 'restaurant');
      const curated: any[] = [];
      curated.push(...attractions.slice(0, 3)); // 3 interesting activities
      if (restaurants.length > 0) {
        curated.push(restaurants[0]); // add one restaurant suggestion
      } else {
        // fallback dinner suggestion if none present
        curated.push({
          key: 'dinner-fallback',
          startTime: '6:00 PM',
          endTime: '7:00 PM',
          name: 'Dinner',
          categoryTag: 'restaurant',
          durationText: '~60 min activity + buffer',
          badges: [] as ItineraryBadge[],
        });
      }
      return curated;
    };

    // Handle multi-day data first
    if (multiDayData && multiDayData.days.length > 0) {
      return multiDayData.days.map((day, dayIndex) => {
        const mapped = day.items.map((item, itemIndex) => ({
          key: `${day.date}-${item.name}-${itemIndex}`,
          startTime: item.arrive_at,
          endTime: item.depart_at,
          name: item.name,
          categoryTag: normalizeType(item.category),
          durationText: `~${item.duration_min} min activity + buffer`,
          badges: [] as ItineraryBadge[],
        }));
        return { date: day.date, items: mapped };
      });
    }

    if (apiResult) {
      const days = groupByDayFromApiResult(apiResult);
      if (days.length > 0) {
        const first = days[0];
        const mapped = (first.items || []).map((it: any, idx: number) => ({
          key: `${first.date}-${it.place_id || it.name || idx}`,
          startTime: it.arrival_time_formatted || (it.scheduled_arrival_time ? new Date(it.scheduled_arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''),
          endTime: it.departure_time_formatted || (it.scheduled_departure_time ? new Date(it.scheduled_departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''),
          name: it.name || 'Place',
          categoryTag: normalizeType(it.category || 'tourist_attraction'),
          durationText: `~${Math.round((it.stay_duration_hours || it.stay_duration || 2) * 60)} min activity + buffer`,
          badges: [] as ItineraryBadge[],
        }));
        return [{ date: first.date, items: curateOneDay(mapped) }];
      }
    }
    // fallback single day from enhancedItinerary
    return [{
      date: new Date().toISOString().slice(0,10),
      items: curateOneDay(
        enhancedItinerary.map((it: any, idx: number) => ({
          key: `fallback-${idx}`,
          startTime: it.startTime,
          endTime: it.endTime,
          name: it.name,
          categoryTag: it.type,
          durationText: `~${it.duration} min activity + buffer`,
          badges: [] as ItineraryBadge[],
        }))
      ),
    }];
  }, [multiDayData, apiResult, enhancedItinerary]);

  // Debug displayDays result
  console.log('📊 Final displayDays:', displayDays.length, displayDays);

  const generateAccommodation = () => {
    const destination = tripData.destination || 'Paris';
    const ecoFriendly = tripData.ecoMode ? 'Eco-friendly ' : '';
    
    const accommodationTemplates = {
      'Paris': {
        name: `${ecoFriendly}Hotel Plaza Athénée`,
        location: '25 Avenue Montaigne, 8th arrondissement',
        rating: 4.8,
        description: 'Luxurious palace hotel with stunning Eiffel Tower views and world-class service',
        amenities: ['WiFi', 'Spa', 'Restaurant', 'Concierge', 'Room Service', 'Fitness Center', 'Business Center'],
        ecoFeatures: tripData.ecoMode ? ['Solar Power', 'Recycling Program', 'Organic Toiletries', 'Energy-efficient Lighting', 'Local Sourcing'] : [],
        roomType: 'Deluxe Room with Eiffel Tower View',
        priceRange: '€800-1200/night',
        highlights: ['Michelin-starred restaurant', 'Historic architecture', 'Prime location near Champs-Élysées']
      },
      'Tokyo': {
        name: `${ecoFriendly}The Ritz-Carlton Tokyo`,
        location: '9-7-1 Akasaka, Minato City',
        rating: 4.9,
        description: 'Ultra-modern luxury hotel with panoramic city views and exceptional Japanese hospitality',
        amenities: ['WiFi', 'Spa', 'Multiple Restaurants', 'Concierge', 'Room Service', 'Fitness Center', 'Business Center', 'Rooftop Bar'],
        ecoFeatures: tripData.ecoMode ? ['Solar Power', 'Recycling Program', 'Organic Toiletries', 'Energy-efficient Lighting', 'Local Sourcing', 'Green Roof'] : [],
        roomType: 'Executive Suite with City View',
        priceRange: '¥80,000-120,000/night',
        highlights: ['Michelin-starred restaurants', 'Stunning city views', 'Traditional Japanese elements']
      },
      'New York': {
        name: `${ecoFriendly}The Plaza Hotel`,
        location: '768 5th Avenue, Manhattan',
        rating: 4.7,
        description: 'Iconic luxury hotel with Central Park views and legendary New York hospitality',
        amenities: ['WiFi', 'Spa', 'Multiple Restaurants', 'Concierge', 'Room Service', 'Fitness Center', 'Business Center', 'Shopping Arcade'],
        ecoFeatures: tripData.ecoMode ? ['Solar Power', 'Recycling Program', 'Organic Toiletries', 'Energy-efficient Lighting', 'Local Sourcing', 'Green Certification'] : [],
        roomType: 'Central Park Suite',
        priceRange: '$800-1500/night',
        highlights: ['Central Park views', 'Historic landmark', 'World-famous afternoon tea']
      }
    };

    const destinationAccommodation = accommodationTemplates[destination as keyof typeof accommodationTemplates] || accommodationTemplates['Paris'];
    return destinationAccommodation;
  };

  const generateTransportation = () => {
    const destination = tripData.destination || 'Paris';
    
    const transportTemplates = {
      'Paris': [
        { type: 'walking', icon: Footprints, name: 'Walking Tour', description: 'Explore the city on foot with guided walking tours', ecoScore: 10, cost: 'Free-€25', duration: '2-4 hours', highlights: ['Hidden gems', 'Local insights', 'Photo opportunities'] },
        { type: 'bicycle', icon: Bike, name: 'Vélib Bike Rental', description: 'Paris bike-sharing system with 1,400+ stations', ecoScore: 9, cost: '€1.70/day', duration: 'Flexible', highlights: ['City-wide access', 'Bike lanes', 'Scenic routes'] },
        { type: 'metro', icon: Train, name: 'Paris Metro', description: 'Extensive underground network covering all major attractions', ecoScore: 8, cost: '€1.90/ticket', duration: '5-30 min', highlights: ['Fast transport', 'Historic stations', 'Comprehensive coverage'] },
        { type: 'boat', icon: Bus, name: 'Seine River Cruise', description: 'Eco-friendly electric boats for sightseeing', ecoScore: 9, cost: '€15-25', duration: '1-2 hours', highlights: ['Unique perspective', 'Commentary', 'Photo opportunities'] }
      ],
      'Tokyo': [
        { type: 'walking', icon: Footprints, name: 'Walking Tour', description: 'Guided walking tours through Tokyo\'s diverse neighborhoods', ecoScore: 10, cost: 'Free-¥3000', duration: '2-4 hours', highlights: ['Cultural insights', 'Hidden spots', 'Local food'] },
        { type: 'bicycle', icon: Bike, name: 'Tokyo Bike Rental', description: 'City bike rental with designated cycling routes', ecoScore: 9, cost: '¥500-1000/day', duration: 'Flexible', highlights: ['Scenic routes', 'Parks', 'Temples'] },
        { type: 'train', icon: Train, name: 'JR Pass & Metro', description: 'Efficient train system connecting all major areas', ecoScore: 8, cost: '¥160-320/ticket', duration: '5-45 min', highlights: ['Punctual service', 'Clean trains', 'English signage'] },
        { type: 'bus', icon: Bus, name: 'Tokyo Bus Tour', description: 'Hop-on-hop-off bus with eco-friendly vehicles', ecoScore: 7, cost: '¥2000-3000', duration: '1-2 hours', highlights: ['Major attractions', 'Audio guide', 'Flexible schedule'] }
      ],
      'New York': [
        { type: 'walking', icon: Footprints, name: 'Walking Tour', description: 'Explore NYC neighborhoods with expert local guides', ecoScore: 10, cost: 'Free-$30', duration: '2-4 hours', highlights: ['Local stories', 'Hidden gems', 'Photo spots'] },
        { type: 'bicycle', icon: Bike, name: 'Citi Bike Rental', description: 'NYC bike-sharing with 1,000+ stations', ecoScore: 9, cost: '$3.50/day', duration: 'Flexible', highlights: ['City-wide access', 'Bike lanes', 'Scenic routes'] },
        { type: 'subway', icon: Train, name: 'NYC Subway', description: 'Extensive subway system covering all boroughs', ecoScore: 8, cost: '$2.75/ticket', duration: '5-45 min', highlights: ['24/7 service', 'Comprehensive coverage', 'Iconic stations'] },
        { type: 'ferry', icon: Bus, name: 'Staten Island Ferry', description: 'Free ferry with stunning skyline views', ecoScore: 9, cost: 'Free', duration: '25 min', highlights: ['Free transport', 'Skyline views', 'Statue of Liberty'] }
      ]
    };

    const destinationTransport = transportTemplates[destination as keyof typeof transportTemplates] || transportTemplates['Paris'];
    return destinationTransport[Math.floor(Math.random() * destinationTransport.length)];
  };

  const generateHighlights = (day: number, totalDays: number) => {
    const destination = tripData.destination || 'Paris';
    
    const highlightTemplates = {
      'Paris': [
        '🏛️ Eiffel Tower at sunrise - Beat the crowds for the best photos',
        '🎨 Louvre Museum - Home to the Mona Lisa and 35,000+ artworks',
        '🍷 Seine River Cruise - Romantic views of Notre-Dame and bridges',
        '🎭 Montmartre - Bohemian charm and Sacré-Cœur basilica',
        '🛍️ Champs-Élysées - World\'s most beautiful avenue for shopping',
        '🍽️ Traditional French dinner - Authentic cuisine in historic bistros'
      ],
      'Tokyo': [
        '🍣 Tsukiji Fish Market - World\'s largest fish market experience',
        '🏯 Senso-ji Temple - Tokyo\'s oldest temple with traditional rituals',
        '🗼 Tokyo Skytree - Panoramic city views from Japan\'s tallest structure',
        '🎌 Harajuku & Shibuya - Youth culture and famous crossing',
        '🍵 Tea Ceremony - Traditional Japanese cultural experience',
        '🍜 Ramen Tasting - Sample different styles of authentic ramen'
      ],
      'New York': [
        '🏃 Central Park - Iconic green space in the heart of Manhattan',
        '🗽 Statue of Liberty - Symbol of freedom with Ellis Island history',
        '🎭 Broadway Show - World-class theater and musical performances',
        '🌉 Brooklyn Bridge - Historic bridge with stunning skyline views',
        '🍕 NYC Food Tour - Sample diverse cuisines from different neighborhoods',
        '🏢 Times Square - The crossroads of the world with bright lights'
      ]
    };

    const destinationHighlights = highlightTemplates[destination as keyof typeof highlightTemplates] || [
      '🗺️ Explore the city center and key landmarks',
      '📸 Capture photos at scenic viewpoints',
      '🍽️ Try a popular local eatery for authentic flavors',
      '🚶 Plan a relaxing evening walk in a safe, lively area'
    ];
    return destinationHighlights.slice(0, 3 + Math.floor(Math.random() * 2));
  };

  const generateTips = () => {
    const destination = tripData.destination || 'Paris';
    const companyType = tripData.companyType || 'solo';
    
    const tipTemplates = {
      'Paris': [
        '👟 Wear comfortable walking shoes - Paris is best explored on foot',
        '📱 Download the RATP app for metro navigation and real-time updates',
        '🍷 Learn basic French phrases - "Bonjour", "Merci", "Excusez-moi"',
        '📸 Visit museums on first Sunday of the month for free entry',
        '☔ Always carry an umbrella - Paris weather can be unpredictable',
        '💳 Keep small change for tips and small purchases',
        '🎫 Book major attractions in advance to avoid long queues',
        '🍽️ Make dinner reservations - Popular restaurants book up quickly'
      ],
      'Tokyo': [
        '🚇 Get a JR Pass for unlimited train travel if staying 7+ days',
        '👟 Remove shoes when entering temples, restaurants, and homes',
        '💴 Carry cash - Many places don\'t accept credit cards',
        '📱 Download Google Translate for Japanese language help',
        '🚶 Walk on the left side of escalators and stairs',
        '🍱 Try convenience store food - Surprisingly delicious and cheap',
        '🎫 Book popular attractions like TeamLab in advance',
        '🌡️ Check weather - Tokyo can be very hot and humid in summer'
      ],
      'New York': [
        '🚇 Get a MetroCard for unlimited subway and bus rides',
        '👟 Wear comfortable shoes - NYC involves lots of walking',
        '📱 Download the NYC Subway app for real-time train info',
        '💰 Carry small bills for tips and street vendors',
        '🎫 Book Broadway shows and major attractions in advance',
        '🍕 Try pizza by the slice - It\'s a NYC tradition',
        '🌆 Visit observation decks at sunset for best city views',
        '🚶 Walk everywhere possible - NYC is a walking city'
      ]
    };

    const destinationTips = tipTemplates[destination as keyof typeof tipTemplates] || tipTemplates['Paris'];
    
    // Add company-specific tips
    const companyTips = {
      solo: ['📱 Use travel apps for solo-friendly activities and meetups'],
      partner: ['💕 Book romantic restaurants and activities in advance'],
      friends: ['🎉 Look for group discounts and shared experiences'],
      family: ['👶 Check family-friendly activities and kid-friendly restaurants']
    };

    const allTips = [...destinationTips, ...(companyTips[companyType as keyof typeof companyTips] || [])];
    return allTips.slice(0, 4 + Math.floor(Math.random() * 2));
  };

// Convert multi-day API response to local display format
const convertMultiDayToLocal = (multiDayData: MultiDayPlanResponse) => {
  return multiDayData.days.map((day, index) => ({
    day: index + 1,
    date: new Date(day.date),
    weather: getRandomWeather(),
    // Convert items to the format expected by displayDays
    items: day.items.map((item, itemIndex) => ({
      key: `day-${index + 1}-item-${itemIndex}`,
      name: item.name,
      categoryTag: item.category.toLowerCase().replace('_', ''),
      startTime: item.arrive_at,
      endTime: item.depart_at,
      durationText: `${item.duration_min} min`,
      badges: [
        { type: 'category', text: item.category },
        { type: 'duration', text: `${item.duration_min} min` },
        { type: 'optimized', text: '✨ Optimized' }
      ]
    })),
    activities: day.items.map((item, itemIndex) => ({
      time: item.arrive_at,
      title: item.name,
      description: `${item.category} • Duration: ${item.duration_min} min`,
      icon: Camera,
      duration: `${Math.round(item.duration_min / 60 * 10) / 10}h`,
      type: item.category.toLowerCase().replace('_', ''),
      location: '',
      cost: '',
      difficulty: 'Easy',
      personalized: '✨ Optimized route'
    })),
    meals: generateMeals(),
    accommodation: generateAccommodation(),
    transportation: generateTransportation(),
    highlights: day.items.slice(0, 3).map(item => 
      `${getActivityEmoji(item.category)} ${item.name} - Perfectly timed visit`
    ),
    tips: generateTips()
  }));
};

// Convert backend itinerary format to local display format
const convertBackendToLocal = (backendItinerary: any) => {
    // Handle backend structure from our FastAPI service
    if (backendItinerary?.itinerary?.optimization_result?.optimized_route) {
      const route = backendItinerary.itinerary.optimization_result.optimized_route as any[];
      const dayDate = new Date();
      const activities = route.map((stop, idx) => ({
        time: stop.arrival_time_formatted || stop.scheduled_arrival_time || `${9 + idx}:00`,
        title: stop.name || `Stop ${idx + 1}`,
        description: `${stop.category || 'Attraction'} · Rating ${stop.rating ?? 'N/A'}`,
        icon: Camera,
        duration: `${stop.stay_duration_hours ?? stop.stay_duration ?? 2}h`,
        type: 'sightseeing',
        location: `${stop.address || ''}`,
        cost: undefined,
        difficulty: 'Easy',
      }));
      return [
        {
          day: 1,
          date: dayDate,
          weather: currentWeather || getRandomWeather(),
          activities,
          meals: generateMeals(),
          accommodation: generateAccommodation(),
          transportation: generateTransportation(),
          highlights: generateHighlights(1, 1),
          tips: generateTips(),
        },
      ];
    }

    // Fallback: try older placeholder shape
    const daysMap = new Map();
    
    (backendItinerary?.activities || []).forEach((activity: any) => {
      const activityDate = activity.time_slot?.start_time ? 
        new Date(activity.time_slot.start_time).toDateString() : 
        new Date().toDateString();
      
      if (!daysMap.has(activityDate)) {
        daysMap.set(activityDate, {
          day: daysMap.size + 1,
          date: new Date(activityDate),
          weather: currentWeather || getRandomWeather(),
          activities: [],
          meals: generateMeals(),
          accommodation: generateAccommodation(),
          transportation: generateTransportation(),
          highlights: [],
          tips: generateTips()
        });
      }
      
      const dayData = daysMap.get(activityDate);
      dayData.activities.push({
        time: activity.time_slot?.start_time ? 
          new Date(activity.time_slot.start_time).toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit', 
            hour12: false 
          }) : 'TBD',
        title: activity.name,
        description: activity.description || 'No description available',
        icon: getActivityIcon(activity.activity_type),
        duration: activity.duration ? `${activity.duration}h` : 'N/A',
        type: activity.activity_type?.toLowerCase().replace('_', '') || 'activity',
        location: activity.location || 'TBD',
        cost: activity.cost ? `$${activity.cost}` : 'TBD',
        difficulty: 'Easy',
        personalized: activity.rating && activity.rating > 4.5 ? '⭐ Highly Rated' : ''
      });
      
      // Add activity-specific highlight
      if (activity.name) {
        dayData.highlights.push(`${getActivityEmoji(activity.activity_type)} ${activity.name} - ${activity.description || 'Great experience'}`);
      }
    });
    
    return Array.from(daysMap.values()).sort((a, b) => a.day - b.day);
  };

  // Helper function to get activity icon based on type
  const getActivityIcon = (activityType: string) => {
    const icons: { [key: string]: any } = {
      'RESTAURANT': Utensils,
      'TOURIST_ATTRACTION': Camera,
      'MUSEUM': Star,
      'PARK': Leaf,
      'SHOPPING_MALL': Star,
      'AMUSEMENT_PARK': Star,
      'ZOO': Star,
      'AQUARIUM': Star,
      'NIGHT_CLUB': Star,
      'BAR': Utensils
    };
    return icons[activityType] || Camera;
  };

  // Helper function to get activity emoji based on type
  const getActivityEmoji = (activityType: string) => {
    const emojis: { [key: string]: string } = {
      'RESTAURANT': '🍽️',
      'TOURIST_ATTRACTION': '🏛️',
      'MUSEUM': '🎨',
      'PARK': '🌳',
      'SHOPPING_MALL': '🛍️',
      'AMUSEMENT_PARK': '🎢',
      'ZOO': '🦁',
      'AQUARIUM': '🐠',
      'NIGHT_CLUB': '🌃',
      'BAR': '🍸'
    };
    return emojis[activityType] || '📍';
  };

  const getTransportIcon = (type: string) => {
    const icons: { [key: string]: any } = {
      walking: Footprints,
      bicycle: Bike,
      'public-transport': Bus,
      train: Train,
      car: Car,
      plane: Plane
    };
    return icons[type] || Footprints;
  };

  const getActivityTypeColor = (type: string) => {
    const colors: { [key: string]: string } = {
      sightseeing: 'bg-blue-100 text-blue-800',
      culture: 'bg-purple-100 text-purple-800',
      food: 'bg-orange-100 text-orange-800',
      adventure: 'bg-green-100 text-green-800',
      leisure: 'bg-pink-100 text-pink-800',
      nightlife: 'bg-indigo-100 text-indigo-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  // If not loading and no itinerary generated, show a helpful message
  if (!isLoading && itinerary.length === 0) {
    const storedCity = localStorage.getItem('currentItineraryCity') || '';
    const effectiveCity = (tripData.destination || storedCity || '').trim();

    const handleGenerateNow = async () => {
      try {
        setIsLoading(true);
        const city = effectiveCity || 'Pune';
        setDebugInfo(prev => prev + `\n[manual-generate] city=${city}`);
        const created = await createCompleteItineraryFromCity(city, 1, { startDate: tripData.startDate || undefined, endDate: tripData.endDate || undefined, startTime: '09:00:00' });
        const newId = created.itinerary_id?.toString?.() || created.itinerary_id || "";
        if (newId) {
          localStorage.setItem('currentItineraryId', newId);
          localStorage.setItem('currentItineraryCity', city);
          setDebugInfo(prev => prev + `\n[getItinerary] newId=${newId}`);
        }
        // Use creation response directly to render day-wise plan (no GET by ID endpoint in backend)
        setApiResult(created);
        setDaywise(groupByDayFromApiResult(created));
        const convertedItinerary = convertCreatedResponseToLocal(created);
        setItinerary(convertedItinerary);
      } catch (e: any) {
        setLastError(`manual create failed: ${e?.message || e}`);
      } finally {
        setIsLoading(false);
      }
    };

    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="max-w-md mx-auto text-center px-4">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="w-8 h-8 text-yellow-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">No Itinerary Yet</h2>
            <p className="text-gray-600 mb-1">Destination: <span className="font-semibold">{effectiveCity || '(not set)'}</span></p>
            <p className="text-gray-600 mb-6">Click Generate to create an itinerary via the backend now.</p>
            <div className="space-y-3">
              <div className="text-left text-xs bg-gray-50 p-3 rounded border mb-3">
                <div className="font-semibold text-gray-700">Debug</div>
                <pre className="whitespace-pre-wrap break-words text-gray-600">{debugInfo}</pre>
                {lastError && (<div className="text-red-600 mt-2">Error: {lastError}</div>)}
                <div className="mt-2 text-gray-600">storedId: {localStorage.getItem('currentItineraryId') || '(none)'} | storedCity: {localStorage.getItem('currentItineraryCity') || '(none)'} | dest: {tripData.destination || '(none)'} | api: {getApiBase()}</div>
              </div>
              <Button onClick={handleGenerateNow} className="w-full bg-green-600 hover:bg-green-700 text-white">
                Generate Itinerary Now
              </Button>
              <Button onClick={() => navigate('/trip-planning')} variant="outline" className="w-full">
                Update Trip Details
              </Button>
              <Button onClick={() => navigate('/')} variant="outline" className="w-full">
                Back to Home
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Creating Your Perfect Itinerary</h2>
          <p className="text-gray-600">Please wait while we craft your personalized travel plan...</p>
        </div>
      </div>
    );
  }

  const currentDayData: any = displayDays[currentDay - 1] || {};
  const totalDays = displayDays.length;
  const dayDate: Date = currentDayData?.date ? new Date(currentDayData.date) : new Date();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <UpdateBanner message={bannerMessage} onClose={() => setBannerMessage(null)} />
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
<Button variant="outline" onClick={() => navigate('/trip-planning')}>
                <ChevronLeft className="w-4 h-4 mr-2" />
                Back to Planning
              </Button>
              <div>
                <h1 className="text-3xl font-bold text-gray-800">
                  Your {isMultiDayTrip ? 'Multi-Day' : ''} Trip Itinerary
                </h1>
                <p className="text-gray-600">
                  {tripData.destination || 'Your destination'} • {displayDays.length} {displayDays.length === 1 ? 'day' : 'days'}
                  {isMultiDayTrip && multiDayData && (
                    <span className="ml-2 inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      ✨ Optimized Route
                    </span>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {backendItinerary && (
                <Badge className="bg-green-100 text-green-800">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Live Updates Active
                </Badge>
              )}
              {alerts.length > 0 && (
                <Badge className="bg-red-100 text-red-800">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {alerts.length} Alert{alerts.length > 1 ? 's' : ''}
                </Badge>
              )}
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button variant="outline" size="sm">
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button variant="outline" size="sm">
                <Bookmark className="w-4 h-4 mr-2" />
                Save
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Day Navigation for multi-day trips */}
        {console.log('🎯 Day navigation check:', { displayDaysLength: displayDays.length, isMultiDayTrip, multiDayData: !!multiDayData })}
        {displayDays.length > 1 ? (
          <div className="flex items-center justify-between mb-8">
            <Button 
              variant="outline" 
              onClick={() => setCurrentDay(Math.max(1, currentDay - 1))}
              disabled={currentDay === 1}
            >
              <ChevronLeft className="w-4 h-4 mr-2" />
              Previous Day
            </Button>
            
            <div className="flex items-center space-x-4">
              {displayDays.map((_, index) => (
                <Button
                  key={index + 1}
                  variant={currentDay === index + 1 ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentDay(index + 1)}
                  className="w-12 h-12 rounded-full"
                >
                  Day {index + 1}
                </Button>
              ))}
            </div>
            
            <Button 
              variant="outline" 
              onClick={() => setCurrentDay(Math.min(totalDays, currentDay + 1))}
              disabled={currentDay === totalDays}
            >
              Next Day
              <ChevronRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        ) : (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-800">Daily Schedule</h2>
          </div>
        )}

        {/* Day Header (only for multi-day view) */}
        {displayDays.length > 1 && (
          <Card className="mb-8">
            <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">Day {currentDay}</CardTitle>
                  <CardDescription className="text-blue-100">
                    {dayDate.toLocaleDateString('en-US', { 
                      weekday: 'long', 
                      year: 'numeric', 
                      month: 'long', 
                      day: 'numeric' 
                    })}
                  </CardDescription>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6">🌤️</span>
                    <span className="text-lg font-semibold">
                      {currentWeather ? `${Math.round(currentWeather.temperature)}°C` : (currentDayData?.weather?.temp ?? '')}
                    </span>
                  </div>
                  { (currentWeather?.description || currentDayData?.weather?.description) && (
                    <Badge variant="secondary" className="bg-white/20 text-white">
                      {currentWeather?.description || currentDayData?.weather?.description}
                    </Badge>
                  )}
                  {currentWeather && (
                    <Badge variant="secondary" className="bg-green-500/20 text-green-100">
                      Live Weather
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
          </Card>
        )}

        {/* Last updated label */}
        {lastUpdated && (
          <div className="text-xs text-muted-foreground mb-3">
            Last updated at {hhmm(lastUpdated)}
          </div>
        )}

        {/* Compact Daily Schedule (moved into Main Activities section below) */}

        {/* Real-time Alerts */}
        {alerts.length > 0 && (
          <Card className="mb-8 border-red-200 bg-red-50">
            <CardHeader>
              <CardTitle className="flex items-center text-red-800">
                <AlertCircle className="w-5 h-5 mr-2" />
                Live Alerts ({alerts.length})
              </CardTitle>
            </CardHeader>
          <CardContent className="space-y-6">
            {/* Enhanced plan moved to main Daily Schedule card below for high visibility */}
              {alerts.slice(-3).map((alert: any, index: number) => (
                <div key={index} className="p-4 rounded-lg bg-white border border-red-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-semibold text-red-800 mb-1">{alert.type?.toUpperCase() || 'ALERT'}</div>
                      <div className="text-sm text-red-700 mb-2">{alert.message || 'New alert received'}</div>
                      <div className="text-xs text-red-600">
                        {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : 'Just now'}
                      </div>
                    </div>
                    <div className="text-xs text-red-500">
                      {alert.severity || 'INFO'}
                    </div>
                  </div>
                </div>
              ))}
              {alerts.length > 3 && (
                <div className="text-center pt-2">
                  <Button variant="outline" size="sm" className="text-red-700 border-red-200">
                    View All {alerts.length} Alerts
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Activities */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Clock className="w-5 h-5 mr-2 text-blue-600" />
                  Daily Schedule
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {multiDayData && displayDays.length > 1 && (
                  <div className="mb-4 text-sm text-blue-700 bg-blue-50 p-3 rounded border">
                    ✨ Multi-day optimized itinerary • Last updated: {multiDayData.last_updated}
                  </div>
                )}
                {(!displayDays[currentDay - 1] || displayDays[currentDay - 1].items.length === 0) && (
                  <div className="text-sm text-gray-600">Generating plan...</div>
                )}
                <div className="space-y-3">
                  <AnimatePresence>
                    {(displayDays[currentDay - 1]?.items || []).map((it) => (
                      <ItineraryCard
                        key={it.key}
                        startTime={it.startTime || ""}
                        endTime={it.endTime || ""}
                        name={it.name}
                        categoryTag={it.categoryTag}
                        durationText={it.durationText}
                        badges={it.badges}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </CardContent>
            </Card>

            {/* Highlights */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Star className="w-5 h-5 mr-2 text-yellow-600" />
                  Day Highlights
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(currentDayData?.highlights || []).map((highlight: string, index: number) => (
                    <div key={index} className="flex items-start space-x-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200 hover:bg-yellow-100 transition-colors duration-200">
                      <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                      <span className="text-sm text-gray-700 leading-relaxed font-medium">{highlight}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Meals */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Utensils className="w-5 h-5 mr-2 text-orange-600" />
                  Meals
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(currentDayData?.meals || []).map((meal: any, index: number) => (
                  <div key={index} className="p-4 rounded-xl bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-200 hover:border-orange-300 transition-all duration-300">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-orange-800 text-sm">{meal.type}</span>
                      <span className="text-sm text-orange-600 font-medium">{meal.time}</span>
                    </div>
                    <div className="text-base font-semibold text-orange-900 mb-2">{meal.name}</div>
                    <div className="text-sm text-orange-700 mb-2 leading-relaxed">{meal.description}</div>
                    <div className="text-xs text-orange-600 mb-2 font-medium">{meal.location}</div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <Star className="w-4 h-4 text-yellow-500 mr-1" />
                        <span className="text-sm text-orange-600 font-medium">{meal.rating}/5</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-orange-800">{meal.cost}</div>
                        <div className="text-xs text-orange-600">{meal.specialty}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Accommodation */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <MapPin className="w-5 h-5 mr-2 text-green-600" />
                  Accommodation
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-800 mb-2">{currentDayData.accommodation?.name || "No accommodation added"}</h3>
                    <p className="text-sm text-gray-600 mb-2">{currentDayData.accommodation?.location || ""}</p>
                    <p className="text-sm text-gray-700 mb-3 leading-relaxed">{currentDayData.accommodation?.description || ""}</p>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center">
                        <Star className="w-4 h-4 text-yellow-500 mr-1" />
                        <span className="text-sm font-medium text-gray-600">{currentDayData.accommodation?.rating ? `${currentDayData.accommodation.rating}/5` : ""}</span>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold text-green-600">{currentDayData.accommodation?.priceRange || ""}</div>
                        <div className="text-xs text-gray-500">{currentDayData.accommodation?.roomType || ""}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-3">🏨 Amenities</h4>
                    <div className="flex flex-wrap gap-2">
                      {(currentDayData.accommodation?.amenities || []).map((amenity: string, index: number) => (
                        <Badge key={index} variant="secondary" className="text-xs px-3 py-1 bg-blue-100 text-blue-800">
                          {amenity}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {(currentDayData.accommodation?.ecoFeatures?.length || 0) > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-green-700 mb-3 flex items-center">
                        <Leaf className="w-4 h-4 mr-2" />
                        🌱 Eco Features
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {(currentDayData.accommodation?.ecoFeatures || []).map((feature: string, index: number) => (
                          <Badge key={index} variant="secondary" className="text-xs px-3 py-1 bg-green-100 text-green-800">
                            {feature}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <h4 className="text-sm font-semibold text-purple-700 mb-3">⭐ Highlights</h4>
                    <div className="space-y-1">
                      {(currentDayData.accommodation?.highlights || []).map((highlight: string, index: number) => (
                        <div key={index} className="flex items-start space-x-2">
                          <div className="w-1.5 h-1.5 bg-purple-600 rounded-full mt-2 flex-shrink-0"></div>
                          <span className="text-sm text-gray-700">{highlight}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Transportation */}
            {currentDayData.transportation && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center">
                    {(() => { const IconT = getTransportIcon(currentDayData.transportation?.type || 'walking'); return <IconT className="w-5 h-5 mr-2 text-blue-600" />; })()}
                    Transportation
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="p-4 rounded-xl bg-gradient-to-r from-blue-50 to-cyan-50 border-2 border-blue-200 hover:border-blue-300 transition-all duration-300">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-lg font-bold text-blue-800">{currentDayData.transportation.name}</span>
                      <Badge className="bg-blue-100 text-blue-800 px-3 py-1">
                        Eco Score: {currentDayData.transportation.ecoScore}/10
                      </Badge>
                    </div>
                    <p className="text-sm text-blue-700 mb-3 leading-relaxed">{currentDayData.transportation.description}</p>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
                      <div className="flex items-center text-xs text-blue-600">
                        <span className="font-semibold text-orange-600">{currentDayData.transportation.cost}</span>
                      </div>
                      <div className="flex items-center text-xs text-blue-600">
                        <Clock className="w-3 h-3 mr-1" />
                        <span>{currentDayData.transportation.duration}</span>
                      </div>
                      <div className="flex items-center text-xs text-blue-600">
                        <Leaf className="w-3 h-3 mr-1" />
                        <span>Sustainable</span>
                      </div>
                    </div>

                    <div>
                      <h5 className="text-sm font-semibold text-blue-800 mb-2">✨ Highlights</h5>
                      <div className="flex flex-wrap gap-1">
                        {(currentDayData.transportation?.highlights || []).map((highlight: string, index: number) => (
                          <Badge key={index} variant="secondary" className="text-xs px-2 py-1 bg-blue-100 text-blue-800">
                            {highlight}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Tips */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Info className="w-5 h-5 mr-2 text-purple-600" />
                  Pro Tips
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {(currentDayData?.tips || []).map((tip: string, index: number) => (
                    <div key={index} className="flex items-start space-x-3 p-3 rounded-lg bg-purple-50 border border-purple-200 hover:bg-purple-100 transition-colors duration-200">
                      <div className="w-2 h-2 bg-purple-600 rounded-full mt-2 flex-shrink-0"></div>
                      <span className="text-sm text-gray-700 leading-relaxed">{tip}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Emergency Contact */}
            {tripData.emergencyContact && (
              <Card className="border-red-200 bg-red-50">
                <CardHeader>
                  <CardTitle className="flex items-center text-red-800">
                    <Phone className="w-5 h-5 mr-2" />
                    Emergency Contact
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="text-sm">
                      <span className="font-semibold text-red-800">{tripData.emergencyContact.name}</span>
                      <div className="text-red-700">{tripData.emergencyContact.phone}</div>
                      <div className="text-red-600 text-xs">{tripData.emergencyContact.relation}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* Trip Summary Footer */}
        <Card className="mt-8 bg-gradient-to-r from-blue-600 to-indigo-600 text-white">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold mb-2">Ready for Your Adventure?</h3>
                <p className="text-blue-100">
                  Your personalized {displayDays.length}-day{isMultiDayTrip ? ' optimized' : ''} itinerary for {tripData.destination || 'your destination'} is ready!
                </p>
              </div>
              <div className="flex space-x-3">
<Button variant="secondary" onClick={() => navigate('/')}>
                  <Globe className="w-4 h-4 mr-2" />
                  Explore More
                </Button>
                <Button variant="outline" className="bg-white text-blue-600 hover:bg-blue-50">
                  <Download className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
