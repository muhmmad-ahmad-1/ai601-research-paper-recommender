import logging
import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client

from dotenv import load_dotenv
import os
load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
supabase = create_client(
    os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
st.set_page_config(
    page_title="AI Research Paper Recommender",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helper Functions for Dashboard ---


@st.cache_data
def load_all_keywords():
    """Loads all unique keyword names from the Supabase 'keywords' table."""
    try:
        response = supabase.table('keywords').select('name').execute()
        if response.data:
            keywords = sorted(
                list(set([item['name'] for item in response.data])))
            return keywords
        else:
            logger.info("No keywords found in the database.")
            return []
    except Exception as e:
        logger.error(f"Error fetching all keywords: {e}")
        st.error(f"Error fetching keywords: {e}")
        return []


@st.cache_data
def load_keyword_publication_trend_data(keyword_name: str):
    """Loads publication trend data for a specific keyword from Supabase."""
    try:
        response = supabase.rpc('keyword_publication_trend', {
                                'keyword_name': keyword_name}).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Ensure columns are 'year' and 'paper_count' as per the SQL function
            return df
        else:
            logger.info(
                f"No publication trend data returned for keyword: {keyword_name}")
            return pd.DataFrame({'year': [], 'paper_count': []})
    except Exception as e:
        logger.error(
            f"Error fetching publication trend for keyword {keyword_name}: {e}")
        st.error(f"Error fetching publication trend for {keyword_name}: {e}")
        return pd.DataFrame({'year': [], 'paper_count': []})


@st.cache_data
def load_avg_citations_trend_data(keyword_name: str):
    """Loads average citation trend data for a specific keyword from Supabase."""
    try:
        response = supabase.rpc('avg_citations_over_time', {
                                'keyword_name': keyword_name}).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Ensure columns are 'year' and 'avg_citations'
            return df
        else:
            logger.info(
                f"No average citation trend data returned for keyword: {keyword_name}")
            return pd.DataFrame({'year': [], 'avg_citations': []})
    except Exception as e:
        logger.error(
            f"Error fetching average citation trend for keyword {keyword_name}: {e}")
        st.error(
            f"Error fetching average citation trend for {keyword_name}: {e}")
        return pd.DataFrame({'year': [], 'avg_citations': []})


@st.cache_data
def load_popular_papers_by_keyword_data(keyword_name: str):
    """Loads most popular papers for a specific keyword from Supabase."""
    try:
        # Ensure the SQL function parameter is 'keyword_name'
        response = supabase.rpc('most_popular_papers_by_keyword', {
                                'keyword_name': keyword_name}).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Expected column: 'result' (text)
            return df
        else:
            logger.info(
                f"No popular papers data returned for keyword: {keyword_name}")
            return pd.DataFrame({'result': []})
    except Exception as e:
        logger.error(
            f"Error fetching popular papers for keyword {keyword_name}: {e}")
        st.error(f"Error fetching popular papers for {keyword_name}: {e}")
        return pd.DataFrame({'result': []})


def display_keyword_trends(keyword_name: str):
    """Displays keyword publication frequency trends over years for a specific keyword."""
    st.subheader(f"Publication Trend for the Keyword:")
    trend_df = load_keyword_publication_trend_data(keyword_name)
    if not trend_df.empty and 'year' in trend_df.columns and 'paper_count' in trend_df.columns:
        trend_df['year'] = trend_df['year'].astype(int)
        trend_df = trend_df.sort_values(by='year')
        st.line_chart(trend_df.set_index('year')['paper_count'], x_label='Year', y_label='Publications')
    else:
        st.markdown(
            f"No publication trend data available for keyword: \"{keyword_name}\".")


def display_publications_per_year(df_filtered):
    """Displays number of publications per year."""
    st.subheader("Number of Publications Over Time")
    publications_data = df_filtered.groupby(
        'year')['publications'].sum().reset_index()
    st.bar_chart(publications_data, x='year', y='publications')


def display_citation_trends(keyword_name: str):
    """Displays average citation trends over years for a specific keyword."""
    st.subheader(
        f"Average Citations Over Time:")
    trend_df = load_avg_citations_trend_data(keyword_name)
    if not trend_df.empty:
        trend_df = trend_df.sort_values(by='year')
        st.line_chart(trend_df.set_index('year')['avg_citations'], x_label='Year', y_label='Average Citations')
    else:
        st.markdown(
            f"No average citation data available for keyword: \"{keyword_name}\".")


def display_popular_papers_or_authors(keyword_name: str = None):
    """Displays most popular papers or authors."""
    if keyword_name:
        st.subheader(f"Most Popular Papers: ")
        papers_df = load_popular_papers_by_keyword_data(keyword_name)
        if not papers_df.empty:
            for index, row in papers_df.iterrows():
                title = row.get('title', 'Title N/A')
                author_name = row.get('author_name', 'Author N/A')
                citation_count = row.get('citation_count', 'Citations N/A')
                pdf_url = row.get('pdf_url')

                if pdf_url:
                    linked_title = f"[{title}]({pdf_url})"
                else:
                    linked_title = title

                st.markdown(
                    f"*   {linked_title} by {author_name} ({citation_count} citations)")
        else:
            st.markdown(
                f"No popular paper data available for keyword: \"{keyword_name}\".")


@st.cache_data
def load_most_published_keywords_data():
    """Loads data from the most_published_keywords Supabase function."""
    try:
        response = supabase.rpc('most_published_keywords').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            return df
        else:
            logger.error("No data returned from most_published_keywords RPC.")
            return pd.DataFrame({'keyword': [], 'publication_count': []})
    except Exception as e:
        logger.error(f"Error fetching most published keywords: {e}")
        st.error(f"Error fetching most published keywords: {e}")
        # Return empty DataFrame on error
        return pd.DataFrame({'keyword': [], 'publication_count': []})


def display_most_published_keywords():
    """Displays a bar chart of most published keywords."""
    df_keywords = load_most_published_keywords_data()
    if not df_keywords.empty:
        st.subheader("Most Published Keywords")
        st.bar_chart(df_keywords.set_index('keyword')[
                     'publication_count'], x_label='Keywords', y_label='Publications', color='#FF611D')
    else:
        st.subheader("Most Published Keywords")
        st.markdown("No keyword data available or error fetching data.")


@st.cache_data
def load_most_popular_authors_data():
    """Loads data from the most_popular_authors Supabase function."""
    try:
        response = supabase.rpc('most_popular_authors').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            return df
        else:
            logger.error("No data returned from most_popular_authors RPC.")
            return pd.DataFrame({'author_name': [], 'citation_count': []})
    except Exception as e:
        logger.error(f"Error fetching most popular authors: {e}")
        st.error(f"Error fetching most popular authors: {e}")
        return pd.DataFrame({'author_name': [], 'citation_count': []})


def display_most_popular_authors():
    """Displays a bar chart of most popular authors with rotated x-axis labels."""
    df_authors = load_most_popular_authors_data()
    if not df_authors.empty:
        st.subheader("Most Popular Authors by Citations")
        st.bar_chart(df_authors.set_index('author_name')[
                     'citation_count'], x_label='Authors', y_label='Citations', color='#E80C6F')

    else:
        st.subheader("Most Popular Authors")
        st.markdown("No author data available or error fetching data.")


@st.cache_data
def load_top_domains_data():
    """Loads data from the top_domains Supabase function."""
    try:
        response = supabase.rpc('top_domains').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            # Expected columns: 'domain', 'paper_count'
            return df
        else:
            logger.error("No data returned from top_domains RPC.")
            return pd.DataFrame({'domain': [], 'paper_count': []})
    except Exception as e:
        logger.error(f"Error fetching top domains: {e}")
        st.error(f"Error fetching top domains: {e}")
        return pd.DataFrame({'domain': [], 'paper_count': []})


def display_top_domains():
    """Displays a bar chart of top domains by paper count."""
    df_domains = load_top_domains_data()
    if not df_domains.empty:
        st.subheader("Top Domains by Paper Publications")
        st.bar_chart(df_domains.set_index('domain')[
                     'paper_count'], x_label='Domains', y_label='Paper Count')
    else:
        st.subheader("Top Domains")
        st.markdown("No domain data available or error fetching data.")


# --- Main Application Logic for Dashboard ---
st.title("📊 Research Trends Dashboard")
st.markdown("Visualize trends in AI research based on publication data.")

# --- Sidebar Filters ---
st.sidebar.header("Dashboard Filters")


all_keywords = load_all_keywords()
overview_option = "Show Overview"  # Option to show general charts

# Prepend the overview option to the list of keywords
keyword_options = [overview_option] + all_keywords

selected_keyword_option = st.sidebar.selectbox(
    "Select Keyword for Specific Trends (or Show Overview)",
    options=keyword_options,
    key="keyword_filter"
)

if selected_keyword_option == overview_option:
    st.header("Overall Research Insights")
    # Display Most Published Keywords
    display_most_published_keywords()
    # Display Most Popular Authors
    display_most_popular_authors()
    # Display Top Domains
    display_top_domains()
else:
    # A specific keyword is selected
    selected_keyword = selected_keyword_option  # Actual keyword name
    st.subheader(
        f"Insights for Keyword: **{selected_keyword}**")

    # Display publication trend for the selected keyword
    display_keyword_trends(selected_keyword)

    col1, col2 = st.columns(2)
    with col1:
        display_citation_trends(selected_keyword)
    with col2:
        display_popular_papers_or_authors(selected_keyword)

st.markdown("---")
