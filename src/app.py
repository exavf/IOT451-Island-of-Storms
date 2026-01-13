# imports
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# page config
st.set_page_config(
    page_title="Main Page",
    layout="centered"
)

# title + intro text
st.title("Island of Storms: A Typhoon-Centric Dashboard for the Philippines")
st.write("An island-based dashboard for analysing extreme-value behaviour and climate-conditioned changes in Philippine typhoons.")
