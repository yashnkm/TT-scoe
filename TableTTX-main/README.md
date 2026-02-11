# TimeTableAI - AI-Powered Academic Timetable Generator

An intelligent web application that generates optimized academic timetables for educational institutions using constraint satisfaction algorithms and AI-powered natural language modifications.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg) ![Flask](https://img.shields.io/badge/Flask-3.1.2-green.svg) ![OR-Tools](https://img.shields.io/badge/OR--Tools-9.14-orange.svg) ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-purple.svg)

---

## 🎯 What is TimeTableAI?

TimeTableAI automates academic scheduling by:
- ✅ Generating conflict-free timetables in seconds
- ✅ Using AI to handle natural language requests 
- ✅ Providing 3 intelligent modification strategies
- ✅ Learning from your preferences
- ✅ Exporting to PDF and Excel

**Problem**: Manual timetable creation is time-consuming and error-prone  
**Solution**: Automated scheduling with intelligent AI modifications

---

## ✨ Features

### 🤖 AI Assistant
- Natural language requests: "Dr. Smith is on leave next Monday"
- 3 diverse modification strategies (Minimal, Strategic, Bold)
- Learns from feedback
- Conflict detection and resolution

### 📊 Timetable Management
- Automated generation (5-20 seconds)
- Handles: Years, Divisions, Batches, Theory & Practical sessions
- Real-time conflict validation
- Multiple export formats

### 👥 Resource Management
- Faculty: Add, assign subjects, manage availability
- Rooms: Define classrooms, labs, auditoriums
- Subjects: Configure theory/practical with hour requirements

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, Flask 3.1.2 |
| Solver | Google OR-Tools 9.14 |
| AI | OpenAI GPT-4o |
| Exports | ReportLab (PDF), OpenPyXL (Excel) |
| Frontend | Bootstrap 5, JavaScript |
| Database | JSON files |

---

## 📥 Installation

### Prerequisites
- Python 3.11 or higher
- pip (package manager)
- OpenAI API key (optional, for AI features)

### Setup (2 minutes)

```bash
# 1. Clone/download project
git clone <repository-url>
cd TimeTableAI

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file (optional, for AI features)
echo OPENAI_API_KEY=sk-proj-your-key-here > .env
echo SESSION_SECRET=your-secret-key >> .env

# 6. Run the app
python app.py

# 7. Open browser to http://localhost:5000
```

---

## 🚀 Quick Start (5 minutes)

1. **Configure Institution**
   - Go to "Configure" → Set years, divisions, time slots, working days

2. **Add Subjects**
   - Go to "Subjects" → Click "Add Subject" → Fill details

3. **Add Faculty**
   - Go to "Faculty" → Click "Add Faculty" → Assign subjects & divisions

4. **Add Rooms**
   - Go to "Rooms" → Click "Add Room" → Set name, type, capacity

5. **Generate Timetable**
   - Go to "Generate Timetable" → Select semester → Click "Generate"
   - Wait 5-20 seconds ✅

6. **Download**
   - Click "Download PDF (All Divisions)" or "Download Excel (All Divisions)"

---

## 🤖 Using AI Assistant

### Request Examples
```
"Dr. Smith is on leave Monday"
"Move Database practical to Friday morning"
"Lab 304 needs maintenance Wed-Thu"
"Optimize Year 3 Division B schedule"
```

### How It Works
1. Type your request
2. Get 3 different strategies
3. Choose the best one
4. Provide feedback (AI learns!)
5. Get better suggestions next time

### 3 Strategies
- **Option 1**: Minimal Disruption (safest, score: 9-10)
- **Option 2**: Strategic Optimization (balanced, score: 7-8)
- **Option 3**: Bold Restructuring (innovative, score: 5-7)

---

## 📁 Project Structure

```
TimeTableAI/
├── app.py                 # Flask app entry point
├── routes.py              # HTTP routes & APIs
├── models.py              # Data management
├── solver.py              # Timetable solver
├── ai_assistant.py        # AI features
├── requirements.txt       # Dependencies
├── README.md              # This file
├── Report.md              # Detailed docs
├── .env                   # Environment vars (create this)
├── data/                  # JSON storage
│   ├── academic_structure.json
│   ├── subjects.json
│   ├── faculty.json
│   └── rooms.json
├── templates/             # HTML pages
└── static/                # CSS & JavaScript
```

---

## 🔌 API Endpoints

### Core APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/structure` | Get academic structure |
| GET | `/api/subjects` | Get all subjects |
| GET | `/api/faculty` | Get all faculty |
| GET | `/api/rooms` | Get all rooms |
| POST | `/generate` | Generate timetable |
| GET | `/api/current-timetable` | Get current timetable |

### AI APIs
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/ai/get-suggestions` | Get AI suggestions |
| POST | `/api/ai/apply-modification` | Apply modification |
| GET | `/api/ai/statistics` | Get AI stats |
| GET | `/api/ai/health` | Check AI status |
| POST | `/api/ai/detect-conflicts` | Scan for conflicts |

### Export APIs
| Endpoint | Purpose |
|----------|---------|
| `/download/pdf?division=...` | Download single division PDF |
| `/download/pdf-all` | Download all divisions PDF |
| `/download/excel?division=...` | Download single division Excel |
| `/download/excel-all` | Download all divisions Excel |

**Full API Documentation**: See [Report.md](Report.md#api-endpoints)

---

## ⚙️ Configuration

### Environment Variables (`.env`)
```env
OPENAI_API_KEY=sk-proj-your-key-here    # Required for AI
SESSION_SECRET=your-random-secret-key    # Flask security
```

### Getting OpenAI API Key
1. Visit https://platform.openai.com/
2. Sign up/login
3. Create API key
4. Add to `.env` file
5. ⚠️ Never commit `.env` to git!

### Customization
- **Time Slots**: Edit in "Configure" page
- **Working Days**: Select in "Configure" page
- **Session Duration**: Set theory/practical minutes in "Configure"
- **Data Backup**: Copy the `data/` folder

---

## 📥 Export Features

### PDF Export
- Single or all divisions
- Landscape orientation
- Professional formatting
- Print-ready

### Excel Export
- One sheet per division
- Styled headers & formatting
- Easy to edit and share
- Full timetable in one file

---

## 🚀 Deployment

### Development
   ```bash
python app.py
# Access: http://localhost:5000
```

### Production
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Docker
docker build -t timetableai .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key timetableai
```

**For detailed deployment guide**: See [Report.md](Report.md#deployment)

---

## 🔧 Troubleshooting

### ⚠️ "OpenAI API key not found"
**Solution**: Create `.env` file with `OPENAI_API_KEY=sk-proj-...`

### ❌ Module not found
**Solution**: Activate virtual environment and install dependencies
   ```bash
pip install -r requirements.txt
```

### ❌ Port 5000 already in use
**Solution**: Change port in `app.py` or kill process on port 5000

### ❌ Timetable generation fails
**Possible causes**:
- No subjects configured
- No faculty assigned to subjects
- Impossible constraints

**Solution**: Verify all data is configured in UI

**More help**: See [Report.md](Report.md#troubleshooting) for detailed troubleshooting

---

## 📚 Documentation

| Document | Contains |
|----------|----------|
| **README.md** | Quick start & essentials (this file) |
| **Report.md** | Complete technical documentation (50+ pages) |

---

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes & test
4. Commit: `git commit -m "Description"`
5. Push & create Pull Request

### Code Style
- Follow PEP 8 (Python)
- Add docstrings
- Comment complex logic
- Test thoroughly

---

## 📄 License

Educational and academic use only.

**Allowed**: ✅ Use in institutions, ✅ Modify for your needs, ✅ Share with attribution  
**Not Allowed**: ❌ Commercial use, ❌ Remove copyright, ❌ Redistribute without attribution

---

## 📊 Project Status

- ✅ Core Features: Complete
- ✅ AI Integration: Complete
- ✅ Export: Complete
- ✅ Documentation: Complete
- 🔄 Testing: Ongoing

---

## 📞 Support & Questions

- **Full Docs**: [Report.md](Report.md)
- **Issues**: Check troubleshooting section above
- **Need Details?**: Every section has links to detailed info in Report.md

---

## 🎓 Key Statistics

- **Lines of Code**: ~3,500
- **Technologies**: 8 core libraries
- **Features**: 25+ major features
- **API Endpoints**: 20+
- **Performance**: <20 seconds for 50+ classes
- **AI Model**: GPT-4o (Latest)

---

**Version**: 1.0 | **Last Updated**: October 22, 2025  
**Made by Abhi**

[⬆ Back to Top](#timetableai---ai-powered-academic-timetable-generator)
