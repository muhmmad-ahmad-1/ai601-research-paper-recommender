import streamlit as st
import time # For simulating delay

# --- Chatbot Backend (Mocked) ---
def get_mock_chatbot_response(user_query: str) -> str:
    """
    Simulates a backend call to a chatbot.
    Returns a markdown-formatted string.
    """
    time.sleep(1.5) # API Call here

    if "hello" in user_query.lower():
        return """
        Hi there! I am your AI Research Assistant. How can I help you today?
        You can ask me about research trends, specific papers, or authors.
        """
    elif "transformer models" in user_query.lower():
        return """
        Transformer models have revolutionized NLP. Here are some key insights:

        *   **Attention is All You Need (Vaswani et al., 2017):** The foundational paper.
            *   *Reference:* [arXiv:1706.03762](https://arxiv.org/abs/1706.03762)
        *   **BERT (Devlin et al., 2018):** Introduced bidirectional pre-training.
            *   *Reference:* [arXiv:1810.04805](https://arxiv.org/abs/1810.04805)

        **Recent Trends:**
        *   Larger models (e.g., GPT-3, PaLM)
        *   Efficiency improvements (e.g., sparse attention, distillation)
        *   Multimodal applications
        """
    elif "latest papers on reinforcement learning" in user_query.lower():
        return """
        Here are a couple of (hypothetical) recent insights in Reinforcement Learning:

        *   **"Self-Correcting Agents for Complex Environments" (AI Journal, 2024):** This paper discusses novel methods for agents to adapt to unforeseen changes.
            *   *Key takeaway:* Improved robustness in dynamic settings.
            *   *Reference:* (Hypothetical Paper ID: RL2024-001)
        *   **"Multi-Agent Collaboration with Shared Intent Modeling" (NeurIPS, 2023):** Focuses on how multiple agents can better coordinate.
            *   *Key takeaway:* Enhanced team performance in cooperative tasks.
            *   *Reference:* (Hypothetical Paper ID: RL2023-105)

        Please note: These are illustrative examples.
        """
    else:
        return f"""
        I'm still under development, but I've noted your query: "{user_query}".

        Here's a generic insight:
        *   The field of AI is rapidly evolving. Staying updated with pre-print servers like arXiv is crucial.
        *   *Reference:* [arXiv.org](https://arxiv.org/)
        """

# --- Chatbot Page UI ---
st.title("🤖 Conversational Research Assistant")
st.markdown("Ask me anything about AI research!")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is your research question?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("Thinking..."):
        response_markdown = get_mock_chatbot_response(prompt)
    
    with st.chat_message("assistant"):
        st.markdown(response_markdown)
    st.session_state.messages.append({"role": "assistant", "content": response_markdown})