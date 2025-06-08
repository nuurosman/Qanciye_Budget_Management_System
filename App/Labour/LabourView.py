from flask import Flask, render_template, request, jsonify, session, redirect, flash,url_for
from App.Labour.LabourModal import get_labour_model 
from App import app
from decimal import Decimal
import traceback
from App.configuration import LabourDbConnetion
import base64
from datetime import datetime, timedelta


# Initialize the user model
status, user_model_db = get_labour_model()
if not status:
    print(f"Error initializing user model: {user_model_db}")
    raise Exception("Failed to initialize user model.")
usermodel = user_model_db

# Register a custom Jinja2 filter for base64 encoding
@app.route('/labour/dashboard')
def labour_dashboard():
    user = session.get('user')

    if not user or user.get('user_type') != 'labour':
        return redirect('/login')

    labour_id = session.get('labour_id')
    if not labour_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_labour_model()
    if not success:
        flash("Failed to load dashboard data.", "danger")
        return redirect('/login')

    try:
        project_id = request.args.get('project_id')
        view_type = request.args.get('view_type', 'attendance')  # Default to attendance

        # Get assigned site engineer
        site_engineer = model.get_assigned_site_engineer(labour_id)

        # Get assigned projects for dropdown
        projects = model.get_my_projects(labour_id)

        # Get attendance data
        attendance_data = model.get_attendance_stats(labour_id, project_id)
        total_present = sum(item['present_days'] for item in attendance_data)
        total_absent = sum(item['absent_days'] for item in attendance_data)

        # Get wage data
        wage_data = model.get_wage_stats(labour_id, project_id)
        total_wages = sum(item['total_wage'] for item in wage_data) if wage_data else 0

        # Calculate project statuses
        projects_status = {
            "ongoing": sum(1 for p in projects if p['status'] == 'ongoing'),
            "completed": sum(1 for p in projects if p['status'] == 'completed'),
            "pending": sum(1 for p in projects if p['status'] == 'pending'),
            "planned": sum(1 for p in projects if p['status'] == 'planned'),
        }

        return render_template(
            'labour/labour_dashboard.html',
            user=user,
            site_engineer=site_engineer,
            projects=projects,
            total_projects_count=len(projects),
            total_wages=total_wages,
            projects_status=projects_status,
            attendance_data=attendance_data,
            wage_data=wage_data,
            total_present=total_present,
            total_absent=total_absent,
            selected_project=project_id,
            present_days=total_present,
            absent_days=total_absent,
            view_type=view_type
        )
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return redirect('/login')

# profile photo

@app.route('/Labour/projects')
def Labour_my_projects():
    login_id = session.get('labour_id')
    if not login_id:
        flash("Unauthorized. Please log in.", "danger")
        return redirect('/login')

    success, model = get_labour_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        projects = model.get_my_projects(login_id)
        # print(f"DEBUG: Projects for labour_id={login_id}: {projects}")  # Debug print
        return render_template('Labour/labour_project.html', projects=projects)
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return f"Error fetching projects: {str(e)}", 500




@app.route('/Labour/logout')
def labour_logout():
    """Log out the site_engineer and clear the session"""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/login')
