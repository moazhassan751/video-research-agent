# Video Research & Synthesis Agent Platform

An enterprise-grade, autonomous AI agent platform for video discovery, speech-to-text audio transcription, and structured insights synthesis. Built with a modern, zero-emoji dark dashboard interface.

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit_Cloud-FF4B4B?style=for-the-badge&logo=streamlit)](https://video-research-agent-moaz.streamlit.app/)
[![Video Demo](https://img.shields.io/badge/Video_Demo-Google_Drive-4285F4?style=for-the-badge&logo=googledrive)](https://drive.google.com/file/d/1iwyRlNu1ZoQQWmqYY4e4G1pXGhzZJjL2/view?usp=sharing)

### Live Links & Demo
- **Deployed Web App**: [video-research-agent-moaz.streamlit.app](https://video-research-agent-moaz.streamlit.app/)
- **Video Walkthrough Demo**: [Watch Video Demo on Google Drive](https://drive.google.com/file/d/1iwyRlNu1ZoQQWmqYY4e4G1pXGhzZJjL2/view?usp=sharing)

---

## Key Features

- **Dark Enterprise UI**: Sleek, high-contrast dark dashboard designed with strict zero-emoji aesthetics, custom SVG vector icons, and smooth micro-interactions.
- **Autonomous Agent Loop**: Powered by Groq LLaMA 3.3 70B with local function calling to dynamically search, download, transcribe, and analyze videos without hardcoded sequences.
- **Real-Time Step Pipeline**: Live progress visualization across 4 core execution stages:
  1. *Ingesting Video Data* (SerpApi YouTube Search)
  2. *Generating Transcripts & Keywords* (Whisper Speech Engine)
  3. *Identifying Key Scenes & Moments* (Content Structuring)
  4. *Synthesizing Insights Report* (AI Summary & Analysis)
- **Rich Media Cards**: Automatic high-resolution YouTube video thumbnail extraction, uploader metadata, and direct watch links.
- **Knowledge Base Document Explorer**: Built-in viewer and search engine for stored transcript text files in `knowledge_base/`.
- **Fully Responsive**: Fluid grid layouts that automatically adapt from desktop to mobile screens.

---

## Technology Stack

| Layer | Component / Tool | Description |
| :--- | :--- | :--- |
| **User Interface** | Streamlit + Custom CSS | Enterprise Dark Dashboard with custom SVG Data-URI styling |
| **LLM Backbone** | Groq (`llama-3.3-70b-versatile`) | Autonomous decision-making, tool invocation, & final synthesis |
| **Speech-to-Text** | Groq (`whisper-large-v3-turbo`) | High-speed audio transcription engine |
| **Search Engine** | SerpApi (YouTube Engine) | Structured video discovery and metadata retrieval |
| **Audio Processing** | `yt-dlp` | Audio stream extractor (M4A / WebM) |

---

## Project Structure

```text
AGENTS/
├── app.py                  # Main Streamlit web dashboard application
├── main.py                 # Interactive CLI entry point
├── agent.py                # Core multi-turn agentic orchestration loop
├── tools/
│   ├── __init__.py         # Tools package initialization
│   ├── video_search.py     # YouTube search tool & schema (SerpApi)
│   └── transcription.py    # Audio downloader (yt-dlp) & Whisper transcription
├── knowledge_base/         # Local directory for stored transcript .txt files
├── index.html              # Standalone static HTML dashboard preview
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment template for API keys
└── .gitignore              # Git ignore rules for credentials & caches
```

---

## Quick Start Guide

### 1. Prerequisites
Ensure you have **Python 3.10+** installed on your system.

### 2. Installation
Clone this repository and install the required dependencies:

```bash
# Clone repository (or navigate to workspace directory)
cd AGENTS

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root directory by copying `.env.example`:

```bash
# Windows PowerShell
copy .env.example .env

# Linux / MacOS
cp .env.example .env
```

Open `.env` and configure your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here
```

> **Note**: 
> - Obtain a Groq API Key at [console.groq.com](https://console.groq.com/)
> - Obtain a SerpApi Key at [serpapi.com](https://serpapi.com/)

---

## How to Run

### Web Dashboard Interface (Recommended)
Launch the dark enterprise web dashboard:

```bash
streamlit run app.py
```
Open your browser to `http://localhost:8501`.

### Command Line Interface (CLI)
Run the agent directly from the terminal:

```bash
# Run interactively
python main.py

# Or pass a query directly
python main.py "how transformers work in AI"
```

---

## How It Works

1. **User Request**: The user submits a research prompt or YouTube video query.
2. **Tool Selection**: Groq LLaMA inspects the prompt and invokes `search_video(query)`.
3. **Video Ingestion**: SerpApi fetches matching YouTube video metadata and thumbnail URLs.
4. **Transcription**: The agent invokes `transcribe_video(video_url)`, extracting audio via `yt-dlp` and generating a full transcript via Groq Whisper.
5. **Knowledge Storage**: Transcripts are automatically stored in UTF-8 format inside `knowledge_base/`.
6. **Synthesis**: LLaMA synthesizes the transcript into a structured Insights Report with key highlights.

---

## License

MIT License. Designed for AI Agent research and enterprise synthesis workflows.
