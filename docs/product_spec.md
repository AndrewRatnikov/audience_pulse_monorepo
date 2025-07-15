# Product Specification – Audience Pulse AI Agent

**Version:** 1.0 (Initial Release – V1 Focus)  
**Product Name:** Audience Pulse AI Agent  
**Target User:** Product developers in personal lines (e.g., insurance, education, financial services, personal coaching, psychology) seeking real-time, automated insights from public social media channels.

---

## 1. Product Vision & Goal

Audience Pulse AI Agent transforms public social media content and engagement data into concise, actionable insights — in real time. By analyzing links to public Instagram, Facebook, and YouTube accounts, the agent delivers summaries, high-level engagement metrics, keyword themes, and sentiment snapshots to help product developers:

- Understand current market sentiment
- Identify audience needs and content resonance
- Spot emerging interest areas and trends
- Reduce manual research effort

> **Note:** This V1 release emphasizes real-time, snapshot-style analysis of publicly accessible data, without persistent storage or private data integration.

---

## 2. Core Features (V1 Scope)

### Supported Social Platforms

- Instagram
- Facebook
- YouTube

Users can input direct links to publicly accessible pages/profiles/channels on these platforms. Multiple links per session may be supported (batch-style), but **comparative analysis is not yet included**.

---

### Audience Metrics (Public Data Only)

- **Current Audience Size:**  
  Total followers/subscribers at the time of analysis.

- **Historical Growth Tracking:**  
  ✅ Deferred to future roadmap.

---

### Engagement Metrics (Platform-Specific)

- **Instagram:** Likes, comments per post (public only)
- **Facebook:** Likes, comments, shares, reactions per public post
- **YouTube:** Views, likes/dislikes, comments per video

#### ✅ Calculated Engagement Rate (Platform-Specific)

Derived as:  
`(Avg. Interactions per Post or Video) / Current Audience Size`

- **Instagram / Facebook:** Likes + Comments + Shares + Reactions (latest 10–15 posts)
- **YouTube:** Views + Likes + Comments (latest 5–10 videos)
- Displayed as a percentage
- Platform-specific benchmarks provided (if available)

---

### Text-Based Content Analysis

1. **Summary Generation**  
   Generates a brief, human-readable summary of overall themes in:

   - Captions (Instagram/Facebook)
   - Titles/descriptions/comments (YouTube)

2. **Keyword Extraction**

   - Frequently mentioned terms in captions, descriptions, or top comments
   - Highlights trending or recurring audience language

3. **Sentiment Analysis**
   - Basic NLP classification (positive, neutral, negative)
   - English-only (other languages passed through untagged in V1)
   - Analyzes top 500–1000 comments per post/video
   - _Note:_ Algorithmic approximation; sarcasm, ambiguity, or cultural nuance may be missed.

---

### Audience Interest Indicators (V1: Keyword Grouping)

- Extracted keywords grouped into high-level interest clusters using co-occurrence and semantic similarity.
- **Example:**
  - Keywords: `anxiety`, `stress`, `mental health`, `calm`
  - Inferred Cluster: **Mental Wellness**

> V1 uses lightweight co-occurrence techniques (e.g., TF-IDF + cosine similarity). No LDA or deep topic modeling included.

---

### Noise & Spam Filtering

- Filters common spam phrases and promotional content
- Deprioritizes bot-like or irrelevant comments

---

### Output Format

Structured text output includes:

- Audience size
- Engagement rate (per platform)
- Summary of themes
- Sentiment breakdown
- Keyword clusters / interest areas

> **Note:** Delivered synchronously when fast. For large accounts, asynchronous processing is triggered with user notification upon completion.

---

### Processing Constraints & Limits

- **Comment Volume Limit:** Up to 1000 comments analyzed per post/video
- **Processing Time Handling:** Uses async background jobs when API volume/load is high
- **Transparency:** Users informed of any sampling or processing limits

---

## 3. Technical & Architectural Principles

### Data Access & Compliance

- Uses only official APIs:
  - Instagram Graph API
  - Facebook Graph API
  - YouTube Data API
- Real-time, public, non-persistent data
- No scraping; fully TOS-compliant
- GDPR & privacy-by-design aligned

---

### NLP & AI Model Use

- Lightweight pipelines for:
  - Keyword extraction (TF-IDF + frequency)
  - Summarization (TextRank / BART-lite)
  - Sentiment analysis (VADER / fastText)

> **Focus on:** speed and explainability over deep learning complexity

---

### Architecture Notes

- Modular, microservice-style design
- API gateway handles analysis jobs with rate limits
- Async job queue (e.g., Celery, Sidekiq) for background processing
- Output rendered from JSON → markdown/text → UI layer (UI not covered here)

---

## 4. Future Enhancements (Planned Roadmap)

| Area                | Enhancement                                           |
| ------------------- | ----------------------------------------------------- |
| Growth Tracking     | Persistent storage + polling for follower counts      |
| Private Analytics   | OAuth login to access owned account metrics           |
| Platform Expansion  | TikTok, LinkedIn, Reddit support                      |
| Advanced Insights   | LDA / embedding-based topic modeling                  |
| Visual Reports      | Engagement trends, audience cluster charts            |
| Competitor Analysis | Side-by-side comparison of multiple accounts          |
| Multimedia Analysis | Analyze image thumbnails, video audio, visual content |
