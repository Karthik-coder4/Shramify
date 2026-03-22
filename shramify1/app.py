from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import os
import re

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, will use environment variables as-is
    pass
import smtplib
import ssl
from twilio.rest import Client as TwilioClient
try:
    import razorpay
except Exception:
    razorpay = None
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
try:
    import pytesseract  # OCR engine wrapper (requires Tesseract installed)
    from PIL import Image
    # Set Tesseract path for Windows - try multiple common locations
    if os.name == 'nt':  # Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe',
        ]
        tesseract_found = False
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                tesseract_found = True
                break
        if not tesseract_found:
            # Tesseract not installed, disable OCR
            pytesseract = None
            Image = None
except Exception:
    pytesseract = None
    Image = None

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "749707430629-imbdvmtvc0rj7ghpikhodvsq5lloa93e.apps.googleusercontent.com")
MAPS_API_KEY = os.getenv("MAPS_API_KEY", "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567")

@app.context_processor
def inject_globals():
    return {
        "google_client_id": GOOGLE_CLIENT_ID,
        "maps_api_key": MAPS_API_KEY,
    }

# File uploads config
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH_MB', '16')) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in (filename or "") and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Aadhaar helpers
# Verhoeff checksum implementation used by Aadhaar numbers
_verhoeff_d = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_verhoeff_p = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8]
]
_verhoeff_inv = [0,4,3,2,1,5,6,7,8,9]

def verhoeff_valid(num: str) -> bool:
    if not (isinstance(num, str) and num.isdigit() and len(num) == 12):
        return False
    c = 0
    # process from right to left
    for i, ch in enumerate(reversed(num)):
        c = _verhoeff_d[c][_verhoeff_p[(i % 8)][int(ch)]]
    return c == 0

def ocr_extract_text(img_path: str) -> str:
    """Extract text from image using OCR with preprocessing for better accuracy"""
    if not (pytesseract and Image):
        return ""
    try:
        # Open and preprocess image
        img = Image.open(img_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if image is too small (improves OCR accuracy)
        width, height = img.size
        if width < 800:
            scale = 800 / width
            new_size = (int(width * scale), int(height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Extract text with custom config for better number recognition
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        
        return text or ""
    except Exception as e:
        # Log error but don't crash
        print(f"OCR Error: {e}")
        return ""

def extract_aadhaar_from_text(text: str) -> str:
    if not text:
        return ""
    # common formats: 1234 5678 9012 or 1234-5678-9012 or continuous
    digits = re.findall(r"\d", text)
    candidates = []
    # windowed 12-digit sequences
    joined = "".join(digits)
    for i in range(0, max(0, len(joined) - 11)):
        cand = joined[i:i+12]
        if len(cand) == 12:
            candidates.append(cand)
    # also parse grouped patterns directly
    for m in re.findall(r"(\d{4}[\s-]?\d{4}[\s-]?\d{4})", text):
        candidates.append(re.sub(r"[^0-9]", "", m))
    # unique preserve order
    seen = set()
    ordered = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    for c in ordered:
        if verhoeff_valid(c):
            return c
    return ""

def extract_dob_from_aadhaar_text(text: str) -> datetime:
    """Extract date of birth from Aadhaar OCR text"""
    if not text:
        return None
    
    # Common date patterns in Aadhaar cards
    date_patterns = [
        # DD/MM/YYYY format
        r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',
        # DD-MM-YYYY format
        r'\b(\d{1,2})\-(\d{1,2})\-(\d{4})\b',
        # YYYY/MM/DD format (less common)
        r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',
        # DD.MM.YYYY format
        r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b',
    ]
    
    # Look for "DOB", "Date of Birth", "Birth" keywords near dates
    dob_keywords = [
        r'(?i)(?:dob|date\s*of\s*birth|birth|born)[\s:]*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})',
        r'(?i)(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4})[\s]*(?:dob|date\s*of\s*birth|birth)',
    ]
    
    # First try to find dates near DOB keywords
    for pattern in dob_keywords:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                # Parse the date string
                date_str = match if isinstance(match, str) else match[0]
                # Try different date formats
                for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y/%m/%d', '%Y-%m-%d']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        # Validate the date is reasonable (between 1900 and current year - 18)
                        current_year = datetime.now().year
                        if 1900 <= parsed_date.year <= current_year - 18:
                            return parsed_date
                    except ValueError:
                        continue
            except Exception:
                continue
    
    # If no DOB keyword found, look for all dates and pick the most likely one
    all_dates = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match) == 3:
                    # Determine if it's DD/MM/YYYY or YYYY/MM/DD based on first number
                    if int(match[0]) > 31:  # Likely YYYY/MM/DD
                        year, month, day = int(match[0]), int(match[1]), int(match[2])
                    else:  # Likely DD/MM/YYYY
                        day, month, year = int(match[0]), int(match[1]), int(match[2])
                    
                    # Validate date components
                    if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= datetime.now().year - 18:
                        parsed_date = datetime(year, month, day)
                        all_dates.append(parsed_date)
            except (ValueError, IndexError):
                continue
    
    # Return the most reasonable date (oldest, as it's likely to be DOB)
    if all_dates:
        return min(all_dates)
    
    return None

def extract_mobile_from_aadhaar_text(text: str) -> str:
    """Extract mobile number from Aadhaar OCR text"""
    if not text:
        return ""
    
    # Common mobile number patterns in Aadhaar cards
    mobile_patterns = [
        # 10-digit mobile numbers with various separators
        r'\b([6-9]\d{9})\b',  # Standard Indian mobile format
        r'\b([6-9][\d\s\-\.]{8,12}\d)\b',  # With flexible separators
        r'\b(\+91[\s\-]?[6-9][\d\s\-\.]{8,12}\d)\b',  # With country code +91
        r'\b(91[\s\-]?[6-9][\d\s\-\.]{8,12}\d)\b',  # With country code 91
    ]
    
    # Look for "Mobile", "Phone", "Contact" keywords near numbers (with flexible spacing/separators)
    mobile_keywords = [
        r'(?i)(?:mobile|phone|contact|mob)[\s:]*([6-9][\d\s\-\.]{8,12}\d)',
        r'(?i)([6-9][\d\s\-\.]{8,12}\d)[\s]*(?:mobile|phone|contact|mob)',
    ]
    
    # First try to find numbers near mobile keywords
    for pattern in mobile_keywords:
        matches = re.findall(pattern, text)
        for match in matches:
            mobile_str = re.sub(r'[^\d]', '', match)  # Remove non-digits
            if len(mobile_str) == 10 and mobile_str[0] in '6789':
                return mobile_str
    
    # If no keyword found, look for all mobile patterns
    for pattern in mobile_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            mobile_str = re.sub(r'[^\d]', '', match)  # Remove non-digits and country code
            if mobile_str.startswith('91') and len(mobile_str) == 12:
                mobile_str = mobile_str[2:]  # Remove country code
            if len(mobile_str) == 10 and mobile_str[0] in '6789':
                return mobile_str
    
    return ""

def compare_dates(date1: datetime, date2: datetime) -> bool:
    """Compare two dates ignoring time component"""
    if not date1 or not date2:
        return False
    return date1.date() == date2.date()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["shramify"]

users = db["users"]
requests_col = db["service_requests"]
reviews = db["reviews"]

# Helpers

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return users.find_one({"_id": ObjectId(uid)})


def login_required(role=None):
    def decorator(fn):
        from functools import wraps
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))
            if role and user.get("role") != role:
                flash("Unauthorized.", "danger")
                return redirect(url_for("index"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Razorpay client (optional)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
rz_client = None

# Check if Razorpay is properly configured
def is_razorpay_configured():
    return (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and 
            not RAZORPAY_KEY_ID.startswith("your_") and 
            not RAZORPAY_KEY_SECRET.startswith("your_") and
            razorpay is not None)

if is_razorpay_configured():
    try:
        rz_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        print("✓ Razorpay client initialized successfully")
    except Exception as e:
        print(f"✗ Razorpay client initialization failed: {e}")
        rz_client = None
else:
    print("⚠️ Razorpay not configured - online payments disabled")


@app.route("/")
def index():
    # Landing page (Get Started)
    return render_template("get_started.html", user=current_user())


@app.route("/map-test")
def map_test():
    # Test page for Google Maps debugging
    return render_template("map_test.html")


@app.route("/home")
def home():
    user = current_user()
    # Display featured workers (top rated)
    pipeline = [
        {"$match": {"role": "worker"}},
        {"$lookup": {"from": "reviews", "localField": "_id", "foreignField": "worker_id", "as": "revs"}},
        {"$addFields": {"avg_rating": {"$cond": [{"$gt": [{"$size": "$revs"}, 0]}, {"$avg": "$revs.rating"}, None]}}},
        {"$sort": {"avg_rating": -1}},
        {"$limit": 6},
        {"$project": {"password": 0, "revs": 0}}
    ]
    featured = list(users.aggregate(pipeline))
    return render_template("index.html", user=user, featured=featured)


# Auth
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role = (request.form.get("role") or "").strip()
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "")
        location = (request.form.get("location") or "").strip()
        phone_raw = (request.form.get("phone") or "").strip()
        phone = re.sub(r"\D+", "", phone_raw)
        worker_type = (request.form.get("worker_type") or "").strip().lower()
        informal_kind = (request.form.get("informal_kind") or "").strip()
        date_of_birth_str = (request.form.get("date_of_birth") or "").strip()

        # Basic email and phone validation
        email_ok = re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None
        phone_ok = phone.isdigit() and 10 <= len(phone) <= 15

        if not email_ok:
            flash("Please enter a valid email.", "warning")
            return redirect(url_for("register"))
        if not phone_ok:
            flash("Please enter a valid phone number (10-15 digits).", "warning")
            return redirect(url_for("register"))

        # Name should contain only alphabetic characters and spaces
        if not re.match(r"^[A-Za-z ]+$", name):
            flash("Name should contain only letters and spaces.", "warning")
            return redirect(url_for("register"))

        # Password must be alphanumeric and contain at least one letter and one digit
        if len(password) < 6 or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$", password):
            flash("Password must be at least 6 characters and contain both letters and numbers.", "warning")
            return redirect(url_for("register"))

        # Age validation for workers
        date_of_birth = None
        age = None
        if role == "worker":
            if not date_of_birth_str:
                flash("Date of birth is required for workers.", "warning")
                return redirect(url_for("register"))
            
            try:
                date_of_birth = datetime.strptime(date_of_birth_str, "%Y-%m-%d")
                today = datetime.utcnow()
                age = today.year - date_of_birth.year
                # Adjust age if birthday hasn't occurred this year
                if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
                    age -= 1
                
                if age < 18:
                    flash("You must be at least 18 years old to register as a worker.", "danger")
                    return redirect(url_for("register"))
            except ValueError:
                flash("Invalid date of birth format.", "warning")
                return redirect(url_for("register"))

        if users.find_one({"email": email}):
            flash("Email already registered.", "warning")
            return redirect(url_for("register"))
        
        if users.find_one({"phone": phone}):
            flash("Mobile number already registered.", "warning")
            return redirect(url_for("register"))

        user_doc = {
            "role": role,
            "name": name,
            "email": email,
            "password": generate_password_hash(password),
            "location": location,
            "phone": phone,
            # Common fields for both workers and customers
            "services": [],               # list of {type, price, desc}
            "bio": "",
            "verified": False,
            "id_number": "",
            "created_at": datetime.utcnow()
        }
        if role == "worker":
            user_doc.update({
                "worker_type": worker_type or "informal",
                "informal_kind": informal_kind if (worker_type == "informal") else "",
                "date_of_birth": date_of_birth,
                "age": age
            })
        users.insert_one(user_doc)
        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in, go home
    if request.method == "GET" and current_user():
        return redirect(url_for("home"))
    if request.method == "POST":
        login_input = (request.form.get("email") or "").strip().lower()
        password = (request.form.get("password") or "")
        
        # Check if input is email or mobile number
        user = None
        if "@" in login_input:
            # Email login
            user = users.find_one({"email": login_input})
        else:
            # Mobile number login - clean the input
            mobile_input = re.sub(r"[^0-9]", "", login_input)
            if len(mobile_input) == 10 and mobile_input[0] in '6789':
                user = users.find_one({"phone": mobile_input})
        
        ok = False
        if user:
            pwd_hash = user.get("password") or ""
            try:
                if pwd_hash and check_password_hash(pwd_hash, password):
                    ok = True
            except Exception:
                ok = False
        if ok:
            session["user_id"] = str(user["_id"])  # store as string
            flash("Welcome back!", "success")
            return redirect(url_for("home"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)




@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))


