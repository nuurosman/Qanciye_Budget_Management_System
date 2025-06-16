from flask import Flask, render_template, request, jsonify, session, redirect, flash, url_for

# Fix import and initialization for AdminModel

import App.admin.admin_model as admin_model_module
from App import app
import hashlib
import os
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer
from App.admin.email_utils import send_reset_email
from collections import defaultdict
import time
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta


# Initialize the user model at the application level
# Instead of calling getAdminModel(), instantiate AdminModel directly
try:
    db_config = admin_model_module.AdminDbConnetion()
    user_db = admin_model_module.UserDatabase(
        host=db_config.DB_HOSTNAME,
        port=3300,
        user=db_config.DB_USERNAME,
        password=db_config.DB_PASSWORD,
        database=db_config.DB_NAME,
    )
    user_db.make_connection()
    adminmodel = admin_model_module.AdminModel(user_db.connection)
except Exception as e:
    print(f"Error initializing user model: {e}")
    raise Exception("Failed to initialize user model.")

# Context Processor to inject user_name into all templates
@app.context_processor
def inject_user():
    user = session.get('user')
    return {
        "user_name": user.get('full_name') if user else None
    }
# Start of admins

# Add these functions to fetch the counts
def get_labourers_assigned_count():
    success, assignments = adminmodel.get_all_labour_projects()
    return len(assignments) if success else 0

# Function to get the total number of projects



def get_total_projects_count():
    success, projects = adminmodel.get_all_projects()
    return len(projects) if success else 0

def get_admins_assigned_count():
    success, projects = adminmodel.get_all_projects()
    if not success:
        return 0
    # If projects is a list of dicts, use the correct key (e.g., 'admin_id')
    assigned_admins = {project.get('admin_id') for project in projects if project.get('admin_id')}
    return len(assigned_admins)

def get_total_site_engineers_count():
    success, site_engineers = adminmodel.get_all_siteEngineers()
    return len(site_engineers) if success else 0


# Admin Dashboard
def get_total_admins_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM admin")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_total_projects_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_total_labourers_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM labour")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_attendance_logs_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM attendance")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_ongoing_tasks_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'ongoing'")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_completed_tasks_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects WHERE status = 'completed'")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_total_expenses_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM expenses")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_material_entries_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM materials")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_payments_made_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM payments")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_total_site_engineers_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM site_engineer")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_labours_assigned_to_projects_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(DISTINCT labour_id) FROM labour_project")
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def get_site_engineers_assigned_to_projects_count():
    cursor = adminmodel.connection.cursor()
    cursor.execute("SELECT COUNT(DISTINCT site_engineer_id) FROM projects WHERE site_engineer_id IS NOT NULL")
    count = cursor.fetchone()[0]
    cursor.close()
    return count
# Admin Dashboard
@app.route('/admin/dashboard')
def dashboard():
    user = session.get('user')  # Retrieve the user data from the session
    if not user or user.get('user_type') != 'admin':  # Check if user is logged in and an admin
        return redirect('/login')  # Redirect to login if not authenticated

    # Fetch all counts
    ongoing_tasks_count = get_ongoing_tasks_count()
    completed_tasks_count = get_completed_tasks_count()
    total_admins_count = get_total_admins_count()
    total_projects_count = get_total_projects_count()
    total_labourers_count = get_total_labourers_count()
    attendance_logs_count = get_attendance_logs_count()
    total_expenses_count = get_total_expenses_count()
    material_entries_count = get_material_entries_count()
    payments_made_count = get_payments_made_count()
    total_site_engineers_count = get_total_site_engineers_count()
    # Add new counts
    labours_assigned_to_projects_count = get_labours_assigned_to_projects_count()
    site_engineers_assigned_to_projects_count = get_site_engineers_assigned_to_projects_count()

    email = user.get('email')

    return render_template('/admin/adminDashboard.html', 
                           total_admins_count=total_admins_count,
                           total_projects_count=total_projects_count,
                           total_labourers_count=total_labourers_count,
                           attendance_logs_count=attendance_logs_count,
                           total_expenses_count=total_expenses_count,
                           material_entries_count=material_entries_count,
                           payments_made_count=payments_made_count,
                           total_site_engineers_count=total_site_engineers_count,
                           labours_assigned_to_projects_count=labours_assigned_to_projects_count,
                           site_engineers_assigned_to_projects_count=site_engineers_assigned_to_projects_count,
                            ongoing_tasks_count=ongoing_tasks_count,
                        completed_tasks_count=completed_tasks_count)


# Admin Dashboard End    
@app.route('/admin/dashboard/data')
def dashboard_data():
    if not session.get('user') or session.get('user').get('user_type') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    # First update all project budgets
    success, message = adminmodel.update_project_budgets()
    if not success:
        return jsonify({'error': message}), 500
    
    # Then proceed with getting dashboard data
    success, ongoing_projects = adminmodel.get_ongoing_projects()
    if not success:
        return jsonify({'error': ongoing_projects}), 500
    
    budget_data = [{
        'name': project['name'],
        'total_budget': float(project['total_budget']),
        'used_budget': float(project['used_budget']),
        'remaining_budget': float(project['remaining_budget'])
    } for project in ongoing_projects]
    
    total_money_spent = sum(float(project['used_budget']) for project in ongoing_projects)
    total_budget = sum(float(project['total_budget']) for project in ongoing_projects)
    budget_usage_percentage = (total_money_spent / total_budget * 100) if total_budget > 0 else 0
    
    today = datetime.now().date()
    success, active_labours_count = adminmodel.get_todays_attendance_count(today)
    if not success:
        return jsonify({'error': active_labours_count}), 500
    
    success, last_attendance = adminmodel.get_last_attendance(today)
    if not success:
        return jsonify({'error': last_attendance}), 500
    
    last_attendance_time = last_attendance['created_at'].strftime('%H:%M:%S') if last_attendance else None
    
    seven_days_ago = today - timedelta(days=7)
    success, attendance_trend = adminmodel.get_attendance_trend(seven_days_ago, today)
    if not success:
        return jsonify({'error': attendance_trend}), 500
    
    return jsonify({
        'budgetData': budget_data,
        'totalMoneySpent': total_money_spent,
        'budgetUsagePercentage': round(budget_usage_percentage, 2),
        'activeLaboursCount': active_labours_count,
        'lastAttendanceTime': last_attendance_time,
        'attendanceTrend': [{'date': str(date), 'count': count} for date, count in attendance_trend]
    })




