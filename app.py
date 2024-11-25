import os
import bcrypt
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from supabase import create_client, Client
import asyncio

# Initialize Supabase client
supabaseUrl = 'https://gippopxafisxpvrkkplt.supabase.co'
supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdpcHBvcHhhZmlzeHB2cmtrcGx0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI1MjM1MTcsImV4cCI6MjA0ODA5OTUxN30.ldQh7QxpG08pERpOKl_-3gGr8CTYdPKGx83dDYJe5ZM"  # Ensure your environment variable is set
supabase: Client = create_client(supabaseUrl, supabaseKey)

# Function to authenticate a user
async def authenticate_user(username, password):
    try:
        user_data = supabase.table('users').select('user_id, password_hash').eq('username', username).single().execute()
        if user_data.data and bcrypt.checkpw(password.encode('utf-8'), user_data.data['password_hash'].encode('utf-8')):
            return user_data.data['user_id']
        else:
            return None
    except Exception as e:
        st.error(f"Error authenticating user: {e}")
        return None

# Function to register a new user
async def register_user(username, email, password):
    try:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        response = supabase.table('users').insert({'username': username, 'email': email, 'password_hash': hashed_password}).execute()
        if response.status_code == 201:
            st.success("User registered successfully! You can now log in.")
        else:
            st.error("Registration failed.")
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")

# Function to add a new expense
async def add_expense(user_id, expense_name, amount, expense_date, category_id):
    try:
        response = supabase.table('expenses').insert({
            'user_id': user_id,
            'expense_name': expense_name,
            'amount': amount,
            'expense_date': expense_date,
            'category_id': category_id
        }).execute()
        if response.status_code == 201:
            st.success("Expense added successfully!")
    except Exception as e:
        st.error(f"Error adding expense: {e}")

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
        # Prepare parameters for the RPC call
        params = {
            "user_id_input": user_id,
            "month_num_input": month_num,
            "year_input": year,
            "category_id_input": category_id,
            "offset_input": offset,
            "limit_input": limit
        }

        # Call the RPC function
        response = supabase.rpc("fetch_expenses", params).execute()

        # Convert the result to a DataFrame
        if response.data:
            df = pd.DataFrame(response.data)
            df.columns = ['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category']
            return df
        else:
            return pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])

    except Exception as e:
        st.error(f"Error fetching expenses: {e}")
        return pd.DataFrame(columns=['Expense ID', 'Expense Name', 'Amount', 'Expense Date', 'Category'])

# Function to delete an expense
async def delete_expense(expense_id):
    try:
        response = supabase.table('expenses').delete().eq('expense_id', expense_id).execute()
        if response.status_code == 204:
            st.success("Expense deleted successfully!")
    except Exception as e:
        st.error(f"Error deleting expense: {e}")

# Function to update an expense based on expense_id and user_id
async def update_expense(expense_id, user_id, expense_name, amount, expense_date, category_id):
    try:
        response = supabase.table('expenses').update({
            'expense_name': expense_name,
            'amount': amount,
            'expense_date': expense_date,
            'category_id': category_id
        }).eq('expense_id', expense_id).eq('user_id', user_id).execute()
        
        if response.status_code == 204:
            st.success("Expense updated successfully!")
    except Exception as e:
        st.error(f"Error updating expense: {e}")

# Helper function to run async code within the synchronous environment
def run_async(coroutine_func):
    return asyncio.run(coroutine_func)

# Initialize session state if it doesn't exist
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "login"
if 'user_id' not in st.session_state:
    st.session_state.user_id = None


# Login Screen
if st.session_state.current_screen == "login":
    st.title("Login to Expense Tracker")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")
        
        if login_button:
            user_id = run_async(authenticate_user(username, password))
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.current_screen = "main_menu"
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
                
    if st.button("Register"):
        st.session_state.current_screen = "register"
        st.rerun()

