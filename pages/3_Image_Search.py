import streamlit as st
import sys 
import os

module_path = ".."
sys.path.append(os.path.abspath(module_path))
from utils import opensearch

st.set_page_config(
    page_title="Movie Search using Images",
    layout="wide",
    page_icon=":technologist:"
)

st.sidebar.header("Search Filters")

st.header(':movie_camera: Search for movies using Image :movie_camera:')
st.divider() 

st.subheader("Stay tuned, Coming Soon!")