import streamlit as st
import pandas as pd
from supabase import create_client, Client
import asyncio

# Initialize Supabase client
supabaseUrl = 'https://gippopxafisxpvrkkplt.supabase.co'
supabaseKey = "YOUR_SUPABASE_KEY"  # Replace with your actual Supabase key
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
        params = {
            "user_id_input": user_id,
            "month_num_input": month_num,
            "year_input": year,
            "category_id_input": category_id,
            "offset_input": offset,
            "limit_input": limit
        }
        response = supabase.rpc("fetch_expenses", params).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])
    except Exception as e:
        st.error(f"Error fetching expenses: {e}")
        return pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])

# Helper function to run async code within the synchronous environment
def run_async(coroutine_func):
    return asyncio.run(coroutine_func)

# Initialize session state if it doesn't exist
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "main_menu"
if 'user_id' not in st.session_state:
    st.session_state.user_id = 1  # Dummy user ID for testing

# Main Menu Screen
if st.session_state.current_screen == "main_menu":
    st.title("Expense Tracker Dashboard")
    
    categories_df = run_async(fetch_categories())
    
    if categories_df.empty:
        st.write("No categories available.")
    else:
        category_names = categories_df['category_name'].tolist()

    # Month Names Dropdown
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

    # Fetch expenses with filters and pagination
    expenses_df = run_async(fetch _expenses(
        st.session_state.user_id,
        month_num=month_num,
        year=year,
        category_id=category_id
    ))

    # Display the expenses DataFrame with expense ID included and no index column 
    if not expenses_df.empty: 
        st.write("### Expense Details") 
        st.dataframe(expenses_df) 
    else: 
        st.write("No expenses found based on the selected filters.")

    if st.button("Logout"): 
        st.session_state.user_id = None  
        st.session_state.current_screen = "login"  
        st.rerun()
