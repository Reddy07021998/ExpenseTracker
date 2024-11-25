import bcrypt
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import asyncpg
import asyncio

# Function to connect to PostgreSQL asynchronously
async def connect_to_db():
    return await asyncpg.connect(
        user='kishore',
        password='Kk07022024!@',
        database='ExpenseTracker',
        host='localhost',
        port='5432'
    )

# Function to authenticate a user
async def authenticate_user(username, password):
    try:
        conn = await connect_to_db()
        query = "SELECT user_id, password_hash FROM users WHERE username = $1"
        user_data = await conn.fetchrow(query, username)
        await conn.close()
        
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password_hash'].encode('utf-8')):
            return user_data['user_id']
        else:
            return None
    except Exception as e:
        st.error(f"Error authenticating user: {e}")
        return None

# Function to register a new user
async def register_user(username, email, password):
    try:
        conn = await connect_to_db()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        query = "INSERT INTO users (username, email, password_hash) VALUES ($1, $2, $3)"
        await conn.execute(query, username, email, hashed_password)
        await conn.close()
        st.success("User registered successfully! You can now log in.")
    except asyncpg.exceptions.UniqueViolationError:
        st.error("Username or email already exists. Please choose a different one.")
    except Exception as e:
        st.error(f"Error registering user: {str(e)}")

# Helper function to run async code within the synchronous environment
def run_async(coroutine_func):
    return asyncio.run(coroutine_func)

# Initialize session state
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

    st.write("Don't have an account?")
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

    if st.button("Back to Login"):
        st.session_state.current_screen = "login"
        st.rerun()

# Function to add a new expense
async def add_expense(user_id, expense_name, amount, expense_date, category_id):
    try:
        conn = await connect_to_db()
        query = """
            INSERT INTO expenses (user_id, expense_name, amount, expense_date, category_id)
            VALUES ($1, $2, $3, $4, $5)
        """
        await conn.execute(query, user_id, expense_name, amount, expense_date, category_id)
        await conn.close()
        st.success("Expense added successfully!")
    except Exception as e:
        st.error(f"Error adding expense: {e}")
        
# Function to fetch categories
async def fetch_categories():
    try:
        conn = await connect_to_db()
        query = "SELECT category_id, category_name FROM categories"
        results = await conn.fetch(query)
        await conn.close()
        return pd.DataFrame(results, columns=['category_id', 'category_name'])
    except Exception as e:
        st.error(f"Error fetching categories: {e}")
        return pd.DataFrame(columns=['category_id', 'category_name'])

async def fetch_expenses(user_id, month_num=None, year=None, category_id=None, offset=0, limit=10):
    try:
        conn = await connect_to_db()

        query = """
            SELECT e.expense_id, e.expense_name, e.amount, e.expense_date, c.category_name
            FROM expenses e
            JOIN categories c ON e.category_id = c.category_id
            WHERE e.user_id = $1
        """
        params = [user_id]

        # Add filters dynamically
        if month_num is not None:
            query += " AND EXTRACT(MONTH FROM e.expense_date) = $2"
            params.append(month_num)

        if year is not None:
            query += f" AND EXTRACT(YEAR FROM e.expense_date) = ${len(params) + 1}"
            params.append(year)

        if category_id is not None:
            query += f" AND e.category_id = ${len(params) + 1}"
            params.append(category_id)

        # Add pagination
        query += f" ORDER BY e.expense_date DESC OFFSET ${len(params) + 1} LIMIT ${len(params) + 2}"
        params.extend([offset, limit])

        # Execute the query
        results = await conn.fetch(query, *params)
        await conn.close()

        # Convert results to a DataFrame
        if results:
            df = pd.DataFrame(results, columns=['expense_id', 'expense_name', 'amount', 'expense_date', 'category_name'])
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
        conn = await connect_to_db()
        query = "DELETE FROM expenses WHERE expense_id = $1"
        await conn.execute(query, expense_id)
        await conn.close()
        st.success("Expense deleted successfully!")
    except Exception as e:
        st.error(f"Error deleting expense: {e}")

