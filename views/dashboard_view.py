import streamlit as st
from supabase_db import SupabaseDB
from datetime import datetime
import time
from dateutil import parser

def parse_date(date_str):
    """Helper function to parse dates in various formats"""
    try:
        return parser.parse(date_str)
    except (ValueError, TypeError):
        return datetime.min

# Status configurations for consistent UI
STATUS_INFO = {
    'New': {'color': 'blue', 'emoji': '✨'},
    'Applied': {'color': 'green', 'emoji': '✅'},
    'Rejected': {'color': 'red', 'emoji': '❌'}
}

def get_status_info(status):
    """Helper function to get consistent status styling"""
    status = status.title() if status else 'New'
    return STATUS_INFO.get(status, {'color': 'gray', 'emoji': '❔'})

def show_dashboard_page():
    """Renders the main content of the dashboard page."""
    st.title("📊 Internship Dashboard")

    # Initialize all session state variables if not already set
    state_defaults = {
        'all_internships': [],
        'button_counter': 0,
        'expanded_card': None,
        'confirm_delete': None,
        'confirm_reject': None,
        'delete_success': False,
        'reject_success': False,
        'last_action': None,
        'last_action_status': None
    }
    
    for key, default_value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
        
    user_id = st.session_state.get('user_id')
    
    # Load internships if needed
    if not st.session_state.all_internships:
        if user_id:
            db = SupabaseDB()
            internships = db.get_internships_by_user(user_id)
            if internships is not None:
                st.session_state.all_internships = internships
    
    all_internships = st.session_state.all_internships

    # Display Statistics with emojis
    st.markdown("### 📈 Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    # Calculate statistics
    total_internships = len(all_internships) if all_internships is not None else 0
    new_internships = len([i for i in (all_internships or []) if i.get('status') == 'new'])
    applied_internships = len([i for i in (all_internships or []) if i.get('status') == 'applied'])
    rejected_internships = len([i for i in (all_internships or []) if i.get('status') == 'rejected'])
    
    with col1:
        st.metric("🎯 Total", total_internships)
    with col2:
        st.metric("✨ New", new_internships)
    with col3:
        st.metric("✅ Applied", applied_internships)
    with col4:
        st.metric("❌ Rejected", rejected_internships)
    
    st.markdown("---")

    # Status options with emojis
    status_options_with_emoji = {
        'All': '🎯 All',
        'new': '✨ New',
        'applied': '✅ Applied',
        'rejected': '❌ Rejected'
    }
    
    # Radio button filter with emojis
    selected_status = st.radio(
        "Filter by status:",
        options=['All'] + ['new', 'applied', 'rejected'],
        format_func=lambda x: status_options_with_emoji.get(x, x),
        horizontal=True,
        key='status_filter'
    )

    # Apply filter based on radio button selection
    if selected_status == 'All':
        filtered_internships = all_internships
    else:
        filtered_internships = [i for i in all_internships if i.get('status') == selected_status]
    
    # Sort internships by status (new -> applied -> rejected) and then by date
    try:
        # Define status priority (new first, then applied, then rejected)
        status_priority = {'new': 0, 'applied': 1, 'rejected': 2}
        
        # Sort function that considers both status and date
        def sort_key(internship):
            # Get status priority (default to highest number if status not found)
            status_prio = status_priority.get(internship.get('status', 'new'), 3)
            # Get date (default to earliest date if not found)
            date = parse_date(internship.get('created_at'))
            # Return tuple for sorting (status priority first, then date in reverse order)
            return (status_prio, -date.timestamp())
        
        filtered_internships = sorted(filtered_internships, key=sort_key)
    except Exception as e:
        st.warning(f"Note: Could not sort internships. Using default order.")
    
    # Refresh button
    if st.button('🔄 Refresh', use_container_width=True):
        st.session_state.all_internships = None
        if not st.session_state.user_id:
            st.error("You must be logged in to view internships.")
            return
        db = SupabaseDB()
        internships = db.get_internships_by_user(st.session_state.user_id)
        if internships is None:
            st.error("Failed to load internships. Please try again.")
            return
        st.session_state.all_internships = internships
        st.rerun()

    # Show internship details in a modal-like dialog using an empty element as backdrop
    if st.session_state.show_details:
        internship = next((i for i in all_internships if i['id'] == st.session_state.show_details), None)
        if internship:
            # Style for the popup
            st.markdown("""
                <style>
                    .popup-container {
                        background-color: white;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        padding: 20px;
                        margin: 20px 0;
                        border: 1px solid #ddd;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            # Modal content
            with st.container():
                st.markdown('<div class="popup-container">', unsafe_allow_html=True)
                # Header with close button
                col1, col2 = st.columns([5,1])
                with col1:
                    st.subheader("📋 Internship Details")
                with col2:
                    if st.button("❌", key="close_details", type="secondary"):
                        st.session_state.show_details = None
                        st.rerun()
                
                # Content in two columns
                left_col, right_col = st.columns([2,1])
                
                with left_col:
                    st.markdown(f"### {internship['job_title']}")
                    st.markdown(f"**Company:** {internship['company_name']}")
                    
                    # Date added
                    if internship.get('created_at'):
                        try:
                            # Handle the datetime string directly
                            created_at_str = internship['created_at']
                            # Convert to datetime object
                            if 'T' in created_at_str:
                                date_part, time_part = created_at_str.split('T')
                                time_part = time_part.split('.')[0]  # Remove microseconds
                                created_at = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                            else:
                                created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                            st.markdown(f"**Added:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                        except Exception:
                            # Fallback to just showing the date part if parsing fails
                            st.markdown(f"**Added:** {internship['created_at'].split('T')[0]}")
                    
                    # Description
                    if internship.get('job_description'):
                        st.markdown("### Description")
                        st.markdown(internship['job_description'])
                
                with right_col:
                    # Status with color and emoji
                    status = internship.get('status', 'new').title()
                    status_info = STATUS_INFO.get(status, {'color': 'gray', 'emoji': '❔'})
                    status_color = status_info['color']
                    status_emoji = status_info['emoji']
                    st.markdown(f"<p style='color: {status_color}; text-align: center; font-size: 1.2em;'><strong>{status_emoji} {status}</strong></p>", 
                               unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # Action Buttons Section
                    st.markdown("### 🎯 Actions")
                    
                    status = internship.get('status', 'new')
                    
                    # Show different action buttons based on status
                    if status == 'rejected':
                        # Only show application link for rejected internships if available
                        if internship.get('application_link'):
                            st.link_button("🌐 View Application", internship['application_link'], use_container_width=True)
                        st.info("This internship has been rejected.")
                    
                    elif status == 'applied':
                        # Show application link and reject button for applied internships
                        if internship.get('application_link'):
                            st.link_button("🌐 View Application", internship['application_link'], use_container_width=True)
                        
                        # Show reject button for applied internships
                        reject_key = f"reject_detail_{internship['id']}_{st.session_state.button_counter}"
                        if st.button("❌ Reject", key=reject_key, type="secondary", use_container_width=True):
                            try:
                                db = SupabaseDB()
                                result = db.update_internship_status(user_id, internship['id'], 'rejected')
                                if result:
                                    st.success("✅ Internship successfully rejected!")
                                    st.session_state.all_internships = None
                                    st.session_state.show_details = None
                                    time.sleep(1)
                                    st.experimental_rerun()
                                else:
                                    st.error("Failed to reject internship. Please try again.")
                            except Exception as e:
                                st.error(f"Error updating status: {str(e)}")
                    
                    else:  # new status
                        # Action buttons for new internships in details view
                        buttons_col1, buttons_col2 = st.columns(2)
                        
                        # Apply button
                        with buttons_col1:
                            apply_key = f"apply_detail_{internship['id']}_{st.session_state.button_counter}"
                            if st.button("✅ Apply", key=apply_key, type="primary", use_container_width=True):
                                try:
                                    db = SupabaseDB()
                                    internship_id = int(internship['id'])
                                    # First update the status
                                    result = db.update_internship_status(user_id, internship_id, 'applied')
                                    if result:
                                        # Update successful, now update the UI
                                        st.session_state.show_details = None  # Close the modal
                                        st.session_state.all_internships = None  # Force refresh of internships
                                        # Show success message and rerun
                                        st.success("✅ Successfully applied to internship!")
                                        time.sleep(0.5)  # Brief pause to show the message
                                        st.rerun()
                                    else:
                                        st.error("Failed to apply to internship. Please try again.")
                                except Exception as e:
                                    st.error(f"Error updating internship status: {str(e)}")
                        
                        # Reject button
                        with buttons_col2:
                            reject_key = f"reject_detail_{internship['id']}_{st.session_state.button_counter}"
                            if st.button("❌ Reject", key=reject_key, type="secondary", use_container_width=True):
                                try:
                                    db = SupabaseDB()
                                    internship_id = int(internship['id'])
                                    # First update the status
                                    result = db.update_internship_status(user_id, internship_id, 'rejected')
                                    if result:
                                        # Update successful, now update the UI
                                        st.session_state.show_details = None  # Close the modal
                                        st.session_state.all_internships = None  # Force refresh of internships
                                        # Show success message and rerun
                                        st.success("✅ Internship successfully rejected!")
                                        time.sleep(0.5)  # Brief pause to show the message
                                        st.rerun()
                                    else:
                                        st.error("Failed to reject internship. Please try again.")
                                except Exception as e:
                                    st.error(f"Error updating internship status: {str(e)}")
                        
                        # Show application link if available
                        if internship.get('application_link'):
                            st.link_button("🌐 Apply Online", internship['application_link'], use_container_width=True)
            
                # Close the popup container
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")

    # Handle delete confirmation with a popup-like dialog
    if st.session_state.confirm_delete:
        internship_to_delete = next((i for i in all_internships if i['id'] == st.session_state.confirm_delete), None)
        if internship_to_delete:
            # Create a popup-like effect
            with st.container():
                # Add some spacing
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                # Create the confirmation dialog
                with st.container(border=True):
                    st.markdown("### 🗑️ Confirm Deletion")
                    st.warning(
                        f"Are you sure you want to delete this internship?\n\n"
                        f"**{internship_to_delete['job_title']}** at **{internship_to_delete['company_name']}**"
                    )
                    
                    # Add some spacing
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, Delete", type="primary", key="confirm_yes", use_container_width=True):
                            db = SupabaseDB()
                            # First mark as rejected
                            if db.update_internship_status(user_id, internship_to_delete['id'], 'rejected'):
                                st.success("✅ Internship successfully marked as rejected!")
                                st.session_state.all_internships = None
                                time.sleep(1)  # Give time to see the rejection message
                                # Then delete the internship
                                if db.delete_internship(user_id, internship_to_delete['id']):
                                    # Store success message in session state
                                    st.session_state.delete_success = True
                                    st.session_state.all_internships = None
                                    st.session_state.confirm_delete = None
                                    st.rerun()
                    with col2:
                        if st.button("No, Cancel", type="secondary", key="confirm_no", use_container_width=True):
                            st.session_state.confirm_delete = None
                            st.rerun()
                            
    # Handle reject confirmation with a popup-like dialog
    if st.session_state.confirm_reject:
        internship_to_reject = next((i for i in all_internships if i['id'] == st.session_state.confirm_reject), None)
        if internship_to_reject:
            # Create a popup-like effect
            with st.container():
                # Add some spacing
                st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
                
                # Create the confirmation dialog
                with st.container(border=True):
                    st.markdown("### ❌ Confirm Rejection")
                    st.warning(
                        f"Are you sure you want to reject this internship?\n\n"
                        f"**{internship_to_reject['job_title']}** at **{internship_to_reject['company_name']}**"
                    )
                    
                    # Add some spacing
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Yes, Reject", type="primary", key="confirm_reject_yes", use_container_width=True):
                            db = SupabaseDB()
                            if db.update_internship_status(user_id, internship_to_reject['id'], 'rejected'):
                                # Store success message in session state
                                st.session_state.reject_success = True
                                st.session_state.all_internships = None
                                st.session_state.confirm_reject = None
                                st.rerun()
                    with col2:
                        if st.button("No, Cancel", type="secondary", key="confirm_reject_no", use_container_width=True):
                            st.session_state.confirm_reject = None
                            st.rerun()

    # Show success message if deletion was successful
    if st.session_state.get('delete_success'):
        st.success("✅ Internship successfully deleted!")
        # Clear the success message after showing it
        st.session_state.delete_success = False
        time.sleep(1)
        st.rerun()

    # Show success message if rejection was successful
    if st.session_state.get('reject_success'):
        st.success("✅ Internship successfully rejected!")
        # Clear the success message after showing it
        st.session_state.reject_success = False
        time.sleep(1)
        st.rerun()

    if not all_internships:
        st.info("You haven't saved any internships yet. Use the scraper to add some!")
        return

    if not filtered_internships:
        st.warning("No internships match your current filter settings.")
        return

    # Display internships
    st.info(f"Displaying {len(filtered_internships)} of {len(all_internships)} total internships.")
    
    def update_internship_status_async(internship_id, new_status):
        """Helper function to update internship status"""
        try:
            db = SupabaseDB()
            result = db.update_internship_status(user_id, internship_id, new_status)
            if result:
                st.session_state.all_internships = None
                st.session_state.last_action = 'update'
                st.session_state.last_action_status = True
                return True
            return False
        except Exception as e:
            st.error(f"Error updating status: {str(e)}")
            st.session_state.last_action = 'update'
            st.session_state.last_action_status = False
            return False

    # Handle previous action results
    if st.session_state.last_action == 'update':
        if st.session_state.last_action_status:
            st.success("✅ Status updated successfully!")
        st.session_state.last_action = None
        st.session_state.last_action_status = None
        st.rerun()
    
    for internship in filtered_internships:
        with st.container(border=True):
            # Header section with company and status
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {internship.get('job_title', 'Untitled Position')}")
                company = internship.get('company_name', 'N/A')
                st.markdown(f"**Company:** {company}")
            
            with col2:
                # Status at the top
                status = internship.get('status', 'new').title()
                status_info = STATUS_INFO.get(status, {'color': 'gray', 'emoji': '❔'})
                st.markdown(f"<p style='color: {status_info['color']}; text-align: center; margin-bottom: 10px;'><strong>{status_info['emoji']} {status}</strong></p>", 
                           unsafe_allow_html=True)
            
            # Content section
            if internship.get('created_at'):
                try:
                    created_at_str = internship['created_at']
                    if isinstance(created_at_str, str):
                        if 'T' in created_at_str:
                            date_part = created_at_str.split('T')[0]
                            time_part = created_at_str.split('T')[1].split('.')[0]
                            created_at = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
                        else:
                            created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                        st.markdown(f"**Added:** {created_at.strftime('%Y-%m-%d %H:%M')}")
                    else:
                        st.markdown(f"**Added:** {created_at_str}")
                except Exception:
                    st.markdown(f"**Added:** {str(internship['created_at']).split('T')[0]}")
            
            # Preview of description
            if internship.get('job_description'):
                description = internship['job_description']
                preview = description[:150] + ('...' if len(description) > 150 else '')
                st.markdown(f"**Preview:** {preview}")
            
            # Actions section
            with st.expander("📋 View Details"):
                if internship.get('job_description'):
                    st.markdown("### Description")
                    st.markdown(internship['job_description'])
                
                st.markdown("### 🎯 Actions")
                current_status = internship.get('status', 'new').lower()
                
                # Application link if available
                if internship.get('application_link'):
                    st.link_button("🌐 Apply Online", internship['application_link'], use_container_width=True)
                
                # Status-based actions
                if current_status == 'rejected':
                    st.info("This internship has been rejected.")
                
                elif current_status == 'applied':
                    reject_key = f"reject_{internship['id']}"
                    if st.button("❌ Reject", key=reject_key, type="secondary", use_container_width=True):
                        with st.spinner("Updating status..."):
                            if update_internship_status_async(internship['id'], 'rejected'):
                                st.success("✅ Status updated to Rejected!")
                                st.rerun()
                
                elif current_status == 'new':
                    cols = st.columns(2)
                    with cols[0]:
                        apply_key = f"apply_{internship['id']}"
                        if st.button("✅ Apply", key=apply_key, type="primary", use_container_width=True):
                            with st.spinner("Updating status..."):
                                if update_internship_status_async(internship['id'], 'applied'):
                                    st.success("✅ Status updated to Applied!")
                                    st.rerun()
                    
                    with cols[1]:
                        reject_key = f"reject_{internship['id']}"
                        if st.button("❌ Reject", key=reject_key, type="secondary", use_container_width=True):
                            with st.spinner("Updating status..."):
                                if update_internship_status_async(internship['id'], 'rejected'):
                                    st.success("✅ Status updated to Rejected!")
                                    st.rerun()
