import os
import bcrypt
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from supabase import create_client, Client
import asyncio
import numpy as np
import logging
import matplotlib
import plotly


# Initialize Supabase client
supabaseUrl = 'https://gippopxafisxpvrkkplt.supabase.co'
supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdpcHBvcHhhZmlzeHB2cmtrcGx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI1MjM1MTcsImV4cCI6MjA0ODA5OTUxN30.ldQh7QxpG08pERpOKl_-3gGr8CTYdPKGx83dDYJe5ZM"  # Ensure your environment variable is set
supabase: Client = create_client(supabaseUrl, supabaseKey)

# Function to fetch categories
async def fetch_categories():
    try:
        response = supabase.table('categories').select('category_id, category_name').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching categories: {e}")
        return pd.DataFrame(columns=['category_id', 'category_name'])

# Function to fetch expenses with filters and pagination
async def fetch_expenses(user_id, month_num=None, year=None, category_id=None, offset=0, limit=10):
  try:
    # Handle category_id to ensure it is an integer (in case it's passed as np.int64)
    if isinstance(category_id, np.int64):
      category_id = int(category_id)

    # Prepare parameters for the RPC call
    params = {
      "user_id_input": user_id,  # user_id is an integer from the `users` table
      "month_num_input": month_num,
      "year_input": year,
      "category_id_input": category_id,
      "offset_input": offset,
      "limit_input": limit
    }

    # Call the RPC function or table query
    response = supabase.rpc("fetch_expenses", params).execute()

    # Convert response to a DataFrame
    if response.data:
      cleaned_data = []
      for row in response.data:
        cleaned_row = {}
        for key, value in row.items():
          # If the value is of type np.int64, convert it to a regular int
          if isinstance(value, np.int64):
            cleaned_row[key] = int(value)
          else:
            cleaned_row[key] = value
        cleaned_data.append(cleaned_row)

      df = pd.DataFrame(cleaned_data)

      # Rename columns
      df.columns = ['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category']

      return df
    else:
      return pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])

  except Exception as e:
    st.error(f"Error fetching expenses: {e}")
    return pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])

# Helper function to run async code within the synchronous environment
def run_async(coroutine_func):
    return asyncio.run(coroutine_func)



# Login Screen
if st.title("Login to Expense Tracker"):

# Main Menu Screen
elif st.session_state.current_screen == "main_menu":
    st.title("Expense Tracker Dashboard")
    # Initialize pagination state variables if they don't exist
    if 'page_offset' not in st.session_state:
        st.session_state.page_offset = 0  # Initialize offset for pagination
    if 'page_limit' not in st.session_state:
        st.session_state.page_limit = 10  # Records per page

    categories_df = run_async(fetch_categories())
    
    if categories_df.empty:
        st.write("No categories available.")
    else:
        category_names = categories_df['category_name'].tolist()

    # Month Names Dropdown (Jan, Feb, etc.)
    month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month = st.selectbox("Select Month", month_names)

    # Year Dropdown
    year = st.selectbox("Select Year", ["All", 2023, 2024])

    # Category Dropdown
    category = st.selectbox("Select Category", ["All"] + category_names)

    # Determine category ID from category name
    category_id = None if category == "All" else categories_df[categories_df['category_name'] == category]['category_id'].values[0]

    # Determine month number from selected month
    month_num = None if month == "All" else month_names.index(month)

    # Determine year from selected year
    year_num = None if year == "All" else int(year)

    # Fetch expenses with filters and pagination
    expenses_df = run_async(fetch_expenses(
        st.session_state.user_id,
        month_num=month_num,
        year=year_num,
        category_id=category_id,
        offset=st.session_state.page_offset,
        limit=st.session_state.page_limit))

    # Display the icons for Add, Edit, and Delete actions
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col3:
        if st.button("➕ Add"):
            st.session_state.current_screen = "add_expense"
            st.rerun()
    
    with col2:
        if st.button("✏️ Edit"):
            st.session_state.current_screen = "edit_expense"
            st.rerun()

    with col4:
        if st.button("🗑️ Delete"):
            st.session_state.current_screen = "confirm_delete"
            st.rerun()

    with col1:
        if st.button("📊 Chart"):
            st.session_state.current_screen = "heatmap_view"
            st.rerun()    

    with col5:
        if st.button("🔄 Refresh"):
            st.rerun()  

    # Display the expenses DataFrame with expense ID included and no index column 
    if not expenses_df.empty: 
        st.write("### Expense Details") 
        st.dataframe(expenses_df) 
    else: 
        st.write("No expenses found based on the selected filters.")

    # Pagination: Back and Next buttons 
    col1, col2 = st.columns([1, 1]) 

    with col1: 
        if (st.button("← Back") and 
                (st.session_state.page_offset > 0)): 
            # Go to previous page 
            st.session_state.page_offset -= (st.session_state.page_limit) 

    with col2:
        if (st.button("Next →")): 
            # Go to next page 
            st.session_state.page_offset += (st.session_state.page_limit)

    if st.button("Logout"): 
        st.session_state.user_id = None  
        st.session_state.current_screen = "login"  
        st.rerun()

# Heatmap Screen
elif st.session_state.current_screen == "heatmap_view":
    set_background(chart_img)
    st.title("Expense Chart")

    try:
        # Fetch expenses data with filters applied (month, year, category)
        expenses_df = run_async(fetch_expenses(
            st.session_state.user_id,
            month_num=st.session_state.get("month_num"),  # Filtered month
            year=st.session_state.get("year_num"),       # Filtered year
            category_id=st.session_state.get("category_id")  # Filtered category
        ))

        if not expenses_df.empty:
            # Debugging: Print or log filtered data
            st.write("Filtered Expenses Data:")
            st.dataframe(expenses_df)

            # Preprocessing expenses data
            expenses_df['Expense Date'] = pd.to_datetime(expenses_df['Expense Date'], errors='coerce').dt.to_period('M').astype(str)
            expenses_df['Amount'] = pd.to_numeric(expenses_df['Amount'], errors='coerce')
            expenses_df = expenses_df.dropna(subset=['Expense Date', 'Amount'])

            # Heatmap visualization
            heatmap_data = expenses_df.groupby(['Expense Date', 'Category'])['Amount'].sum().unstack(fill_value=0)
            plt.figure(figsize=(10, 6))
            sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", fmt='.2f')
            st.pyplot(plt)

    except Exception as e:
        st.error(f"Error generating visualizations: {e}")

    # Navigation button
    if st.button("⬅️"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

