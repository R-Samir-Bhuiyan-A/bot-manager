# Bot Manager (Pterodactyl-inspired)

## Overview
This is a web-based management interface for Discord selfbots, inspired by Pterodactyl Panel. It allows you to create, configure, and manage multiple selfbots from a single interface.

Each bot runs as a subprocess within the manager's container. New bots are created by copying a template, and each bot's configuration is stored separately.

## Security Notice
This project uses Discord selfbots, which may violate Discord's Terms of Service. Use at your own risk.

## Prerequisites
- Docker
- Docker Compose (for development)

## Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd bot-manager
```

### 2. Configure Your Bot Template
Before creating bots, you need to set up the template configuration:

1. Copy the sample configuration:
   ```bash
   cp templates/discum_selfbot/config.sample.toml templates/discum_selfbot/config.toml
   ```

2. Edit `templates/discum_selfbot/config.toml` with your:
   - Discord user token
   - Gemini API key (for AI features)
   - Channel IDs to monitor
   - Bot persona settings

⚠️ **Important:** Never commit your actual credentials to version control!

### 3. Build & Run

#### Development (with live reload):
```bash
docker-compose up --build
```

Open http://localhost:8080/ui

#### Production:
```bash
docker build -t botmgr .
docker run -p 8080:8080 -v $(pwd)/data:/data botmgr
```

Open http://localhost:8080/ui

## Usage

### Create a bot
- Click "Create Bot" in the UI
- Open the bot card → edit config → Start

### Managing bots
- Each bot runs as a subprocess inside this single container
- A new bot is created by copying `templates/discum_selfbot` → `data/bots/bot_X`
- Each bot logs to `/data/bots/bot_X/debug_log.txt` (visible in UI)
- Scheduler uses cron or every_seconds to **start/stop/restart/custom**
- "Custom" action sets env `BOT_COMMAND` (bot template logs/handles it)

## Enhanced Bot Template Features
The discum selfbot template has been upgraded with several improvements:

### Robust API Integration
- Retry mechanism with exponential backoff for Gemini API calls
- Better error handling for various failure modes
- API usage statistics tracking

### Enhanced Prompt Engineering
- Better structured prompts for more consistent responses
- Improved context management
- More detailed persona instructions

### Advanced Error Handling
- Fallback responses based on current mood
- Comprehensive logging of API interactions
- Statistics tracking for monitoring performance

## Configuration

### Manager Settings
Manager settings are stored in `data/manager_settings.toml` and can be edited through the UI.

### Bot Configuration
Each bot's configuration is stored in its own `config.toml` file:
- Location: `data/bots/bot_X/config.toml`
- Format: TOML
- Schema: Defined by the template

## Data Persistence
Bot data and logs are stored in the `data/` directory:
- Bot instances: `data/bots/`
- Manager settings: `data/manager_settings.toml`

This directory is mounted as a volume in Docker to persist data between container restarts.

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a pull request

## License
This project is licensed under the MIT License - see the LICENSE file for details.