@app.route("/auth/google", methods=["POST"])
def auth_google():
    cred = None
    if request.is_json:
        body = request.get_json(silent=True) or {}
        cred = body.get("credential")
    if not cred:
        cred = request.form.get("credential")
    if not cred:
        return jsonify({"ok": False, "error": "missing_credential"}), 400
    try:
        req = google_requests.Request()
        idinfo = google_id_token.verify_oauth2_token(cred, req, GOOGLE_CLIENT_ID)
        email = (idinfo.get("email") or "").lower().strip()
        name = (idinfo.get("name") or "").strip() or email.split("@")[0]
        if not email:
            return jsonify({"ok": False, "error": "no_email"}), 400
        user = users.find_one({"email": email})
        if not user:
            doc = {
                "role": "customer",
                "name": name,
                "email": email,
                "password": "",
                "location": "",
                "phone": "",
                "services": [],
                "bio": "",
                "verified": False,
                "id_number": "",
                "profile_incomplete": True,  # Flag for Google users without mobile
                "created_at": datetime.utcnow()
            }
            ins = users.insert_one(doc)
            user = users.find_one({"_id": ins.inserted_id})
        session["user_id"] = str(user["_id"])
        
        # Check if user needs to complete profile (no mobile number)
        if not user.get("phone"):
            return jsonify({"ok": True, "redirect": "/complete-profile"})
        
        return jsonify({"ok": True})
    except Exception:
        return jsonify({"ok": False, "error": "invalid_token"}), 401