# Registration Screen
elif st.session_state.current_screen == "register":
    st.title("Register for Expense Tracker")
    with st.form("register_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        register_button = st.form_submit_button("Register")
        
        if register_button:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                run_async(register_user(username, email, password))
                st.session_state.current_screen = "login"
                st.rerun()

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
    col1, col2, col3, col4 = st.columns(4)
    
    with col4:
        if st.button("➕ Add Expense"):
            st.session_state.current_screen = "add_expense"
            st.rerun()
    
    with col2:
        if st.button("✏️ Edit Expense"):
            st.session_state.current_screen = "edit_expense"
            st.rerun()

    with col3:
        if st.button("🗑️ Delete Expense"):
            st.session_state.current_screen = "confirm_delete"
            st.rerun()

    with col1:
        if st.button("Show Heatmap"):
            st.session_state.current_screen = "heatmap_view"
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
    st.title("Expense Heatmap")

    try:
        expenses_df = run_async(fetch_expenses(st.session_state.user_id))

        if not expenses_df.empty:
            expenses_df['Expense Date'] = pd.to_datetime(expenses_df['Expense Date'], errors='coerce').dt.date
            expenses_df['Amount'] = pd.to_numeric(expenses_df['Amount'], errors='coerce')
            expenses_df = expenses_df.dropna(subset=['Expense Date', 'Amount'])

            heatmap_data = expenses_df.groupby(['Expense Date', 'Category'])['Amount'].sum().unstack(fill_value=0)

            plt.figure(figsize=(10, 6))
            sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", fmt='.2f')
            st.pyplot(plt)

        else:
            st.write("No data available to generate heatmap.")

    except Exception as e:
        st.error(f"Error generating heatmap: {e}")

    if st.button("⬅️"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

# Add Expense Screen
elif st.session_state.current_screen == "add_expense":
    st.title("Add Expense")

    expense_name = st.text_input("Expense Name")
    amount = st.number_input("Amount", min_value=0.01 , step=0.01)
    expense_date = st.date_input("Expense Date")

    categories_df = run_async(fetch_categories())

    category_names = categories_df['category_name'].tolist()
    category = st.selectbox("Category", category_names)

    if st.button("Save Expense"):
        category_id = categories_df[categories_df['category_name'] == category]['category_id'].values[0]
        run_async(add_expense(st.session_state.user_id, expense_name, amount, expense_date, category_id))
        st.session_state.current_screen = "main_menu"
        st.rerun()

    if st.button("Cancel"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

# Edit Expense Screen
elif st.session_state.current_screen == "edit_expense":
    st.title("Edit Expense")

    # Fetch expenses to populate a dropdown of expense IDs
    expenses_df = run_async(fetch_expenses(st.session_state.user_id))

    if expenses_df.empty:
        st.warning("No expenses available to edit.")
        if st.button("Back to Main Menu"):
            st.session_state.current_screen = "main_menu"
            st.rerun()
    else:
        expense_ids = expenses_df['Expense ID'].tolist()
        selected_expense_id = st.selectbox("Select Expense ID to Edit", ["Select"] + expense_ids)

        if selected_expense_id != "Select":
            # Fetch the details of the selected expense
            expense_details = expenses_df[expenses_df['Expense ID'] == selected_expense_id].iloc[0]

            # Display current details for editing
            expense_name = st.text_input("Expense Name", expense_details['Expense Name'])
            amount = st.number_input("Amount", min_value=0.0, step=0.01, value=float(expense_details['Amount']))
            expense_date = st.date_input("Expense Date", pd.to_datetime(expense_details['Expense Date']))
            categories_df = run_async(fetch_categories())
            category_names = categories_df['category_name'].tolist()
            current_category = expense_details['Category']
            category = st.selectbox("Category", category_names, index=category_names.index(current_category))

            # Update the expense
            if st.button("Save Changes"):
                category_id = categories_df[categories_df['category_name'] == category]['category_id'].values[0]
                run_async(update_expense(selected_expense_id, st.session_state.user_id, expense_name, amount, expense_date, category_id))
                st.session_state.current_screen = "main_menu"
                st.success("Expense updated successfully!")
                st.rerun()

            if st.button("Cancel"):
                st.session_state.current_screen = "main_menu"
                st.rerun()

# Delete Expense Screen
elif st.session_state.current_screen == "confirm_delete":
    st.title("Delete Expense")

    # Fetch expenses to populate a dropdown of expense IDs
    expenses_df = run_async(fetch_expenses(st.session_state.user_id))

    if expenses_df.empty:
        st.warning("No expenses available to delete.")
        if st.button("Back to Main Menu"):
            st.session_state.current_screen = "main_menu"
            st.rerun()
    else:
        expense_ids = expenses_df['Expense ID'].tolist()
        selected_expense_id = st.selectbox("Select Expense ID to Delete", ["Select"] + expense_ids)

        if selected_expense_id != "Select":
            # Fetch the details of the selected expense
            expense_details = expenses_df[expenses_df['Expense ID'] == selected_expense_id].iloc[0]

            # Display details for confirmation
            st.write("### Expense Details")
            st.write(f"**Name:** {expense_details['Expense Name']}")
            st.write(f"**Amount:** {expense_details['Amount']}")
            st.write(f"**Date:** {expense_details['Expense Date']}")
            st.write(f"**Category:** {expense_details['Category']}")

            # Confirm deletion
            if st.button("Confirm Delete"):
                run_async(delete_expense(selected_expense_id))
                st.success("Expense deleted successfully!")
                st.session_state.current_screen = "main_menu"
                st.rerun()

            if st.button("Cancel"):
                st.session_state.current_screen = "main_menu"
                st.rerun()
