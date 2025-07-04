import streamlit as st
from supabase_db import SupabaseDB
import time

# Import views
from views.home_view import show_home_page
from views.dashboard_view import show_dashboard_page
from views.history_view import show_history_page
from views.scraper_view import show_scraper_page
from views.telegram_settings_view import show_telegram_settings_page

st.set_page_config(page_title="AI Internship Assistant", layout="wide")

# --- DATABASE INITIALIZATION ---
try:
    db = SupabaseDB()
except Exception as e:
    st.error(f"Failed to connect to the database: {e}")
    st.stop()

def load_internships():
    if st.session_state.user_id:
        print(f"Loading internships for user: {st.session_state.user_id}")  # Debug print
        internships = db.get_internships_by_user(st.session_state.user_id)
        print(f"Loaded {len(internships) if internships else 0} internships")  # Debug print
        st.session_state.all_internships = internships or []
        return internships
    return []

# --- SESSION STATE INITIALIZATION ---
# Initialize all session state variables with their default values
defaults = {
    'logged_in': False,
    'page': 'Login',
    'view': 'Home',
    'user_session': None,
    'user_id': None,
    'username': None,
    'all_internships': [],  # Always initialize as empty list, never None
    'show_details': None,
    'confirm_delete': None,
    'show_descriptions': {},
    'continuous_search_active': False,
    'search_thread': None,
    'delete_success': False  # Add this for delete confirmation handling
}

# Initialize any missing session state variables with defaults
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- HANDLER FUNCTIONS ---
def handle_login(email, password):
    if not email or not password:
        st.error("Please enter both email and password.")
        return
    result = db.sign_in_user(email, password)
    if "error" not in result:
        st.session_state.logged_in = True
        st.session_state.user_session = result['session']
        st.session_state.user_id = result['session'].user.id
        profile = db.get_user_profile()
        st.session_state.username = profile.get('username', email) if profile else email
        # Load internships after successful login
        load_internships()
        st.success("Logged in successfully!")
        time.sleep(1)
        st.rerun()
    else:
        st.error(result["error"])

def handle_register(email, password, confirm_password, username, telegram_bot_token, telegram_chat_id):
    if password != confirm_password:
        st.error("Passwords do not match.")
        return
    if not all([email, password, confirm_password, username, telegram_bot_token, telegram_chat_id]):
        st.error("Please fill in all fields.")
        return
    result = db.sign_up_user(email, password, username, telegram_bot_token, telegram_chat_id)
    if "error" not in result:
        st.success("Registration successful! Please check your email to confirm your account and then login.")
        st.session_state.page = 'Login'
        time.sleep(2)
        st.rerun()
    else:
        st.error(result["error"])

# --- UI RENDERING ---

# --- LOGIN/REGISTRATION VIEW ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        if st.session_state.page == 'Login':
            st.header("Welcome Back!")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Login", use_container_width=True)
                if submitted:
                    handle_login(email, password)
            
            if st.button("Don't have an account? Register", use_container_width=True):
                st.session_state.page = 'Register'
                st.rerun()

        elif st.session_state.page == 'Register':
            st.header("Create an Account")
            with st.form("register_form"):
                username = st.text_input("Username", placeholder="Choose a username")
                email = st.text_input("Email", placeholder="Enter your email")
                password = st.text_input("Password", type="password", placeholder="Create a password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                telegram_bot_token = st.text_input("Telegram Bot Token", placeholder="Enter your Telegram Bot Token")
                telegram_chat_id = st.text_input("Telegram Chat ID", placeholder="Enter your Telegram Chat ID")
                submitted = st.form_submit_button("Register", use_container_width=True)
                if submitted:
                    handle_register(email, password, confirm_password, username, telegram_bot_token, telegram_chat_id)

            if st.button("Already have an account? Login", use_container_width=True):
                st.session_state.page = 'Login'
                st.rerun()

# --- MAIN APPLICATION VIEW ---
else:
    # --- SIDEBAR NAVIGATION ---
    st.sidebar.success(f"Welcome, {st.session_state.get('username', 'User')}!")
    
    PAGES = {
        "Home": {"icon": "🏠", "function": show_home_page},
        "Dashboard": {"icon": "📊", "function": show_dashboard_page},
        "Application History": {"icon": "📜", "function": show_history_page},
        "Run Scrapper": {"icon": "⚙️", "function": show_scraper_page},
        "Telegram Settings": {"icon": "🔧", "function": show_telegram_settings_page}
    }

    st.sidebar.title("Choose page")
    
    # Create buttons for each page
    for page_name, page_info in PAGES.items():
        # Use a different type for the selected button to make it look active
        button_type = "primary" if st.session_state.view == page_name else "secondary"
        if st.sidebar.button(f"{page_info['icon']} {page_name}", use_container_width=True, type=button_type):
            st.session_state.view = page_name
            st.rerun()

    # Logout button at the bottom
    st.sidebar.write("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.page = 'Login'
        # Clear session state on logout
        for key in list(st.session_state.keys()):
            if key not in ['page']:
                del st.session_state[key]
        st.rerun()

    # --- CENTRALIZED DATA LOADER ---            # This ensures that the main internship data is always loaded and consistent
    def ensure_data_loaded():
        with st.spinner("Loading internships..."):
            # Always initialize all_internships as an empty list if it doesn't exist
            if 'all_internships' not in st.session_state:
                st.session_state['all_internships'] = []
            elif st.session_state.get('all_internships') is None:
                st.session_state['all_internships'] = []

            current_internships = st.session_state.get('all_internships', [])
            
            # Only attempt load if user is logged in and internships need refresh
            if st.session_state.get('logged_in') and not current_internships:
                user_id = st.session_state.get('user_id')
                
                if not user_id:
                    st.error("No user ID found in session. Please try logging in again.")
                    return False

                try:
                    internships = db.get_internships_by_user(user_id)
                    
                    # Ensure internships is always a list
                    if internships is None:
                        internships = []
                    elif not isinstance(internships, list):
                        internships = list(internships) if hasattr(internships, '__iter__') else []
                    
                    st.session_state['all_internships'] = internships
                    return True
                except Exception as e:
                    st.error("Error loading internships. Please try again.")
                    st.session_state.all_internships = []
                    return False

    # Load data when needed
    if st.session_state.view == 'Dashboard' or not st.session_state.get('all_internships'):
        ensure_data_loaded()

    # --- RENDER SELECTED PAGE ---
    # Use st.session_state.view to render the correct page. Default to Home.
    page_to_render = st.session_state.get('view', 'Home')
    page = PAGES[page_to_render]
    page["function"]()