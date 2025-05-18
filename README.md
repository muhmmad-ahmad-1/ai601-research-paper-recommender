---
title: AI Research Paper Recommender
emoji: 📄
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.45.0"
app_file: src/frontend/app.py
pinned: false
---

# AI Research Paper Recommender

A comprehensive system for discovering and recommending AI research papers using advanced NLP and RAG techniques.

# Note: This branch is still under development. Please refer to the pipeline_fixing class for the latest updated/working code with proper instructions

## Features

- **Paper Ingestion**: Automated collection of papers from arXiv and Semantic Scholar
- **Data Processing**: Cleaning, feature extraction, and embedding generation
- **Storage**: PostgreSQL for metadata and Zillis Cloud (Milvus) for embedding storage, Supabase Object Storage for paper content jsons
- **Recommendation Engine**: RAG-based paper retrieval and recommendation
- **Analytics**: Trend analysis and publication volume tracking
- **API**: FastAPI endpoints for recommendations
- **Frontend**: Streamlit-based user interface

## Project Structure

```
├── data/                    # Data storage
│   ├── raw/                # Raw data from APIs
│   ├── processed/          # Cleaned and transformed data
│   └── embeddings/         # Generated embeddings
├── src/                    # Source code
│   ├── ingestion/          # Data collection
│   ├── transformation/     # Data processing
│   ├── storage/            # Data storage
│   ├── analytics/          # Analytics computation
│   ├── recommendation/     # Recommendation logic
│   ├── workflow/           # Workflow management
│   ├── api/                # FastAPI endpoints
│   ├── frontend/           # Streamlit app
│   └── utils/              # Utility functions
├── tests/                  # Unit tests
├── deployment/             # Deployment config
└── requirements.txt        # Python dependencies
```

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai601-research-paper-recommender.git
cd ai601-research-paper-recommender
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration:
# - PostgreSQL credentials
# - Backblaze B2 credentials (application key ID and key)
# - B2 bucket name
```

4. Initialize the database:
```bash
python src/storage/database.py
```

## Usage

1. Start the API server:
```bash
uvicorn src.api.main:app --reload
```

2. Start the Streamlit frontend:
```bash
streamlit run src/frontend/app.py
```

## Development

- Run tests: `pytest`
- Format code: `black .`
- Lint code: `flake8`

## License

MIT License