# Admins Management
@app.route('/admin/adminManage')
def adminManage():
    """Render the Admins form with user data."""
    success, result = adminmodel.get_all_admins()
    print("Admins passed to template:", result)  # Print the result in the console
    if success:
        return render_template('/admin/adminManage.html', users=result) 
    else:
        return f"Error fetching Admins view: {result}", 500

# Admin Update data
@app.route('/update_user', methods=['POST'])
def update_admin():
    user_id = request.form.get('user_id')
    full_name = request.form.get('full_name')
    email = request.form.get('email')
    password = request.form.get('password')  # Password is optional

    # Call the update function
    success, message = adminmodel.update_admin(user_id, full_name, email, password)

    if success:
        print('Admin updated successfully')
        return redirect(url_for('adminManage'))
    else:
        print(f"Failed to update admin: {message}")
        return f"Error: {message}", 400  # Return error message
    

# Delete admin    
@app.route('/delete_admin/<int:admin_id>', methods=['POST'])
def delete_admin(admin_id):
    """Deletes a admin record from the database."""
    # List of tables where the site_engineer_id might be referenced
    related_tables = ['projects'] # Add more tables as needed

    # Check if the site engineer is referenced
    can_delete, message = adminmodel.check_referen(admin_id, related_tables)

    if not can_delete:
        print(f"Cannot delete admin View: {message}")
        return f"Cannot delete admin View: {message}", 400

    # Proceed with deletion if no references exist
    success, message = adminmodel.delete_admin(admin_id)
    if success:
        print(message)
        return redirect(url_for('adminManage'))  # Redirect back to the manage page
    else:
        print(f"Failed to delete admin: {message}")
        return f"Error: {message}", 400  # Return error message





    

# END ADMIN



# START LABOUR MANAGEMENT
# Labour Management
@app.route('/admin/LabourManage')
def labour_Manage():
    """Render the labour list form with user data."""
    success, result = adminmodel.get_all_labours()
    print("Labours passed to template:", result)  # Print the result in the console
    if success:
        return render_template('/admin/labourManage.html', users=result)
    else:
        return f"Error fetching Labours view: {result}", 500



@app.route('/update_labour', methods=['POST'])
def update_labour():
    user_id = request.form.get('labour_id')
    full_name = request.form.get('labour_full_name')
    email = request.form.get('labour_email')
    password = request.form.get('labour_password')  # Password is optional

    # Ensure required fields are not empty
    if not user_id or not full_name or not email:
        flash("Missing required fields", "error")
        return redirect(url_for('labour_Manage'))  # Redirect back to labour management page

    # Call the update function
    success, message = adminmodel.update_labour(user_id, full_name, email, password)

    # Redirect to labour management page with success or error message
    if success:
        flash("Labour updated successfully!", "success")
        return redirect(url_for('labour_Manage'))  # Redirect to prevent JSON output
    else:
        flash("Error: " + message, "error")
        return redirect(url_for('labour_Manage'))


# Delete Labour 

# @app.route('/delete_labour/<int:labour_id>', methods=['POST'])
# def delete_labour(labour_id):
#     """Deletes a labour record from the database."""
#     try:
#         # Ensure the correct table name is used
#         success, message = adminmodel.delete_labour(labour_id)

#         if success:
#             flash("Labour deleted successfully!", "success")
#         else:
#             flash(f"Error deleting labour: {message}", "error")

#     except Exception as e:
#         flash(f"An error occurred: {str(e)}", "error")

#     return redirect(url_for('labour_Manage'))  # Redirect back to labour management page

@app.route('/delete_labour/<int:labour_id>', methods=['POST'])
def delete_labour(labour_id):
    """Deletes a labour record from the database."""
    # List of tables where the site_engineer_id might be referenced
    related_tables = ['wages', 'attendance']  # Add more tables as needed

    # Check if the site engineer is referenced
    can_delete, message = adminmodel.check_references(labour_id, related_tables)

    if not can_delete:
        print(f"Cannot delete labour View: {message}")
        return f"Cannot delete labour View: {message}", 400

    # Proceed with deletion if no references exist
    success, message = adminmodel.delete_labour(labour_id)
    if success:
        print(message)
        return redirect(url_for('labour_Manage'))  # Redirect back to the manage page
    else:
        print(f"Failed to delete engineer: {message}")
        return f"Error: {message}", 400  # Return error message



# END LABOUR MANAGEMENT

# START SITE ENGINEER

# Site engineer page
@app.route('/site_engineerManage', methods=['GET'])
def site_engineerManage():
    """Render the registration form with user data."""
    success, result = adminmodel.get_all_siteEngineers()
    # Ensure result is a list of dicts
    if success and result and isinstance(result, list) and not isinstance(result[0], dict):
        # Convert list of tuples to list of dicts if needed
        keys = ['site_engineer_id', 'full_name', 'email', 'created_at']
        result = [dict(zip(keys, row)) for row in result]
    if success:
        return render_template('admin/site_engineerManage.html', users=result)
    else:
        return f"Error fetching users: {result}", 500

# Admin Update data
@app.route('/update_siteE+Ngineer', methods=['POST'])
def update_siteENgineer():
    user_id = request.form.get('site_engineer_id')
    full_name = request.form.get('site_engineer_full_name')
    email = request.form.get('site_engineer_email')
    password = request.form.get('site_engineer_password')  # Password is optional

    # Call the update function
    success, message = adminmodel.update_siteENgineer(user_id, full_name, email, password)

    if success:
        print('Admin updated successfully View')
        return redirect(url_for('site_engineerManage'))
    else:
        print(f"Failed to update engineer: {message}")
        return f"Error: {message}", 400  # Return error message
    

    
@app.route('/delete_siteEngineer/<int:site_engineer_id>', methods=['POST'])
def delete_siteEngineer(site_engineer_id):
    """Deletes a site engineer record from the database."""
    # List of tables where the site_engineer_id might be referenced
    related_tables = ['materials', 'projects',  # Add more tables as needed
]

    # Check if the site engineer is referenced
    can_delete, message = adminmodel.check_referenc(site_engineer_id, related_tables)

    if not can_delete:
        print(f"Cannot delete site engineer View: {message}")
        return f"Cannot delete site engineer View: {message}", 400

    # Proceed with deletion if no references exist
    success, message = adminmodel.delete_siteEngineer(site_engineer_id)
    if success:
        print(message)
        return redirect(url_for('site_engineerManage'))  # Redirect back to the manage page
    else:
        print(f"Failed to delete engineer: {message}")
        return f"Error: {message}", 400  # Return error message