@app.context_processor
def inject_profile_data():
    """Make profile data available to all templates for navbar avatar."""
    user = session.get('user')
    if user:
        user_type = user.get('user_type')
        if user_type == 'labour':
            labour_id = session.get('labour_id')
            if labour_id:
                try:
                    success, model = get_labour_model()
                    if success:
                        profile_data = model.get_labour_profile(labour_id)
                        if profile_data and profile_data.get('profile_picture'):
                            return {
                                'global_profile': {
                                    'picture': base64.b64encode(profile_data['profile_picture']).decode('utf-8'),
                                    'filename': profile_data.get('profile_picture_filename', 'jpeg')
                                },
                                'user_name': user.get('full_name'),
                                'email': user.get('email'),
                                'user_type': user_type
                            }
                        else:
                            return {
                                'global_profile': None,
                                'user_name': user.get('full_name'),
                                'email': user.get('email'),
                                'user_type': user_type
                            }
                except Exception as e:
                    print(f"Error loading labour profile data: {e}")
        elif user_type == 'site_engineer':
            site_engineer_id = session.get('site_engineer_id')
            if site_engineer_id:
                try:
                    success, model = get_labour_model()
                    if success and hasattr(model, 'get_site_engineer_profile'):
                        profile_data = model.get_site_engineer_profile(site_engineer_id)
                        if profile_data and profile_data.get('profile_picture'):
                            return {
                                'global_profile': {
                                    'picture': base64.b64encode(profile_data['profile_picture']).decode('utf-8'),
                                    'filename': profile_data.get('profile_picture_filename', 'jpeg')
                                },
                                'user_name': user.get('full_name'),
                                'email': user.get('email'),
                                'user_type': user_type
                            }
                        else:
                            return {
                                'global_profile': None,
                                'user_name': user.get('full_name'),
                                'email': user.get('email'),
                                'user_type': user_type
                            }
                except Exception as e:
                    print(f"Error loading site engineer profile data: {e}")
        elif user_type == 'admin':
            admin_id = session.get('admin_id')
            if admin_id:
                try:
                    success, model = get_labour_model()
                    if success and hasattr(model, 'get_admin_profile'):
                        profile_data = model.get_admin_profile(admin_id)
                        if profile_data and profile_data.get('profile_picture'):
                            return {
                                'global_profile': {
                                    'picture': base64.b64encode(profile_data['profile_picture']).decode('utf-8'),
                                    'filename': profile_data.get('profile_picture_filename', 'jpeg')
                                },
                                'user_name': user.get('full_name', 'Admin'),
                                'email': user.get('email', ''),
                                'user_type': user_type
                            }
                        else:
                            return {
                                'global_profile': None,
                                'user_name': user.get('full_name', 'Admin'),
                                'email': user.get('email', ''),
                                'user_type': user_type
                            }
                except Exception as e:
                    print(f"Error loading admin profile data: {e}")
        # fallback for any user
        return {
            'global_profile': None,
            'user_name': user.get('full_name'),
            'email': user.get('email'),
            'user_type': user.get('user_type')
        }
    return {'global_profile': None, 'user_name': None, 'email': None, 'user_type': None}


@app.route('/labour/profile')
def labour_profile():
    user = session.get('user')
    if not user or user.get('user_type') != 'labour':
        flash("Unauthorized access. Please log in.", "danger")
        return redirect('/login')

    labour_id = session.get('labour_id')
    if not labour_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_labour_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        profile_data = model.get_labour_profile(labour_id)
        profile_picture = None
        if profile_data and profile_data.get('profile_picture'):
            profile_picture = base64.b64encode(profile_data['profile_picture']).decode('utf-8')
        return render_template(
            'Labour/labour_profile.html',
            user_name=user.get('full_name'),
            email=user.get('email'),
            profile_picture=profile_picture
        )
    except Exception as e:
        print(f"Error loading labour profile: {e}")
        flash("An error occurred while loading the profile.", "danger")
        return redirect('/login')

