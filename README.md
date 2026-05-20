# Voice Flight Agent

A conversational AI agent that lets you search for flights using natural language and responds with a voice output in **Gujarati**. Built entirely in Python, it combines LLM-powered intent extraction, a live flight API, and multilingual text-to-speech.

---

## Features

- **LLM-Powered Intent Extraction** - Uses [Groq](https://groq.com/) to extract origin, destination, and travel date from free-form text
- **Conversational State Management** - Tracks the conversation and asks follow-up questions if any details are missing
- **Live Flight Search** - Fetches real-time flight data via the [Amadeus API](https://developers.amadeus.com/)
- **Flight Ranking** - Parses and ranks results to surface the most relevant options
- **Gujarati Text-to-Speech** - Reads flight results aloud in Gujarati using gTTS
- **Language Detection** - Detects the language of user input with langdetect
- **Audio Support** - Records and processes audio using sounddevice and faster-whisper

---

## Project Structure

The repository is organized into focused modules:

- **main.py** - Entry point that runs the conversation loop
- **app/llm/** - Intent extraction using the Groq LLM API
- **app/conversation/** - Conversation state manager and question generator
- **app/flights/** - Flight search providers (Amadeus), parser, and ranker
- **app/response/** - Response formatter for flight results
- **app/tts/** - Gujarati text-to-speech output
- **temp/** - Temporary audio cache files

---

## Installation

**Prerequisites:** Python 3.9+



---

## Environment Variables

Create a  file in the root directory:



| Variable | Where to get it |
|---|---|
| GROQ_API_KEY | [console.groq.com](https://console.groq.com/) |
| AMADEUS_CLIENT_ID | [developers.amadeus.com](https://developers.amadeus.com/) |
| AMADEUS_CLIENT_SECRET | [developers.amadeus.com](https://developers.amadeus.com/) |

---

## Usage



The agent holds a conversation to collect all required travel details before searching:



If any detail (origin, destination, or date) is missing, the agent will ask:



---

## Dependencies

| Package | Purpose |
|---|---|
|  | LLM API for intent extraction |
|  | Live flight search API |
|  | Speech-to-text transcription |
|  | Google Text-to-Speech (Gujarati output) |
|  | Audio recording |
|  /  | Audio processing |
|  | Data validation |
|  | Language detection |
|  | Flexible date parsing |
|  | Environment variable management |

---

## How It Works

1. **User Input** - The user types a flight query in natural language
2. **Intent Extraction** - Groq LLM parses the query to extract source, destination, and date
3. **State Management** - The conversation state is updated; missing fields trigger a follow-up question
4. **Flight Search** - Once all details are available, the Amadeus API is queried for available flights
5. **Parse and Rank** - Raw flight data is parsed and ranked by relevance
6. **Response Generation** - A human-readable response is generated
7. **Voice Output** - The response is read aloud in Gujarati via gTTS

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

This project is open source. See the repository for license details.