@app.route('/get_site_engineers_with_projects')
def get_site_engineers_with_projects():
    success, site_engineers = adminmodel.get_site_engineers_with_projects()
    if success:
        return jsonify({"site_engineers": site_engineers}), 200
    else:
        return jsonify({"error": "Failed to fetch site engineers"}), 500

@app.route('/get_projects_for_site_engineer/<int:site_engineer_id>')
def get_projects_for_site_engineer(site_engineer_id):
    success, projects = adminmodel.get_projects_for_site_engineer(site_engineer_id)
    if success:
        # projects is a list of tuples or dicts, handle both
        return jsonify({"success": True, "projects": [
            {"id": p[0], "name": p[1]} if isinstance(p, (list, tuple)) else {"id": p["project_id"], "name": p["name"]}
            for p in projects
        ]}), 200
    else:
        return jsonify({"success": False, "message": "Failed to fetch projects"}), 500

@app.route('/get_site_engineers', methods=['GET'])
def get_site_engineers():
    """Fetch all site engineers."""
    success, site_engineers = adminmodel.get_all_siteEngineers()
    if success:
        # site_engineers is a list of dicts
        return jsonify({"success": True, "site_engineers": [
            {"id": se["site_engineer_id"], "name": se["full_name"]} for se in site_engineers
        ]}), 200
    else:
        return jsonify({"success": False, "message": "Failed to fetch site engineers"}), 500

@app.route('/get_projects_by_site_engineer/<int:site_engineer_id>', methods=['GET'])
def get_projects_by_site_engineer(site_engineer_id):
    """Fetch projects assigned to a specific site engineer."""
    success, projects = adminmodel.get_projects_for_site_engineer(site_engineer_id)
    if success:
        # projects is a list of tuples or dicts, handle both
        return jsonify({"success": True, "projects": [
            {"id": p[0], "name": p[1]} if isinstance(p, (list, tuple)) else {"id": p["project_id"], "name": p["name"]}
            for p in projects
        ]}), 200
    else:
        return jsonify({"success": False, "message": "Failed to fetch projects"}), 500


# END SITE ENGINEER PAGE


# Here comes the login and Register and password manages

# Registration Handler
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    full_name = data.get('full_name')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type')
    type_of_work = data.get('type_of_work', None)

    if not full_name or not email or not password or user_type not in ['admin', 'site_engineer', 'labour']:
        return jsonify({"success": False, "message": "Invalid input."}), 400

    success, message = adminmodel.register_user(full_name, email, password, user_type, type_of_work)
    return jsonify({"success": success, "message": message})

# User Login
@app.route('/')
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('admin/user_login.html')


@app.route('/login', methods=['POST'])
def login_user():
    try:
        if request.content_type != 'application/json':
            return jsonify({"success": False, "message": "Invalid Content-Type. Expected application/json."}), 415

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        user_type = data.get('user_type')

        if not email or not password or user_type not in ['admin', 'site_engineer', 'labour']:
            return jsonify({"success": False, "message": "Invalid input."}), 400

        print(f"Login Attempt: Email={email}, UserType={user_type}")

        # Authenticate user
        success, user_data = adminmodel.authenticate_user(email, password, user_type)
        if success:
            # Clear any previous session
            session.clear()

            # Store user data in session
            session['user'] = {
                "email": email,
                "user_type": user_type,
                "full_name": user_data['full_name'],
                "user_id": user_data['user_id'],
            }

            # Optionally store specific role-based IDs
            if user_type == 'site_engineer':
                session['site_engineer_id'] = user_data['user_id']
            elif user_type == 'admin':
                session['admin_id'] = user_data['user_id']
            elif user_type == 'labour':
                session['labour_id'] = user_data['user_id']

            redirect_url = f"/{user_type}/dashboard"
            return jsonify({"success": True, "message": "Login successful.", "redirect_url": redirect_url}), 200
        else:
            return jsonify({"success": False, "message": user_data}), 401
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500


# Password Reset Page
@app.route('/reset_password')
def render_reset_password():
    return render_template('admin/reset_password.html')

