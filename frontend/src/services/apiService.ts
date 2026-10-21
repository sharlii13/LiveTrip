// API Service for connecting to FastAPI backend
// Prefer VITE_API_BASE if provided (strip trailing /api for root base)
const VITE_API_BASE = (import.meta as any).env?.VITE_API_BASE as string | undefined;
const API_BASE_URL = VITE_API_BASE
  ? VITE_API_BASE.replace(/\/?api\/?$/, '')
  : ''; // same origin: the Vite dev proxy (or the production host) serves /api

export interface CreateItineraryRequest {
  user_id: string;
  destination: string;
  start_date: string;
  end_date: string;
  user_preferences: {
    food_preference: string;
    budget_range: string;
    travel_style: string;
    mobility_requirements?: string;
    language_preference: string;
    interests: string[];
    avoid_activities: string[];
    eco_mode: boolean;
    preferred_transport: string[];
  };
  must_visit_places: string[];
  budget_limit?: number;
  flight_details?: {
    flight_number: string;
    airline: string;
    departure_time: string;
    arrival_time: string;
    status: string;
  };
}

export interface Itinerary {
  id: string;
  user_id: string;
  destination: string;
  start_date: string;
  end_date: string;
  days: ItineraryDay[];
  user_preferences: UserPreferences;
  total_budget: number;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface ItineraryDay {
  date: string;
  time_slots: TimeSlot[];
  total_budget: number;
  total_travel_time: number;
  weather_forecast?: WeatherData;
}

export interface TimeSlot {
  start_time: string;
  end_time: string;
  activity: Activity;
  priority: number;
  flexibility: number;
}

export interface Activity {
  id: string;
  name: string;
  description?: string;
  location: {
    latitude: number;
    longitude: number;
    address: string;
    city: string;
    country: string;
  };
  activity_type: string;
  estimated_duration: number;
  cost?: number;
  rating?: number;
  weather_dependent: boolean;
  indoor_alternative?: string;
  opening_hours?: any;
  booking_required: boolean;
  difficulty_level?: string;
  accessibility_info?: string;
}

export interface UserPreferences {
  food_preference: string;
  budget_range: string;
  travel_style: string;
  mobility_requirements?: string;
  language_preference: string;
  interests: string[];
  avoid_activities: string[];
  eco_mode: boolean;
  preferred_transport: string[];
}

export interface WeatherData {
  temperature: number;
  condition: string;
  humidity: number;
  wind_speed: number;
  precipitation_probability: number;
  timestamp: string;
}

export interface RealTimeAlert {
  id: string;
  itinerary_id: string;
  alert_type: string;
  severity: string;
  message: string;
  suggested_actions: string[];
  timestamp: string;
  acknowledged: boolean;
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }
    return response.json();
  }

  // Create a new itinerary
  async createItinerary(data: CreateItineraryRequest): Promise<Itinerary> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      return this.handleResponse<Itinerary>(response);
    } catch (error) {
      console.error('Failed to create itinerary:', error);
      throw error;
    }
  }

  // Get itinerary by ID
  async getItinerary(itineraryId: string): Promise<Itinerary> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}`);
      return this.handleResponse<Itinerary>(response);
    } catch (error) {
      console.error('Failed to get itinerary:', error);
      throw error;
    }
  }

  // Get user's itineraries
  async getUserItineraries(userId: string): Promise<Itinerary[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/user/${userId}`);
      return this.handleResponse<Itinerary[]>(response);
    } catch (error) {
      console.error('Failed to get user itineraries:', error);
      throw error;
    }
  }

  // Update user preferences
  async updatePreferences(itineraryId: string, preferences: Partial<UserPreferences>, applyImmediately = true): Promise<{ message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/preferences`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          itinerary_id: itineraryId,
          preferences,
          apply_immediately: applyImmediately,
        }),
      });

      return this.handleResponse<{ message: string }>(response);
    } catch (error) {
      console.error('Failed to update preferences:', error);
      throw error;
    }
  }

  // Get alerts for an itinerary
  async getAlerts(itineraryId: string): Promise<RealTimeAlert[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/alerts`);
      return this.handleResponse<RealTimeAlert[]>(response);
    } catch (error) {
      console.error('Failed to get alerts:', error);
      throw error;
    }
  }

  // Acknowledge an alert
  async acknowledgeAlert(itineraryId: string, alertId: string): Promise<{ message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/alerts/${alertId}/acknowledge`, {
        method: 'POST',
      });

      return this.handleResponse<{ message: string }>(response);
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      throw error;
    }
  }

  // Get current weather for itinerary
  async getCurrentWeather(itineraryId: string): Promise<WeatherData> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/current-weather`);
      return this.handleResponse<WeatherData>(response);
    } catch (error) {
      console.error('Failed to get current weather:', error);
      throw error;
    }
  }

  // Optimize route for a specific day
  async optimizeRoute(itineraryId: string, dayIndex: number = 0): Promise<{ message: string; day_index: number; activities_count: number }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/route-optimization?day_index=${dayIndex}`, {
        method: 'GET',
      });

      return this.handleResponse<{ message: string; day_index: number; activities_count: number }>(response);
    } catch (error) {
      console.error('Failed to optimize route:', error);
      throw error;
    }
  }

  // Export itinerary
  async exportItinerary(itineraryId: string, format: 'json' | 'summary' = 'json'): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}/export?format=${format}`);
      return this.handleResponse<any>(response);
    } catch (error) {
      console.error('Failed to export itinerary:', error);
      throw error;
    }
  }

  // Delete itinerary
  async deleteItinerary(itineraryId: string): Promise<{ message: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/${itineraryId}`, {
        method: 'DELETE',
      });

      return this.handleResponse<{ message: string }>(response);
    } catch (error) {
      console.error('Failed to delete itinerary:', error);
      throw error;
    }
  }

  // Health check
  async healthCheck(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return this.handleResponse<any>(response);
    } catch (error) {
      console.error('Failed to check health:', error);
      throw error;
    }
  }

  // Get API stats
  async getStats(): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/stats`);
      return this.handleResponse<any>(response);
    } catch (error) {
      console.error('Failed to get stats:', error);
      throw error;
    }
  }

  // Plan multi-day trip
  async planMultiDayTrip(request: MultiDayPlanRequest): Promise<MultiDayResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/itinerary/plan-multi-day`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      return this.handleResponse<MultiDayResponse>(response);
    } catch (error) {
      console.error('Failed to plan multi-day trip:', error);
      throw error;
    }
  }
}

// Create and export a singleton instance
export const apiService = new ApiService();

// WebSocket connection for real-time updates
export class WebSocketService {
  private ws: WebSocket | null = null;
  private itineraryId: string | null = null;
  private listeners: { [key: string]: Function[] } = {};

  connect(itineraryId: string) {
    this.itineraryId = itineraryId;
    const wsUrl = API_BASE_URL.replace('http', 'ws') + `/ws/itinerary/${itineraryId}`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected for itinerary:', itineraryId);
        this.emit('connected', { itineraryId });
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type, data);
          this.emit('message', data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket connection closed');
        this.emit('disconnected', { itineraryId });
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.emit('error', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.itineraryId = null;
    }
  }

  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  // Event listener management
  on(event: string, callback: Function) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  off(event: string, callback: Function) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  private emit(event: string, data: any) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  // Send specific message types
  requestWeatherUpdate() {
    this.send({ type: 'request_weather_update' });
  }

  requestAlerts() {
    this.send({ type: 'request_alerts' });
  }

  acknowledgeAlert(alertId: string) {
    this.send({ type: 'acknowledge_alert', alert_id: alertId });
  }

  ping() {
    this.send({ type: 'ping' });
  }
}

// Create and export WebSocket service instance
export const webSocketService = new WebSocketService();

// Multi-day planning types
export interface MultiDayPlanRequest {
  city: string;
  days: number;
  start_time: string;
  end_time: string;
  mode: string;
  pace: string;
  hotel: {
    lat: number;
    lng: number;
  };
}

export interface MultiDayPOI {
  poi: string;
  category: string;
  start: string;
  end: string;
  duration_hr: number;
  coordinates: {
    lat: number;
    lng: number;
  };
}

export interface MultiDayItinerary {
  day: number;
  total_distance_km: number;
  total_duration_hr: number;
  utilization_percent: number;
  category_mix: { [category: string]: number };
  diversity_score: number;
  schedule: MultiDayPOI[];
}

export interface MultiDayResponse {
  itinerary: MultiDayItinerary[];
  summary: {
    total_days: number;
    total_pois_covered: number;
    avg_daily_diversity: string;
    avg_daily_utilization: string;
    categories_distribution: { [category: string]: number };
    unassigned_pois: string[];
  };
  metadata?: any;
}

export default apiService;
