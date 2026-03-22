# Shramify - Complete Documentation

## Quick Start

### Start the Application
```bash
python app.py
```
Then visit: http://localhost:5000

### System Check
```bash
python check_setup.py
```

## Project Structure

```
shramify1/
├── app.py                 # Main Flask application
├── check_setup.py         # System verification script
├── requirements.txt       # Python dependencies
├── .env                   # Environment configuration (keep secret)
├── .env.example          # Example environment file
├── static/               # CSS, JS, images
│   ├── styles.css        # Professional blue theme
│   ├── app.js           # Frontend JavaScript
│   ├── navigation.js    # Navigation handling
│   └── uploads/         # User uploaded files
└── templates/           # HTML templates
    ├── base.html        # Base template
    ├── index.html       # Landing page
    ├── login.html       # Login page
    ├── register.html    # Registration
    └── ...              # Other pages
```

## Color Scheme

### Primary Colors
- **Blue**: #0066FF (Trust & professionalism)
- **Teal**: #00C9A7 (Modern accent)
- **Success**: #10B981 (Green)
- **Warning**: #F59E0B (Amber)
- **Danger**: #EF4444 (Red)

### Usage
- Primary buttons: Blue gradient
- Secondary buttons: Ghost style with border
- Success actions: Green gradient
- Cards: White with subtle shadows

## Configuration

### Required Settings (.env)
```bash
FLASK_SECRET_KEY=your-secret-key
MONGO_URI=mongodb://localhost:27017/
```

### Optional Settings
```bash
# Google Maps (for location features)
MAPS_API_KEY=your_google_maps_api_key

# Razorpay (for payments)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id

# Email (for OTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Twilio SMS
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

## API Keys Setup

### Google Maps API
1. Go to: https://console.cloud.google.com/
2. Create project → Enable Maps JavaScript API, Places API, Geocoding API
3. Create credentials → API Key
4. Add to `.env`: `MAPS_API_KEY=your_key_here`

### Razorpay Payment Gateway
1. Sign up at: https://dashboard.razorpay.com/signup
2. Go to Settings → API Keys
3. Generate Test Keys
4. Add to `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_xxxxx
   RAZORPAY_KEY_SECRET=xxxxx
   ```

### Tesseract OCR (for Aadhaar scanning)
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **Linux**: `sudo apt-get install tesseract-ocr`
- **Mac**: `brew install tesseract`

## Features

### For Customers
- Search for local workers by service and location
- View worker profiles, ratings, and reviews
- Request services with custom offers
- Make payments (online or cash)
- Rate and review completed services
- Track service requests

### For Workers
- Create professional profile with services and pricing
- Receive and manage service requests
- Accept/reject requests
- Build reputation through ratings
- Receive payments
- Aadhaar verification for trust

## Database Collections

### users
- Worker and customer profiles
- Authentication credentials
- Verification status
- Location and contact info

### requests
- Service requests
- Status tracking (pending, accepted, completed)
- Payment information
- Customer offers

### reviews
- Customer ratings (1-5 stars)
- Written reviews
- Timestamps

### reports
- Worker reporting system
- Safety and quality concerns

## Security Features

- Secure password hashing (Werkzeug)
- Session management
- Input validation
- File upload security
- Aadhaar verification
- Payment security (Razorpay)

## Troubleshooting

### MongoDB Connection Failed
```bash
# Windows
net start MongoDB

# Linux
sudo systemctl start mongod

# Mac
brew services start mongodb-community
```

### Port Already in Use
```bash
# Change port in app.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Dependencies Missing
```bash
pip install -r requirements.txt
```

### Tesseract Not Found
- Install Tesseract OCR
- Add to system PATH
- Restart terminal/IDE

## Development

### Run in Debug Mode
```python
# app.py (already configured)
app.run(debug=True, host='0.0.0.0', port=5000)
```

### Check for Errors
```bash
python check_setup.py
```

### Test Database Connection
```python
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
print(client.list_database_names())
```

## Deployment

### Production Checklist
- [ ] Change FLASK_SECRET_KEY to strong random value
- [ ] Use production MongoDB with authentication
- [ ] Enable HTTPS
- [ ] Set debug=False in app.py
- [ ] Configure proper CORS settings
- [ ] Set up regular database backups
- [ ] Use production API keys (not test keys)
- [ ] Configure proper logging
- [ ] Set up monitoring

### Environment Variables
Never commit `.env` file to version control. Use `.env.example` as template.

## Support

- **Email**: kkarthik99875@gmail.com
- **Phone**: +91 9353345530
- **Location**: Ballari, Karnataka, India

## License

Educational and demonstration purposes. Ensure compliance with local regulations for production use.

---

**Shramify** - *Connecting Skills, Building Trust* 🤝