# Email helper and password reset (OTP)
def send_email(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    from_addr = os.getenv("SMTP_FROM", user or "")
    if not from_addr:
        return False
    msg = f"From: {from_addr}\r\nTo: {to_email}\r\nSubject: {subject}\r\n\r\n{body}"
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to_email], msg)
        return True
    except Exception:
        return False


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        user = users.find_one({"email": email})
        if user:
            from random import randint
            otp = f"{randint(100000, 999999)}"
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            users.update_one({"_id": user["_id"]}, {"$set": {"reset_otp": otp, "reset_expires": expires_at}})
            subj = "Your password reset code"
            body = f"Your OTP is {otp}. It expires in 10 minutes."
            send_email(email, subj, body)
        flash("If the email exists, an OTP has been sent.", "info")
        return redirect(url_for("reset_password", email=email))
    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        otp = (request.form.get("otp") or "").strip()
        new_password = (request.form.get("password") or "")
        confirm_password = (request.form.get("confirm_password") or "")
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("reset_password", email=email))

        # Enforce same alphanumeric password rules on reset
        if len(new_password) < 6 or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$", new_password):
            flash("Password must be at least 6 characters and contain both letters and numbers.", "warning")
            return redirect(url_for("reset_password", email=email))
        user = users.find_one({"email": email})
        ok = False
        if user:
            u_otp = (user.get("reset_otp") or "").strip()
            exp = user.get("reset_expires")
            if u_otp and otp == u_otp and isinstance(exp, datetime) and datetime.utcnow() <= exp:
                ok = True
        if not ok:
            flash("Invalid or expired OTP.", "danger")
            return redirect(url_for("reset_password", email=email))
        users.update_one({"_id": user["_id"]}, {"$set": {"password": generate_password_hash(new_password)}, "$unset": {"reset_otp": "", "reset_expires": ""}})
        flash("Password has been reset. Please login.", "success")
        return redirect(url_for("login"))
    # GET
    prefill_email = (request.args.get("email") or "").strip().lower()
    return render_template("reset_password.html", email=prefill_email)


# SMS helper (Twilio) and phone-based password reset (OTP)
def normalize_phone_e164(phone_raw: str) -> str:
    digits = re.sub(r"\D+", "", phone_raw or "")
    if not digits:
        return ""
    if phone_raw.strip().startswith("+"):
        return "+" + digits
    default_cc = os.getenv("DEFAULT_COUNTRY_CODE", "+91")
    return f"{default_cc}{digits}"


