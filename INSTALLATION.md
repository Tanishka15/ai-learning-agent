# Installation Guide

## Prerequisites
- Python 3.9+
- Git
- Google Cloud Console Account (for Classroom integration)

## Quick Setup

### 1. Clone Repository
```bash
git clone https://github.com/Tanishka15/ai-learning-agent.git
cd ai-learning-agent
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
GOOGLE_GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### 5. Initialize Database
```bash
python -c "from classroom_agent import initialize_db; initialize_db()"
```

### 6. Run Application
```bash
python app_web.py
```

Access at: `http://localhost:5005`

## Google Classroom Setup (Optional)

1. Create Google Cloud Project
2. Enable Classroom API
3. Download `credentials.json` to project root
4. Run authentication:
```bash
python google_classroom_auth.py
```

## Available Features

### Web Interface
- AI Chat with 6-step reasoning visualization
- Google Classroom integration
- Interactive bulletin board
- Study plan generation
- Course management

### API Endpoints
- `/chat` - AI conversation with reasoning toggle
- `/api/courses` - List enrolled courses
- `/api/study-plan` - Generate personalized study plans
- `/api/bulletin-board` - Get announcements and assignments
- `/api/search` - Search classroom content

## Troubleshooting

### Port Issues
```bash
lsof -ti:5005 | xargs kill -9
```

### Missing Dependencies
```bash
pip install --upgrade -r requirements.txt
```

### Database Reset
```bash
rm -rf chroma_db/
python -c "from classroom_agent import initialize_db; initialize_db()"
```

### Authentication Issues
- Verify `credentials.json` is in project root
- Check Google Cloud Console API enablement
- Ensure OAuth2 redirect URLs match

### Reasoning Chain Not Working
- Verify Gemini API key in `.env`
- Check API quota limits
- Ensure `show_reasoning=true` in requests
