<!-- Improved README.md -->
<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=32&duration=3000&pause=1000&color=81E6D9&center=true&vCenter=true&width=600&lines=Bot+Manager+(Pterodactyl-inspired);Discord+Selfbot+Management+System;AI-Powered+Chatbots" alt="Typing SVG" />
</div>

<p align="center">
  <img src="https://img.shields.io/github/license/R-Samir-Bhuiyan-A/bot-manager?style=for-the-badge&color=4a5568" alt="License" />
  <img src="https://img.shields.io/github/languages/top/R-Samir-Bhuiyan-A/bot-manager?style=for-the-badge&color=81e6d9" alt="Top Language" />
  <img src="https://img.shields.io/github/last-commit/R-Samir-Bhuiyan-A/bot-manager?style=for-the-badge&color=718096" alt="Last Commit" />
  <img src="https://img.shields.io/github/issues/R-Samir-Bhuiyan-A/bot-manager?style=for-the-badge&color=e53e3e" alt="Issues" />
</p>

<h2 align="center">🚀 A powerful web-based management interface for Discord selfbots</h2>

<p align="center">
  <b>Bot Manager</b> is inspired by Pterodactyl Panel and allows you to create, configure, and manage multiple selfbots from a single interface.
  <br>
  <i>Each bot runs as a subprocess within the manager's container with AI-powered responses.</i>
</p>

---

## 🌟 Features

<table>
  <tr>
    <td width="50%">
      <h3>🤖 Multiple Bot Management</h3>
      <ul>
        <li>Create unlimited selfbots from templates</li>
        <li>Individual configuration for each bot</li>
        <li>Start/Stop/Restart with one click</li>
        <li>Real-time status monitoring</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🧠 AI-Powered Responses</h3>
      <ul>
        <li>Gemini API integration for smart replies</li>
        <li>Persona-based conversation styles</li>
        <li>Mood-based response variations</li>
        <li>Context-aware conversation memory</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>⏰ Advanced Scheduling</h3>
      <ul>
        <li>Cron-based scheduling system</li>
        <li>Interval-based automation</li>
        <li>Custom command execution</li>
        <li>Flexible action triggers</li>
      </ul>
    </td>
    <td width="50%">
      <h3>🎨 Beautiful UI/UX</h3>
      <ul>
        <li>Dark theme with glassmorphism effects</li>
        <li>Responsive design for all devices</li>
        <li>Real-time log streaming</li>
        <li>Animated transitions and interactions</li>
      </ul>
    </td>
  </tr>
</table>

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/R-Samir-Bhuiyan-A/bot-manager.git
cd bot-manager

# Configure your bot template
cp templates/discum_selfbot/config.sample.toml templates/discum_selfbot/config.toml
# Edit templates/discum_selfbot/config.toml with your credentials

# Run with Docker Compose (development)
docker-compose up --build

# Visit http://localhost:8080/ui
```

## 🛠️ Installation

### Prerequisites
- **Docker** - Containerization platform
- **Docker Compose** - Multi-container Docker applications

### Environment Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/R-Samir-Bhuiyan-A/bot-manager.git
   cd bot-manager
   ```

2. **Configure Your Bot Template**
   ```bash
   cp templates/discum_selfbot/config.sample.toml templates/discum_selfbot/config.toml
   ```
   Edit `templates/discum_selfbot/config.toml` with your:
   - Discord user token
   - Gemini API key (for AI features)
   - Channel IDs to monitor
   - Bot persona settings

3. **Run the Application**

   **Development (with live reload):**
   ```bash
   docker-compose up --build
   ```
   Open http://localhost:8080/ui

   **Production:**
   ```bash
   docker build -t botmgr .
   docker run -p 8080:8080 -v $(pwd)/data:/data botmgr
   ```
   Open http://localhost:8080/ui

## 🤖 Bot Configuration

### Authentication
```toml
# DISCORD USER TOKEN (REQUIRED)
discord_user_token = "YOUR_DISCORD_USER_TOKEN_HERE"

# GEMINI API KEY (REQUIRED for AI features)
gemini_api_key = "YOUR_GEMINI_API_KEY_HERE"
```

### Persona Settings
```toml
[persona]
name = "Rafi"  # Bot name
style = "Casual Banglish with slang"
quirks = "Short, chatty lines with emojis"
moods = ["happy", "chill", "tired", "playful", "annoyed"]
```

### Reply Behavior
```toml
[reply]
max_reply_chars = 600
min_delay_sec = 300   # 5 minutes
max_delay_sec = 600   # 10 minutes
typing_speed_wpm = 120
```

## ⏰ Scheduling

Bots can be configured with automated schedules:

```toml
[[schedules]]
name = "Morning Greeting"
action = "start"       # start|stop|restart|custom
cron = "0 9 * * *"     # Crontab format (9 AM daily)
# OR
every_seconds = 3600   # Interval in seconds (1 hour)
custom_cmd = "greet"   # Custom command
```

## 📊 Data Persistence

Bot data and logs are stored in the `data/` directory:
- **Bot instances**: `data/bots/`
- **Manager settings**: `data/manager_settings.toml`

This directory is mounted as a volume in Docker to persist data between container restarts.

## 🔐 Security Notice

> **⚠️ Important:** This project uses Discord selfbots, which may violate Discord's Terms of Service. Use at your own risk.

### Credential Protection
- Real credentials are excluded via `.gitignore`
- Sample files provided for proper setup
- Never commit actual credentials to version control

## 🧠 Enhanced Bot Features

### Robust API Integration
- ✅ Retry mechanism with exponential backoff
- ✅ Better error handling for various failure modes
- ✅ API usage statistics tracking

### Advanced Prompt Engineering
- ✅ Better structured prompts for consistent responses
- ✅ Improved context management
- ✅ Detailed persona instructions

### Intelligent Error Handling
- ✅ Fallback responses based on current mood
- ✅ Comprehensive logging of API interactions
- ✅ Statistics tracking for performance monitoring

## 📁 Project Structure

```
bot-manager/
├── app/                 # Main application
│   ├── manager.py       # FastAPI application
│   ├── bots_manager.py  # Bot instance management
│   ├── schemas.py       # Pydantic models
│   ├── utils.py         # Utility functions
│   └── static/          # Frontend assets
├── templates/           # Bot templates
│   └── discum_selfbot/  # Selfbot template
├── data/                # Persistent data
├── docker-compose.yml   # Development setup
├── Dockerfile           # Production Dockerfile
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

Please ensure your code follows the existing style and includes appropriate tests.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Pterodactyl Panel](https://pterodactyl.io/) for UI inspiration
- [Discum](https://github.com/Merubokkusu/Discord-S.C.U.M) for Discord API interactions
- [Google Gemini](https://ai.google.dev/) for AI capabilities
- All contributors who have helped shape this project

---

<p align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&weight=600&size=24&duration=4000&pause=1000&color=81E6D9&center=true&vCenter=true&width=400&lines=Made+with+❤️;Happy+coding!;Discord+Bot+Management" alt="Typing SVG" />
</p>