# Bot Manager Project Analysis

## Overview
The Bot Manager is a web application that allows users to create, configure, and manage multiple Discord self-bots from a single interface. It uses a FastAPI backend with a JavaScript frontend, and runs bots as subprocesses within a Docker container.

## Architecture

### Core Components

1. **FastAPI Manager (`app/manager.py`)**
   - REST API endpoints for bot management
   - WebSocket endpoints for real-time status updates and log streaming
   - Configuration management via TOML files
   - Static file serving for the web UI

2. **Bot Registry (`app/bots_manager.py`)**
   - Manages bot lifecycle (create, start, stop, delete)
   - Process management using subprocess and psutil
   - Scheduling system using APScheduler
   - Bot discovery from filesystem

3. **Bot Template (`templates/discum_selfbot/`)**
   - Discord self-bot implementation using the discum library
   - AI-powered responses via Google's Gemini API
   - SQLite database for persistent storage
   - Friendship scoring system based on interactions
   - Style mirroring (emoji usage, lowercase preference, message length)
   - Fact extraction from chat messages

4. **Web UI (`app/static/`)**
   - Dashboard for managing bots
   - Real-time status updates via WebSocket
   - Configuration editing with dynamic form generation
   - Live log viewing

## Key Features

### Bot Management
- Create bots from templates with personalized names
- Start, stop, and restart bots
- Delete bots (after stopping)
- Real-time status monitoring (CPU, memory usage)
- Log viewing and downloading

### AI-Powered Responses
- Integration with Google's Gemini API for natural language responses
- Personality system with mood changes
- Style mirroring to match user communication patterns
- Friendship scoring based on interactions
- Fact learning from conversations

### Configuration System
- Dynamic form generation based on TOML schema
- Support for various data types (strings, numbers, booleans, arrays, objects)
- Real-time configuration updates
- Scheduled actions (start/stop/restart) with cron or interval support

### Database Features
- SQLite for local data storage
- Chat history tracking
- User fact extraction and storage
- Friendship scoring system
- Style analysis (emoji usage, lowercase preference, message length)
- Topic tracking

## How It Works

1. **Bot Creation**
   - User clicks "Create Bot" in the UI
   - Frontend sends request to `/api/bots` endpoint
   - Backend creates new bot instance by copying template
   - Personalizes bot configuration with provided name
   - Returns new bot ID to frontend

2. **Bot Execution**
   - User starts bot from UI
   - Backend spawns new Python subprocess running `bot.py`
   - Bot connects to Discord using discum library
   - stdout/stderr redirected to log file for UI display
   - Process ID tracked for status monitoring

3. **AI Response Generation**
   - Bot receives message via discum event handler
   - Checks if bot should respond based on friendship score and probability
   - Builds prompt with chat history, user facts, and style information
   - Sends prompt to Gemini API
   - Processes and sends response back to Discord

4. **Configuration Management**
   - UI requests current config from `/api/bots/{bot_id}/config`
   - Backend reads TOML file and generates JSON schema
   - UI dynamically creates form based on schema
   - User edits configuration and saves
   - Backend validates and saves updated configuration

5. **Real-time Updates**
   - WebSocket connection to `/ws/status` for bot status
   - WebSocket connection to `/ws/logs/{bot_id}` for live logs
   - Automatic reconnection on connection loss

## Technologies Used

- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Database**: SQLite
- **Task Scheduling**: APScheduler
- **Process Management**: subprocess, psutil
- **Configuration**: TOML
- **AI Integration**: Google Gemini API
- **Discord Integration**: discum library
- **Containerization**: Docker, Docker Compose

## Deployment

The application can be run in two ways:

1. **Production Mode**:
   ```bash
   docker build -t botmgr .
   docker run -p 8080:8080 -v $(pwd)/data:/data botmgr
   ```

2. **Development Mode**:
   ```bash
   docker-compose up --build
   ```
   This mode includes live reloading for development.

The web UI is accessible at `http://localhost:8080/ui`.