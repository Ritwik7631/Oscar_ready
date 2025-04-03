import streamlit as st


def login():
    """
    Simulate a user login by storing the username in Streamlit's session state.
    Returns the username if logged in, otherwise None.
    """

    if 'username' not in st.session_state:
        st.session_state.username = None

    if st.session_state.username is None:
        username_input = st.text_input(
            "Enter your username", key="login_username")
        if st.button("Login"):
            st.session_state.username = username_input
            st.success(f"Welcome, {username_input}")

    return st.session_state.username


def logout():
    if st.button("Logout"):
        st.session_state.username = None
        st.success("You have been logged out")
