# 🚀 CPQ Quote Generator System

A professional **Configure, Price, Quote (CPQ)** system for migration services with client management, automated pricing calculations, and professional PDF generation.

## ✨ Features

### 🏢 Client Management
- **Complete CRUD operations** for client information
- **Persistent storage** in MongoDB
- **Professional client database** with search and update capabilities

### 🧮 Quote Generation
- **Automated pricing calculations** for 3 service tiers
- **Configurable parameters**: users, instances, duration, data size
- **Real-time cost breakdown** with detailed pricing tables
- **Professional quote templates** with company branding

### 📄 PDF Generation
- **Direct server-side PDF creation** (no HTML conversion issues)
- **Professional layouts** with tables, colors, and formatting
- **Instant download** with custom naming
- **High-quality output** using ReportLab

### 🗄️ Data Persistence
- **MongoDB integration** for reliable data storage
- **Quote history tracking** with client relationships
- **Data export capabilities** for reporting

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB with PyMongo
- **PDF Generation**: ReportLab
- **Frontend**: HTML5, CSS3, JavaScript
- **Data Transfer**: localStorage + RESTful APIs
- **Styling**: Modern CSS with responsive design

## 📋 Prerequisites

- Python 3.7+
- MongoDB instance (local or cloud)
- pip package manager

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <your-github-repo-url>
cd hubspot19
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup
Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb://localhost:27017/cpq_db
# Or for MongoDB Atlas:
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/cpq_db
```

### 4. Start MongoDB
```bash
# Local MongoDB
mongod

# Or use MongoDB Atlas (cloud)
```

### 5. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📱 Usage

### 1. Client Information
- Navigate to the home page
- Fill in client details (name, company, email, phone, service type, requirements)
- Save client information to database

### 2. Quote Generation
- Go to Quote Calculator page
- Configure migration parameters:
  - Number of users
  - Instance type (Small, Standard, Large, Extra Large)
  - Number of instances
  - Project duration
  - Migration type (Content, Email, Messaging)
  - Data size in GB
- Generate quote with automatic pricing calculations

### 3. PDF Export
- Click "Generate PDF Quote" button
- Professional PDF downloads instantly
- Includes all client and quote information

## 🏗️ Project Structure

```
hubspot19/
├── app.py                 # Main Flask application
├── db.py                  # Database connection and collections
├── pricing_logic.py       # Pricing calculation algorithms
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
├── README.md             # This file
├── index.html            # Client information page
├── quote-calculator.html # Quote calculation interface
└── quote-template.html   # HTML quote template
```

## 🔌 API Endpoints

### Client Management
- `POST /api/clients` - Create new client
- `GET /api/clients` - Get all clients
- `PUT /api/clients/<id>` - Update client
- `DELETE /api/clients/<id>` - Delete client

### Quote Operations
- `POST /api/quote` - Generate quote with validation
- `POST /api/generate-pdf` - Direct PDF generation

### Page Routes
- `/` - Client information page
- `/quote-calculator` - Quote calculation page
- `/quote-template` - HTML template preview

## 🎨 Customization

### Company Branding
- Update company information in `quote-template.html`
- Modify contact details in PDF generation
- Customize color schemes and styling

### Pricing Logic
- Adjust pricing in `pricing_logic.py`
- Modify service tiers and cost structures
- Add new pricing parameters

### PDF Template
- Customize PDF layout in `create_quote_pdf()` function
- Add company logo and branding
- Modify terms and conditions

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Check if MongoDB is running
   - Verify MONGO_URI in .env file
   - Ensure network connectivity

2. **PDF Generation Fails**
   - Install ReportLab: `pip install reportlab==4.0.4`
   - Check server logs for errors
   - Verify data format

3. **Port Already in Use**
   - Change port in `app.py`: `app.run(debug=True, port=5001)`
   - Kill existing process using the port

### Debug Mode
Enable debug mode in `app.py`:
```python
app.run(debug=True)
```

## 🔒 Security Considerations

- **Environment Variables**: Store sensitive data in .env file
- **Input Validation**: All user inputs are validated
- **Error Handling**: Comprehensive error handling prevents crashes
- **Data Sanitization**: MongoDB injection protection

## 🚀 Deployment

### Local Development
```bash
python app.py
```

### Production Deployment
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Docker (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Flask framework for web development
- MongoDB for data persistence
- ReportLab for PDF generation
- Modern web technologies for responsive UI

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ for professional quote generation and client management**