# Function to update an expense based on expense_id and user_id
async def update_expense(expense_id, user_id, expense_name, amount, expense_date, category_id):
    try:
        conn = await connect_to_db()
        query = """
            UPDATE expenses 
            SET expense_name = $1, amount = $2, expense_date = $3, category_id = $4 
            WHERE expense_id = $5 AND user_id = $6
        """
        await conn.execute(query, expense_name, amount, expense_date, category_id, expense_id, user_id)
        await conn.close()
        st.success("Expense updated successfully!")
    except Exception as e:
        st.error(f"Error updating expense: {e}")

# Helper function to run async code within the synchronous environment
def run_async(coroutine_func):
    return asyncio.run(coroutine_func)

# Initialize session state variables if they don't exist
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "main_menu"  # Default screen

if 'user_id' not in st.session_state:
    st.session_state.user_id = 3  # Set user_id to 3 for now

# Pagination state
if 'page_offset' not in st.session_state:
    st.session_state.page_offset = 0  # Initialize offset for pagination
if 'page_limit' not in st.session_state:
    st.session_state.page_limit = 10  # Records per page

# Main Menu Screen
if st.session_state.current_screen == "main_menu":
    st.title("Expense Tracker Dashboard")

    categories_df = run_async(fetch_categories())
    if categories_df.empty:
        st.write("No categories available.")
    else:
        category_names = categories_df['category_name'].tolist()

        # Month Names Dropdown (Jan, Feb, etc.)
        month_names = ["All", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        month = st.selectbox("Select Month", month_names, index=0)

        # Year Dropdown
        year = st.selectbox("Select Year", ["All", 2023, 2024], index=0)

        # Category Dropdown
        category = st.selectbox("Select Category", ["All"] + category_names, index=0)

        # Determine category_id from category name
        category_id = None
        if category != "All":
            category_id = categories_df[categories_df['category_name'] == category]['category_id'].values[0]

        # Determine month_num from selected month
        month_num = None
        if month != "All":
            month_num = month_names.index(month)  # Convert month name to month number (1 = Jan, 12 = Dec)

        # Determine year from selected year
        year_num = None
        if year != "All":
            year_num = int(year)

        # Fetch expenses with filters and pagination
        expenses_df = run_async(fetch_expenses(
            st.session_state.user_id,
            month_num=month_num,
            year=year_num,
            category_id=category_id,
            offset=st.session_state.page_offset,
            limit=st.session_state.page_limit
        ))

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
        
        # Display the expenses DataFrame with expense_id included and no index column
        if not expenses_df.empty:
            st.write("### Expense Details")
            st.dataframe(expenses_df)
            
        else:
            st.write("No expenses found based on the selected filters.")

        # Pagination: Back and Next buttons
        col1, col2 = st.columns([1, 1])  # Create two columns for buttons

        with col1:
            if st.button("← Back") and st.session_state.page_offset > 0:
                st.session_state.page_offset -= st.session_state.page_limit  # Go to previous page
                st.rerun()

        with col2:
            if st.button("Next →"):
                st.session_state.page_offset += st.session_state.page_limit  # Go to next page
                st.rerun()
        
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
# Add Expense Screen
elif st.session_state.current_screen == "add_expense":
    st.title("Add Expense")
    expense_name = st.text_input("Expense Name")
    amount = st.number_input("Amount", min_value=0.01, step=0.01)
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
                st.rerun()

            if st.button("Cancel"):
                st.session_state.current_screen = "main_menu"
                st.rerun()


# delete Expense Screen
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
                st.session_state.current_screen = "main_menu"
                st.rerun()

            if st.button("Cancel"):
                st.session_state.current_screen = "main_menu"
                st.rerun()
