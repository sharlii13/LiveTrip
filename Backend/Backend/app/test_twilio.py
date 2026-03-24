# test_twilio.py
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

# Your Twilio credentials
account_sid = "ACd632bd18433d59c00a3e7339ad0fb0b3"
auth_token = "fddd72cd1f8193f78f75980095e5fd2b"

def get_twilio_number():
    """Get your Twilio trial number"""
    try:
        client = Client(account_sid, auth_token)
        
        # Get your Twilio phone numbers
        phone_numbers = client.incoming_phone_numbers.list(limit=5)
        
        if phone_numbers:
            twilio_number = phone_numbers[0].phone_number
            print(f"✅ Found your Twilio number: {twilio_number}")
            return twilio_number
        else:
            print("❌ No Twilio phone numbers found")
            print("Go to: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")
            return None
            
    except Exception as e:
        print(f"❌ Error getting Twilio number: {e}")
        return None

def test_sms(from_number, to_number):
    """Test SMS sending"""
    try:
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body="🚨 TEST: TravelBuddy SOS system is working! This is a test emergency alert from your hackathon project.",
            from_=from_number,
            to=to_number
        )
        
        print("✅ SMS sent successfully!")
        print(f"Message SID: {message.sid}")
        print(f"Status: {message.status}")
        print(f"From: {from_number}")
        print(f"To: {to_number}")
        return True
        
    except Exception as e:
        print(f"❌ SMS failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure your phone number is verified in Twilio")
        print("2. Check phone number format: +919876543210")
        print("3. Verify Twilio account has credit")
        return False

if __name__ == "__main__":
    print("🧪 Testing Twilio SOS System...")
    print("="*50)
    
    # Step 1: Get your Twilio number
    twilio_number = get_twilio_number()
    
    if twilio_number:
        # Step 2: Test SMS (replace with YOUR phone number)
        your_phone = input("Enter your phone number (format: +919876543210): ")
        
        if your_phone:
            test_sms(twilio_number, your_phone)
        else:
            print("❌ Please provide your phone number")
    else:
        print("❌ Cannot test without Twilio phone number")
