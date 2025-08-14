#!/bin/bash

# Bot Manager Setup Script

echo "Bot Manager Setup"
echo "================="

# Check if running on Linux or macOS
if [[ "$OSTYPE" != "linux-gnu"* && "$OSTYPE" != "darwin"* ]]; then
    echo "Warning: This script is designed for Linux/macOS. Please follow the README for manual setup."
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data/bots
fi

# Check if template config exists
if [ ! -f "templates/discum_selfbot/config.toml" ]; then
    echo "Creating template configuration from sample..."
    if [ -f "templates/discum_selfbot/config.sample.toml" ]; then
        cp templates/discum_selfbot/config.sample.toml templates/discum_selfbot/config.toml
        echo "Template configuration created. Please edit templates/discum_selfbot/config.toml with your credentials."
    else
        echo "Error: config.sample.toml not found. Please check your installation."
        exit 1
    fi
else
    echo "Template configuration already exists."
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit templates/discum_selfbot/config.toml with your credentials"
echo "2. Run 'docker-compose up --build' to start the manager"
echo "3. Visit http://localhost:8080/ui in your browser"