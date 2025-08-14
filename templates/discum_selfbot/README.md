# Enhanced Discum Selfbot Template

This is an upgraded version of the discum selfbot template with several improvements:

## Key Enhancements

1. **Robust Gemini API Integration**:
   - Retry mechanism with exponential backoff
   - Better error handling for various failure modes
   - Improved request configuration with safety settings
   - API usage statistics tracking

2. **Enhanced Prompt Engineering**:
   - Better structured prompts for more consistent responses
   - Improved context management
   - More detailed persona instructions

3. **Advanced Error Handling**:
   - Fallback responses based on current mood
   - Comprehensive logging of API interactions
   - Statistics tracking for monitoring performance

4. **Code Improvements**:
   - Type hints for better code clarity
   - Modular functions for easier maintenance
   - Improved database schema with API stats tracking

## Configuration

The `config.toml` file contains all the customizable parameters for the bot's behavior.

## Database Schema

The bot uses SQLite for persistent storage with the following tables:
- chat_history: Message history for context
- user_facts: Extracted user information
- friendships: User relationship scores
- user_topics: User interest tracking
- user_style: User communication style analysis
- channel_counts: Message rate limiting
- api_stats: Gemini API usage statistics

## API Statistics

The bot now tracks API usage statistics in the `api_stats` table, which can be used to monitor:
- Success rate of API calls
- Error patterns
- Token usage over time