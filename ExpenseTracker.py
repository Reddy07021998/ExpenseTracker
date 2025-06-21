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
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

# Initialize Supabase client
supabaseUrl = 'https://ofvcxjmgynwzngobgamv.supabase.co'
supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9mdmN4am1neW53em5nb2JnYW12Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA0OTI1OTEsImV4cCI6MjA2NjA2ODU5MX0.9Pb0Q9n0nG9QtyZSW8RKCFCL1fPOsEWrRgvsfgPxSnk"  # Ensure your environment variable is set
supabase: Client = create_client(supabaseUrl, supabaseKey) 

# Assuming your logo is in the same directory as your script
login_img = "https://img.freepik.com/premium-photo/top-view-stylish-workspace-with-laptop-computer-coffee-cup-notebook-copy-space_35674-5781.jpg?ga=GA1.1.1158903708.1732594736&semt=ais_hybrid"
chart_img = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQlkf5w_kMhasj8ERvaGvasnxqX76OUDGOLuA&s"

# Define a function to set the background
def set_background(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{image_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            height: 100vh; /* Make sure the app occupies the full viewport height */
            margin: 0;
        }}
         div[data-testid="stVerticalBlock"] {{
            background-color: transparent; /* Remove white box */
            border-radius: 10px;
            padding: 10px;
            max-height: 90vh; /* Limit height to 90% of the viewport */
            overflow-y: auto; /* Add scroll bar if content overflows vertically */
        }}
        </style>
        """, 
        unsafe_allow_html=True
    )



# Call this function at the start of your app to set the background

set_background(login_img)

# Display the logo
# st.logo(login_img)

# Configure logging
logging.basicConfig(
    filename="expense_app.log", 
    level=logging.ERROR, 
    format="%(asctime)s - %(levelname)s - %(message)s")

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

# Function to register a new user in Supabase
async def register_user(username, email, password):
    try:
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Check if the username already exists
        existing_user = supabase.table('users').select('user_id').eq('username', username).execute()

        if existing_user.data:
            st.error("Username already exists! Please choose a different one.")
            return

        # Insert the new user into the 'users' table in Supabase
        result = supabase.table('users').insert({
            'username': username,
            'email': email,
            'password_hash': hashed_password
        }).execute()

        if result.status_code == 201:
            st.success("User registered successfully! You can now log in.")
        else:
            st.error("Error registering user. Please try again.")
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")
        
# Wrapper to handle async calls in Streamlit
def run_async(coro):
    return asyncio.run(coro)

async def add_expense(user_id, expense_name, amount, expense_date, category_id):
    try:
        # Ensure all data is in the correct format
        user_id = int(user_id)
        category_id = int(category_id)
        amount = float(amount)  # Convert to a standard float
        expense_date = str(expense_date)  # Ensure the date is a string in ISO format

        # Insert data into the 'expenses' table
        response = supabase.table('expenses').insert({
            'user_id': user_id,
            'expense_name': expense_name,
            'amount': amount,
            'expense_date': expense_date,
            'category_id': category_id
        }).execute()

        # Debugging: print or log the response
        logging.debug(f"Response from Supabase: {response}")

        # Check if 'data' or 'error' attributes exist
        if response and hasattr(response, 'data') and response.data:
            st.success("Expense added successfully!")
            return True

        if response and hasattr(response, 'error') and response.error:
            st.error(f"Failed to add expense: {response.error}")
            return False

        st.error("Failed to add expense: Unknown error occurred.")
        return False

    except Exception as e:
        # Log and show the exception
        logging.error(f"Error adding expense: {e}")
        st.error(f"Error adding expense: {e}")
        return False


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
      return pd.DataFrame(columns=['Expense ID','Expense Name', 'Amount', 'Expense Date', 'Category'])

  except Exception as e:
    st.error(f"Error fetching expenses: {e}")
    return pd.DataFrame(columns=['Expense ID','Expense Name', 'Amount', 'Expense Date', 'Category'])
      
# Function to update an expense based on expense_id and user_id
async def update_expense(expense_id, user_id, expense_name, amount, expense_date, category_id):
    try:
        # Ensure proper conversion for JSON serialization
        expense_id = int(expense_id)  # Convert expense_id to int if it's not already
        user_id = int(user_id)  # Convert user_id to int if it's not already
        amount = float(amount)  # Convert amount to float
        category_id = int(category_id)  # Convert category_id to int if it's not already
        expense_date = str(expense_date)  # Ensure expense_date is a string in ISO format

        # Update the expense record in Supabase table
        response = supabase.table('expenses').update({
            'expense_name': expense_name,
            'amount': amount,
            'expense_date': expense_date,
            'category_id': category_id
        }).eq('expense_id', expense_id).eq('user_id', user_id).execute()

        # Handle the response
        if response.status_code == 204:
            st.success("Expense updated successfully!")
        else:
            st.error(f"Error updating expense: {response.error}")
    except Exception as e:
        st.error(f"Error updating expense: {e}")
        logging.error(f"Error updating expense: {e}")

# Function to delete an expense
async def delete_expense(expense_id):
    try:
        response = supabase.table('expenses').delete().eq('expense_id', expense_id).execute()
        if response.status_code == 204:
            st.success("Expense deleted successfully!")
        else:
            error_message = f"Error deleting expense. Status code: {response.status_code}, Response: {response}"
            st.error(error_message)
            logging.error(error_message)
    except Exception as e:
        error_message = f"Exception during deletion of expense ID {expense_id}: {e}"
        st.error(error_message)
        logging.error(error_message)

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
    # Set the background (optional, customize as needed)
    set_background(login_img)
    
    # Registration Form Title
    st.title("Register for Expense Tracker")
    
    # Form for user registration
    with st.form("register_form"):
        username = st.text_input("Username", key="register_username")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        register_button = st.form_submit_button("Register")

    # Registration process
    if register_button:
        if not username or not email or not password:
            st.error("Please fill in all the fields.")
        elif password != confirm_password:
            st.error("Passwords do not match.")
        else:
            try:
                # Asynchronous function to register the user
                run_async(register_user(username, email, password))
                st.success("Registration successful! Please log in.")
                st.session_state.current_screen = "login"
                st.rerun()
            except Exception as e:
                st.error(f"Registration failed: {e}")
    
    # Option to go back to the login screen
    if st.button("Back to Login"):
        st.session_state.current_screen = "login"
        st.rerun()

# Main Menu Screen
elif st.session_state.current_screen == "main_menu":
    st.title("Expense Tracker Dashboard")

    categories_df = run_async(fetch_categories())

    if categories_df.empty:
        st.write("No categories available.")
    else:
        category_names = categories_df['category_name'].tolist()

    col11, col12, col13 = st.columns(3)

    with col11:
        month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month = st.selectbox("Select Month", month_names)
        month_num = None if month == "All" else month_names.index(month)

    with col12:
        category = st.selectbox("Select Category", ["All"] + category_names)
        category_id = None if category == "All" else categories_df[categories_df['category_name'] == category]['category_id'].values[0]

    with col13:
        current_year = datetime.now().year
        year_range = list(range(2022, current_year + 2))
        year_options = ["All"] + year_range
        year = st.selectbox("Select Year", year_options)
        year_num = None if year == "All" else int(year)

    # ✅ Fetch all expenses (no offset/limit)
    expenses_df = run_async(fetch_expenses(
        st.session_state.user_id,
        month_num=month_num,
        year=year_num,
        category_id=category_id
    ))

    # Actions
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("➕ Add Expense"):
            st.session_state.current_screen = "add_expense"
            st.rerun()
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col3:
        if st.button("📊 Chart View"):
            st.session_state.current_screen = "heatmap_view"
            st.rerun()

    # ✅ AgGrid Display
    if not expenses_df.empty:
        st.subheader("💸 Expense Details")

        page_size = 10 #st.selectbox("Rows per page", [10, 20, 30, 50, 100], index=0)

        gb = GridOptionsBuilder.from_dataframe(expenses_df)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)
        gb.configure_default_column(editable=False, groupable=True)
        gb.configure_selection('single', use_checkbox=True)

        grid_options = gb.build()

        grid_response = AgGrid(
            expenses_df,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
            fit_columns_on_grid_load=True,
            height=400,
            width='100%'
        )

        selected_rows = grid_response.get("selected_rows", [])

        selected_rows = grid_response.get("selected_rows", [])

        if len(selected_rows) > 0:
            selected = selected_rows[0]
            selected_expense = {
                "Expense ID": selected.get("Expense ID"),
                "Expense Name": selected.get("Expense Name"),
                "Amount": selected.get("Amount"),
                "Expense Date": selected.get("Expense Date"),
                "Category": selected.get("Category")
            }
        
            st.markdown("### 🎯 Selected Expense")
            st.write(selected_expense)
        
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Edit Selected"):
                    st.session_state.editing_expense = selected_expense
                    st.session_state.current_screen = "inline_edit"
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete Selected"):
                    run_async(delete_expense(int(selected_expense["Expense ID"])))
                    st.rerun()
        else:
            st.info("Select an expense to edit or delete.")

    if st.button("Logout"):
        st.session_state.user_id = None
        st.session_state.current_screen = "login"
        st.rerun()

# Heatmap Screen
elif st.session_state.current_screen == "heatmap_view":
    set_background(login_img)
    st.title("Expense Chart")

    categories_df = run_async(fetch_categories())
    
    if categories_df.empty:
        st.write("No categories available.")
    else:
        category_names = categories_df['category_name'].tolist()

    # Display the icons for Add, Edit, and Delete actions
    col1, col2, col3 = st.columns(3)

    with col1:
            # Month Names Dropdown (Jan, Feb, etc.)
            month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            current_month_index = datetime.now().month
            month = st.selectbox("Select Month", month_names)
            month_num = None if month == "All" else month_names.index(month)
                        
    with col2:
            # Category Dropdown
            category_options = ["All"] + categories_df['category_name'].tolist()
            category = st.selectbox("Select Category", category_options)
            category_id = None if category == "All" else int(categories_df[categories_df['category_name'] == category]['category_id'].values[0])

    with col3:
            # Year Dropdown
            current_year = datetime.now().year
            year_range = list(range(2022, current_year + 2))
            year_options = ["All"] + year_range
            default_year_index = year_options.index(current_year)
            year = st.selectbox("Select Year", year_options)
            year_num = None if year == "All" else int(year)       
                        
    try:
        # Fetch expenses data with filters applied (month, year, category)
        expenses_df = run_async(fetch_expenses(
            st.session_state.user_id,
            month_num= month_num,  # Filtered month
            year= year_num,       # Filtered year
            category_id= category_id # Filtered category
        ))

        expenses_df = pd.DataFrame(expenses_df)

        # State management for the cell to edit
        if "cell_to_edit" not in st.session_state:
            st.session_state.cell_to_edit = None
        if "edited_df" not in st.session_state:
            st.session_state.edited_df = expenses_df.copy()
        
        if not expenses_df.empty:

            # Heatmap visualization
            heatmap_data = expenses_df.groupby(['Expense Date', 'Category'])['Amount'].sum().unstack(fill_value=0)
            plt.figure(figsize=(10, 6))
            sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", fmt='.2f')
            st.pyplot(plt)

        else:
            st.write("No data available to generate visualizations.")

    except Exception as e:
        st.error(f"Error generating visualizations: {e}")

    # Navigation button
    if st.button("⬅️"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

# Add Expense Screen
elif st.session_state.current_screen == "add_expense":
    st.title("Add Expense")

    # Inputs for expense details
    expense_name = st.text_input("Expense Name")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)
    expense_date = st.date_input("Expense Date")

    # Fetch categories
    categories_df = run_async(fetch_categories())

    if categories_df.empty:
        st.warning("No categories available. Please add categories first.")
    else:
        category_names = categories_df['category_name'].tolist()
        category = st.selectbox("Category", category_names)

        # Get category_id for selected category
        try:
            category_id = categories_df[categories_df['category_name'] == category]['category_id'].values[0]
        except IndexError:
            st.error("Failed to fetch the category ID. Please check the category data.")
            category_id = None

    # Save Expense Button
    if st.button("Save Expense"):
        if not expense_name or not amount or not expense_date or not category_id:
            st.error("All fields are required to add an expense.")
        else:
            # Run async function to add the expense
            result = run_async(
                add_expense(
                    st.session_state.user_id,
                    expense_name,
                    amount,
                    expense_date.isoformat(),
                    category_id
                )
            )
            if result:
                st.success("Expense added successfully!")
                st.session_state.current_screen = "main_menu"
                st.rerun()

    # Cancel Button
    if st.button("Cancel"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

    if st.button("⬅️"):
            st.session_state.current_screen = "main_menu"
            st.rerun()

elif st.session_state.current_screen == "inline_edit":
    st.title("Edit Expense")

    row = st.session_state.editing_expense
    if not row:
        st.error("No expense selected for editing.")
        st.session_state.current_screen = "main_menu"
        st.rerun()

    expense_name = st.text_input("Expense Name", row['Expense Name'])
    amount = st.number_input("Amount", min_value=0.01, step=0.01, value=float(row['Amount']))
    expense_date = st.date_input("Expense Date", pd.to_datetime(row['Expense Date']))

    categories_df = run_async(fetch_categories())
    category_names = categories_df['category_name'].tolist()
    category = st.selectbox("Category", category_names, index=category_names.index(row['Category']))
    category_id = categories_df[categories_df['category_name'] == category]['category_id'].values[0]

    if st.button("Save Changes"):
        run_async(update_expense(
            row['Expense ID'],
            st.session_state.user_id,
            expense_name,
            amount,
            expense_date,
            category_id
        ))
        st.session_state.current_screen = "main_menu"
        st.rerun()

    if st.button("Cancel"):
        st.session_state.current_screen = "main_menu"
        st.rerun()
                
    if st.button("⬅️"):
        st.session_state.current_screen = "main_menu"
        st.rerun()

# Delete Expense Screen
elif st.session_state.current_screen == "inline_delete":
    st.title("Delete Expense")

    row = st.session_state.deleting_expense
    if not row:
        st.error("No expense selected for deletion.")
        st.session_state.current_screen = "main_menu"
        st.rerun()
        
    if  row:
        run_async(delete_expense(row['Expense ID']))
        st.session_state.current_screen = "main_menu"        
        st.rerun()
