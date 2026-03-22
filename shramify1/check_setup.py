"""
System Check Script for Shramify
Verifies all dependencies and configurations are properly set up
"""

import sys
import os

print("=" * 60)
print("SHRAMIFY SYSTEM CHECK")
print("=" * 60)
print()

# Track issues
issues = []
warnings = []

# 1. Check Python version
print("1. Checking Python version...")
py_version = sys.version_info
if py_version.major == 3 and py_version.minor >= 8:
    print(f"   ✓ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
else:
    print(f"   ✗ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    issues.append("Python 3.8+ required")
print()

# 2. Check required packages
print("2. Checking Python packages...")
required_packages = {
    'flask': 'Flask',
    'pymongo': 'PyMongo',
    'werkzeug': 'Werkzeug',
    'dotenv': 'python-dotenv',
    'twilio': 'Twilio',
    'razorpay': 'Razorpay',
    'google.auth': 'google-auth',
    'PIL': 'Pillow',
    'pytesseract': 'pytesseract'
}

for module, package in required_packages.items():
    try:
        __import__(module)
        print(f"   ✓ {package}")
    except ImportError:
        print(f"   ✗ {package} - NOT INSTALLED")
        issues.append(f"Install {package}: pip install {package.lower()}")
print()

# 3. Check Tesseract OCR
print("3. Checking Tesseract OCR...")
try:
    import pytesseract
    from PIL import Image
    
    # Try to get version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   ✓ Tesseract {version}")
    except Exception as e:
        print(f"   ⚠ Tesseract not installed or not in PATH")
        warnings.append("Tesseract OCR not found (OPTIONAL - for Aadhaar scanning)")
        warnings.append("Workers can still manually enter Aadhaar numbers")
        warnings.append("Download from: https://github.com/UB-Mannheim/tesseract/wiki")
except ImportError:
    print("   ⚠ pytesseract not installed")
    warnings.append("OCR will not work. Install: pip install pytesseract")
print()

# 4. Check MongoDB connection
print("4. Checking MongoDB connection...")
try:
    from pymongo import MongoClient
    from dotenv import load_dotenv
    load_dotenv()
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    client.server_info()
    print(f"   ✓ MongoDB connected at {mongo_uri}")
    client.close()
except Exception as e:
    print(f"   ✗ MongoDB connection failed: {e}")
    issues.append("Start MongoDB: net start MongoDB (Windows) or sudo systemctl start mongod (Linux)")
print()

# 5. Check .env file
print("5. Checking .env configuration...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = {
        'FLASK_SECRET_KEY': 'Flask secret key',
        'MAPS_API_KEY': 'Google Maps API key',
        'GOOGLE_CLIENT_ID': 'Google OAuth Client ID',
        'RAZORPAY_KEY_ID': 'Razorpay Key ID',
        'RAZORPAY_KEY_SECRET': 'Razorpay Key Secret',
    }
    
    for var, desc in env_vars.items():
        value = os.getenv(var)
        if value and value not in ['your_', 'AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567']:
            print(f"   ✓ {desc}")
        else:
            print(f"   ⚠ {desc} - NOT CONFIGURED")
            if var in ['RAZORPAY_KEY_ID', 'RAZORPAY_KEY_SECRET']:
                warnings.append(f"{desc} not configured (OPTIONAL - for online payments)")
                warnings.append("Cash payments will still work without Razorpay")
            elif var == 'MAPS_API_KEY':
                warnings.append(f"{desc} not configured (OPTIONAL - for maps feature)")
                warnings.append("App will work without maps, see GET_API_KEYS.md")
            else:
                warnings.append(f"Configure {desc} in .env")
except Exception as e:
    print(f"   ✗ Error reading .env: {e}")
    issues.append("Create .env file with required configuration")
print()

# 6. Check file structure
print("6. Checking file structure...")
required_files = [
    'app.py',
    'requirements.txt',
    'templates/base.html',
    'templates/index.html',
    'static/styles.css',
    'static/app.js',
]

for file in required_files:
    if os.path.exists(file):
        print(f"   ✓ {file}")
    else:
        print(f"   ✗ {file} - MISSING")
        issues.append(f"Missing file: {file}")
print()

# 7. Check upload directory
print("7. Checking upload directory...")
upload_dir = os.path.join('static', 'uploads')
if os.path.exists(upload_dir):
    print(f"   ✓ Upload directory exists")
else:
    print(f"   ⚠ Upload directory will be created on first run")
print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)

if not issues and not warnings:
    print("✓ All checks passed! Your system is ready.")
    print()
    print("Next steps:")
    print("1. Create admin account: python create_admin.py")
    print("2. Start the app: python app.py")
    print("3. Visit: http://localhost:5000")
elif not issues:
    print("✓ Core system is ready! Optional features have warnings.")
    print()
    print("You can start using the app now:")
    print("1. Create admin account: python create_admin.py")
    print("2. Start the app: python app.py")
    print("3. Visit: http://localhost:5000")
    print()
    print("Optional features (see warnings below):")
    print("- Google Maps (for location features)")
    print("- Razorpay (for online payments)")
    print("- Tesseract OCR (for Aadhaar scanning)")
    print()
    print("See GET_API_KEYS.md for setup instructions.")
else:
    if issues:
        print()
        print("❌ CRITICAL ISSUES (must fix):")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if warnings:
        print()
        print("⚠ WARNINGS (optional features):")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
    
    print()
    print("Fix the issues above and run this script again.")

print()
print("=" * 60)
print("For detailed setup instructions, see: SETUP_GUIDE.md")
print("=" * 60)
