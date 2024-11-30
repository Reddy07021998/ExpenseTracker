import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go

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

# Initialize session state if it doesn't exist
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "heatmap_view"

# Heatmap Screen
if st.session_state.current_screen == "heatmap_view":
    set_background(chart_img)
    st.title("Expense Chart")

    # Placeholder for expenses DataFrame
    # In a real application, this data would be fetched from a database
    expenses_df = pd.DataFrame({
        'Expense Date': pd.date_range(start='2023-01-01', periods=12, freq='M'),
        'Category': ['Food', 'Transport', 'Utilities', 'Entertainment', 'Groceries'] * 2 + ['Miscellaneous'] * 2,
        'Amount': [200, 150, 100, 300, 250, 400, 350, 450, 200, 300, 150, 100]
    })

    if not expenses_df.empty:
        # Preprocessing expenses data
        expenses_df['Expense Date'] = pd.to_datetime(expenses_df['Expense Date'], errors='coerce').dt.to_period('M').astype(str)
        expenses_df['Amount'] = pd.to_numeric(expenses_df['Amount'], errors='coerce')
        expenses_df = expenses_df.dropna(subset=['Expense Date', 'Amount'])

        # Heatmap visualization
        heatmap_data = expenses_df.groupby(['Expense Date', 'Category'])['Amount'].sum().unstack(fill_value=0)
        plt.figure(figsize=(10, 6))
        sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", fmt='.2f')
        st.pyplot(plt)

        # Dual visualization: Bar chart + Line plot
        st.subheader("Budget vs Need/Expense")

        # Aggregate data for the bar chart and line plot
        aggregated_df = expenses_df.groupby('Expense Date')['Amount'].sum().reset_index()
        aggregated_df['Budget'] = 900  # Set a fixed budget for demonstration

        # Generate the dual visualization
        fig = go.Figure()

        # Add bar chart for "Need/Expense"
        fig.add_trace(go.Bar(
            x=aggregated_df['Expense Date'],
            y=aggregated_df['Amount'],
            name="Need/Expense",
            marker_color='red'
        ))

        # Add line plot for "Budget"
        fig.add_trace(go.Scatter(
            x=aggregated_df['Expense Date'],
            y=aggregated_df['Budget'],
            name="Budget",
            mode='lines+markers',
            line=dict(color='yellow', width=2),
            marker=dict(size=8)
        ))

        # Customize layout
        fig.update_layout(
            title="Budget vs Need/Expense",
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            legend_title="Legend",
            barm
