import streamlit as st
import pandas as pd 
import numpy as np

st.set_page_config(
    page_title="AI Research Paper Recommender",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Functions for Dashboard (Placeholders) ---
@st.cache_data
def load_data():
    """Loads placeholder data for the dashboard."""
    # Replace with actual data loading (e.g., from CSV or API)
    dates = pd.to_datetime(['2020-01-01', '2020-07-01', '2021-01-01', '2021-07-01', '2022-01-01', '2022-07-01', '2023-01-01', '2023-07-01'])
    data = {
        'year': dates.year,
        'month': dates.month,
        'keyword_A_freq': np.random.randint(10, 100, size=len(dates)),
        'keyword_B_freq': np.random.randint(5, 80, size=len(dates)),
        'publications': np.random.randint(50, 200, size=len(dates)),
        'avg_citations': np.random.randint(5, 50, size=len(dates)),
        'timestamp': dates
    }
    df = pd.DataFrame(data)
    df['date_str'] = df['timestamp'].dt.strftime('%Y-%m')
    return df

def display_keyword_trends(df_filtered):
    """Displays keyword frequency trends."""
    st.subheader("Keyword Frequency Trends")
    st.line_chart(df_filtered, x='date_str', y=['keyword_A_freq', 'keyword_B_freq'])

def display_publications_per_year(df_filtered):
    """Displays number of publications per year."""
    st.subheader("Number of Publications Over Time")
    publications_data = df_filtered.groupby('year')['publications'].sum().reset_index()
    st.bar_chart(publications_data, x='year', y='publications')

def display_citation_trends(df_filtered):
    """Displays citation counts distribution or average citations."""
    st.subheader("Average Citations Over Time")
    st.line_chart(df_filtered, x='date_str', y='avg_citations')

def display_popular_papers_or_authors():
    """Displays most popular papers or authors (placeholder)."""
    st.subheader("Most Popular (Placeholder)")
    st.markdown("""
    *   Paper X by Author Y (1500 citations)
    *   Author Z (Overall 5000 citations)
    *   Paper A by Author B (1200 mentions)
    """)

# --- Main Application Logic for Dashboard ---
st.title("📊 Research Trends Dashboard")
st.markdown("Visualize trends in AI research based on publication data.")

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Dashboard Filters")

min_date = df['timestamp'].min().date()
max_date = df['timestamp'].max().date()

default_start_date = min_date
default_end_date = max_date

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(default_start_date, default_end_date),
    min_value=min_date,
    max_value=max_date,
    key="date_filter"
)

start_date, end_date = date_range
start_datetime = pd.to_datetime(start_date)
end_datetime = pd.to_datetime(end_date)

study_fields = ["All", "Natural Language Processing", "Computer Vision", "Reinforcement Learning"]
selected_field = st.sidebar.selectbox("Filter by Field of Study", study_fields, key="field_filter")

selected_keyword = st.sidebar.text_input("Filter by Keyword (e.g., 'transformer')", key="keyword_filter")

df_filtered = df[
    (df['timestamp'] >= start_datetime) & (df['timestamp'] <= end_datetime)
]
if selected_field != "All":
    st.sidebar.caption(f"Field filter for '{selected_field}' is a placeholder.")
if selected_keyword:
    st.sidebar.caption(f"Keyword filter for '{selected_keyword}' is a placeholder.")

st.header("AI Research Insights")

col1, col2 = st.columns(2)
with col1:
    display_keyword_trends(df_filtered)
with col2:
    display_publications_per_year(df_filtered)

col3, col4 = st.columns(2)
with col3:
    display_citation_trends(df_filtered)
with col4:
    display_popular_papers_or_authors()

if st.checkbox("Show Raw Data"):
    st.subheader("Raw Data")
    st.dataframe(df_filtered)

st.markdown("---")