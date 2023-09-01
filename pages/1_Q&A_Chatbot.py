import streamlit as st
import sys
import os

module_path = ".."
sys.path.append(os.path.abspath(module_path))
from utils import bedrock
from utils import opensearch

# global constants
session_variables = [("question", []), ("answer", [])]
_ = [st.session_state.setdefault(k, v) for k,v in session_variables]

if "shared" not in st.session_state:
   st.session_state["shared"] = True

def get_answers(question, model_filter, knowledgebase_filter):
    context = " "
    answer = ""
    try:
        # Query OpenSearch by converting text to vector, and retrieve top X maching chunks
        response = opensearch.query_qna(question, "opensearch_qna")
        for i, rel_doc in enumerate(response["hits"]["hits"]):
            context += response["hits"]["hits"][i]["fields"]["content"][0]
    except ValueError:
        st.write("Sorry, We could not find an answer, please try again!")
        return

    if model_filter == "Titan":
        # Pass 20K char for context, as Titan fails beyond that
        prompt = opensearch.get_titan_prompt(context[:20000], question, knowledgebase_filter)
        answer = opensearch.titan_llm(prompt)
    else:
        # Pass 36K char for context, as Claude fails beyond that
        prompt = opensearch.get_claude_prompt(context[:36000], question, knowledgebase_filter)
        answer = opensearch.claude_llm(prompt)

    st.session_state.question.append(question)
    st.session_state.answer.append(f"Answer By {model_filter} 🎯:" + answer)


st.set_page_config(
    page_title="Amazon OpenSearch Service Question Answering App",
    layout="wide",
    page_icon=":technologist:"
)

st.sidebar.header("Q&A ChatBot Filters")

st.header('Maximizing AI Potentials: Perform Intelligent Enterprise Search for your OpenSearch documents and blogs :technologist:')
st.caption('by Leveraging Foundational Models from :blue[Amazon Bedrock and Amazon OpenSearch Serverless as Vector Engine]')
st.divider()
question = st.text_input("Ask me anything about OpenSearch:", "Difference between OpenSearch Service and OpenSearch Serverless")

# Filters
with st.sidebar.form("Q&A Form"):
    model_filter = st.sidebar.selectbox("Select LLM Model", ["Claude", "Titan"])
    knowledgebase_filter = st.sidebar.toggle("Within Knowledge Base", value=True )

if question:
    get_answers(question, model_filter, knowledgebase_filter)

    # Create Expander for Conversational Search
    with st.expander("Conversational Search", expanded=True):
        for i in range(len(st.session_state['answer'])-1, -1, -1):
            st.info(st.session_state["question"][i],icon="❓")
            st.success(st.session_state["answer"][i], icon="🧑")