@app.route('/labour/update_profile_image', methods=['POST'])
def labour_update_profile_image():
    user = session.get('user')
    if not user or user.get('user_type') != 'labour':
        flash("Unauthorized access. Please log in as a labour.", "danger")
        return redirect('/login')

    labour_id = session.get('labour_id')
    if not labour_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    if 'profile_image' not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for('labour_profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash("No file selected.", "danger")
        return redirect(url_for('labour_profile'))

    if not allowed_file(file.filename):
        flash("Allowed image types are: png, jpg, jpeg, gif", "danger")
        return redirect(url_for('labour_profile'))

    max_size = 2 * 1024 * 1024  # 2MB
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_size:
        flash("Image size must be less than 2MB", "danger")
        return redirect(url_for('labour_profile'))

    if file:
        try:
            file_data = file.read()
            success, model = get_labour_model()
            if not success:
                flash("Database connection failed.", "danger")
                return redirect(url_for('labour_profile'))

            update_success, message = model.update_labour_profile_picture(
                labour_id, file_data, file.filename
            )

            if update_success:
                flash("Profile image updated successfully.", "success")
            else:
                flash(f"Failed to update profile image: {message}", "danger")

        except Exception as e:
            print(f"Error updating profile image: {e}")
            flash("An error occurred while updating the profile image.", "danger")

    return redirect(url_for('labour_profile'))

@app.route('/site_engineer/update_profile_image', methods=['POST'])
def site_engineer_update_profile_image_local():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    if 'profile_image' not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for('site_engineer_profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash("No file selected.", "danger")
        return redirect(url_for('site_engineer_profile'))

    if not allowed_file(file.filename):
        flash("Allowed image types are: png, jpg, jpeg, gif", "danger")
        return redirect(url_for('site_engineer_profile'))

    max_size = 2 * 1024 * 1024  # 2MB
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_size:
        flash("Image size must be less than 2MB", "danger")
        return redirect(url_for('site_engineer_profile'))

    if file:
        try:
            file_data = file.read()
            success, model = get_labour_model()
            if not success:
                flash("Database connection failed.", "danger")
                return redirect(url_for('site_engineer_profile'))

            update_success, message = model.update_site_engineer_profile_picture(
                site_engineer_id, file_data, file.filename
            )

            if update_success:
                flash("Profile image updated successfully.", "success")
            else:
                flash(f"Failed to update profile image: {message}", "danger")

        except Exception as e:
            print(f"Error updating profile image: {e}")
            flash("An error occurred while updating the profile image.", "danger")

    return redirect(url_for('site_engineer_profile'))

def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


@app.route('/admin/profile')
def admin_profile():
    user = session.get('user')
    if not user or user.get('user_type') != 'admin':
        flash("Unauthorized access. Please log in.", "danger")
        return redirect('/login')

    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_labour_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        profile_data = model.get_admin_profile(admin_id)
        profile_picture = None
        if profile_data and profile_data.get('profile_picture'):
            profile_picture = base64.b64encode(profile_data['profile_picture']).decode('utf-8')
        return render_template(
            'Admin/admin_profile.html',
            user_name=user.get('full_name', 'Admin'),
            email=user.get('email', ''),
            profile_picture=profile_picture
        )
    except Exception as e:
        print(f"Error loading admin profile: {e}")
        flash("An error occurred while loading the profile.", "danger")
        return redirect('/login')
    
# Admin profile photo
@app.route('/admin/update_profile_image', methods=['POST'])
def admin_update_profile_image():
    user = session.get('user')
    if not user or user.get('user_type') != 'admin':
        flash("Unauthorized access. Please log in as an admin.", "danger")
        return redirect('/login')

    admin_id = session.get('admin_id')
    if not admin_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    if 'profile_image' not in request.files:
        flash("No file selected.", "danger")
        return redirect(url_for('admin_profile'))

    file = request.files['profile_image']
    if file.filename == '':
        flash("No file selected.", "danger")
        return redirect(url_for('admin_profile'))

    if not allowed_file(file.filename):
        flash("Allowed image types are: png, jpg, jpeg, gif", "danger")
        return redirect(url_for('admin_profile'))

    max_size = 2 * 1024 * 1024  # 2MB
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_size:
        flash("Image size must be less than 2MB", "danger")
        return redirect(url_for('admin_profile'))

    if file:
        try:
            file_data = file.read()
            success, model = get_labour_model()
            if not success:
                flash("Database connection failed.", "danger")
                return redirect(url_for('admin_profile'))

            update_success, message = model.update_admin_profile_picture(
                admin_id, file_data, file.filename
            )

            if update_success:
                flash("Profile image updated successfully.", "success")
            else:
                flash(f"Failed to update profile image: {message}", "danger")

        except Exception as e:
            print(f"Error updating profile image: {e}")
            flash("An error occurred while updating the profile image.", "danger")

    return redirect(url_for('admin_profile'))

# Secret key
app.secret_key = 'your_secret_key_here'