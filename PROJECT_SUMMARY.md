# Bot Manager Project Summary

## Overview
The Bot Manager is a Pterodactyl-inspired web application for managing multiple Discord self-bots from a single interface. It uses FastAPI for the backend and runs bots as subprocesses within a Docker container.

## Project Structure
```
bot-manager/
├── app/                    # FastAPI application
│   ├── manager.py         # Main FastAPI app and endpoints
│   ├── bots_manager.py    # Bot lifecycle management
│   ├── schemas.py         # Pydantic models
│   ├── utils.py           # Utility functions
│   └── static/            # Frontend UI files
├── templates/             # Bot templates
│   └── discum_selfbot/    # Template for discum-based bots
├── data/                  # Runtime data (bot instances)
├── Dockerfile             # Container definition
├── docker-compose.yml     # Development setup
├── requirements.txt       # Python dependencies
└── README.md             # Project documentation
```

## Key Components

### 1. Bot Manager (FastAPI)
- REST API for bot management (create, start, stop, delete)
- WebSocket endpoints for real-time status and logs
- Configuration management via TOML files
- Scheduling system using APScheduler

### 2. Bot Template (discum_selfbot)
- Discord self-bot implementation using discum library
- AI-powered responses via Google's Gemini API
- Friendship scoring system based on interactions
- Style mirroring (emoji usage, lowercase preference, message length)
- Fact extraction from chat messages
- SQLite database for persistent storage

### 3. Web UI
- Dashboard for managing bots
- Real-time status updates
- Configuration editing
- Log viewing

## Technologies Used
- Python 3.11
- FastAPI (backend API)
- discum (Discord API)
- Google Gemini API (AI responses)
- SQLite (local storage)
- Docker (containerization)
- TOML (configuration)
- APScheduler (scheduling)

## How It Works
1. Bots are created from templates stored in `templates/`
2. Each bot runs as a subprocess managed by the BotRegistry
3. Bot configurations are stored in `data/bots/bot_X/config.toml`
4. Bots connect to Discord using user tokens and respond to messages using AI
5. The web interface provides management capabilities

## Key Features
- Multiple bot management
- AI-powered chat responses
- Friendship scoring system
- Style mirroring
- Fact learning from conversations
- Scheduled actions (start/stop/restart)
- Real-time logs and status