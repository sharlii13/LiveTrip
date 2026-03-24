# LiveTripBuddy - The Living Itinerary Chatbot 🤖✈️

LiveTripBuddy is an AI-powered travel companion that helps you manage your trips with dynamic suggestions, smart updates, and travel-focused conversations. Built with Google's Gemini AI, it provides proactive assistance while keeping travel stress-free.

## 🎯 Key Features

- **Travel-Focused Conversations**: Only discusses travel, itinerary, transport, flights, weather, and trip-related topics
- **Smart Update Handling**: Auto-updates critical information (flight delays, gate changes) and asks confirmation for preferences (weather changes, activity swaps)
- **Proactive Assistance**: Monitors your trip and suggests improvements in real-time
- **Context Awareness**: Remembers your preferences, itinerary, and conversation history
- **Graceful Error Handling**: Provides helpful fallbacks when APIs are unavailable

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key

### Installation

1. **Clone or download the project**
   ```bash
   git clone <your-repo-url>
   cd LIveTrip
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy the `.env` file and update with your API key
   - Or set the environment variable directly:
   ```bash
   # Windows
   set GEMINI_API_KEY=your_api_key_here
   
   # Linux/Mac
   export GEMINI_API_KEY=your_api_key_here
   ```

4. **Test the installation**
   ```bash
   python example_usage.py
   ```

## 📚 Usage Examples

### Basic Chat
```python
from live_trip_buddy import LiveTripBuddy

bot = LiveTripBuddy()
user_id = "your_user_id"

# Start chatting
response = bot.process_message(user_id, "I'm planning a trip to Paris")
print(response)
```

### Proactive Updates
```python
from live_trip_buddy import TravelEvent, EventCategory, UpdateType

# Create a travel event
event = TravelEvent(
    category=EventCategory.WEATHER,
    message="🌧 Rain expected this afternoon",
    update_type=UpdateType.ASK_USER,
    suggested_action="Would you like indoor activity suggestions?"
)

# Send proactive update
response = bot.send_proactive_update(user_id, event)
print(response)
```

### Context Management
```python
# Set user preferences
preferences = {
    "dietary_restrictions": ["vegetarian"],
    "interests": ["museums", "art"],
    "budget": "mid-range"
}
bot.set_user_preferences(user_id, preferences)

# Update itinerary
itinerary = {
    "day1": {"morning": "Flight to Paris", "afternoon": "Hotel check-in"}
}
bot.update_itinerary(user_id, itinerary)
```

## 🎯 Core Behavior Rules

### 1. Stay Focused
- Only discusses travel-related topics
- Politely redirects off-topic conversations
- Example: "I'm here to help with your trip and itinerary. Would you like me to adjust or suggest something for your journey?"

### 2. Smart Event Handling

**Auto-update (no confirmation needed):**
- Flight delays and gate changes
- Boarding updates
- Critical safety alerts

**Ask first (requires user confirmation):**
- Weather-based activity changes
- Traffic route alternatives
- Mood-based activity swaps

### 3. User Interaction Style
- Friendly, concise, and proactive
- Always provides solutions, not just problems
- Uses light emojis for clarity: 🌧 ✈ 🚗

### 4. Response Format
- **Success**: "✅ Updated your itinerary with a new indoor option."
- **API Failure**: "⚠️ I couldn't update the system right now. Do you want to adjust manually, or stick with your basic itinerary?"

## 🏗️ Architecture

### Core Components

1. **GeminiClient** (`gemini_client.py`)
   - Handles Google Gemini API communication
   - Manages prompt preparation and response generation
   - Includes health checks and error handling

2. **LiveTripBuddy** (`live_trip_buddy.py`)
   - Main chatbot logic and conversation management
   - Context handling and user preference storage
   - Travel-focused behavior implementation

3. **Data Models**
   - `TravelEvent`: Represents travel-related events
   - `ConversationContext`: Stores user context and history
   - `EventCategory` & `UpdateType`: Event classification enums

### Key Classes

```python
class LiveTripBuddy:
    def process_message(user_id, message) -> str
    def send_proactive_update(user_id, event) -> str
    def update_itinerary(user_id, itinerary)
    def set_user_preferences(user_id, preferences)
    def is_healthy() -> bool

class GeminiClient:
    def generate_response(prompt, context) -> str
    def is_healthy() -> bool

class TravelEvent:
    category: EventCategory
    message: str
    update_type: UpdateType
    suggested_action: Optional[str]
```

## 🧪 Testing

Run the example demos:

```bash
python example_usage.py
```

Available demos:
- Basic chat functionality
- Proactive updates and confirmations
- Context management
- Error handling
- Interactive chat session

## 🛠️ Configuration

### Environment Variables

```bash
GEMINI_API_KEY=your_api_key_here
BOT_NAME=LiveTripBuddy
BOT_VERSION=1.0.0
DEBUG_MODE=True
```

### Travel Keywords
The bot recognizes these travel-related keywords to stay focused:
- Transportation: flight, hotel, train, taxi, uber, airport
- Activities: restaurant, museum, tour, sightseeing, attraction
- Planning: itinerary, trip, booking, reservation, route
- Events: delay, cancel, reschedule, weather, traffic

### Auto-Update Patterns
These patterns trigger automatic updates without user confirmation:
- `flight.*delay`
- `gate.*change`
- `boarding.*update`
- `safety.*alert`
- `emergency.*notification`
- `critical.*update`

## 🔧 Customization

### Adding New Event Categories
```python
class EventCategory(Enum):
    FLIGHT = "flight"
    WEATHER = "weather"
    TRAFFIC = "traffic"
    ACTIVITY = "activity"
    SAFETY = "safety"
    CUSTOM = "custom"  # Add your category
```

### Custom Travel Keywords
```python
bot.travel_keywords.update({
    'custom_keyword1', 'custom_keyword2'
})
```

### Custom Auto-Update Patterns
```python
bot.auto_update_patterns.append(r'custom.*pattern')
```

## 🚨 Error Handling

The bot includes comprehensive error handling:

1. **API Failures**: Graceful fallbacks with helpful messages
2. **Network Issues**: Retry logic with exponential backoff
3. **Invalid Input**: Friendly error messages and suggestions
4. **Rate Limits**: Automatic throttling and queue management

## 🔒 Security

- API keys are loaded from environment variables
- No sensitive data is logged
- User context is stored in memory only
- Input sanitization for all user messages

## 📈 Performance

- Conversation history is automatically trimmed
- Context cleanup for inactive users
- Efficient pattern matching for keywords
- Optimized API calls with caching

## 🐛 Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not found"**
   - Check your `.env` file
   - Verify environment variable is set

2. **"Bot is not healthy"**
   - Verify API key is valid
   - Check internet connection
   - Review API quotas

3. **Off-topic responses**
   - Check if your message contains travel keywords
   - Try rephrasing with travel-related terms

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♀️ Support

For issues and questions:
- Check the troubleshooting section
- Review the example usage
- Open an issue on GitHub

---

**Happy Travels! 🌍✈️**