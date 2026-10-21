"""Starter data: well-known destinations and demo partner offers. Runs only on empty tables."""
import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import Destination, Offer

DESTINATIONS = [
    ("dest1", "Hawa Mahal", "Jaipur", "attraction", 26.9239, 75.8267, "$",
     "The 'Palace of Winds', a five-storey pink sandstone facade with 953 small windows built in 1799 so royal women "
     "could watch street life unseen.", "Jaipur's iconic honeycomb palace facade.", "9:00 AM – 4:30 PM",
     ["Heritage", "Photography", "Architecture"]),
    ("dest2", "Amber Fort", "Jaipur", "attraction", 26.9855, 75.8513, "$$",
     "A hilltop fort-palace of red sandstone and marble overlooking Maota Lake, known for the mirrored Sheesh Mahal.",
     "Hilltop fort with the famous mirror palace.", "8:00 AM – 5:30 PM", ["Heritage", "Fort", "Views"]),
    ("dest3", "Baga Beach", "Goa", "experience", 15.5553, 73.7517, "$$",
     "One of North Goa's liveliest beaches, with water sports by day and beach shacks and music by night.",
     "Lively North Goa beach with water sports.", "Open 24 hours", ["Beach", "Water sports", "Nightlife"]),
    ("dest4", "Fort Aguada", "Goa", "attraction", 15.4923, 73.7735, "$",
     "A 17th-century Portuguese fort and lighthouse at the mouth of the Mandovi river with views over the Arabian Sea.",
     "Portuguese fort and lighthouse above the sea.", "9:30 AM – 6:00 PM", ["Heritage", "Views", "Photography"]),
    ("dest5", "Shaniwar Wada", "Pune", "attraction", 18.5195, 73.8553, "$",
     "The 18th-century seat of the Peshwas of the Maratha Empire, with massive gates and an evening light-and-sound show.",
     "Historic Maratha palace fortification.", "8:00 AM – 6:30 PM", ["Heritage", "History", "Light show"]),
    ("dest6", "Gateway of India", "Mumbai", "attraction", 18.9220, 72.8347, "$",
     "A basalt arch on the Mumbai waterfront completed in 1924, the starting point for ferries to Elephanta Caves.",
     "Mumbai's waterfront arch monument.", "Open 24 hours", ["Monument", "Waterfront", "Ferries"]),
    ("dest7", "Taj Mahal", "Agra", "attraction", 27.1751, 78.0421, "$$",
     "The white marble mausoleum built by Shah Jahan for Mumtaz Mahal, a UNESCO World Heritage Site. Closed on Fridays.",
     "The world-famous white marble mausoleum.", "6:00 AM – 6:30 PM (closed Fridays)", ["UNESCO", "Heritage", "Sunrise"]),
    ("dest8", "Mysore Palace", "Mysuru", "attraction", 12.3052, 76.6552, "$",
     "The official residence of the Wadiyar dynasty, lit by nearly 100,000 bulbs on Sunday evenings and during Dasara.",
     "Grand royal palace famous for its illuminations.", "10:00 AM – 5:30 PM", ["Heritage", "Architecture", "Festivals"]),
    ("dest9", "Dashashwamedh Ghat", "Varanasi", "experience", 25.3069, 83.0104, "$",
     "The main ghat on the Ganges in Varanasi, best known for the evening Ganga Aarti ceremony.",
     "Riverside ghat with the evening Ganga Aarti.", "Open 24 hours", ["Spiritual", "Culture", "Boat rides"]),
    ("dest10", "City Palace", "Udaipur", "attraction", 24.5764, 73.6835, "$$",
     "A sprawling palace complex on the banks of Lake Pichola blending Rajasthani and Mughal architecture.",
     "Lakeside palace complex in the City of Lakes.", "9:00 AM – 5:30 PM", ["Heritage", "Lake views", "Museum"]),
    ("dest11", "Tea Gardens of Munnar", "Munnar", "experience", 10.0889, 77.0595, "$",
     "Rolling tea estates in the Western Ghats with plantation walks, a tea museum and misty viewpoints.",
     "Misty hill-station tea estates.", "8:00 AM – 5:00 PM", ["Nature", "Hiking", "Tea tasting"]),
    ("dest12", "Dal Lake Shikara Ride", "Srinagar", "experience", 34.1100, 74.8650, "$$",
     "Gliding across Dal Lake in a wooden shikara past houseboats, floating gardens and vegetable markets.",
     "Shikara boat ride on Srinagar's Dal Lake.", "6:00 AM – 7:00 PM", ["Lake", "Boat ride", "Photography"]),
]

OFFERS = [
    ("Chai Corner (demo partner)", "10% off any order", "Show the code at the counter.", 100),
    ("Thali House (demo partner)", "Free dessert with a vegetarian thali", "One per visit.", 250),
    ("City Heritage Walks (demo partner)", "20% off a guided heritage walk", "Book a day ahead.", 400),
    ("Lakeside Café (demo partner)", "Coffee and snack combo", "Valid on weekdays.", 600),
]


def seed(db: Session) -> None:
    if not db.query(Destination).first():
        for (did, name, city, cat, lat, lng, price, desc, short, hours, features) in DESTINATIONS:
            db.add(Destination(id=did, name=name, location=city, country="India", category=cat, description=desc,
                               short_description=short, images="[]", price_range=price, opening_hours=hours,
                               address=f"{name}, {city}, India", features=json.dumps(features), lat=lat, lng=lng))
    if not db.query(Offer).first():
        expires = (date.today() + timedelta(days=365)).isoformat()
        for business, title, desc, cost in OFFERS:
            db.add(Offer(business_name=business, title=title, description=desc, cost_points=cost,
                         per_user_limit=1, total_limit=500, expires_on=expires))
    db.commit()
