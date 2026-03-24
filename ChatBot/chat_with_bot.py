"""
Interactive Chat Interface for LiveTripBuddy
Chat directly with your conversational UI bot!
"""

import logging
import os
from conversational_ui import ConversationalUI
from backend_client import BackendSuggestion

# Set up minimal logging to avoid clutter during chat
logging.basicConfig(level=logging.ERROR)

def display_welcome():
    """Display welcome message"""
    print("=" * 60)
    print("🤖 LiveTripBuddy - Interactive Chat")
    print("=" * 60)
    print("Hi! I'm your AI travel companion. I'm here to help with your")
    print("trip planning, itinerary adjustments, and travel questions.")
    print()
    print("💡 Try asking me about:")
    print("  • Planning a trip to any destination")
    print("  • Weather forecasts for your location")
    print("  • Restaurant recommendations")
    print("  • Flight status and changes")
    print("  • Activity suggestions")
    print()
    print("📝 Commands:")
    print("  • Type 'demo' to see a quick suggestion demo")
    print("  • Type 'quit', 'exit', or 'bye' to end the chat")
    print("  • Ask me anything travel-related!")
    print()
    print("-" * 60)

def simulate_backend_event(ui, user_id):
    """Simulate a backend suggestion for demonstration"""
    print("\n🎬 Demo: Simulating a backend event...")
    
    # Create a weather suggestion
    weather_suggestion = BackendSuggestion(
        event_type="weather_change",
        message="Heavy rain is forecasted for tomorrow afternoon in your destination.",
        suggestion="Would you like me to suggest indoor activities to replace your outdoor plans?",
        auto_update=False,
        metadata={"demo": True}
    )
    
    response = ui.handle_backend_suggestion(user_id, weather_suggestion)
    print(f"🤖 LiveTripBuddy: {response}")
    print("\n💡 You can now respond with 'yes' or 'no' to this suggestion!")

def main():
    """Main chat interface"""
    display_welcome()
    
    try:
        # Initialize the conversational UI with mock backend
        print("🔄 Starting up LiveTripBuddy...")
        ui = ConversationalUI(use_mock_backend=True)
        
        # Check health
        if not ui.is_healthy():
            print("❌ System is not healthy. Please check your configuration.")
            return
        
        print("✅ LiveTripBuddy is ready to chat!")
        print()
        
        user_id = "interactive_user"
        conversation_count = 0
        
        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = input("👤 You: ").strip()
                
                # Handle empty input
                if not user_input:
                    continue
                
                # Handle quit commands
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("🤖 LiveTripBuddy: Safe travels! Have a wonderful journey! 👋")
                    break
                
                # Handle demo command
                if user_input.lower() == 'demo':
                    simulate_backend_event(ui, user_id)
                    continue
                
                # Process the message through the conversational UI
                response = ui.process_message(user_id, user_input)
                print(f"🤖 LiveTripBuddy: {response}")
                
                conversation_count += 1
                
                # Show demo suggestion after a few exchanges
                if conversation_count == 3:
                    print("\n" + "-" * 40)
                    print("💡 Tip: Type 'demo' to see how I handle backend suggestions!")
                    print("-" * 40)
                
            except KeyboardInterrupt:
                print("\n🤖 LiveTripBuddy: Goodbye! Feel free to chat with me anytime! 👋")
                break
            except Exception as e:
                print(f"❌ Oops! Something went wrong: {str(e)}")
                print("🤖 LiveTripBuddy: Let's try that again!")
                continue
    
    except Exception as e:
        print(f"❌ Failed to start LiveTripBuddy: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure you have all dependencies installed: pip install -r requirements.txt")
        print("2. Check that your GEMINI_API_KEY is set in the .env file")
        print("3. Verify your internet connection")

if __name__ == "__main__":
    main()