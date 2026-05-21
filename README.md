# Voice Flight Agent

A conversational AI agent that lets you search for flights using natural language and responds with a voice output in **Gujarati**. Built entirely in Python, it combines LLM-powered intent extraction, the Skyscanner API for live flight data, and multilingual text-to-speech.

---

## Features

- **LLM-Powered Intent Extraction** — Uses [Groq](https://groq.com/) to extract origin, destination, and travel date from free-form text
- **Conversational State Management** — Tracks the conversation and asks follow-up questions if any details are missing
- **Live Flight Search** — Fetches real-time flight data via the [Skyscanner API on RapidAPI](https://rapidapi.com/skyscanner/api/skyscanner-flights-travel-api)
- **Flight Ranking** — Parses and ranks results by price, duration, and number of stops
- **Gujarati Text-to-Speech** — Reads flight results aloud in Gujarati using gTTS
- **Language Detection** — Detects the language of user input with langdetect
- **Audio Support** — Records and processes voice input using sounddevice and faster-whisper

---

## Project Structure

```
voice-flight-agent/
├── main.py                              # Entry point — runs the conversation loop
├── requirements.txt                     # Python dependencies
├── .env                                 # API keys (not committed to git)
├── .env.example                         # Template showing required env variables
├── .gitignore
├── app/
│   ├── llm/
│   │   ├── intent_extractor.py          # Extracts flight info via Groq LLM
│   │   ├── prompts.py                   # System prompt for intent extraction
│   │   └── schemas.py                   # Pydantic schema for flight intent
│   ├── conversation/
│   │   ├── state_manager.py             # Tracks conversation state and missing fields
│   │   └── question_generator.py        # Generates follow-up questions
│   ├── flights/
│   │   ├── providers/
│   │   │   └── skyscanner_provider.py   # Airport and flight search (Skyscanner API)
│   │   ├── parser.py                    # Parses raw API flight responses
│   │   └── ranker.py                    # Ranks flights by price, duration, stops
│   ├── response/
│   │   └── response_generator.py        # Formats flight results into readable text
│   ├── audio/
│   │   └── recorder.py                  # Records voice input from microphone
│   ├── stt/
│   │   └── whisper_engine.py            # Transcribes audio using faster-whisper
│   └── tts/
│       └── gujarati_tts.py              # Text-to-Speech output in Gujarati
├── tests/                               # All test files
└── temp/                                # Temporary audio files
```

---

## Installation

**Prerequisites:** Python 3.9+

```bash
# Clone the repository
git clone https://github.com/hiten4/voice-flight-agent.git
cd voice-flight-agent

# Install dependencies
pip install -r requirements.txt
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=your_groq_api_key
RAPIDAPI_KEY=your_rapidapi_key
RAPIDAPI_HOST=skyscanner-flights-travel-api.p.rapidapi.com
```

| Variable | Where to get it |
|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com/) |
| `RAPIDAPI_KEY` | [rapidapi.com](https://rapidapi.com/) — subscribe to the Skyscanner Flights Travel API |
| `RAPIDAPI_HOST` | Fixed value — copy exactly as shown above |

---

## Usage

```bash
python main.py
```

The agent holds a conversation to collect all required travel details before searching:

```
You: I want to fly from Ahmedabad to Delhi on June 15th
Assistant: Searching for flights...

Assistant:
I found 5 flight options.

Option 1:
IndiGo flight. Departure at 06:00 AM. Arrival at 08:10 AM.
Duration is 130 minutes. Ticket price is rupees 4500.

Option 2:
Air India flight. Departure at 09:30 AM. Arrival at 11:45 AM.
Duration is 135 minutes. Ticket price is rupees 5200.
[Gujarati voice response plays]
```

If any detail is missing, the agent asks for it:

```
You: I want to go to Mumbai
Assistant: Where are you travelling from?

You: Ahmedabad
Assistant: When do you want to travel?
```

---

## How It Works

1. **User Input** — The user types a flight query in natural language
2. **Intent Extraction** — Groq LLM parses the query and extracts source, destination, and date
3. **State Management** — Conversation state is updated; missing fields trigger a follow-up question
4. **Flight Search** — Once all details are collected, the Skyscanner API is queried for available flights
5. **Parse and Rank** — Raw flight data is parsed and ranked by price, duration, and stops
6. **Response Generation** — A human-readable response listing the top options is generated
7. **Voice Output** — The response is read aloud in Gujarati via gTTS

---

## Dependencies

| Package | Purpose |
|---|---|
| `groq` | LLM API for intent extraction |
| `requests` | HTTP calls to the Skyscanner RapidAPI |
| `faster-whisper` | Speech-to-text transcription |
| `gtts` | Google Text-to-Speech (Gujarati voice output) |
| `playsound` | Plays the generated audio file |
| `sounddevice` | Records audio from the microphone |
| `scipy` / `numpy` | Audio file processing |
| `pydantic` | Data validation for flight intent schema |
| `langdetect` | Detects the language of user input |
| `dateparser` | Parses natural language dates like 'tomorrow' or 'next Friday' |
| `python-dateutil` | Additional date parsing utilities |
| `python-dotenv` | Loads environment variables from `.env` |

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## License

This project is open source. See the repository for license details.