# 🧳✨ The Living Itinerary - Backend API

**Your AI-powered co-traveler that adapts to real-time conditions**

This is the FastAPI-based backend that powers The Living Itinerary's intelligent, adaptive travel planning system.

## 🌟 Key Features

- **🌧 Weather-aware**: Outdoor plans automatically swap with indoor alternatives if it rains
- **🚗 Traffic-smart**: Routes and timings shuffle instantly if traffic builds up  
- **✈ Flight-integrated**: Delays or changes reorganize your entire day seamlessly
- **😴 Mood-adaptive**: Dynamic preference updates affect itinerary in real-time
- **📊 Smart insights**: Track expenses, time spent, and trip highlights automatically
- **🔔 Smart notifications**: Proactive solutions via WebSocket connections
- **🤖 Greedy Algorithm**: Multi-criteria optimization for the best travel experience

## 🏗 Technical Architecture

### Core Components

- **Greedy Optimization Algorithm**: Real-time itinerary optimization based on multiple factors
- **Live API Integration**: Weather (OpenWeather), Maps (Google), Flights (AviationStack), Events (EventBrite)
- **WebSocket Support**: Real-time updates and bidirectional communication
- **Multi-criteria Scoring**: User preferences, weather suitability, traffic, cost efficiency

### API Services

| Service | Purpose | API Provider |
|---------|---------|-------------|
| WeatherService | Real-time weather data and forecasts | OpenWeather |
| MapsService | Traffic data, routing, places | Google Maps |
| FlightService | Flight status, delays, tracking | AviationStack |
| EventsService | Local events and activities | EventBrite |

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- API Keys for external services (see `.env.example`)

### Installation

1. **Clone and setup**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run the server**
   ```bash
   # Development
   python -m app.main
   
   # Or with uvicorn
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health
   - WebSocket: ws://localhost:8000/ws/itinerary/{itinerary_id}

## 📡 API Endpoints

### Core Itinerary Management

```http
POST   /api/itinerary/create              # Create optimized itinerary
GET    /api/itinerary/{itinerary_id}      # Get itinerary details
GET    /api/itinerary/user/{user_id}      # Get user's itineraries
PUT    /api/itinerary/{id}/preferences    # Update preferences
DELETE /api/itinerary/{itinerary_id}      # Delete itinerary
```

### Real-time Adaptations

```http
POST   /api/itinerary/{id}/weather-update  # Handle weather changes
POST   /api/itinerary/{id}/traffic-update  # Handle traffic delays
POST   /api/itinerary/{id}/flight-update   # Handle flight changes
```

### Monitoring & Alerts

```http
GET    /api/itinerary/{id}/alerts         # Get real-time alerts
POST   /api/itinerary/{id}/alerts/{alert_id}/acknowledge
GET    /api/itinerary/{id}/current-weather
```

### WebSocket Events

Connect to `/ws/itinerary/{itinerary_id}` to receive:

- `weather_update` - Weather condition changes
- `traffic_update` - Traffic delay notifications  
- `flight_update` - Flight status changes
- `alert` - Real-time alerts and recommendations
- `itinerary_updated` - Itinerary modifications

## 🤖 The Greedy Algorithm

Our optimization algorithm uses a multi-criteria scoring system:

### Scoring Factors
- **Preference Match** (25%): How well activities match user interests
- **Travel Efficiency** (20%): Optimal routing and time management  
- **Weather Suitability** (20%): Weather-appropriate activity selection
- **Time Utilization** (15%): Efficient use of available time
- **Cost Efficiency** (10%): Budget-conscious recommendations
- **Flexibility** (10%): Adaptability to changes

### Real-time Adaptations

The algorithm continuously monitors:

1. **Weather Changes**: Replaces outdoor activities with indoor alternatives
2. **Traffic Delays**: Reschedules flexible activities and suggests alternative routes
3. **Flight Delays**: Adjusts entire day schedule, moves activities between days
4. **User Feedback**: Instantly incorporates preference changes

## 🔧 Configuration

### Environment Variables

```bash
# Server
HOST=0.0.0.0
PORT=8000
NODE_ENV=development

# API Keys (required)
OPENWEATHER_API_KEY=your_openweather_key
GOOGLE_MAPS_API_KEY=your_google_maps_key
AVIATIONSTACK_API_KEY=your_aviationstack_key
EVENTBRITE_API_KEY=your_eventbrite_key
ACCUWEATHER_API_KEY=your_accuweather_key

# CORS Origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

See `.env.example` for complete configuration options.

## 🔍 Monitoring & Health

### Health Check

```bash
curl http://localhost:8000/health
```

Returns status of all services:
- Core API functionality
- WebSocket connections  
- External API availability

### Statistics

```bash
curl http://localhost:8000/api/stats
```

Real-time statistics on:
- Active itineraries
- WebSocket connections
- Alerts and notifications

## 🧪 Development

### Project Structure

```
backend/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Business logic
│   ├── services/         # External API integrations  
│   ├── schemas/          # Pydantic models
│   └── main.py           # FastAPI application
├── requirements.txt      # Python dependencies
└── .env.example         # Configuration template
```

### Key Design Patterns

- **Dependency Injection**: Services are injected into route handlers
- **Async/Await**: All external API calls are asynchronous
- **WebSocket Management**: Connection pooling and automatic cleanup
- **Error Handling**: Comprehensive error responses and logging
- **Real-time Monitoring**: Background tasks for continuous optimization

## 🚀 Production Deployment

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
EXPOSE 8000

CMD ["python", "-m", "app.main"]
```

### Using Gunicorn

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📊 API Rate Limits

| Service | Requests/Hour |
|---------|---------------|
| OpenWeather | 1,000 |
| Google Maps | 2,500 |
| AviationStack | 500 |
| EventBrite | 1,000 |
| AccuWeather | 50 |

## 🤝 Integration with Frontend

The backend is designed to work seamlessly with the React frontend:

1. **RESTful API**: Standard HTTP endpoints for CRUD operations
2. **WebSocket Support**: Real-time updates without polling
3. **CORS Configured**: Ready for cross-origin requests
4. **JSON Responses**: Consistent, typed data structures

## 📝 License

MIT License - see LICENSE file for details.

---

**Making travel stress-free, one algorithm at a time!** 🎯