def send_sms(to_phone: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_phone = os.getenv("TWILIO_FROM") or os.getenv("TWILIO_PHONE_NUMBER")
    
    # Check if Twilio is configured
    if not (sid and token and from_phone):
        print(f"SMS not configured. Missing: SID={bool(sid)}, TOKEN={bool(token)}, FROM={bool(from_phone)}")
        return False
    
    # Check if credentials are placeholder values
    if sid == "your_twilio_account_sid" or token == "your_twilio_auth_token":
        print("SMS not configured - using placeholder credentials")
        return False
        
    try:
        client = TwilioClient(sid, token)
        message = client.messages.create(to=to_phone, from_=from_phone, body=body)
        print(f"SMS sent successfully. Message SID: {message.sid}")
        return True
    except Exception as e:
        print(f"SMS sending failed: {e}")
        return False


@app.route("/forgot-password-sms", methods=["GET", "POST"])
def forgot_password_sms():
    if request.method == "POST":
        phone_raw = (request.form.get("phone") or "").strip()
        phone_e164 = normalize_phone_e164(phone_raw)
        user = users.find_one({"phone": re.sub(r"\D+", "", phone_raw)}) or users.find_one({"phone": phone_e164})
        if user:
            from random import randint
            otp = f"{randint(100000, 999999)}"
            expires_at = datetime.utcnow() + timedelta(minutes=10)
            users.update_one({"_id": user["_id"]}, {"$set": {"reset_otp": otp, "reset_expires": expires_at}})
            body = f"Your Shramify OTP is {otp}. Valid for 10 minutes."
            
            # Check if SMS is configured
            sid = os.getenv("TWILIO_ACCOUNT_SID")
            token = os.getenv("TWILIO_AUTH_TOKEN")
            if not sid or not token or sid == "your_twilio_account_sid" or token == "your_twilio_auth_token":
                flash("SMS service is not configured. Please contact administrator or use email reset instead.", "warning")
                return redirect(url_for("forgot_password"))
            
            # Try sending to e164 number; if stored number is digits-only, fallback
            ok = send_sms(phone_e164, body)
            if not ok:
                try:
                    # Last attempt: use stored phone as-is
                    ok = send_sms(user.get("phone", phone_e164), body)
                except Exception:
                    pass
            
            if ok:
                flash("OTP has been sent to your mobile number via SMS.", "success")
            else:
                flash("Failed to send SMS. Please try again or use email reset.", "danger")
                return redirect(url_for("forgot_password"))
        else:
            flash("If the phone exists, an OTP has been sent via SMS.", "info")
        return redirect(url_for("reset_password_sms"))
    return render_template("forgot_password_sms.html")


@app.route("/reset-password-sms", methods=["GET", "POST"])
def reset_password_sms():
    if request.method == "POST":
        phone_raw = (request.form.get("phone") or "").strip()
        otp = (request.form.get("otp") or "").strip()
        new_password = (request.form.get("password") or "")
        # Users may have phone stored as digits-only; compare on digits
        phone_digits = re.sub(r"\D+", "", phone_raw)
        user = users.find_one({"phone": phone_digits}) or users.find_one({"phone": normalize_phone_e164(phone_raw)})
        ok = False
        if user:
            u_otp = (user.get("reset_otp") or "").strip()
            exp = user.get("reset_expires")
            if u_otp and otp == u_otp and isinstance(exp, datetime) and datetime.utcnow() <= exp:
                ok = True
        if not ok:
            flash("Invalid or expired OTP.", "danger")
            return redirect(url_for("reset_password_sms"))

        # Enforce same alphanumeric password rules on SMS reset
        if len(new_password) < 6 or not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+$", new_password):
            flash("Password must be at least 6 characters and contain both letters and numbers.", "warning")
            return redirect(url_for("reset_password_sms"))
        users.update_one({"_id": user["_id"]}, {"$set": {"password": generate_password_hash(new_password)}, "$unset": {"reset_otp": "", "reset_expires": ""}})
        flash("Password has been reset. Please login.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password_sms.html")


@app.route("/complete-profile", methods=["GET", "POST"])
@login_required()
def complete_profile():
    u = current_user()
    
    # If user already has phone number, redirect to home
    if u.get("phone"):
        return redirect(url_for("home"))
    
    if request.method == "POST":
        phone_raw = (request.form.get("phone") or "").strip()
        location = (request.form.get("location") or "").strip()
        
        # Clean phone number
        phone = re.sub(r"\D+", "", phone_raw)
        
        # Validate phone number
        if not phone or len(phone) != 10 or not phone[0] in '6789':
            flash("Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.", "warning")
            return redirect(url_for("complete_profile"))
        
        # Check if phone number is already registered
        if users.find_one({"phone": phone, "_id": {"$ne": u["_id"]}}):
            flash("This mobile number is already registered with another account.", "warning")
            return redirect(url_for("complete_profile"))
        
        # Update user profile
        updates = {
            "phone": phone,
            "location": location,
            "profile_incomplete": False
        }
        users.update_one({"_id": u["_id"]}, {"$set": updates})
        
        flash("Profile completed successfully! You can now use all features.", "success")
        return redirect(url_for("home"))
    
    return render_template("complete_profile.html", user=u)


# Worker: profile management
@app.route("/worker/profile")
@login_required(role="worker")
def worker_profile():
    user = current_user()
    # Attach average rating
    agg = list(reviews.aggregate([
        {"$match": {"worker_id": user["_id"]}},
        {"$group": {"_id": "$worker_id", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]))
    avg = agg[0]["avg"] if agg else None
    count = agg[0]["count"] if agg else 0
    return render_template("worker_profile.html", user=user, avg=avg, count=count)


@app.route("/worker/profile/edit", methods=["GET", "POST"])
@login_required(role="worker")
def edit_worker_profile():
    user = current_user()
    if request.method == "POST":
        bio = request.form.get("bio", "")
        location = request.form.get("location", "")
        id_number = request.form.get("id_number", "")
        verified = request.form.get("verified") == "on"

        # Services as dynamic list
        types = request.form.getlist("service_type")
        prices = request.form.getlist("service_price")
        descs = request.form.getlist("service_desc")
        services_list = []
        for t, p, d in zip(types, prices, descs):
            if t.strip():
                try:
                    price_val = float(p)
                except:
                    price_val = 0.0
                services_list.append({"type": t.strip(), "price": price_val, "desc": d.strip()})

        update_fields = {
            "bio": bio,
            "location": location,
            "id_number": id_number,
            "verified": verified,
            "services": services_list
        }

        # Optional profile image upload for workers
        file = request.files.get("profile_image")
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Prefix with user id to reduce collisions
                unique_name = f"{user['_id']}_profile_{filename}"
                save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                try:
                    file.save(save_path)
                    update_fields["profile_image"] = f"{app.config['UPLOAD_FOLDER']}/{unique_name}".replace("\\", "/")
                except Exception:
                    flash("Failed to upload profile picture. Please try again.", "warning")
            else:
                flash("Invalid profile picture format. Allowed: PNG, JPG, JPEG, GIF, WEBP.", "warning")

        users.update_one({"_id": user["_id"]}, {"$set": update_fields})
        flash("Profile updated.", "success")
        return redirect(url_for("worker_profile"))

    return render_template("worker_edit.html", user=user)


# Worker: Aadhaar upload and OCR verification
@app.route("/worker/aadhaar", methods=["GET", "POST"])
@login_required(role="worker")
def worker_aadhaar():
    user = current_user()
    if request.method == "POST":
        action = request.form.get("action", "upload")
        
        # Manual entry option
        if action == "manual":
            manual_number = request.form.get("manual_aadhaar", "").strip()
            manual_dob = request.form.get("manual_dob", "").strip()
            manual_mobile = request.form.get("manual_mobile", "").strip()
            
            # Remove spaces and hyphens from Aadhaar number
            manual_number = re.sub(r"[^0-9]", "", manual_number)
            # Clean mobile number
            manual_mobile = re.sub(r"[^0-9]", "", manual_mobile)
            
            if not manual_number:
                flash("Please enter an Aadhaar number.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            if len(manual_number) != 12:
                flash("Aadhaar number must be exactly 12 digits.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            if not verhoeff_valid(manual_number):
                flash("Invalid Aadhaar number. Please check and try again.", "danger")
                return redirect(url_for("worker_aadhaar"))
            
            if not manual_dob:
                flash("Please enter the date of birth from your Aadhaar card.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            if not manual_mobile:
                flash("Please enter the mobile number from your Aadhaar card.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            if len(manual_mobile) != 10 or not manual_mobile[0] in '6789':
                flash("Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            # Parse manual DOB
            try:
                aadhaar_dob = datetime.strptime(manual_dob, "%Y-%m-%d")
            except ValueError:
                flash("Invalid date format. Please enter date as YYYY-MM-DD.", "warning")
                return redirect(url_for("worker_aadhaar"))
            
            # Compare with registered DOB and mobile
            user_dob = user.get("date_of_birth")
            user_mobile = user.get("phone", "")
            
            if not user_dob:
                flash("No date of birth found in your profile. Please update your profile first.", "warning")
                return redirect(url_for("edit_worker_profile"))
            
            if not user_mobile:
                flash("No mobile number found in your profile. Please update your profile first.", "warning")
                return redirect(url_for("edit_worker_profile"))
            
            # Check if DOBs and mobile numbers match
            dob_matches = compare_dates(user_dob, aadhaar_dob)
            mobile_matches = user_mobile == manual_mobile
            
            if dob_matches and mobile_matches:
                # Both DOB and mobile match - full verification
                updates = {
                    "id_number": manual_number,
                    "aadhaar_number": manual_number,
                    "verified": True,
                    "aadhaar_verified": True,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": manual_mobile,
                    "dob_verified": True,
                    "mobile_verified": True,
                    "verification_method": "manual_entry"
                }
                users.update_one({"_id": user["_id"]}, {"$set": updates})
                flash("✅ Aadhaar verified successfully! Both date of birth and mobile number match your profile.", "success")
            elif dob_matches and not mobile_matches:
                # DOB matches but mobile doesn't
                updates = {
                    "id_number": manual_number,
                    "aadhaar_number": manual_number,
                    "verified": False,
                    "aadhaar_verified": False,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": manual_mobile,
                    "dob_verified": True,
                    "mobile_verified": False,
                    "verification_method": "manual_entry",
                    "verification_error": "Mobile number mismatch"
                }
                users.update_one({"_id": user["_id"]}, {"$set": updates})
                flash(f"⚠️ Partial verification: Date of birth matches but mobile number doesn't. Profile mobile: {user_mobile}, Aadhaar mobile: {manual_mobile}", "warning")
            elif not dob_matches and mobile_matches:
                # Mobile matches but DOB doesn't
                updates = {
                    "id_number": manual_number,
                    "aadhaar_number": manual_number,
                    "verified": False,
                    "aadhaar_verified": False,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": manual_mobile,
                    "dob_verified": False,
                    "mobile_verified": True,
                    "verification_method": "manual_entry",
                    "verification_error": "Date of birth mismatch"
                }
                users.update_one({"_id": user["_id"]}, {"$set": updates})
                user_dob_str = user_dob.strftime("%d/%m/%Y") if user_dob else "Unknown"
                aadhaar_dob_str = aadhaar_dob.strftime("%d/%m/%Y")
                flash(f"⚠️ Partial verification: Mobile number matches but date of birth doesn't. Profile DOB: {user_dob_str}, Aadhaar DOB: {aadhaar_dob_str}", "warning")
            else:
                # Neither matches
                updates = {
                    "id_number": manual_number,
                    "aadhaar_number": manual_number,
                    "verified": False,
                    "aadhaar_verified": False,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": manual_mobile,
                    "dob_verified": False,
                    "mobile_verified": False,
                    "verification_method": "manual_entry",
                    "verification_error": "Both date of birth and mobile number mismatch"
                }
                users.update_one({"_id": user["_id"]}, {"$set": updates})
                user_dob_str = user_dob.strftime("%d/%m/%Y") if user_dob else "Unknown"
                aadhaar_dob_str = aadhaar_dob.strftime("%d/%m/%Y")
                flash(f"❌ Verification failed: Both date of birth and mobile number mismatch. Profile DOB: {user_dob_str}, Aadhaar DOB: {aadhaar_dob_str}, Profile mobile: {user_mobile}, Aadhaar mobile: {manual_mobile}", "danger")
            
            return redirect(url_for("worker_aadhaar"))
        
        # Upload and auto-verify option
        f = request.files.get("aadhaar_image")
        if not f or not f.filename:
            flash("Please select an image.", "warning")
            return redirect(url_for("worker_aadhaar"))
        if not allowed_file(f.filename):
            flash("Unsupported file type. Please upload an image.", "warning")
            return redirect(url_for("worker_aadhaar"))
        fname = secure_filename(f.filename)
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        subdir = os.path.join(app.config['UPLOAD_FOLDER'], 'aadhaar', str(user["_id"]))
        os.makedirs(subdir, exist_ok=True)
        final_name = f"{ts}_{fname}"
        save_path = os.path.join(subdir, final_name)
        try:
            f.save(save_path)
        except Exception:
            flash("Failed to save file.", "danger")
            return redirect(url_for("worker_aadhaar"))

        # OCR extract
        text = ocr_extract_text(save_path)
        number = extract_aadhaar_from_text(text)
        aadhaar_dob = extract_dob_from_aadhaar_text(text)
        aadhaar_mobile = extract_mobile_from_aadhaar_text(text)
        rel_path = os.path.join('uploads', 'aadhaar', str(user["_id"]), final_name).replace("\\", "/")

        updates = {
            "aadhaar_image": rel_path,
            "aadhaar_ocr_text": text[:5000] if text else "",
            "verification_method": "ocr_upload"
        }
        
        if number and aadhaar_dob and aadhaar_mobile:
            # All three extracted: Aadhaar number, DOB, and mobile
            user_dob = user.get("date_of_birth")
            user_mobile = user.get("phone", "")
            
            if not user_dob:
                updates.update({
                    "id_number": number,
                    "aadhaar_number": number,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": aadhaar_mobile,
                    "verified": False,
                    "aadhaar_verified": False,
                    "dob_verified": False,
                    "mobile_verified": False,
                    "verification_error": "No profile DOB to compare"
                })
                flash("❌ Aadhaar details extracted but no date of birth in your profile to compare. Please update your profile first.", "warning")
            elif not user_mobile:
                updates.update({
                    "id_number": number,
                    "aadhaar_number": number,
                    "aadhaar_dob": aadhaar_dob,
                    "aadhaar_mobile": aadhaar_mobile,
                    "verified": False,
                    "aadhaar_verified": False,
                    "dob_verified": False,
                    "mobile_verified": False,
                    "verification_error": "No profile mobile to compare"
                })
                flash("❌ Aadhaar details extracted but no mobile number in your profile to compare. Please update your profile first.", "warning")
            else:
                # Compare DOBs and mobile numbers
                dob_matches = compare_dates(user_dob, aadhaar_dob)
                mobile_matches = user_mobile == aadhaar_mobile
                
                if dob_matches and mobile_matches:
                    # Full verification success
                    updates.update({
                        "id_number": number,
                        "aadhaar_number": number,
                        "aadhaar_dob": aadhaar_dob,
                        "aadhaar_mobile": aadhaar_mobile,
                        "verified": True,
                        "aadhaar_verified": True,
                        "dob_verified": True,
                        "mobile_verified": True,
                    })
                    flash("✅ Aadhaar verified successfully via OCR! Both date of birth and mobile number match your profile.", "success")
                elif dob_matches and not mobile_matches:
                    # DOB matches but mobile doesn't
                    updates.update({
                        "id_number": number,
                        "aadhaar_number": number,
                        "aadhaar_dob": aadhaar_dob,
                        "aadhaar_mobile": aadhaar_mobile,
                        "verified": False,
                        "aadhaar_verified": False,
                        "dob_verified": True,
                        "mobile_verified": False,
                        "verification_error": "Mobile number mismatch"
                    })
                    flash(f"⚠️ Partial verification: Date of birth matches but mobile number doesn't. Profile mobile: {user_mobile}, Aadhaar mobile: {aadhaar_mobile}", "warning")
                elif not dob_matches and mobile_matches:
                    # Mobile matches but DOB doesn't
                    updates.update({
                        "id_number": number,
                        "aadhaar_number": number,
                        "aadhaar_dob": aadhaar_dob,
                        "aadhaar_mobile": aadhaar_mobile,
                        "verified": False,
                        "aadhaar_verified": False,
                        "dob_verified": False,
                        "mobile_verified": True,
                        "verification_error": "Date of birth mismatch"
                    })
                    user_dob_str = user_dob.strftime("%d/%m/%Y") if user_dob else "Unknown"
                    aadhaar_dob_str = aadhaar_dob.strftime("%d/%m/%Y")
                    flash(f"⚠️ Partial verification: Mobile number matches but date of birth doesn't. Profile DOB: {user_dob_str}, Aadhaar DOB: {aadhaar_dob_str}", "warning")
                else:
                    # Neither matches
                    updates.update({
                        "id_number": number,
                        "aadhaar_number": number,
                        "aadhaar_dob": aadhaar_dob,
                        "aadhaar_mobile": aadhaar_mobile,
                        "verified": False,
                        "aadhaar_verified": False,
                        "dob_verified": False,
                        "mobile_verified": False,
                        "verification_error": "Both date of birth and mobile number mismatch"
                    })
                    user_dob_str = user_dob.strftime("%d/%m/%Y") if user_dob else "Unknown"
                    aadhaar_dob_str = aadhaar_dob.strftime("%d/%m/%Y")
                    flash(f"❌ Verification failed: Both date of birth and mobile number mismatch. Profile DOB: {user_dob_str}, Aadhaar DOB: {aadhaar_dob_str}, Profile mobile: {user_mobile}, Aadhaar mobile: {aadhaar_mobile}", "danger")
        elif number and aadhaar_dob and not aadhaar_mobile:
            # Aadhaar number and DOB extracted, but no mobile
            user_dob = user.get("date_of_birth")
            if not user_dob:
                updates.update({
                    "id_number": number,
                    "aadhaar_number": number,
                    "aadhaar_dob": aadhaar_dob,
                    "verified": False,
                    "aadhaar_verified": False,
                    "dob_verified": False,
                    "mobile_verified": False,
                    "verification_error": "No profile DOB to compare and could not extract mobile"
                })
                flash("❌ Aadhaar number extracted but no date of birth in your profile to compare and could not extract mobile number from image.", "warning")
            else:
                dob_matches = compare_dates(user_dob, aadhaar_dob)
                updates.update({
                    "id_number": number,
                    "aadhaar_number": number,
                    "aadhaar_dob": aadhaar_dob,
                    "verified": False,
                    "aadhaar_verified": False,
                    "dob_verified": dob_matches,
                    "mobile_verified": False,
                    "verification_error": "Could not extract mobile number from image"
                })
                if dob_matches:
                    flash("⚠️ Date of birth matches but could not extract mobile number from image. Please use manual entry option or upload a clearer image.", "warning")
                else:
                    user_dob_str = user_dob.strftime("%d/%m/%Y") if user_dob else "Unknown"
                    aadhaar_dob_str = aadhaar_dob.strftime("%d/%m/%Y")
                    flash(f"⚠️ Date of birth mismatch and could not extract mobile number. Profile DOB: {user_dob_str}, Aadhaar DOB: {aadhaar_dob_str}", "warning")
        elif number and not aadhaar_dob:
            # Only Aadhaar number extracted
            updates.update({
                "id_number": number,
                "aadhaar_number": number,
                "verified": False,
                "aadhaar_verified": False,
                "dob_verified": False,
                "mobile_verified": False,
                "verification_error": "Could not extract date of birth or mobile number from image"
            })
            if aadhaar_mobile:
                updates["aadhaar_mobile"] = aadhaar_mobile
                flash("⚠️ Aadhaar number and mobile extracted but could not read date of birth from image. Please use manual entry option or upload a clearer image.", "warning")
            else:
                flash("⚠️ Only Aadhaar number extracted. Could not read date of birth or mobile number from image. Please use manual entry option or upload a clearer image.", "warning")
        elif not number and (aadhaar_dob or aadhaar_mobile):
            # DOB or mobile extracted but no Aadhaar number
            updates.update({
                "verified": False,
                "aadhaar_verified": False,
                "dob_verified": False,
                "mobile_verified": False,
                "verification_error": "Could not extract Aadhaar number from image"
            })
            if aadhaar_dob:
                updates["aadhaar_dob"] = aadhaar_dob
            if aadhaar_mobile:
                updates["aadhaar_mobile"] = aadhaar_mobile
            flash("⚠️ Some details extracted but could not read Aadhaar number from image. Please use manual entry option or upload a clearer image.", "warning")
        else:
            # Nothing extracted
            updates.update({
                "verified": False,
                "aadhaar_verified": False,
                "dob_verified": False,
                "mobile_verified": False,
                "verification_error": "Could not extract Aadhaar number, date of birth, or mobile number from image"
            })
            flash("❌ Could not auto-verify Aadhaar. Please upload a clear image or use manual entry option below.", "warning")

        users.update_one({"_id": user["_id"]}, {"$set": updates})
        return redirect(url_for("worker_aadhaar"))

    # GET
    return render_template("worker_aadhaar.html", user=user)
# General profile page for all users
@app.route("/profile")
@login_required()
def profile():
    user = current_user()
    if user["role"] == "worker":
        return redirect(url_for("worker_profile"))
    else:
        # For customers, show a simple profile or redirect to requests
        return render_template("profile.html", user=user)


# Customer dashboard with nearby workers
@app.route("/customer/dashboard")
@login_required(role="customer")
def customer_dashboard():
    user = current_user()
    # Use Leaflet/OpenStreetMap (free alternative to Google Maps)
    return render_template("customer_dashboard_leaflet.html", user=user)


# API endpoint to find nearby workers
@app.route("/api/nearby-workers")
@login_required(role="customer")
def nearby_workers():
    from math import radians, sin, cos, sqrt, atan2
    
    try:
        customer_lat = float(request.args.get('lat'))
        customer_lng = float(request.args.get('lng'))
        location_name = request.args.get('location', '')
        radius_km = float(request.args.get('radius', 10))  # Default 10km
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400
    
    # Get all workers
    workers = list(db.users.find({"role": "worker"}))
    
    # Calculate distances and filter
    nearby = []
    for worker in workers:
        if not worker.get('location'):
            continue
        
        # For simplicity, we'll use the location string match or geocode
        # In production, store lat/lng in database
        worker_location = worker.get('location', '')
        
        # Get services
        services = ', '.join([s.get('type', '') for s in worker.get('services', [])[:3]])
        
        # Get rating
        reviews = list(db.reviews.find({"worker_id": worker["_id"]}))
        avg_rating = sum(r.get('rating', 0) for r in reviews) / len(reviews) if reviews else None
        rating_str = f"{avg_rating:.1f} ★ ({len(reviews)})" if avg_rating else "No reviews"
        
        # Simple distance estimation (you can enhance with actual geocoding)
        # For now, we'll show all workers and mark distance as "Near you"
        nearby.append({
            "id": str(worker["_id"]),
            "name": worker.get("name", "Unknown"),
            "location": worker_location,
            "distance": "Within 10km",  # Placeholder
            "rating": rating_str,
            "services": services
        })
    
    return jsonify({"workers": nearby})


# Report worker page
@app.route("/worker/<worker_id>/report", methods=["GET", "POST"])
@login_required(role="customer")
def report_worker(worker_id):
    from datetime import datetime
    
    worker = db.users.find_one({"_id": ObjectId(worker_id), "role": "worker"})
    if not worker:
        flash("Worker not found.", "error")
        return redirect(url_for("search"))
    
    user = current_user()
    
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        description = request.form.get("description", "").strip()
        service_request_id = request.form.get("service_request_id", "").strip()
        incident_date = request.form.get("incident_date", "").strip()
        
        if not reason or not description:
            flash("Please provide a reason and description.", "error")
            return redirect(request.url)
        
        # Create report
        report = {
            "customer_id": user["_id"],
            "customer_name": user.get("name", "Unknown"),
            "worker_id": ObjectId(worker_id),
            "worker_name": worker.get("name", "Unknown"),
            "reason": reason,
            "description": description,
            "service_request_id": service_request_id,
            "incident_date": incident_date,
            "status": "pending",  # pending, investigating, resolved, dismissed
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.reports.insert_one(report)
        flash("Report submitted successfully. We will investigate and take appropriate action.", "success")
        return redirect(url_for("view_worker", worker_id=worker_id))
    
    # Get user's previous reports for this worker
    user_reports = list(db.reports.find({
        "customer_id": user["_id"],
        "worker_id": ObjectId(worker_id)
    }).sort("created_at", -1))
    
    from datetime import date
    today = date.today().isoformat()
    
    return render_template("report_worker.html", worker=worker, user_reports=user_reports, today=today)




@app.route("/search")
def search():
    q_type = request.args.get("service_type", "").strip()
    q_loc = request.args.get("location", "").strip()

    filter_q = {"role": "worker"}
    if q_type:
        filter_q["services.type"] = {"$regex": q_type, "$options": "i"}
    if q_loc:
        filter_q["location"] = {"$regex": q_loc, "$options": "i"}

    matches = list(users.find(filter_q, {"password": 0}))

    # Attach average rating quickly
    worker_ids = [w["_id"] for w in matches]
    ratings_map = {}
    if worker_ids:
        for r in reviews.aggregate([
            {"$match": {"worker_id": {"$in": worker_ids}}},
            {"$group": {"_id": "$worker_id", "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]):
            ratings_map[r["_id"]] = {"avg": r["avg"], "count": r["count"]}

    return render_template("search.html", user=current_user(), workers=matches, ratings_map=ratings_map, q_type=q_type, q_loc=q_loc)


@app.route("/api/suggest/services")
def api_suggest_services():
    q = request.args.get("q", "").strip()
    suggestions = set()
    # common fallbacks
    common = [
        "Electrician", "Plumber", "House Cleaning", "Carpenter",
        "Cook", "Gardener", "AC Repair", "Pest Control", "Tiffin Service"
    ]
    for s in common:
        if not q or q.lower() in s.lower():
            suggestions.add(s)
    # fetch from DB services
    try:
        cursor = users.aggregate([
            {"$unwind": "$services"},
            {"$group": {"_id": "$services.type"}},
        ])
        for row in cursor:
            s = row.get("_id")
            if isinstance(s, str) and (not q or q.lower() in s.lower()):
                suggestions.add(s)
    except Exception:
        pass
    out = sorted(list(suggestions), key=lambda x: x.lower())[:10]
    return jsonify(out)


@app.route("/worker/<worker_id>")
def view_worker(worker_id):
    w = users.find_one({"_id": ObjectId(worker_id)}, {"password": 0})
    if not w or w.get("role") != "worker":
        flash("Worker not found.", "warning")
        return redirect(url_for("search"))
    revs = list(reviews.find({"worker_id": w["_id"]}).sort("created_at", -1))
    return render_template("worker_view.html", user=current_user(), w=w, revs=revs)


# Service request flow
@app.route("/request/<worker_id>", methods=["GET", "POST"])
@login_required(role=None)
def request_service(worker_id):
    u = current_user()
    w = users.find_one({"_id": ObjectId(worker_id)})
    if not w or w.get("role") != "worker":
        flash("Worker not found.", "warning")
        return redirect(url_for("search"))

    if request.method == "POST":
        # Prevent booking a worker who already has an active job
        active_statuses = ["accepted", "awaiting_approval", "approved", "paid"]
        existing_active = requests_col.find_one({"worker_id": w["_id"], "status": {"$in": active_statuses}}) or users.find_one({"_id": w["_id"], "busy": True})
        if existing_active:
            flash("This worker is already booked. Please try another worker.", "warning")
            return redirect(url_for("view_worker", worker_id=worker_id))
        details = request.form.get("details")
        date_str = request.form.get("date")
        try:
            date_needed = datetime.fromisoformat(date_str) if date_str else None
        except:
            date_needed = None
        
        # Get customer offer amount
        customer_offer_str = request.form.get("customer_offer", "").strip()
        customer_offer = None
        if customer_offer_str:
            try:
                customer_offer = float(customer_offer_str)
                if customer_offer <= 0:
                    customer_offer = None
            except ValueError:
                customer_offer = None
        # Parse selected services with quantities if present
        items = []
        sel_indices = request.form.getlist("sel")
        if sel_indices:
            total = 0.0
            for idx in sel_indices:
                t = (request.form.get(f"type_{idx}") or "").strip()
                try:
                    p = float(request.form.get(f"price_{idx}") or 0)
                except:
                    p = 0.0
                try:
                    q = int(request.form.get(f"qty_{idx}") or 1)
                except:
                    q = 1
                if t and q > 0:
                    line_total = p * q
                    items.append({"type": t, "price": p, "qty": q, "line_total": line_total})
                    total += line_total
            requested_total = round(total, 2)
        else:
            # Backward compatibility: single select
            service_type = (request.form.get("service_type") or "").strip()
            # Lookup price from worker services
            price_map = {s.get("type"): float(s.get("price") or 0) for s in (w.get("services") or [])}
            p = price_map.get(service_type, 0.0)
            items = [{"type": service_type, "price": p, "qty": 1, "line_total": p}]
            requested_total = round(p, 2)

        doc = {
            "customer_id": u["_id"],
            "worker_id": w["_id"],
            "service_type": ", ".join([it["type"] for it in items]) if items else None,
            "items": items,
            "requested_total": requested_total,
            "customer_offer": customer_offer,  # Customer's offered amount
            "currency": os.getenv("PAYMENT_CURRENCY", "INR"),
            "details": details,
            "date_needed": date_needed,
            "status": "pending",  # pending -> accepted/rejected -> completed/paid
            "photos": [],
            "created_at": datetime.utcnow()
        }
        requests_col.insert_one(doc)
        flash("Request sent to worker.", "success")
        return redirect(url_for("my_requests"))

    return render_template("request_service.html", user=u, w=w)


@app.route("/my/requests")
@login_required()
def my_requests():
    u = current_user()
    if u["role"] == "worker":
        reqs = list(requests_col.find({"worker_id": u["_id"]}).sort("created_at", -1))
    else:
        reqs = list(requests_col.find({"customer_id": u["_id"]}).sort("created_at", -1))
    return render_template("my_requests.html", user=u, reqs=reqs)


@app.route("/request/<rid>/status", methods=["POST"])
@login_required(role="worker")
def update_request_status(rid):
    u = current_user()
    action = request.form.get("action")  # accept/reject/complete
    req_doc = requests_col.find_one({"_id": ObjectId(rid), "worker_id": u["_id"]})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))

    if action == "accept":
        new_status = "accepted"
        try:
            agreed_total = float(request.form.get("agreed_total") or req_doc.get("customer_offer") or req_doc.get("requested_total") or 0)
        except:
            agreed_total = req_doc.get("customer_offer") or req_doc.get("requested_total") or 0
        # Atomically mark worker busy if not already
        busy_res = users.update_one({"_id": u["_id"], "busy": {"$ne": True}}, {"$set": {"busy": True}})
        if not busy_res.matched_count:
            flash("Cannot accept: worker already has an active booking.", "warning")
            return redirect(url_for("my_requests"))
        # Now transition request to accepted; rollback busy if transition fails
        res = requests_col.update_one({"_id": req_doc["_id"], "worker_id": u["_id"], "status": "pending"}, {"$set": {"status": new_status, "agreed_total": round(agreed_total, 2)}})
        if res.matched_count:
            flash("Request accepted.", "success")
        else:
            # rollback busy flag since accept failed
            users.update_one({"_id": u["_id"]}, {"$unset": {"busy": ""}})
            flash("Request no longer pending. Could not accept.", "warning")
        return redirect(url_for("my_requests"))
    elif action == "reject":
        new_status = "rejected"
    elif action == "complete":
        new_status = "awaiting_approval"
    else:
        flash("Invalid action.", "danger")
        return redirect(url_for("my_requests"))

    # Atomic state checks for reject/complete
    if new_status == "rejected":
        res = requests_col.update_one({"_id": req_doc["_id"], "worker_id": u["_id"], "status": "pending"}, {"$set": {"status": new_status}})
    elif new_status == "awaiting_approval":
        res = requests_col.update_one({"_id": req_doc["_id"], "worker_id": u["_id"], "status": "accepted"}, {"$set": {"status": new_status}})
    else:
        res = None

    if res and res.matched_count:
        flash(f"Request {new_status}.", "success")
    else:
        flash("Request is not in a valid state for this action.", "warning")
    return redirect(url_for("my_requests"))


@app.route("/request/<rid>/photos", methods=["POST"])
@login_required(role="worker")
def upload_request_photos(rid):
    u = current_user()
    req_doc = requests_col.find_one({"_id": ObjectId(rid), "worker_id": u["_id"]})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))

    files = request.files.getlist("photos")
    if not files:
        flash("No files selected.", "warning")
        return redirect(url_for("my_requests"))

    saved = []
    subdir = os.path.join(app.config['UPLOAD_FOLDER'], str(rid))
    os.makedirs(subdir, exist_ok=True)

    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            continue
        fname = secure_filename(f.filename)
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        final_name = f"{ts}_{fname}"
        save_path = os.path.join(subdir, final_name)
        try:
            f.save(save_path)
            rel_path = os.path.join('uploads', str(rid), final_name).replace("\\", "/")
            saved.append(rel_path)
        except Exception:
            continue

    if saved:
        requests_col.update_one({"_id": req_doc["_id"]}, {"$push": {"photos": {"$each": saved}}})
        flash(f"Uploaded {len(saved)} photo(s).", "success")
    else:
        flash("No valid photos uploaded.", "warning")
    return redirect(url_for("my_requests"))


@app.route("/request/<rid>/approve", methods=["POST"])
@login_required(role=None)
def approve_request(rid):
    u = current_user()
    req_doc = requests_col.find_one({"_id": ObjectId(rid), "customer_id": current_user()["_id"]})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))
    res = requests_col.update_one({"_id": req_doc["_id"], "customer_id": u["_id"], "status": "awaiting_approval"}, {"$set": {"status": "approved"}})
    if res.matched_count:
        flash("Work approved. You can proceed to payment.", "success")
    else:
        flash("Request is not awaiting approval.", "warning")
    return redirect(url_for("my_requests"))


@app.route("/pay/<rid>", methods=["GET", "POST"])
@login_required(role=None)
def pay_request(rid):
    u = current_user()
    req_doc = requests_col.find_one({"_id": ObjectId(rid)})
    if not req_doc or (u["role"] != "worker" and req_doc.get("customer_id") != u["_id"]) and (u["role"] == "worker" and req_doc.get("worker_id") != u["_id"]):
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))
    if req_doc.get("status") != "approved":
        flash("Payment is only available after customer approval.", "warning")
        return redirect(url_for("my_requests"))

    worker = None
    if req_doc.get("worker_id"):
        worker = users.find_one({"_id": req_doc["worker_id"]}, {"password": 0})

    amt = req_doc.get("agreed_total") or req_doc.get("requested_total") or 0

    if request.method == "GET":
        return render_template("pay.html", user=u, req=req_doc, amount=amt, worker=worker)

    method = (request.form.get("method") or "").lower()
    if method not in ("online", "cash"):
        flash("Please choose a valid payment option.", "warning")
        return redirect(url_for("pay_request", rid=rid))
    if method == "online":
        return redirect(url_for("pay_online", rid=rid))

    # Cash flow: mark as paid by cash
    res = requests_col.update_one({"_id": req_doc["_id"], "status": "approved", "customer_id": req_doc["customer_id"]}, {"$set": {"status": "paid", "paid_at": datetime.utcnow(), "paid_amount": amt, "payment_method": method}})
    if res.matched_count:
        users.update_one({"_id": req_doc["worker_id"]}, {"$unset": {"busy": ""}})
        # Notify customer via email that payment has been received by the worker
        try:
            customer = users.find_one({"_id": req_doc["customer_id"]})
            worker = users.find_one({"_id": req_doc["worker_id"]})
            if customer and customer.get("email"):
                currency = req_doc.get("currency", "INR")
                subject = "Shramify - Payment received confirmation"
                body = (
                    f"Hello {customer.get('name', 'Customer')},\n\n"
                    f"Your payment of {currency} {amt} for your recent service request "
                    f"with worker {worker.get('name', 'Worker')} has been marked as received.\n\n"
                    f"Thank you for using Shramify."
                )
                send_email(customer["email"], subject, body)
        except Exception:
            pass
        flash(f"Cash payment selected. Marked as paid for {req_doc.get('currency','INR')} {amt}.", "info")
    else:
        flash("Payment not processed. The request might already be paid or not approved yet.", "warning")
    return redirect(url_for("my_requests"))


@app.route("/pay/<rid>/online", methods=["GET"]) 
@login_required(role=None)
def pay_online(rid):
    u = current_user()
    req_doc = requests_col.find_one({"_id": ObjectId(rid)})
    worker = None
    if req_doc and req_doc.get("worker_id"):
        worker = users.find_one({"_id": req_doc["worker_id"]}, {"password": 0})

    if not req_doc or req_doc.get("customer_id") != u["_id"]:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))
    if req_doc.get("status") != "approved":
        flash("Payment is only available after approval.", "warning")
        return redirect(url_for("pay_request", rid=rid))
    if not rz_client:
        if not is_razorpay_configured():
            flash("Online payment is not configured. Please contact administrator or use cash payment.", "warning")
        else:
            flash("Online payment service is temporarily unavailable. Please try again or use cash payment.", "warning")
        return redirect(url_for("pay_request", rid=rid))

    amt = int(round((req_doc.get("agreed_total") or req_doc.get("requested_total") or 0) * 100))
    currency = req_doc.get("currency", "INR")
    
    # Validate amount
    if amt <= 0:
        flash("Invalid payment amount.", "danger")
        return redirect(url_for("pay_request", rid=rid))
    
    try:
        order = rz_client.order.create({
            "amount": amt,
            "currency": currency,
            "payment_capture": 1,
            "receipt": str(rid)
        })
        print(f"✓ Razorpay order created: {order.get('id')} for amount ₹{amt/100}")
    except Exception as e:
        print(f"✗ Razorpay order creation failed: {e}")
        flash("Failed to create online payment order. Please try again or use cash payment.", "danger")
        return redirect(url_for("pay_request", rid=rid))

    requests_col.update_one({"_id": req_doc["_id"]}, {"$set": {"rz_order_id": order.get("id")}})
    return render_template("pay_online.html", user=u, req=req_doc, amount=amt, currency=currency, rz_key_id=RAZORPAY_KEY_ID, order=order, worker=worker)


@app.route("/payment/verify", methods=["POST"]) 
@login_required(role=None)
def payment_verify():
    if not rz_client:
        flash("Online payment is not configured.", "warning")
        return redirect(url_for("my_requests"))
    rid = request.form.get("rid")
    order_id = request.form.get("razorpay_order_id")
    payment_id = request.form.get("razorpay_payment_id")
    signature = request.form.get("razorpay_signature")
    if not (rid and order_id and payment_id and signature):
        flash("Invalid payment verification payload.", "danger")
        return redirect(url_for("my_requests"))
    try:
        rz_client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
    except Exception:
        flash("Payment verification failed.", "danger")
        return redirect(url_for("my_requests"))

    req_doc = requests_col.find_one({"_id": ObjectId(rid)})
    if not req_doc:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))
    amt_minor = int(round((req_doc.get("agreed_total") or req_doc.get("requested_total") or 0) * 100))
    res = requests_col.update_one({"_id": req_doc["_id"], "status": "approved", "rz_order_id": order_id}, {"$set": {"status": "paid", "paid_at": datetime.utcnow(), "paid_amount": amt_minor/100.0, "payment_method": "online", "rz_payment_id": payment_id}})
    if res.matched_count:
        users.update_one({"_id": req_doc["worker_id"]}, {"$unset": {"busy": ""}})
        # Notify customer via email that payment has been received by the worker
        try:
            customer = users.find_one({"_id": req_doc["customer_id"]})
            worker = users.find_one({"_id": req_doc["worker_id"]})
            if customer and customer.get("email"):
                currency = req_doc.get("currency", "INR")
                amount = amt_minor / 100.0
                subject = "Shramify - Payment received confirmation"
                body = (
                    f"Hello {customer.get('name', 'Customer')},\n\n"
                    f"Your online payment of {currency} {amount} for your recent service request "
                    f"with worker {worker.get('name', 'Worker')} has been successfully received.\n\n"
                    f"Thank you for using Shramify."
                )
                send_email(customer["email"], subject, body)
        except Exception:
            pass
        flash("Payment successful.", "success")
    else:
        flash("Payment already processed or invalid state.", "warning")
    return redirect(url_for("my_requests"))


# Ratings
@app.route("/rate/<rid>", methods=["GET", "POST"])
@login_required(role=None)
def rate_request(rid):
    u = current_user()
    req_doc = requests_col.find_one({"_id": ObjectId(rid)})
    if not req_doc or req_doc.get("customer_id") != u["_id"]:
        flash("Request not found.", "warning")
        return redirect(url_for("my_requests"))
    if req_doc.get("status") not in ("paid", "completed"):
        flash("You can only rate after payment/completion.", "warning")
        return redirect(url_for("my_requests"))

    if request.method == "POST":
        try:
            rating = int(request.form.get("rating"))
        except:
            rating = 0
        feedback = request.form.get("feedback", "")
        reviews.insert_one({
            "worker_id": req_doc["worker_id"],
            "customer_id": u["_id"],
            "request_id": req_doc["_id"],
            "rating": max(1, min(5, rating)),
            "feedback": feedback,
            "created_at": datetime.utcnow()
        })
        flash("Thanks for your feedback!", "success")
        return redirect(url_for("view_worker", worker_id=str(req_doc["worker_id"])) )

    return render_template("rate_service.html", user=u, req=req_doc)




if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
