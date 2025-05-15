# pages/02_Citation_Graph.py
import streamlit as st
import networkx as nx
import matplotlib.pyplot as plt
import sys
import json
from pathlib import Path

# Go up 3 levels: pages → frontend → src
src_path = Path(__file__).resolve().parents[2]
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from recommendation import CitationLogic

st.title("📈 Citation Graph Explorer")

def query_graph():
    functionality = CitationLogic()
    
    try:
        res = functionality.fetch_all_citation_graph(50)
        return json.loads(res)['allPapers']
    except Exception as e:
        st.error(f"Graph query failed: {e}")
        return None

def build_graph(data):
    obj = data
    g = nx.DiGraph()

    for paper in obj:
        paper_title = paper["title"]
        g.add_node(paper_title)

        for cited in paper.get("cites", []):
            cited_title = cited["title"]
            g.add_node(cited_title)
            g.add_edge(paper_title, cited_title)
    return g

graph_data = query_graph()
if graph_data:
    G = build_graph(graph_data)
    plt.figure(figsize=(12, 8))
    nx.draw_networkx(G, with_labels=True, node_size=500, font_size=8, arrows=True)
    st.pyplot(plt.gcf())
else:
    st.warning("No citation graph data found.")
