---
title: AI Research Paper Recommender
emoji: 📄
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# AI Research Paper Recommender

A comprehensive system for discovering and recommending AI research papers using advanced NLP and RAG techniques.

## Features

- **Paper Ingestion**: Automated collection of papers from arXiv and metadata from Semantic Scholar
- **Data Processing**: Cleaning, feature extraction, and embedding generation
- **Storage**: PostgreSQL for metadata and Zillis Cloud (Milvus) for embedding storage, DGraph for citation graph storage, Supabase Object Storage for paper content JSONs
- **Recommendation Engine**: RAG-based paper retrieval and recommendation
- **Analytics**: Trend analysis and publication volume tracking
- **API**: FastAPI endpoints for recommendations
- **Frontend**: Streamlit-based user interface

## Project Structure

```
├── src/                    # Source code
│   ├── ingestion/          # Data collection
│   ├── transformation/     # Data processing
│   ├── storage/            # Data storage
│   ├── recommendation/     # Recommendation logic
│   ├── workflow/           # Workflow management
│   ├── api/                # FastAPI endpoints
│   ├── frontend/           # Streamlit app
├── Dockerfile              # docker file for building an image
├── run_pipeline.py         # prefect based logging pipeline runner
├── schedule_pipeline.py    # prefect based scheduling
└── requirements.txt        # Python dependencies

```

## Setup

1. Clone the repository:
```bash
git clone https://github.com/muhmmad-ahmad-1/ai601-research-paper-recommender.git
cd ai601-research-paper-recommender
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install grpcio==1.71.0
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration:
# - Supabase credentials
# - Zilliz Cloud (Milvus) credentials
# - DGraph credentials
# - Groq key
# - Google API Key
```
Link to our env has been provided with the submission

## Usage
1. Run an end to end pipeline (latest papers)
In a separate terminal:
```bash
prefect server start
```
then:

```bash
python run_pipeline.py
```

2. Schedule the pipeline:
```bash
python schedule_pipeline.py
```

Optional (in a separate terminal): 
```bash
prefect agent start -p default
```
Creates an agent that will listen for scheduled flows and run them on their time 

3. Start the Streamlit frontend:
```bash
streamlit run src/frontend/app.py
```

# Deployment
Streamlit App is deployed at [ResearchXplore](https://huggingface.co/spaces/ehmadsaeed/ResearchXplore)

Dockerization is complete, but registering the image is taking time due to the heavy packages

Details will be added in the GitHub repo
