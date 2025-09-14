# Installation and Usage Guide

## Quick Start

### 1. Clone or Download the Project

Make sure you have the AI Learning Agent project in your directory:
```
/Users/harshmodi/Desktop/Agent/2.0/
```

### 2. Set Up Virtual Environment

```bash
cd /Users/harshmodi/Desktop/Agent/2.0
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Basic Dependencies

```bash
pip install pyyaml python-dotenv rich typer
```

### 4. Run the Demo

```bash
python demo.py
```

## Demo Usage

Once the demo is running, you can use these commands:

- `learn <topic>` - Research and learn about a topic
  - Example: `learn quantum computing`
  
- `ask <question>` - Ask a question about learned topics
  - Example: `ask what is quantum computing?`
  
- `quiz <topic>` - Take a quiz about a learned topic
  - Example: `quiz quantum computing`
  
- `topics` - List all topics you've learned about
  
- `help` - Show available commands
  
- `quit` - Exit the demo

## Example Session

```
> learn artificial intelligence
🔍 Researching 'artificial intelligence'...
✅ Successfully learned about 'artificial intelligence'!
📝 Summary: This is what I learned about artificial intelligence...
🧠 Key concepts: fundamental artificial intelligence, artificial intelligence principles, artificial intelligence applications

> ask what is artificial intelligence?
🤔 Thinking about: what is artificial intelligence?
💡 Answer: Based on what I learned about artificial intelligence: This is what I learned about artificial intelligence. It's an important concept that involves multiple aspects and applications.

> quiz artificial intelligence
🎯 Quick Quiz: artificial intelligence
==============================
Question: What is artificial intelligence?
A) A simple concept
B) A fundamental concept with multiple aspects
C) An outdated theory
D) None of the above

Your answer (A/B/C/D): B
✅ Correct! Great job!
💡 Explanation: This is what I learned about artificial intelligence...
```

## Advanced Setup (Optional)

For full functionality with web scraping, NLP, and AI integration:

### Install Additional Dependencies

```bash
# Web scraping
pip install requests beautifulsoup4 selenium aiohttp httpx

# Natural Language Processing
pip install nltk spacy sentence-transformers

# AI/ML Integration
pip install openai anthropic transformers

# Database support
pip install sqlalchemy psycopg2-binary pymongo

# Web interface
pip install fastapi uvicorn streamlit gradio

# Data processing
pip install pandas numpy scikit-learn networkx
```

### Download NLP Models

```bash
# NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# spaCy model
python -m spacy download en_core_web_sm
```

### Set Up API Keys

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Run Full Application

```bash
python app.py
```

## Configuration

Edit `config.yaml` to customize:

- Data source settings
- AI model preferences
- Learning parameters
- API configurations
- Logging levels

## Troubleshooting

### Python Not Found
- Use `python3` instead of `python`
- Make sure Python 3.7+ is installed

### Permission Errors
- Use virtual environment (recommended)
- Or add `--user` flag: `pip install --user package_name`

### Import Errors
- Make sure virtual environment is activated
- Install missing dependencies
- Check Python path

### API Errors
- Verify API keys in `.env` file
- Check internet connection
- Ensure API quotas aren't exceeded

## Project Structure

```
ai_learning_agent/
├── core/                    # Core agent logic
│   ├── agent.py            # Main agent orchestrator
│   ├── reasoning.py        # Reasoning and planning
│   └── memory.py           # Knowledge storage
├── connectors/             # Data source connectors
│   ├── web_scraper.py      # Web scraping
│   ├── api_client.py       # API integrations
│   └── database.py         # Database connections
├── processors/             # Knowledge processing
│   ├── text_processor.py   # Text analysis
│   ├── knowledge_graph.py  # Knowledge graphs
│   └── summarizer.py       # Content summarization
├── teacher/                # Teaching interface
│   ├── tutor.py            # Interactive teaching
│   ├── curriculum.py       # Learning paths
│   └── quiz.py             # Assessments
└── utils/                  # Utilities
    ├── config.py           # Configuration
    └── logger.py           # Logging
```

## Features

### Current (Demo Version)
- ✅ Basic topic learning simulation
- ✅ Question answering
- ✅ Simple quizzing
- ✅ Knowledge tracking
- ✅ Interactive CLI interface

### Planned (Full Version)
- 🔄 Web scraping and research
- 🔄 API integrations (Wikipedia, etc.)
- 🔄 Advanced NLP processing
- 🔄 Knowledge graph construction
- 🔄 Intelligent reasoning
- 🔄 Adaptive teaching
- 🔄 Progress tracking
- 🔄 Web interface

## Support

For issues or questions:
1. Check this guide
2. Review error messages
3. Ensure all dependencies are installed
4. Verify configuration files
5. Check logs in `logs/` directory