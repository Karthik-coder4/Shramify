# 🏠 Shramify - Connecting Skills, Building Trust

A comprehensive Flask + MongoDB platform that connects verified informal workers (electricians, plumbers, maids, daily wage laborers) directly with customers. Built with security, trust, and user experience in mind.

## ✨ Key Features

### 🔐 Security & Verification
- **Aadhaar Verification System**: Both workers and customers must verify their Aadhaar cards before using the platform
- **OCR Technology**: Automatic extraction of Aadhaar details from uploaded images using Tesseract OCR
- **Manual Entry Option**: Fallback option for manual Aadhaar verification
- **Mobile Number Verification**: Cross-verification with registered mobile numbers

### 👷 Worker Features
- **Complete Profile Management**: Bio, services, pricing, location
- **Service Listings**: Multiple services with individual pricing
- **Rating System**: Customer reviews and ratings with averages
- **Request Management**: Accept/reject service requests
- **Payment Integration**: Razorpay integration for online payments
- **Location Mapping**: Interactive maps using OpenStreetMap/Leaflet

### 👥 Customer Features
- **Aadhaar Verification Required**: Must verify Aadhaar before requesting services
- **Advanced Search**: Filter by service type, location, ratings
- **Service Requests**: Detailed request system with custom offers
- **Live Tracking**: Real-time location tracking for workers
- **Review System**: Rate and review completed services
- **Payment Options**: Online (Razorpay) and cash payment methods

### 🗺️ Location & Maps
- **Interactive Maps**: OpenStreetMap integration (free alternative to Google Maps)
- **Geocoding**: Automatic location detection and address formatting
- **Nearby Workers**: Find workers within specified radius
- **Service Area Visualization**: Visual representation of worker service areas

### 💳 Payment System
- **Razorpay Integration**: Secure online payment processing
- **Cash Payments**: Traditional cash payment option
- **Payment Verification**: Secure payment verification system
- **Transaction History**: Complete payment tracking

## 🛠️ Technical Stack

- **Backend**: Flask (Python 3.10+)
- **Database**: MongoDB (local/cloud)
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Maps**: Leaflet.js with OpenStreetMap tiles
- **OCR**: Tesseract OCR with Pillow for image processing
- **Payments**: Razorpay API integration
- **Authentication**: Flask sessions with secure password hashing
- **SMS**: Twilio integration for SMS notifications

## 🚀 Quick Setup

### Prerequisites
- Python 3.10 or higher
- MongoDB (local or cloud)
- Tesseract OCR (for Aadhaar verification)

### Installation Steps

1. **Clone and Setup Environment**
   ```bash
   cd shramify1
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR**
   - **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
   - **Linux**: `sudo apt-get install tesseract-ocr`
   - **Mac**: `brew install tesseract`

4. **Setup MongoDB**
   - Install MongoDB locally or use MongoDB Atlas
   - Default connection: `mongodb://localhost:27017/`

5. **Configure Environment Variables**
   - Copy `.env` file and update with your credentials:
   ```bash
   FLASK_SECRET_KEY=your-super-secret-key-change-this
   MONGO_URI=mongodb://localhost:27017/
   RAZORPAY_KEY_ID=your_razorpay_key_id_here
   RAZORPAY_KEY_SECRET=your_razorpay_key_secret_here
   GOOGLE_CLIENT_ID=your_google_client_id_here
   ```

6. **Run the Application**
   ```bash
   python app.py
   ```

7. **Access the Website**
   - Open http://localhost:5000
   - Register as a customer or worker
   - Complete Aadhaar verification to use all features

## 📱 Usage Guide

### For Customers
1. **Register** with your details
2. **Verify Aadhaar** using image upload or manual entry
3. **Search Workers** by service type and location
4. **Request Services** with custom offers
5. **Track Progress** and make payments
6. **Rate & Review** completed services

### For Workers
1. **Register** as a worker (18+ years required)
2. **Complete Profile** with services and pricing
3. **Verify Aadhaar** for trust and credibility
4. **Receive Requests** from verified customers
5. **Accept/Negotiate** service requests
6. **Complete Work** and receive payments

## 🔧 Configuration Options

### Payment Gateway (Razorpay)
- Get API keys from https://dashboard.razorpay.com/
- Update `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env`

### Google OAuth (Optional)
- Get client ID from Google Cloud Console
- Update `GOOGLE_CLIENT_ID` in `.env`

### SMS Notifications (Twilio)
- Get credentials from https://www.twilio.com/
- Update Twilio settings in `.env`

## 🛡️ Security Features

- **Aadhaar Verification**: Mandatory for all users
- **Secure Password Hashing**: Using Werkzeug security
- **Session Management**: Secure Flask sessions
- **Input Validation**: Comprehensive form validation
- **File Upload Security**: Secure file handling for Aadhaar images
- **Payment Security**: Razorpay's secure payment processing

## 🌟 Key Improvements Made

1. **Enhanced Aadhaar Verification**: Complete OCR-based verification system
2. **Customer Verification Requirement**: Customers must verify before requesting services
3. **Improved UI/UX**: Modern, responsive design with better navigation
4. **Better Error Handling**: Comprehensive error messages and user feedback
5. **Security Enhancements**: Multiple layers of verification and validation
6. **Mobile-Friendly**: Responsive design for all devices

## 📊 Database Collections

- **users**: Worker and customer profiles with verification status
- **requests**: Service requests with status tracking
- **reviews**: Customer reviews and ratings
- **reports**: Worker reporting system for safety

## 🚨 Important Notes

- **Production Deployment**: Additional security hardening required for production
- **API Keys**: Never commit real API keys to version control
- **Database Security**: Use proper MongoDB authentication in production
- **HTTPS**: Enable HTTPS for production deployment
- **Backup**: Regular database backups recommended

## 📞 Support

For issues or questions:
- Email: kkarthik99875@gmail.com
- Phone: +91 9353345530

## 📄 License

This project is for educational and demonstration purposes. Please ensure compliance with local regulations when deploying in production.

---

**Shramify** - *Connecting Skills, Building Trust* 🤝
