# Airbnb Check-In/Check-Out Automation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent automation system for managing early check-in and late check-out requests for Airbnb properties. Coordinates between guests (via Smoobu), cleaning personnel (via email), and property managers (via Trello), using AI to handle routine communications while escalating exceptions to human oversight.

## 🎯 Features

- **Event-Driven Architecture**: Real-time webhook processing from Smoobu
- **AI-Powered Intent Detection**: Uses Claude AI to analyze guest messages  
- **Smart Escalation**: Automatically escalates urgent or ambiguous requests
- **Multi-Channel Communication**: Email for cleaners, Smoobu API for guests, Trello for task management
- **Automated Door Codes**: Generates time-based access codes when check-in times change
- **Human-in-the-Loop**: Ensures critical decisions get manager approval

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/airbnb-checkin-automation.git
cd airbnb-checkin-automation

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python src/main.py
```

## 📚 Documentation

- [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) - Complete system design
- [**SETUP.md**](docs/SETUP.md) - Detailed setup guide
- [**Smoobu API**](docs/api-specs/smoobu/README.md) - Integration docs

## 📄 License

MIT License - see LICENSE file

---

**Status**: 🚧 MVP Development
