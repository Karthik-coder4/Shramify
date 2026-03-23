"""
Seed script - inserts 5 demo workers with profile pictures into MongoDB
"""
import os, urllib.request
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from bson.objectid import ObjectId

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["shramify"]
users = db["users"]

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

WORKERS = [
    {
        "name": "Ravi Kumar",
        "email": "ravi.kumar@demo.com",
        "phone": "9876543210",
        "location": "Bangalore, Karnataka",
        "worker_type": "informal",
        "informal_kind": "Electrician",
        "bio": "10+ years experience in residential and commercial electrical work. Licensed electrician.",
        "services": [
            {"type": "Electrical Wiring", "price": 500, "desc": "Full home wiring and repairs"},
            {"type": "Fan Installation", "price": 200, "desc": "Ceiling and wall fan fitting"},
        ],
        "date_of_birth": datetime(1988, 4, 15),
        "age": 36,
        "portrait": "https://randomuser.me/api/portraits/men/32.jpg",
    },
    {
        "name": "Suresh Plumber",
        "email": "suresh.plumber@demo.com",
        "phone": "9876543211",
        "location": "Hyderabad, Telangana",
        "worker_type": "informal",
        "informal_kind": "Plumber",
        "bio": "Expert plumber with 8 years experience. Handles leaks, pipe fitting, bathroom work.",
        "services": [
            {"type": "Pipe Repair", "price": 300, "desc": "Fix leaks and broken pipes"},
            {"type": "Bathroom Fitting", "price": 800, "desc": "Complete bathroom plumbing setup"},
        ],
        "date_of_birth": datetime(1990, 7, 22),
        "age": 34,
        "portrait": "https://randomuser.me/api/portraits/men/45.jpg",
    },
    {
        "name": "Meena Devi",
        "email": "meena.devi@demo.com",
        "phone": "9876543212",
        "location": "Chennai, Tamil Nadu",
        "worker_type": "informal",
        "informal_kind": "Maid",
        "bio": "Reliable and trustworthy house cleaning professional. 6 years experience.",
        "services": [
            {"type": "House Cleaning", "price": 400, "desc": "Full home deep cleaning"},
            {"type": "Cooking", "price": 350, "desc": "Daily meal preparation"},
        ],
        "date_of_birth": datetime(1992, 1, 10),
        "age": 32,
        "portrait": "https://randomuser.me/api/portraits/women/44.jpg",
    },
    {
        "name": "Arjun Carpenter",
        "email": "arjun.carpenter@demo.com",
        "phone": "9876543213",
        "location": "Pune, Maharashtra",
        "worker_type": "informal",
        "informal_kind": "Carpenter",
        "bio": "Skilled carpenter specializing in furniture repair, custom woodwork and door fitting.",
        "services": [
            {"type": "Furniture Repair", "price": 600, "desc": "Fix and restore furniture"},
            {"type": "Door/Window Fitting", "price": 700, "desc": "Install and repair doors and windows"},
        ],
        "date_of_birth": datetime(1985, 11, 5),
        "age": 39,
        "portrait": "https://randomuser.me/api/portraits/men/67.jpg",
    },
    {
        "name": "Lakshmi Painter",
        "email": "lakshmi.painter@demo.com",
        "phone": "9876543214",
        "location": "Delhi, NCR",
        "worker_type": "informal",
        "informal_kind": "Painter",
        "bio": "Professional painter with 12 years experience in interior and exterior painting.",
        "services": [
            {"type": "Interior Painting", "price": 1500, "desc": "Full room interior painting"},
            {"type": "Exterior Painting", "price": 2000, "desc": "Exterior wall painting and waterproofing"},
        ],
        "date_of_birth": datetime(1983, 6, 18),
        "age": 41,
        "portrait": "https://randomuser.me/api/portraits/women/68.jpg",
    },
]

inserted = 0
skipped = 0

for w in WORKERS:
    if users.find_one({"email": w["email"]}):
        print(f"⚠  Skipping {w['name']} — already exists")
        skipped += 1
        continue

    # Download profile picture
    img_filename = f"demo_{w['phone']}_profile.jpg"
    img_path = os.path.join(UPLOAD_FOLDER, img_filename)
    try:
        urllib.request.urlretrieve(w["portrait"], img_path)
        profile_image = f"static/uploads/{img_filename}"
        print(f"✓  Downloaded photo for {w['name']}")
    except Exception as e:
        profile_image = ""
        print(f"⚠  Could not download photo for {w['name']}: {e}")

    doc = {
        "role": "worker",
        "name": w["name"],
        "email": w["email"],
        "password": generate_password_hash("Worker123"),
        "phone": w["phone"],
        "location": w["location"],
        "worker_type": w["worker_type"],
        "informal_kind": w["informal_kind"],
        "bio": w["bio"],
        "services": w["services"],
        "date_of_birth": w["date_of_birth"],
        "age": w["age"],
        "profile_image": profile_image,
        "verified": True,
        "id_number": "",
        "created_at": datetime.utcnow(),
    }

    users.insert_one(doc)
    print(f"✓  Inserted worker: {w['name']}")
    inserted += 1

print(f"\nDone. {inserted} workers inserted, {skipped} skipped.")
print("Login password for all demo workers: Worker123")
