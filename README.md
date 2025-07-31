# 🎯 Audience Pulse AI Agent

Audience Pulse is an AI-powered tool that analyzes public social media profiles and content to deliver instant, actionable insights on audience engagement, sentiment, and topical trends.

It supports platforms like Instagram, Facebook, and YouTube, and is designed for product developers working in personal lines industries (e.g., insurance, education, coaching, mental health).

The system combines platform-specific data collection with a lightweight NLP pipeline to provide:

- Public audience and engagement metrics
- Text summarization of post content
- Keyword extraction and interest grouping
- Sentiment analysis from public comments

Built with a modular backend (FastAPI, Python) and a modern frontend (React, TypeScript).

> **Note**: This is the MVP version, focused on real-time public data only.

## Instructions

To run the backend project locally:

1. Open a terminal and navigate to the `backend` directory:
  ```bash
  cd backend
  ```

2. Create and activate your own Python virtual environment using `venv`:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```
  
3. Start the FastAPI server with Uvicorn:
  ```bash
  uvicorn app.main:app --reload
  ```

The API will be available at http://127.0.0.1:8000
