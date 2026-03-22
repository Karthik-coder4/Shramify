# Shramify - Clean Project Structure

## 📁 Project Files

```
shramify1/
├── 📄 app.py                    # Main Flask application (core)
├── 📄 check_setup.py            # System verification script
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env                      # Environment configuration (SECRET - don't commit)
├── 📄 .env.example             # Example environment file (safe to commit)
├── 📄 README.md                # Project overview and features
├── 📄 DOCUMENTATION.md         # Complete setup and usage guide
├── 📄 PROJECT_STRUCTURE.md     # This file
│
├── 📁 static/                  # Frontend assets
│   ├── styles.css              # Professional blue theme CSS
│   ├── app.js                  # Frontend JavaScript
│   ├── navigation.js           # Navigation handling
│   └── uploads/                # User uploaded files (Aadhaar, profiles)
│
├── 📁 templates/               # HTML templates
│   ├── base.html               # Base template with nav/footer
│   ├── index.html              # Landing page
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── search.html             # Worker search
│   ├── worker_profile.html     # Worker profile view
│   ├── customer_dashboard.html # Customer dashboard with map
│   ├── my_requests.html        # Service requests management
│   ├── rate_service.html       # Rating and review
│   ├── pay_online.html         # Razorpay payment
│   └── ...                     # Other templates
│
├── 📁 __pycache__/             # Python cache (auto-generated)
├── 📁 .venv/                   # Virtual environment (optional)
└── 📁 .vscode/                 # VS Code settings (optional)
```

## 🎯 Essential Files

### Core Application
- **app.py** - Main Flask application with all routes and logic
- **requirements.txt** - All Python dependencies
- **.env** - Configuration (keep secret, never commit)
- **.env.example** - Template for environment variables

### Documentation
- **README.md** - Project overview, features, and quick intro
- **DOCUMENTATION.md** - Complete setup guide, API keys, troubleshooting
- **PROJECT_STRUCTURE.md** - This file explaining the structure

### Utilities
- **check_setup.py** - Verify system configuration and dependencies

### Frontend
- **static/styles.css** - Professional design with blue theme
- **static/app.js** - Frontend functionality
- **static/navigation.js** - Navigation handling
- **static/uploads/** - User uploaded files

### Templates
All HTML files in `templates/` directory for different pages

## 🚀 Quick Commands

### Start Application
```bash
python app.py
```

### Check System
```bash
python check_setup.py
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## 📝 What Was Removed

### Removed Files (50+ redundant files)
- ❌ All test files (test_*.py)
- ❌ Redundant documentation (40+ MD files)
- ❌ Batch files (start.bat, get_mobile_url.bat)
- ❌ Utility scripts (update_api_key.py)
- ❌ Old fix summaries and guides

### Why Removed?
- **Test files**: Not needed for production
- **Multiple docs**: Consolidated into DOCUMENTATION.md
- **Batch files**: Use `python app.py` instead
- **Old guides**: Information now in DOCUMENTATION.md

## 📚 Documentation Guide

### For Quick Start
→ Read **README.md**

### For Setup & Configuration
→ Read **DOCUMENTATION.md**

### For Project Structure
→ Read **PROJECT_STRUCTURE.md** (this file)

## 🔒 Important Notes

### Never Commit
- `.env` file (contains secrets)
- `__pycache__/` directory
- `.venv/` directory
- `static/uploads/` (user data)

### Safe to Commit
- `.env.example` (template only)
- All `.py` files
- All `.html`, `.css`, `.js` files
- `requirements.txt`
- All `.md` documentation files

## 🎨 Design System

### Colors
- Primary: #0066FF (Blue)
- Secondary: #00C9A7 (Teal)
- Success: #10B981 (Green)
- Warning: #F59E0B (Amber)
- Danger: #EF4444 (Red)

### Files
- CSS: `static/styles.css`
- JavaScript: `static/app.js`, `static/navigation.js`

## 🗄️ Database

### Collections
- **users** - Worker and customer profiles
- **requests** - Service requests
- **reviews** - Ratings and reviews
- **reports** - Worker reports

### Connection
Configured in `.env` file:
```
MONGO_URI=mongodb://localhost:27017/
```

## 🔧 Configuration

All configuration in `.env` file:
- Flask secret key
- MongoDB URI
- Google Maps API key (optional)
- Razorpay keys (optional)
- Email/SMS settings (optional)

See **DOCUMENTATION.md** for detailed setup instructions.

## 📦 Dependencies

All listed in `requirements.txt`:
- Flask (web framework)
- PyMongo (database)
- Werkzeug (security)
- python-dotenv (environment)
- Razorpay (payments)
- Twilio (SMS)
- Pillow & pytesseract (OCR)
- google-auth (OAuth)

## 🎯 Next Steps

1. Read **README.md** for overview
2. Read **DOCUMENTATION.md** for setup
3. Configure `.env` file
4. Run `python check_setup.py`
5. Start with `python app.py`

---

**Clean, organized, and production-ready!** ✨
