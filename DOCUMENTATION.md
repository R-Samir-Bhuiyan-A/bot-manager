# Bot Manager Documentation

## Table of Contents
1. [Architecture](#architecture)
2. [API Endpoints](#api-endpoints)
3. [Bot Template Structure](#bot-template-structure)
4. [Configuration](#configuration)
5. [Scheduling](#scheduling)
6. [Data Storage](#data-storage)
7. [Security Considerations](#security-considerations)

## Architecture

The Bot Manager is a FastAPI application that manages multiple Discord selfbots through subprocesses. The architecture consists of:

1. **Manager Service**: The main FastAPI application that provides the web interface and API
2. **Bot Registry**: Manages bot instances, their lifecycle, and scheduling
3. **Bot Templates**: Base configurations used to create new bot instances
4. **Bot Instances**: Individual bot processes with their own configurations and data

### Flow
1. User creates a new bot through the UI/API
2. Manager copies the template to create a new bot instance
3. User configures the bot through the UI
4. User starts the bot, which spawns a subprocess
5. Bot runs according to its configuration
6. Logs and status are reported back to the manager

## API Endpoints

### Manager Settings
- `GET /api/manager/settings` - Get manager settings
- `PUT /api/manager/settings` - Update manager settings

### Bot Management
- `GET /api/bots` - List all bots
- `POST /api/bots` - Create a new bot
- `DELETE /api/bots/{bot_id}` - Delete a bot
- `POST /api/bots/{bot_id}/start` - Start a bot
- `POST /api/bots/{bot_id}/stop` - Stop a bot
- `POST /api/bots/{bot_id}/restart` - Restart a bot

### Configuration
- `GET /api/bots/{bot_id}/config` - Get bot configuration
- `PUT /api/bots/{bot_id}/config` - Update bot configuration

### Logs
- `GET /api/bots/{bot_id}/logs.txt` - Get bot logs as text
- `GET /api/bots/{bot_id}/logs` - Download bot logs as file

### WebSockets
- `WS /ws/status` - Real-time status updates for all bots
- `WS /ws/logs/{bot_id}` - Real-time log streaming for a specific bot
- `WS /ws/manager/logs` - Manager log streaming

## Bot Template Structure

Each bot is created from a template located in `templates/discum_selfbot/`:

```
templates/discum_selfbot/
├── bot.py              # Main bot script
├── config.sample.toml  # Sample configuration with placeholders
├── config.toml         # Actual configuration (gitignored)
└── README.md           # Template documentation
```

### bot.py
The main bot script that implements the Discord selfbot functionality using the `discum` library and Gemini API for AI responses.

### Configuration
The `config.toml` file contains all bot settings:
- Authentication tokens
- Channel IDs
- Persona settings
- Reply behavior
- Friendship engine
- Memory and facts
- Style mirroring
- Filters and triggers
- Emoji reactions
- Active hours
- Self-start behavior
- Rate limits
- Storage settings

## Configuration

### Manager Configuration
Manager settings are stored in `data/manager_settings.toml`:

```toml
[ui]
theme = "dark"               # UI theme
refresh_interval = 2000      # Status refresh interval (ms)

[logs]
max_lines = 1000             # Max lines in log display
auto_scroll = true           # Auto-scroll to new logs
buffer_size = 8192           # Log tailing buffer size

[web]
host = "0.0.0.0"             # Web server host
port = 8080                  # Web server port
```

### Bot Configuration
Each bot has its own `config.toml` with the following sections:

#### Authentication
```toml
discord_user_token = "YOUR_TOKEN"
gemini_api_key = "YOUR_API_KEY"
```

#### Channels
```toml
channel_ids = ["123456789012345678"]
```

#### Persona
```toml
[persona]
name = "BotName"
style = "Casual Banglish"
quirks = "Short, chatty lines"
boundaries = "No NSFW/offensive content"
```

#### Reply Behavior
```toml
[reply]
max_reply_chars = 600
min_delay_sec = 300
max_delay_sec = 600
```

#### Friendship Engine
```toml
[friendship]
start_score = 0
direct_mention_boost = 5
```

#### Memory & Facts
```toml
[memory]
max_history_per_channel = 15
enable_fact_learning = true
```

## Scheduling

Bots can be configured with schedules for automated actions:

```toml
[[schedules]]
name = "Morning Greeting"
action = "start"           # start|stop|restart|custom
cron = "0 9 * * *"         # Crontab format
# OR
every_seconds = 3600       # Interval in seconds
custom_cmd = "greet"       # Custom command for "custom" action
```

Schedule actions:
- `start`: Start the bot
- `stop`: Stop the bot
- `restart`: Restart the bot
- `custom`: Execute a custom command

Schedules can use either:
- `cron`: Standard crontab format
- `every_seconds`: Simple interval

## Data Storage

### Manager Data
- `data/manager_settings.toml`: Manager configuration
- `data/bots/`: Directory containing all bot instances

### Bot Data
Each bot instance stores its data in `data/bots/bot_X/`:
- `config.toml`: Bot configuration
- `logs/bot.log`: Bot logs
- `run.pid`: Process ID file
- `chatbrain.sqlite`: SQLite database with:
  - Chat history
  - User facts
  - Friendships
  - User topics
  - User style analysis
  - Channel counts
  - API statistics

## Security Considerations

### Discord Selfbots
Discord selfbots violate Discord's Terms of Service and may result in account termination. Use at your own risk.

### Credential Management
- Never commit actual credentials to version control
- Use the provided `config.sample.toml` as a template
- Store credentials in environment variables when possible
- Use the `.gitignore` file to exclude sensitive files

### Data Protection
- Bot data contains sensitive information (chat logs, user facts)
- Protect the `data/` directory with appropriate permissions
- Regularly backup important data
- Consider encryption for highly sensitive information

### Network Security
- The manager exposes a web interface - protect it with authentication if exposed to the internet
- Use HTTPS in production environments
- Restrict access to the manager's API