@app.route('/reset_password', methods=['POST'])
def handle_reset_password():
    try:
        data = request.get_json()
        email = data.get('email')
        new_password = data.get('new_password')
        user_type = data.get('user_type')

        # Validate input
        if not email or not new_password or user_type not in ['admin', 'site_engineer', 'labour']:
            return jsonify({"success": False, "message": "Invalid input."}), 400

        # Check if the email exists in the database
        sql_check_email = f"SELECT COUNT(*) FROM {user_type} WHERE email = %s"
        adminmodel.cursor.execute(sql_check_email, (email,))
        email_exists = adminmodel.cursor.fetchone()[0]

        if email_exists == 0:
            return jsonify({"success": False, "message": "Email not found in the database."}), 404

        # Hash the new password
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

        # Update the database with the new hashed password
        sql_update_password = f"UPDATE {user_type} SET password = %s WHERE email = %s"
        adminmodel.cursor.execute(sql_update_password, (hashed_password, email))
        adminmodel.connection.commit()

        return jsonify({"success": True, "message": "Password reset successful."}), 200
    except Exception as e:
        print(f"Error during password reset: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

# Start Project Section Start---------------------------------------------------------------------



# Register a new project

@app.route('/register_project', methods=['POST'])
def register_project():
    data = request.get_json() if request.content_type == 'application/json' else request.form

    name = data.get('name')
    description = data.get('description')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    total_budget = data.get('total_budget')
    material_budget = data.get('material_budget')
    wages_budget = data.get('wages_budget')
    other_expenses_budget = data.get('other_expenses_budget')
    status = data.get('status')
    site_engineer_id = data.get('site_engineer_id')
    admin_id = data.get('admin_id')

    if not all([name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id, admin_id]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    success, message = adminmodel.register_project(
        name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id, admin_id
    )
    # If validation fails, return 400 with the message
    return jsonify({"success": success, "message": message}), 201 if success else 400

# Fetch and display projects
@app.route('/admin/projectManage')
def project_manage():
    """Render All The Projects In the Table."""
    success, projects = adminmodel.get_all_projects()

    # Get the logged-in admin info
    user = session.get('user')
    current_admin = None
    if user and user.get('user_type') == 'admin':
        current_admin = {
            "id": user.get('user_id'),
            "name": user.get('full_name')
        }

    if success:
        # print("Projects fetched successfully:", projects)  # Debugging
        return render_template(
            'admin/projectManage.html',
            projects=projects,
            current_admin=current_admin
        )
    else:
        print("Error fetching project data:", projects)  # Debugging
        return "Error fetching project data", 500  


    



# Update a project
@app.route('/update_project', methods=['POST'])
def update_project():
    data = request.form

    project_id = data.get('project_id')
    name = data.get('name')
    description = data.get('description')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    total_budget = data.get('total_budget')
    material_budget = data.get('material_budget')
    wages_budget = data.get('wages_budget')
    other_expenses_budget = data.get('other_expenses_budget')
    status = data.get('status')
    site_engineer_id = data.get('site_engineer_id')  # Now included in update

    # Fix: Pass site_engineer_id to the model
    success, message = adminmodel.update_project(
        project_id, name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id
    )
    if success:
        return redirect(url_for('project_manage'))
    else:
        # Optionally, flash the error or handle as needed
        return f"Error: {message}", 400

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    success, message = adminmodel.delete_project(project_id)
    if success:
        return redirect(url_for('project_manage'))
    else:
        print(f"Failed to delete project: {message}")
        return f"Error: {message}", 400

@app.route('/get_project_budget/<int:project_id>')
def get_project_budget(project_id):
    success, project_budget = adminmodel.get_project_budget(project_id)
    if success:
        return jsonify({"project_budget": project_budget}), 200
    else:
        return jsonify({"error": "Failed to fetch project budget"}), 500

@app.route('/get_dropdown_data')
def get_dropdown_data():
    success_se, site_engineers = adminmodel.get_all_siteEngineers()
    success_ad, admins = adminmodel.get_all_admins()
    success_lb, labours = adminmodel.get_all_labours()
    success_pr, projects = adminmodel.get_all_projects()

    if success_se and success_ad and success_lb and success_pr:
        site_engineers_list = [{"id": se[0], "name": se[1]} for se in site_engineers]
        admins_list = [{"id": admin[0], "name": admin[1]} for admin in admins]
        labours_list = [{"id": labour[0], "name": labour[1]} for labour in labours]
        # Fix: Use dict keys for projects
        projects_list = [{"id": project["project_id"], "name": project["name"]} for project in projects]

        return jsonify({
            "site_engineers": site_engineers_list,
            "admins": admins_list,
            "labours": labours_list,
            "projects": projects_list
        })

    return jsonify({"error": "Failed to fetch data"}), 500




# Start Project Section End---------------------------------------------------------------------

# Material Management Section Start---------------------------------------------------------------------
@app.route('/register_material', methods=['POST'])
def register_material():
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form

        item_name = data.get('item_name')
        quantity = int(data.get('quantity')) if data.get('quantity') else None
        unit_price = float(data.get('unit_price')) if data.get('unit_price') else None
        project_id = data.get('project_id')
        admin_id = data.get('admin_id')
        amount = float(data.get('amount')) if data.get('amount') else (quantity * unit_price if quantity and unit_price else None)

        # Ensure all required fields are present
        if not all([item_name, quantity, unit_price, project_id, admin_id]):
            return jsonify({"success": False, "message": "Missing required fields."}), 400

        # Pass None for site_engineer_id
        success, message = adminmodel.register_material(item_name, quantity, unit_price, amount, None, project_id, admin_id)
        # FIX: Correct conditional expression syntax
        return jsonify({"success": success, "message": message}), (201 if success else 400)

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

@app.route('/update_material', methods=['POST'])
def update_material():
    # Accept both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form


    material_id = data.get('material_id')
    item_name = data.get('item_name')
    quantity = data.get('quantity')
    unit_price = data.get('unit_price')
    amount = data.get('amount')
    project_id = data.get('project_id')
    admin_id = session.get('user', {}).get('user_id')


    # Validate required fields
    if not all([material_id, item_name, quantity, unit_price, amount, project_id, admin_id]):
        # If AJAX/JSON, return JSON error
        if request.is_json:
            return jsonify({"success": False, "message": "Missing required fields."}), 400
        return "Missing required fields.", 400

    # Call the update function
    success, message = adminmodel.update_material(
        material_id, item_name, quantity, unit_price, amount, project_id, admin_id
    )
    if request.is_json:
        return jsonify({"success": success, "message": message}), 200 if success else 400
    if success:
        return redirect(url_for('manageMmaterials'))
    else:
        return f"Error: {message}", 400


@app.route('/manage_materials')
def manageMmaterials():
    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
    except Exception as e:
        print(f"Error committing transactions: {e}")

    success, materials = adminmodel.get_all_materials()
    current_admin = None
    user = session.get('user')
    
    if user and user.get('user_type') == 'admin':
        current_admin = {
            "id": user.get('user_id'),
            "name": user.get('full_name')
        }
    
    if success:
        return render_template('admin/Manage_materials.html', 
                            materials=materials, 
                            current_admin=current_admin)
    else:
        flash(materials, "error")  # materials contains the error message here
        return redirect(url_for('dashboard'))


@app.route('/delete_material/<int:material_id>', methods=['POST'])
def delete_material(material_id):
    try:
        success, message = adminmodel.delete_material(material_id)
        return jsonify({"success": True, "message": message}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

@app.route('/get_material/<int:material_id>', methods=['GET'])
def get_material(material_id):
    success, material = adminmodel.get_material_by_id(material_id)
    if success:
        return jsonify({"success": True, "material": material}), 200
    else:
        return jsonify({"success": False, "message": material}), 500


@app.route('/manage_materials_data')
def manage_materials_data():
    success, materials = adminmodel.get_all_materials()
    if success:
        return jsonify({"success": True, "materials": materials})
    else:
        return jsonify({"success": False, "message": materials})

# Wages Management Section Start---------------------------------------------------------------------
@app.route('/admin/manage_wages')
def manage_wages():
    user = session.get('user')
    if not user or user.get('user_type') != 'admin':
        flash("Unauthorized access. Please log in as an admin.", "danger")
        return redirect('/login')

    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
    except Exception as e:
        print(f"Error committing transactions: {e}")

    wage_records = adminmodel.get_wages_by_admin()
    
    # Fetch all labours and all projects for dropdowns
    success_lb, all_labours = adminmodel.get_all_labours()
    success_pr, all_projects = adminmodel.get_all_projects()

    return render_template(
        'admin/Manage_wages.html',
        admin_name=user.get('full_name'),
        wage_records=wage_records,
        assigned_labour=all_labours if success_lb else [],
        projects=all_projects if success_pr else []
    )

@app.route('/admin/register_wages', methods=['POST'])
def admin_register_wages():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'admin':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        admin_id = session.get('admin_id')
        if not admin_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided."}), 400

        required_fields = ['labour_id', 'project_id', 'daily_rate', 'total_days', 'total_wage']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        try:
            daily_rate = float(data['daily_rate'])
            total_days = int(data['total_days'])
            total_wage = float(data['total_wage'])
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid numeric values in daily rate, total days, or total wage"
            }), 400

        # Register wage as admin
        success, message = adminmodel.register_wage_admin(
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            daily_rate=daily_rate,
            total_days=total_days,
            total_wage=total_wage,
            admin_id=admin_id
        )

        if success:
            return jsonify({"success": True, "message": message, "redirect_url": "/admin/manage_wages"}), 200
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Error in admin_register_wages: {e}")
        return jsonify({
            "success": False,
            "message": "An internal error occurred while processing your request"
        }), 500

@app.route('/admin/update_wage', methods=['POST'])
def admin_update_wage():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'admin':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        data = request.get_json()
        required_fields = ['wage_id', 'labour_id', 'project_id', 'daily_rate', 'total_days', 'total_wage']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        success, message = adminmodel.update_wage_admin(
            wage_id=data['wage_id'],
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            daily_rate=data['daily_rate'],
            total_days=data['total_days'],
            total_wage=data['total_wage']
        )

        if success:
            return jsonify({"success": True, "message": message, "redirect_url": "/admin/manage_wages"}), 200
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Error in admin_update_wage: {e}")
        return jsonify({"success": False, "message": "An internal error occurred"}), 500
    
@app.route('/admin/get_wage/<int:wage_id>', methods=['GET'])
def admin_get_wage(wage_id):
    try:
        wage = adminmodel.get_wage_by_id_admin(wage_id)
        if wage:
            return jsonify({
                "success": True,
                "wage": {
                    "wage_id": wage["wage_id"],
                    "labour_id": wage["labour_id"],
                    "project_id": wage["project_id"],
                    "daily_rate": float(wage["daily_rate"]),
                    "total_days": wage["total_days"],
                    "total_wage": float(wage["total_wage"])
                }
            }), 200
        return jsonify({"success": False, "message": "Wage record not found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/admin/delete_wage/<int:wage_id>', methods=['POST'])
def admin_delete_wage(wage_id):
    try:
        success, message = adminmodel.delete_wage_admin(wage_id)
        return jsonify({"success": success, "message": message, "redirect_url": "/admin/manage_wages"}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/admin/get_labour_present_days', methods=['GET'])
def admin_get_labour_present_days():
    try:
        labour_id = request.args.get('labour_id')
        project_id = request.args.get('project_id')

        if not labour_id or not project_id:
            return jsonify({"success": False, "message": "Missing labour_id or project_id"}), 400

        present_days = adminmodel.get_unpaid_present_days_count(labour_id, project_id)
        return jsonify({"success": True, "present_days": present_days}), 200
    except Exception as e:
        print(f"Error in admin_get_labour_present_days: {e}")
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/admin/check_labour_assignment', methods=['GET'])
def check_labour_assignment():
    try:
        labour_id = request.args.get('labour_id')
        project_id = request.args.get('project_id')
        
        if not labour_id or not project_id:
            return jsonify({"is_assigned": False, "message": "Missing parameters"}), 400
            
        # Check if labour is assigned to project
        sql = """
        SELECT 1 FROM labour_project 
        WHERE labour_id = %s AND project_id = %s
        """
        adminmodel.cursor.execute(sql, (labour_id, project_id))
        is_assigned = adminmodel.cursor.fetchone() is not None
        
        return jsonify({
            "is_assigned": is_assigned,
            "message": "Labour is assigned to project" if is_assigned else "Labour is not assigned to this project"
        }), 200
        
    except Exception as e:
        print(f"Error in check_labour_assignment: {e}")
        return jsonify({"is_assigned": False, "message": str(e)}), 500

# Manage Labour Project
@app.route('/admin/manage_labour_project')
def manage_labour_project():
    success, assignments = adminmodel.get_all_labour_projects()
    if success:
        return render_template('/admin/Manage_labour_project.html', assignments=assignments)
    else:
        return f"Error fetching assignments: {assignments}", 500

@app.route('/register_assignment', methods=['POST'])
def register_assignment():
    data = request.get_json() if request.content_type == 'application/json' else request.form
    labour_id = data.get('labour_id')
    project_id = data.get('project_id')

    if not all([labour_id, project_id]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    success, message = adminmodel.register_labour_project(labour_id, project_id)
    return jsonify({"success": success, "message": message}), 201 if success else 400

@app.route('/update_assignment', methods=['POST'])
def update_assignment():
    data = request.get_json() if request.content_type == 'application/json' else request.form
    assignment_id = data.get('assignment_id')
    labour_id = data.get('labour_id')
    project_id = data.get('project_id')

    if not all([assignment_id, labour_id, project_id]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    success, message = adminmodel.update_labour_project(assignment_id, labour_id, project_id)
    return jsonify({"success": success, "message": message}), 200 if success else 400

@app.route('/delete_assignment/<int:assignment_id>', methods=['POST'])
def delete_assignment(assignment_id):
    success, message = adminmodel.delete_labour_project(assignment_id)
    return jsonify({"success": success, "message": message}), 200 if success else 400


# Attendance Management
@app.route('/admin/manage_attendance')
def manage_attendance():
    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
        success, attendance_records = adminmodel.get_all_attendance()
        if success:
            return render_template('/admin/Manage_attendance.html', attendance_records=attendance_records)
        else:
            flash(f"Error fetching attendance records: {attendance_records}", "danger")
            return redirect('/admin/dashboard')
    except Exception as e:
        print(f"Error in manage_attendance: {e}")
        flash("An error occurred while fetching attendance records", "danger")
        return redirect('/admin/dashboard')
    
    
@app.route('/register_attendance', methods=['POST'])
def register_attendance():
    data = request.get_json() if request.content_type == 'application/json' else request.form
    labour_id = data.get('labour_id')
    project_id = data.get('project_id')
    date = data.get('date')
    status = data.get('status')
    admin_id = data.get('admin_id')
    site_engineer_id = data.get('site_engineer_id')

    if not all([labour_id, project_id, date, status]) or (not admin_id and not site_engineer_id):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    # If admin_id is present, pass site_engineer_id as None
    if admin_id:
        site_engineer_id = None
    elif site_engineer_id:
        admin_id = None

    success, message = adminmodel.register_attendance(
        labour_id, project_id, date, status, site_engineer_id, admin_id
    )
    return jsonify({"success": success, "message": message}), 201 if success else 400

@app.route('/update_attendance', methods=['POST'])
def update_attendance():
    data = request.get_json() if request.content_type == 'application/json' else request.form
    attendance_id = data.get('attendance_id')
    labour_id = data.get('labour_id')
    project_id = data.get('project_id')
    date = data.get('date')
    status = data.get('status')
    site_engineer_id = data.get('site_engineer_id', None)

    if not all([attendance_id, labour_id, project_id, date, status]):
        return jsonify({"success": False, "message": "Missing required fields."}), 400

    success, message = adminmodel.update_attendance(
        attendance_id, labour_id, project_id, date, status, site_engineer_id
    )
    return jsonify({"success": success, "message": message}), 200 if success else 400


@app.route('/delete_attendance/<int:attendance_id>', methods=['POST'])
def delete_attendance(attendance_id):
    success, message = adminmodel.delete_attendance(attendance_id)
    return jsonify({"success": success, "message": message}), 200 if success else 400

@app.route('/get_labour_projects')
def get_labour_projects():
    success, labour_projects = adminmodel.get_all_labour_projects()
    if success:
        return jsonify({"success": True, "labour_projects": labour_projects}), 200
    else:
        return jsonify({"success": False, "message": "Failed to fetch labour projects"}), 500

@app.route('/get_labours_assigned_to_projects')
def get_labours_assigned_to_projects():
    success, labours = adminmodel.get_labours_assigned_to_projects()
    if success:
        labours_list = [{"labour_id": labour[0], "full_name": labour[1], "project_id": labour[2], "project_name": labour[3]} for labour in labours]
        return jsonify({"success": True, "labours": labours_list}), 200
    else:
        return jsonify({"success": False, "message": "Failed to fetch labours assigned to projects"}), 500


@app.route('/get_total_days_present', methods=['GET'])
def get_total_days_present():
    labour_id = request.args.get('labour_id')
    project_id = request.args.get('project_id')

    if not labour_id or not project_id:
        return jsonify({"success": False, "message": "Missing required parameters."}), 400

    success, total_days = adminmodel.get_total_days_present(labour_id, project_id)
    if success:
        return jsonify({"success": True, "total_days": total_days}), 200
    else:
        return jsonify({"success": False, "message": total_days}), 500

@app.route('/admin/manage_expenses')
def manage_expenses():
    """Render the expenses management page."""
    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
    except Exception as e:
        print(f"Error committing transactions: {e}")

    success, expenses = adminmodel.get_all_expenses_dict()
    user = session.get('user')
    admin_name = user.get('full_name') if user and user.get('user_type') == 'admin' else ''
    # Fetch all projects for the dropdown
    success_pr, projects = adminmodel.get_all_projects()
    if not success_pr:
        projects = []
    else:
        # Fix: Use dict keys for projects
        projects = [{"project_id": p["project_id"], "name": p["name"]} for p in projects]
        
    if success:
        return render_template(
            '/admin/Manage_expenses.html',
            Expenses=expenses,
            admin_name=admin_name,
            projects=projects  # Pass all projects for dropdown
        )
    else:
        return f"Error fetching expenses: {expenses}", 500
@app.route('/register_expense', methods=['POST'])
def register_expense():
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form
        project_id = data.get('project_id')
        item_name = data.get('item_name')
        amount = data.get('amount')
        description = data.get('description')
        expense_type = data.get('expense_type')
        admin_id = session.get('admin_id')
        if not all([project_id, item_name, amount, description, expense_type, admin_id]):
            return jsonify({"success": False, "message": "All fields are required. Please fill out the form completely."}), 400
        if not adminmodel.is_valid_project(project_id):
            return jsonify({"success": False, "message": "Invalid project selected."}), 400
        success, message = adminmodel.register_expense(
            project_id, item_name, amount, description, None, expense_type, admin_id
        )
        return jsonify({"success": success, "message": message}), 201 if success else 400
    except Exception as e:
        print(f"Error during expense registration: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route('/update_expense', methods=['POST'])
def update_expense():
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form
        expense_id = data.get('expense_id')
        item_name = data.get('item_name')
        amount = data.get('amount')
        description = data.get('description')
        project_id = data.get('project_id')
        expense_type = data.get('expense_type')
        site_engineer_id = None
        if not all([expense_id, item_name, amount, description, project_id, expense_type]):
            return jsonify({"success": False, "message": "All fields are required. Please fill out the form completely."}), 400
        try:
            expense_id = int(expense_id)
            amount = float(amount)
            project_id = int(project_id)
        except Exception:
            return jsonify({"success": False, "message": "Invalid data format."}), 400
        success, message = adminmodel.update_expense(
            expense_id, item_name, amount, description, project_id, site_engineer_id, expense_type
        )
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        print(f"Error during expense update: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    try:
        success, message = adminmodel.delete_expense(expense_id)
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500

# Budget_tracking Section Start---------------------------------------------------------------------
@app.route('/admin/manage_budget_transactions')
def manage_budget_transactions():
    """Render the budget transactions management page."""
    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
    except Exception as e:
        print(f"Error committing transactions: {e}")

    success, transactions = adminmodel.get_all_budget_transactions_dict()
    user = session.get('user')
    admin_name = user.get('full_name') if user and user.get('user_type') == 'admin' else ''
    
    # Fetch all projects for the dropdown
    success_pr, projects = adminmodel.get_all_projects()
    if not success_pr:
        projects = []
    else:
        # Fix: Use dict keys for projects
        projects = [{"project_id": p["project_id"], "name": p["name"]} for p in projects]
        
    if success:
        return render_template(
            '/admin/Budget_tracking.html',
            transactions=transactions,
            admin_name=admin_name,
            projects=projects
        )
    else:
        return f"Error fetching budget transactions: {transactions}", 500

@app.route('/admin/register_budget_transaction', methods=['POST'])
def register_budget_transaction():
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form
        project_id = data.get('project_id')
        transaction_type = data.get('transaction_type')
        reference_id = data.get('reference_id')
        amount = data.get('amount')
        remarks = data.get('remarks', '')
        admin_id = session.get('admin_id')
        
        if not all([project_id, transaction_type, reference_id, amount, admin_id]):
            return jsonify({"success": False, "message": "All required fields must be filled"}), 400
            
        # Validate transaction type
        valid_types = ['payment_wage', 'material_purchase', 'expense_payment', 'project_funding']
        if transaction_type not in valid_types:
            return jsonify({"success": False, "message": "Invalid transaction type"}), 400
            
        # Validate reference exists based on type
        if not adminmodel.validate_reference(transaction_type, reference_id):
            return jsonify({"success": False, "message": "Invalid reference ID for this transaction type"}), 400
            
        success, message = adminmodel.register_budget_transaction(
            project_id, transaction_type, reference_id, amount, remarks, admin_id
        )
        
        return jsonify({"success": success, "message": message}), 201 if success else 400
    except Exception as e:
        print(f"Error during budget transaction registration: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route('/admin/update_budget_transaction', methods=['POST'])
def update_budget_transaction():
    try:
        data = request.get_json() if request.content_type == 'application/json' else request.form
        transaction_id = data.get('transaction_id')
        project_id = data.get('project_id')
        transaction_type = data.get('transaction_type')
        reference_id = data.get('reference_id')
        amount = data.get('amount')
        remarks = data.get('remarks', '')
        
        if not all([transaction_id, project_id, transaction_type, reference_id, amount]):
            return jsonify({"success": False, "message": "All required fields must be filled"}), 400
            
        # Validate transaction exists
        if not adminmodel.budget_transaction_exists(transaction_id):
            return jsonify({"success": False, "message": "Transaction not found"}), 404
            
        # Validate transaction type
        valid_types = ['payment_wage', 'material_purchase', 'expense_payment', 'project_funding']
        if transaction_type not in valid_types:
            return jsonify({"success": False, "message": "Invalid transaction type"}), 400
            
        # Validate reference exists based on type
        if not adminmodel.validate_reference(transaction_type, reference_id):
            return jsonify({"success": False, "message": "Invalid reference ID for this transaction type"}), 400
            
        success, message = adminmodel.update_budget_transaction(
            transaction_id, project_id, transaction_type, reference_id, amount, remarks
        )
        
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        print(f"Error during budget transaction update: {e}")
        return jsonify({"success": False, "message": "An internal error occurred."}), 500

@app.route('/admin/delete_budget_transaction/<int:transaction_id>', methods=['POST'])
def delete_budget_transaction(transaction_id):
    try:
        if not adminmodel.budget_transaction_exists(transaction_id):
            return jsonify({"success": False, "message": "Transaction not found"}), 404
            
        success, message = adminmodel.delete_budget_transaction(transaction_id)
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {e}"}), 500


@app.route('/admin/manage_payments')
def manage_payments():
    user = session.get('user')
    if not user or user.get('user_type') != 'admin':
        flash("Unauthorized access. Please log in as an admin.", "danger")
        return redirect('/login')

    try:
        adminmodel.connection.commit()  # Ensure latest data is visible
    except Exception as e:
        print(f"Error committing transactions: {e}")

    payment_records = adminmodel.get_all_payments()
    unpaid_wages = adminmodel.get_unpaid_wages()
    unpaid_materials = adminmodel.get_unpaid_materials()
    unpaid_expenses = adminmodel.get_unpaid_expenses()
    
    # Fetch all projects for dropdown
    success_pr, all_projects = adminmodel.get_all_projects()
    if not success_pr:
        all_projects = []

    return render_template(
        'admin/manage_payments.html',
        admin_name=user.get('full_name'),
        admin_id=session.get('admin_id'),  # <-- Fix: get admin_id from session, not user dict
        payment_records=payment_records,
        unpaid_wages=unpaid_wages,
        unpaid_materials=unpaid_materials,
        unpaid_expenses=unpaid_expenses,
        projects=all_projects
    )

@app.route('/admin/register_payment', methods=['POST'])
def admin_register_payment():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'admin':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        admin_id = session.get('admin_id')  # <-- FIX: always get from session
        if not admin_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided."}), 400

        required_fields = ['project_id', 'amount', 'payment_date', 'payment_method', 'payment_status']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Handle optional fields
        wage_id = data.get('wage_id', None)
        material_id = data.get('material_id', None)
        expense_id = data.get('expense_id', None)

        try:
            amount = float(data['amount'])
            payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            return jsonify({
                "success": False,
                "message": f"Invalid numeric values in amount or invalid date format: {str(e)}"
            }), 400

        # Register payment
        result = adminmodel.register_payment(
            project_id=data['project_id'],
            amount=amount,
            payment_date=payment_date,
            payment_method=data['payment_method'],
            payment_status=data['payment_status'],
            admin_id=admin_id,
            wage_id=wage_id,
            material_id=material_id,
            expense_id=expense_id
        )

        if result[0]:  # success flag
            return jsonify({
                "success": True, 
                "message": result[1],  # message
                "redirect_url": "/admin/manage_payments"
            }), 200
        else:
            return jsonify({"success": False, "message": result[1]}), 400

    except Exception as e:
        print(f"Error in admin_register_payment: {e}")
        return jsonify({
            "success": False,
            "message": "An internal error occurred while processing your request"
        }), 500

@app.route('/admin/update_payment', methods=['POST'])
def admin_update_payment():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'admin':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        data = request.get_json()
        required_fields = ['payment_id', 'project_id', 'amount', 'payment_date', 'payment_method', 'payment_status']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        try:
            amount = float(data['amount'])
            payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
        except (ValueError, TypeError) as e:
            return jsonify({
                "success": False,
                "message": f"Invalid numeric values in amount or invalid date format: {str(e)}"
            }), 400

        result = adminmodel.update_payment(
            payment_id=data['payment_id'],
            project_id=data['project_id'],
            amount=amount,
            payment_date=payment_date,
            payment_method=data['payment_method'],
            payment_status=data['payment_status']
        )

        if result[0]:  # success flag
            return jsonify({
                "success": True, 
                "message": result[1],  # message
                "redirect_url": "/admin/manage_payments"
            }), 200
        else:
            return jsonify({"success": False, "message": result[1]}), 400

    except Exception as e:
        print(f"Error in admin_update_payment: {e}")
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@app.route('/admin/delete_payment/<int:payment_id>', methods=['POST'])
def admin_delete_payment(payment_id):
    try:
        result = adminmodel.delete_payment(payment_id)
        return jsonify({
            "success": result[0], 
            "message": result[1], 
            "redirect_url": "/admin/manage_payments"
        }), 200 if result[0] else 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# All Admin Report Routes
@app.route('/admin/reports')
def admin_reports():
    # Get filter parameters from request
    project_id = request.args.get('project_id', 'all')
    site_engineer_id = request.args.get('site_engineer_id', 'all')
    report_type = request.args.get('report_type', 'budget')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status_filter = request.args.get('status', 'all')

    # Get base data using your adminmodel
    success, projects = adminmodel.get_all_projects()
    if not success:
        projects = []
    
    # Get all site engineers
    success, site_engineers = adminmodel.get_all_siteEngineers()
    if not success:
        site_engineers = []

    # Initialize report data
    report_data = []
    totals = {
        'amount': 0,
        'count': 0
    }

    # Get project-specific data if a project is selected
    selected_project = None
    if project_id != 'all':
        success, selected_project = adminmodel.get_project_by_id(project_id)
        if not success:
            selected_project = None

    # Get site engineer-specific data if an engineer is selected
    selected_engineer = None
    if site_engineer_id != 'all':
        success, selected_engineer = adminmodel.get_site_engineer_by_id(site_engineer_id)
        if not success:
            selected_engineer = None

    # Query based on report type using your adminmodel
    if report_type == 'budget':
        if project_id == 'all':
            report_data = projects
        else:
            report_data = [selected_project] if selected_project else []
            
    elif report_type == 'wages':
        success, wages = adminmodel.get_wages_report(project_id, site_engineer_id, start_date, end_date, status_filter)
        if success:
            report_data = wages
            totals['amount'] = sum(wage['total_wage'] for wage in wages)
            totals['count'] = len(wages)
        
    elif report_type == 'material':
        success, materials = adminmodel.get_materials_report(project_id, site_engineer_id, start_date, end_date, status_filter)
        if success:
            report_data = materials
            totals['amount'] = sum(material['amount'] for material in materials)
            totals['count'] = len(materials)
        
    elif report_type == 'expense':
        success, expenses = adminmodel.get_expenses_report(project_id, site_engineer_id, start_date, end_date, status_filter)
        if success:
            report_data = expenses
            totals['amount'] = sum(expense['amount'] for expense in expenses)
            totals['count'] = len(expenses)
        
        elif report_type == 'attendance':
            success, attendance = adminmodel.get_attendance_report(
                project_id, 
                site_engineer_id, 
                start_date, 
                end_date
            )
            if success:
                report_data = attendance
                totals['count'] = len(attendance)
                # Calculate paid/pending counts if needed
                totals['paid'] = sum(1 for a in attendance if a.get('is_paid'))
                totals['pending'] = totals['count'] - totals['paid']
                
    elif report_type == 'labour':
        success, labour = adminmodel.get_labour_report(project_id, site_engineer_id)
        if success:
            report_data = labour
            totals['count'] = len(labour)
            
    elif report_type == 'payments':
        success, payments = adminmodel.get_payments_report(project_id, site_engineer_id, start_date, end_date)
        if success:
            report_data = payments
            totals['amount'] = sum(payment['amount'] for payment in payments)
            totals['count'] = len(payments)
            
    elif report_type == 'engineers':
        success, engineers = adminmodel.get_engineers_report()
        if success:
            report_data = engineers
            totals['count'] = len(engineers)
            
    elif report_type == 'budget_tracking':
        success, tracking = adminmodel.get_budget_tracking_report(project_id, start_date, end_date)
        if success:
            report_data = tracking
            totals['amount'] = sum(track['amount'] for track in tracking)
            totals['count'] = len(tracking)

    # Calculate dashboard metrics using adminmodel
    success, total_site_engineers_count = adminmodel.get_total_site_engineers_count()
    success, labours_assigned_to_projects_count = adminmodel.get_labours_assigned_count()
    success, site_engineers_assigned_to_projects_count = adminmodel.get_site_engineers_assigned_count()
    success, completed_tasks_count = adminmodel.get_completed_projects_count()

    return render_template(
        'admin/All_Admin_Reports.html',
        projects=projects,
        site_engineers=site_engineers,
        report_data=report_data,
        totals=totals,
        report_type=report_type,
        project_id=project_id,
        site_engineer_id=site_engineer_id,
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        selected_project=selected_project,
        selected_engineer=selected_engineer,
        total_site_engineers_count=total_site_engineers_count or 0,
        labours_assigned_to_projects_count=labours_assigned_to_projects_count or 0,
        site_engineers_assigned_to_projects_count=site_engineers_assigned_to_projects_count or 0,
        completed_tasks_count=completed_tasks_count or 0
    )

# Here are all my forgot and reset password routes
basedir = os.path.abspath(os.path.dirname(__file__))
app.config.from_pyfile(os.path.join(basedir, 'config.py'))
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

reset_attempts = defaultdict(list)  # email → list of timestamps

# Setup adminmodel instance
try:
    db_config = admin_model_module.AdminDbConnetion()
    user_db = admin_model_module.UserDatabase(
        host=db_config.DB_HOSTNAME,
        port=3300,
        user=db_config.DB_USERNAME,
        password=db_config.DB_PASSWORD,
        database=db_config.DB_NAME,
    )
    user_db.make_connection()
    adminmodel = admin_model_module.AdminModel(user_db.connection)
except Exception as e:
    print(f"Error initializing user model in routes.py: {e}")
    raise Exception("Failed to initialize user model in routes.py.")

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip()
        user_type = request.form.get('user_type')
        now = time.time()
        
        # Clear old attempts (older than 10 minutes)
        reset_attempts[email] = [t for t in reset_attempts[email] if now - t < 600]

        if len(reset_attempts[email]) >= 3:
            flash("Too many reset attempts. Please try again later.", "danger")
            return render_template('admin/forgot_password.html')

        # Check if email exists in database
        sql = f"SELECT COUNT(*) FROM {user_type} WHERE email = %s"
        adminmodel.cursor.execute(sql, (email,))
        exists = adminmodel.cursor.fetchone()[0]

        if exists > 0:
            token = s.dumps({'email': email, 'user_type': user_type}, salt='reset-password')
            send_reset_email(email, token)
            reset_attempts[email].append(now)
            flash('Password reset link has been sent to your email!', 'success')
        else:
            flash('Email not found in our system!', 'danger')

    return render_template('admin/forgot_password.html')

@app.route('/admin/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        data = s.loads(token, salt='reset-password', max_age=3600)  # 1 hour expiration
        email = data['email']
        user_type = data['user_type']
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('admin/reset_password.html', token=token)
        
        # Hash the new password
        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Update password in database
        sql = f"UPDATE {user_type} SET password = %s WHERE email = %s"
        adminmodel.cursor.execute(sql, (hashed_password, email))
        adminmodel.connection.commit()
        
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('login_page'))  # Make sure you have a login route

    return render_template('admin/reset_password.html', token=token)


@app.route('/admin/admin_logout')
def admin_logout():
    """Log out the site engineer and clear the session"""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/login')


# Set the secret key
app.secret_key = '123'