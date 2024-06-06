import streamlit as st
import pandas as pd
 
## Create a sample DataFrame with latitude and longitude values
data = pd.DataFrame({
    'latitude': [38.57670000],
    'longitude': [-92.17352000]
})
#  ## Create a map with a specified zoom level

# ## Create a map with the data
# # Create a map with a specified zoom level and center
st.map(data=data, zoom=6, latitude="38.57670000", longitude="-92.17352000")
# Add an additional column for pop-up information
