from flask import Flask, render_template, request, jsonify, session, redirect, flash,url_for
from App.site_engineer.SiteEngineerModel import get_user_model
from App import app
from decimal import Decimal
import traceback
from App.configuration import UserDbConnection
import base64
from datetime import datetime, timedelta



# Initialize the user model
status, user_model_db = get_user_model()
if not status:
    print(f"Error initializing user model: {user_model_db}")
    raise Exception("Failed to initialize user model.")
usermodel = user_model_db

# Register a custom Jinja2 filter for base64 encoding
@app.template_filter('b64encode')
def b64encode_filter(data):
    if data:
        return base64.b64encode(data).decode('utf-8')
    return None

# Ensure the filter is available in the app's Jinja2 environment
app.jinja_env.filters['b64encode'] = b64encode_filter

@app.route('/site_engineer/dashboard')
def site_engineer_dashboard():
    user = session.get('user')

    if not user or user.get('user_type') != 'site_engineer':
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Failed to load dashboard data.", "danger")
        return redirect('/login')

    try:
        # Fetch required data
        labourers_assigned_count = len(model.get_site_engineer_assigned_labour(site_engineer_id))
        total_projects = model.get_my_projects(site_engineer_id)
        total_projects_count = len(total_projects)
        materials_count = sum([p['material_budget'] for p in total_projects])
        wages_count = sum([p['wages_budget'] for p in total_projects])
        

        # Calculate project statuses
        projects_status = {
            "ongoing": sum(1 for p in total_projects if p['status'] == 'ongoing'),
            "completed": sum(1 for p in total_projects if p['status'] == 'completed'),
            "pending": sum(1 for p in total_projects if p['status'] == 'pending'),
            "planned": sum(1 for p in total_projects if p['status'] == 'planned'),

        }

        # Calculate budget allocation
        budget_allocation = {
            "material": sum([p['material_budget'] for p in total_projects]),
            "wages": sum([p['wages_budget'] for p in total_projects]),
            "usedAmount": sum([p['used_budget'] for p in total_projects]),
            "remaining": sum([p['remaining_budget'] for p in total_projects]),
            "total": sum([p['total_budget'] for p in total_projects]),
            "other": sum([p['other_expenses_budget'] for p in total_projects])


        }

        return render_template(
            'site_engineer/site_engineer_dashboard.html',
            user=user,
            labourers_assigned_count=labourers_assigned_count,
            total_projects_count=total_projects_count,
            materials_count=materials_count,
            wages_count=wages_count,
            projects_status=projects_status,
            total_projects=total_projects,
            other_expenses_budget=budget_allocation["other"],
            budget_allocation=budget_allocation
        )
    except Exception as e:
        print(f"Error loading dashboard: {e}")
        flash("An error occurred while loading the dashboard.", "danger")
        return redirect('/login')
    

# profile photo

@app.route('/site_engineer/projects')
def view_my_projects():
    login_id = session.get('site_engineer_id')
    if not login_id:
        flash("Unauthorized. Please log in.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        projects = model.get_my_projects(login_id)
        return render_template('/site_engineer/siteEngineerProjects.html', projects=projects)
    except Exception as e:
        return f"Error fetching projects: {str(e)}", 500

@app.route('/site_engineer/Site_engineer_materials', methods=['GET', 'POST'])
def Site_engineer_materials():
    # Validate session and user type
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    site_engineer_name = user.get('full_name')  # Get the logged-in site engineer's name

    # Fetch materials and assigned projects for the logged-in site engineer
    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        # Fetch materials for the site engineer's assigned projects
        materials = model.get_materials_for_site_engineer(site_engineer_id)
        # Fetch only the projects assigned to the site engineer
        projects = model.get_my_projects(site_engineer_id)
        return render_template(
            'site_engineer/Site_engineer_materials.html',
            materials=materials,
            projects=projects,
            site_engineer_name=site_engineer_name
        )
    
    except Exception as e:
        print(f"Error fetching materials or projects: {e}")
        flash("An error occurred while fetching materials or projects.", "danger")
        return redirect('/login')

@app.route('/site_engineer/project/<int:project_id>')
def view_project(project_id):
    """View details of a specific project assigned to the logged-in site engineer."""
    if 'site_engineer_id' not in session:
        return redirect('/login')

    site_engineer_id = session['site_engineer_id']
    success, model = get_user_model()
    
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        # Verify the project belongs to the logged-in site engineer
        if not model.check_project_assignment(site_engineer_id, project_id):
            flash("Unauthorized access to project.", "danger")
            return redirect('/site_engineer/projects')

        # Fetch project details
        projects = model.get_my_projects(site_engineer_id)
        project = next((p for p in projects if p['project_id'] == project_id), None)
        return render_template('site_engineer/viewProject.html', project=project)
    except Exception as e:
        print(f"Error fetching project details: {e}")
        flash("An error occurred while fetching project details.", "danger")
        return redirect('/site_engineer/projects')

@app.route('/site_engineer/materials/create', methods=['POST'])
def create_material():
    try:
        # Validate session and user
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        site_engineer_id = session.get('site_engineer_id')
        if not site_engineer_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        # Get and validate request data
        data = request.get_json()
        print("Received data:", data)

        required_fields = ['item_name', 'quantity', 'unit_price', 'amount', 'project_id']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "All fields are required."}), 400

        try:

            quantity = Decimal(str(data['quantity']))
            unit_price = Decimal(str(data['unit_price']))
            amount = Decimal(str(data['amount']))
            project_id = int(data['project_id'])
        except (ValueError, TypeError) as e:
            print(f"Conversion error: {e}")
            return jsonify({"success": False, "message": "Invalid numeric values."}), 400

        # Get database model
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        # Verify project exists and get budget
        try:
            sql_fetch_budget = """
            SELECT material_budget 
            FROM projects 
            WHERE project_id = %s
            """
            model.cursor.execute(sql_fetch_budget, (project_id,))
            project = model.cursor.fetchone()
            
            if not project:
                print(f"Project {project_id} not found in database")
                return jsonify({
                    "success": False,
                    "message": f"Project {project_id} not found or has no budget configured"
                }), 404
                
            material_budget = model.safe_decimal(project['material_budget'] if isinstance(project, dict) else project[0])
            
            print(f"Project budget: {material_budget}")

            if material_budget is None:
                return jsonify({
                    "success": False,
                    "message": "Project budget is not set"
                }), 400

            if amount > material_budget:
                return jsonify({
                    "success": False,
                    "message": f"Insufficient budget. Available: {material_budget}, Needed: {amount}"
                }), 400

        except Exception as e:
            print(f"Budget check error: {str(e)}")
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": "Error checking project budget"
            }), 500

        # Register material
        success, message = model.register_material(
            item_name=data['item_name'],
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            site_engineer_id=site_engineer_id,
            project_id=project_id
        )

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            print(f"Registration failed: {message}")
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "An internal error occurred"
        }), 500
    
# @app.route('/site_engineer/materials/project_budget/<int:project_id>', methods=['GET'])
# def get_project_budgets(project_id):
#     try:
#         budget_data = usermodel.get_project_material_budget(project_id)
#         if budget_data:
#             return jsonify({"success": True, "budget": budget_data["budget"]})
#         return jsonify({"success": False, "message": "Project not found"}), 404
#     except Exception as e:
#         return jsonify({"success": False, "message": str(e)}), 500
@app.route('/site_engineer/materials/project_budget/<int:project_id>', methods=['GET'])
def get_project_budgets(project_id):
    try:
        budget_data = usermodel.get_project_budget_status(project_id)
        if budget_data.get("success"):
            return jsonify({
                "success": True,
                "budgets": {
                    "total_budget": budget_data["total_budget"],
                    "material_budget": budget_data["material_budget"],
                    "used_budget": budget_data["used_budget"],
                    "remaining_budget": budget_data["remaining_budget"]
                }
            })
        return jsonify({
            "success": False,
            "message": budget_data.get("message", "Project not found")
        }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    
@app.route('/update_materials', methods=['POST'])
def update_materials():
    try:
        data = request.get_json()

        # Required fields with type checking
        required = {
            'material_id': int,
            'item_name': str,
            'quantity': int,
            'unit_price': float,
            'project_id': int
        }

        for field, field_type in required.items():
            if field not in data:
                return jsonify({"success": False, "message": f"Missing {field}"}), 400
            try:
                data[field] = field_type(data[field])
            except (ValueError, TypeError):
                return jsonify({"success": False, "message": f"Invalid {field} format"}), 400

        # Calculate amount
        data['amount'] = data['quantity'] * data['unit_price']

        # Update materials in the database
        success, message = usermodel.update_materials(
            data['material_id'],
            data['item_name'],
            data['quantity'],
            data['unit_price'],
            data['amount'],
            data['project_id']
        )

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"Error in update_materials: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/update_materials_/<int:material_id>', methods=['GET'])
def get_material_by_id(material_id):
    try:
        material = usermodel.get_material_by_id(material_id)
        if material:
            return jsonify({
                "success": True,
                "material": {
                    "material_id": material["material_id"],
                    "item_name": material["item_name"],
                    "quantity": material["quantity"],
                    "unit_price": material["unit_price"],
                    "amount": material["amount"],
                    "project_id": material["project_id"]
                }
            }), 200
        else:
            return jsonify({"success": False, "message": f"Material with ID {material_id} not found"}), 404
    except Exception as e:
        print(f"Error in get_material_by_id: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_materials/<int:material_id>', methods=['POST'])
def delete_materials(material_id):
    print(f"Getting material with ID: {material_id}")
    try:
        success, message = usermodel.delete_materials(material_id)
        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Server Error: {str(e)}"}), 500



# Expenses Routes
@app.route('/site_engineer/site_engineer_expenses')
def site_engineer_expenses():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    projects = model.get_my_projects(site_engineer_id)
    success_exp, expenses = model.get_all_expenses_dict(site_engineer_id)
    
    if not success_exp:
        expenses = []
        flash("Error loading expenses", "warning")

    return render_template(
        'site_engineer/site_engineer_expenses.html',
        site_engineer_name=user.get('full_name'),
        projects=projects,
        expenses=expenses,
        current_site_engineer_id=site_engineer_id  # Pass this to template
    )

@app.route('/site_engineer/register_expenses', methods=['POST'])
def register_expenses():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        site_engineer_id = session.get('site_engineer_id')
        if not site_engineer_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided."}), 400

        required_fields = ['item_name', 'amount', 'description', 'expense_type', 'project_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing_fields)}"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        # Determine which budget column to check
        budget_column = {
            'material': 'material_budget',
            'wages': 'wages_budget',
            'other': 'other_expenses_budget'
        }.get(data['expense_type'], None)

        if not budget_column:
            return jsonify({"success": False, "message": "Invalid expense type."}), 400

       

        sql_check = f"""
        SELECT 
            COALESCE({budget_column}, 0) AS available_budget,
            COALESCE(used_budget, 0) AS current_used
        FROM projects 
        WHERE project_id = %s
        """
        model.cursor.execute(sql_check, (data['project_id'],))
        project = model.cursor.fetchone()

        if not project:
            return jsonify({"success": False, "message": "Project not found"}), 404

        available_budget = model.safe_decimal(project['available_budget'])
        amount = model.safe_decimal(data['amount'])

        if amount > available_budget:
            return jsonify({
                "success": False,
                "message": f"Insufficient {data['expense_type']} budget. Available: {available_budget}, Needed: {amount}"
            }), 400

        # Register expense
        success, message = model.register_expenses(
            item_name=data['item_name'],
            amount=amount,
            description=data['description'],
            expense_type=data['expense_type'],
            site_engineer_id=site_engineer_id,
            project_id=data['project_id']
        )

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Error in register_expenses: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@app.route('/update_expenses', methods=['POST'])
def update_expenses():
    try:
        data = request.get_json()
        required_fields = ['expense_id', 'item_name', 'amount', 'description', 'expense_type', 'project_id']
        if not all(field in data for field in required_fields):
            return jsonify({"success": False, "message": "All fields are required."}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        success, message = model.update_expenses(
            expense_id=data['expense_id'],
            item_name=data['item_name'],
            amount=data['amount'],
            description=data['description'],
            expense_type=data['expense_type'],
            project_id=data['project_id']
        )

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/get_expenses/<int:expense_id>', methods=['GET'])
def get_expenses(expense_id):
    try:
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        expense = model.get_expense_by_id(expense_id)
        if expense:
            return jsonify({
                "success": True,
                "expense": {
                    "expense_id": expense["expense_id"],
                    "item_name": expense["item_name"],
                    "amount": expense["amount"],
                    "description": expense["description"],
                    "expense_type": expense["expense_type"],
                    "project_id": expense["project_id"]
                }
            }), 200
        return jsonify({"success": False, "message": "Expense not found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_expenses/<int:expense_id>', methods=['POST'])
def delete_expenses(expense_id):
    try:
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        success, message = model.delete_expenses(expense_id)
        # Ensure commit after operation
        model.connection.commit()
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/check_expenses_budget', methods=['POST'])
def check_expenses_budget():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        expense_type = data.get('expense_type')
        amount = data.get('amount')

        if not all([project_id, expense_type, amount]):
            return jsonify({"success": False, "message": "Missing parameters"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed"}), 500

        # Determine budget column
        budget_column = {
            'material': 'material_budget',
            'wages': 'wages_budget',
            'other': 'other_expenses_budget'
        }.get(expense_type, None)

        if not budget_column:
            return jsonify({"success": False, "message": "Invalid expense type"}), 400

        # Get full budget status
        budget_data = model.get_project_budget_status(project_id)
        if not budget_data.get("success"):
            return jsonify({
                "success": False,
                "message": budget_data.get("message", "Project not found")
            }), 404

        available_budget = budget_data.get(budget_column, 0)
        requested_amount = model.safe_decimal(amount)
        used_budget = budget_data.get("used_budget", 0)
        remaining_budget = budget_data.get("remaining_budget", 0)

        if requested_amount > available_budget:
            return jsonify({
                "success": False,
                "message": f"Insufficient {expense_type} budget. Available: {available_budget}, Needed: {requested_amount}",
                "budgets": {
                    "total_budget": budget_data["total_budget"],
                    "available_budget": available_budget,
                    "used_budget": used_budget,
                    "remaining_budget": remaining_budget
                }
            }), 400

        return jsonify({
            "success": True,
            "message": "Budget available",
            "budgets": {
                "total_budget": budget_data["total_budget"],
                "available_budget": available_budget,
                "used_budget": used_budget,
                "remaining_budget": remaining_budget
            }
        }), 200
    except Exception as e:
        print(f"Error in check_expenses_budget: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": "Internal server error"}), 500


#Section site_engineer_assigned_labour start

@app.route('/site_engineer/site_engineer_assigned_labour')
def site_engineer_assigned_labour():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Failed to load projects.", "danger")
        return redirect('/login')

    try:
        assigned_labours = model.get_site_engineer_assigned_labour(site_engineer_id)
        if not assigned_labours:
            flash("No Labour assigned to your projects yet.", "info")
        return render_template(
            'site_engineer/site_engineer_labour.html',
            user=user,
            assigned_labour=assigned_labours  # Note the variable name matches the template
        )
    except Exception as e:
        print(f"Error Loading Site Engineer Assigned Labour : {e}")
        flash("An error occurred while loading the Site Engineer Assigned Labour.", "danger")
        return redirect('/login')


@app.route('/site_engineer/projects')
def view_site_engineer_assigned_labour():
    login_id = session.get('site_engineer_id')
    if not login_id:
        flash("Unauthorized. Please log in.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        site_eingineer_labour_assigned = model.get_site_engineer_assigned_labour(login_id)
        return render_template('/site_engineer/site_engineer_labour.html', site_eingineer_labour_assigned=site_eingineer_labour_assigned)
    except Exception as e:
        return f"Error fetching projects: {str(e)}", 500

#Section site_engineer_assigned_labour end
@app.route('/site_engineer/site_engineer_labour_attendance')
def site_engineer_labour_attendance():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    # Only show attendance for this engineer's assigned projects,
    # and only if registered by this engineer or by admin (not by other engineers)
    attendance_records = model.get_attendance_for_site_engineer_view(site_engineer_id)
    assigned_labours = model.get_site_engineer_assigned_labour(site_engineer_id)
    projects = model.get_my_projects(site_engineer_id)

    return render_template(
        'site_engineer/site_engineer_labour_attendance.html',
        site_engineer_name=user.get('full_name'),
        attendance_records=attendance_records,
        assigned_labour=assigned_labours,
        projects=projects
    )

@app.route('/site_engineer/register_siteEngineer_attendance', methods=['POST'])
def register_siteEngineer_attendance():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        site_engineer_id = session.get('site_engineer_id')
        if not site_engineer_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided."}), 400

        required_fields = ['labour_id', 'project_id', 'date', 'status']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing_fields)}"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        # Check if attendance already exists for this labour on this date
        existing_attendance = model.check_existing_attendance(data['labour_id'], data['date'])
        if existing_attendance:
            return jsonify({
                "success": False,
                "message": f"Attendance already recorded for this labour on {data['date']}"
            }), 400

        # Check if labour is assigned to the selected project
        labour_assigned = model.check_labour_project_assignment(data['labour_id'], data['project_id'])
        if not labour_assigned:
            return jsonify({
                "success": False,
                "message": "This labour is not assigned to the selected project."
            }), 400

        # Register attendance
        success, message = model.register_siteEngineer_attendance(
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            date=data['date'],
            status=data['status'],
            site_engineer_id=site_engineer_id
        )
        
        # Ensure changes are committed and visible
        model.connection.commit()
        

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Error in register_attendance: {e}")
        model.connection.rollback()
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@app.route('/update_siteEngineer_attendance', methods=['POST'])
def update_siteEngineer_attendance():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['attendance_id', 'labour_id', 'project_id', 'date', 'status']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        # Check if attendance already exists for this labour on this date (excluding current record)
        existing_attendance = model.check_existing_attendance_for_update(
            data['labour_id'], 
            data['date'], 
            data['attendance_id']
        )
        if existing_attendance:
            return jsonify({
                "success": False,
                "message": f"Attendance already recorded for this labour on {data['date']}"
            }), 400

        # Check if labour is assigned to the selected project
        labour_assigned = model.check_labour_project_assignment(data['labour_id'], data['project_id'])
        if not labour_assigned:
            return jsonify({
                "success": False,
                "message": "This labour is not assigned to the selected project."
            }), 400

        # Update attendance
        success, message = model.update_siteEngineer_attendance(
            attendance_id=data['attendance_id'],
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            date=data['date'],
            status=data['status']
        )
        # Ensure commit after operation
        model.connection.commit()

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"Error in update_siteEngineer_attendance: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": "An internal error occurred"}), 500

@app.route('/get_siteEngineer_attendance/<int:attendance_id>', methods=['GET'])
def get_siteEngineer_attendance(attendance_id):
    try:
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        attendance = model.get_siteEngineer_attendance_by_id(attendance_id)
        if attendance:
            return jsonify({
                "success": True,
                "attendance": {
                    "attendance_id": attendance["attendance_id"],
                    "labour_id": attendance["labour_id"],
                    "project_id": attendance["project_id"],
                    "date": attendance["date"],
                    "status": attendance["status"]
                }
            }), 200
        return jsonify({"success": False, "message": "Attendance record not found"}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/delete_siteEngineer_attendance/<int:attendance_id>', methods=['POST'])
def delete_siteEngineer_attendance(attendance_id):
    try:
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        success, message = model.delete_siteEngineer_attendance(attendance_id)
        # Ensure commit after operation
        model.connection.commit()
        return jsonify({"success": success, "message": message}), 200 if success else 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/get_siteEngineer_labour_project/<int:labour_id>', methods=['GET'])
def get_siteEngineer_labour_project(labour_id):
    try:
        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        # Fix: Query the labour_project table for assigned projects
        sql = """
        SELECT project_id 
        FROM labour_project 
        WHERE labour_id = %s
        """
        model.cursor.execute(sql, (labour_id,))
        results = model.cursor.fetchall()
        
        if results:
            # Return all assigned project_ids as a list
            project_ids = [row['project_id'] if isinstance(row, dict) else row[0] for row in results]
            return jsonify({
                "success": True,
                "project_ids": project_ids
            }), 200
        return jsonify({"success": False, "message": "No projects found for this labour"}), 404
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500



@app.route('/site_engineer/profile')
def site_engineer_profile():
    # Validate session and user type
    user = session.get('user')
    if not user:
        flash("Unauthorized access. Please log in.", "danger")
        return redirect('/login')

    if user.get('user_type') != 'site_engineer':
        flash("Access restricted to site engineers only.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    # Fetch user model
    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        # Fetch the last assigned project and its total budget
        projects = model.get_my_projects(site_engineer_id)
        last_project = projects[-1] if projects else None

        # Fetch profile picture and other details
        profile_data = model.get_site_engineer_profile(site_engineer_id)
        
        # Convert binary image data to base64
        profile_picture = None
        if profile_data and profile_data.get('profile_picture'):
            profile_picture = base64.b64encode(profile_data['profile_picture']).decode('utf-8')

        return render_template(
            'site_engineer/site_engineer_profile.html',
            user_name=user.get('full_name'),
            email=user.get('email'),
            last_project=last_project,
            profile_picture=profile_picture
        )
    except Exception as e:
        print(f"Error loading profile: {e}")
        flash("An error occurred while loading the profile.", "danger")
        return redirect('/login')
    
@app.route('/site_engineer/update_profile_image', methods=['POST'])
def site_engineer_update_profile_image():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        return jsonify({"success": False, "message": "Unauthorized access. Please log in as a site engineer."}), 401

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

    if 'profile_image' not in request.files:
        return jsonify({"success": False, "message": "No file selected."}), 400

    file = request.files['profile_image']
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Allowed image types are: png, jpg, jpeg, gif"}), 400

    max_size = 2 * 1024 * 1024  # 2MB
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)
    if file_size > max_size:
        return jsonify({"success": False, "message": "Image size must be less than 2MB"}), 400

    if file:
        try:
            file_data = file.read()
            success, model = get_user_model()
            if not success:
                return jsonify({"success": False, "message": "Database connection failed."}), 500

            update_success, message = model.update_site_engineer_profile_picture(
                site_engineer_id, file_data, file.filename
            )

            if update_success:
                return jsonify({"success": True, "message": "Profile image updated successfully."}), 200
            else:
                return jsonify({"success": False, "message": f"Failed to update profile image: {message}"}), 400

        except Exception as e:
            print(f"Error updating profile image: {e}")
            return jsonify({"success": False, "message": "An error occurred while updating the profile image."}), 500

    return jsonify({"success": False, "message": "Unknown error."}), 500


def allowed_file(filename):
    """Check if the file has an allowed extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}



@app.context_processor
def inject_profile_data():
    """Make profile data available to all templates"""
    if 'user' in session and session['user'].get('user_type') == 'site_engineer':
        site_engineer_id = session.get('site_engineer_id')
        if site_engineer_id:
            try:
                success, model = get_user_model()
                if success:
                    profile_data = model.get_site_engineer_profile(site_engineer_id)
                    if profile_data and profile_data.get('profile_picture'):
                        return {
                            'global_profile': {
                                'picture': base64.b64encode(profile_data['profile_picture']).decode('utf-8'),
                                'filename': profile_data.get('profile_picture_filename', 'jpeg')
                            }
                        }
            except Exception as e:
                print(f"Error loading profile data: {e}")
    
    return {'global_profile': None}

# wages
# @app.route('/site_engineer/site_engineer_manage_wages')
# def site_engineer_manage_wages():
#     return render_template('site_engineer/Site_engineer_manage_wages.html')
@app.route('/site_engineer/site_engineer_manage_wages')
def site_engineer_manage_wages():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    # Only show wages for projects assigned to this site engineer
    wage_records = model.get_wages_by_site_engineer(site_engineer_id)
    assigned_labours = model.get_site_engineer_assigned_labour(site_engineer_id)
    projects = model.get_my_projects(site_engineer_id)

    return render_template(
        'site_engineer/Site_engineer_manage_wages.html',
        site_engineer_name=user.get('full_name'),
        wage_records=wage_records,
        assigned_labour=assigned_labours,
        projects=projects,
        user=user
    )

@app.route('/check_wage_ownership', methods=['POST'])
def check_wage_ownership():
    user = session.get('user')
    if not user:
        return jsonify({"can_edit": False, "can_delete": False})

    data = request.get_json()
    wage_id = data.get('wage_id')

    # Get the wage record
    success, model = get_user_model()
    wage = model.get_wage_by_id(wage_id)
    if not wage:
        return jsonify({"can_edit": False, "can_delete": False})

    if user['user_type'] == 'admin':
        return jsonify({"can_edit": True, "can_delete": True})
    elif user['user_type'] == 'site_engineer':
        # Only allow if the wage's project is assigned to this site engineer
        site_engineer_id = session.get('site_engineer_id')
        # Check if this project is assigned to this site engineer
        assigned_projects = [p['project_id'] for p in model.get_my_projects(site_engineer_id)]
        if wage['project_id'] in assigned_projects:
            return jsonify({"can_edit": True, "can_delete": True})
    return jsonify({"can_edit": False, "can_delete": False})

@app.route('/site_engineer/register_wages', methods=['POST'])
def register_wages():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized access."}), 403

        site_engineer_id = session.get('site_engineer_id')
        if not site_engineer_id:
            return jsonify({"success": False, "message": "Session expired. Please log in again."}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided."}), 400

        # Validate required fields
        required_fields = ['labour_id', 'project_id', 'daily_rate', 'total_days', 'total_wage']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Only allow registration for assigned projects
        success, model = get_user_model()
        assigned_projects = [p['project_id'] for p in model.get_my_projects(site_engineer_id)]
        if int(data['project_id']) not in assigned_projects:
            return jsonify({"success": False, "message": "You can only register wages for your assigned projects."}), 403

        try:
            daily_rate = float(data['daily_rate'])
            total_days = int(data['total_days'])
            total_wage = float(data['total_wage'])
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Invalid numeric values in daily rate, total days, or total wage"
            }), 400

        success, message = model.register_wage(
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            daily_rate=daily_rate,
            total_days=total_days,
            total_wage=total_wage,
            site_engineer_id=site_engineer_id
        )
        # Ensure commit after operation
        model.connection.commit()

        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        print(f"Error in register_wages: {e}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "An internal error occurred while processing your request"
        }), 500
    
    
@app.route('/update_siteEngineer_wage', methods=['POST'])
def update_siteEngineer_wage():
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        site_engineer_id = session.get('site_engineer_id')
        if not site_engineer_id:
            return jsonify({"success": False, "message": "Session expired"}), 401

        data = request.get_json()
        required_fields = ['wage_id', 'labour_id', 'project_id', 'daily_rate', 'total_days', 'total_wage']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed"}), 500

        # Convert numeric fields
        try:
            data['daily_rate'] = float(data['daily_rate'])
            data['total_days'] = int(data['total_days'])
            data['total_wage'] = float(data['total_wage'])
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Invalid numeric values"}), 400

        success, message = model.update_siteEngineer_wage(
            wage_id=data['wage_id'],
            labour_id=data['labour_id'],
            project_id=data['project_id'],
            daily_rate=data['daily_rate'],
            total_days=data['total_days'],
            total_wage=data['total_wage'],
            site_engineer_id=site_engineer_id
        )
        # Ensure commit after operation
        model.connection.commit()

        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"Error in update_siteEngineer_wage: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": "An internal error occurred"}), 500
    

@app.route('/delete_siteEngineer_wage/<int:wage_id>', methods=['POST'])
def delete_siteEngineer_wage(wage_id):
    try:
        user = session.get('user')
        if not user or user.get('user_type') != 'site_engineer':
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        success, model = get_user_model()
        wage = model.get_wage_by_id(wage_id)
        if not wage:
            return jsonify({"success": False, "message": "Wage record not found"}), 404

        site_engineer_id = session.get('site_engineer_id')
        assigned_projects = [p['project_id'] for p in model.get_my_projects(site_engineer_id)]
        if wage['project_id'] not in assigned_projects:
            return jsonify({"success": False, "message": "You can only delete wages for your assigned projects."}), 403

        success, message = model.delete_siteEngineer_wage(wage_id, site_engineer_id)
        # Ensure commit after operation
        model.connection.commit()
        return jsonify({"success": success, "message": message}), 200 if success else 400

    except Exception as e:
        print(f"Error in delete_siteEngineer_wage: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": "An internal error occurred"}), 500


@app.route('/get_labour_present_days', methods=['GET'])
def get_labour_present_days():
    try:
        labour_id = request.args.get('labour_id')
        project_id = request.args.get('project_id')

        if not labour_id or not project_id:
            return jsonify({"success": False, "message": "Missing labour_id or project_id"}), 400

        success, model = get_user_model()
        if not success:
            return jsonify({"success": False, "message": "Database connection failed."}), 500

        unpaid_present_days = model.get_unpaid_present_days_count(labour_id, project_id)
        return jsonify({"success": True, "present_days": unpaid_present_days}), 200
    except Exception as e:
        print(f"Error in get_labour_present_days: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

    

#Report section start
@app.route('/site_engineer/reports/financial', methods=['GET'])
def financial_report():
    user = session.get('user')
    if not user or user.get('user_type') != 'site_engineer':
        flash("Unauthorized access. Please log in as a site engineer.", "danger")
        return redirect('/login')

    site_engineer_id = session.get('site_engineer_id')
    if not site_engineer_id:
        flash("Session expired. Please log in again.", "danger")
        return redirect('/login')

    success, model = get_user_model()
    if not success:
        flash("Database connection failed.", "danger")
        return redirect('/login')

    try:
        # Get report parameters
        report_type = request.args.get('report_type', 'expense')
        period = request.args.get('period', 'daily')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        project_id = request.args.get('project_id', 'all')
        
        # Get all projects for the dropdown
        projects = model.get_projects_by_engineer(site_engineer_id)
        
        # Get selected project details if a specific project is selected
        selected_project = None
        if project_id and project_id != 'all':
            selected_project = next((p for p in projects if str(p['project_id']) == project_id), None)
        
        # Initialize dates
        end_date = datetime.now()
        start_date = end_date  # Default to same day
        
        # Parse dates if provided
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid start date format. Using default date range.", "warning")
                
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                flash("Invalid end date format. Using default date range.", "warning")
        
        # Adjust dates based on period if specific dates not provided
        if not start_date_str and not end_date_str:
            if period == 'daily':
                start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'weekly':
                start_date = end_date - timedelta(days=7)
            elif period == 'monthly':
                start_date = end_date - timedelta(days=30)
        
        # Ensure end date includes the entire day
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999)
        
        # Fetch data based on report type
        if report_type == 'expense':
            data = model.get_filtered_expenses(site_engineer_id, start_date, end_date, project_id)
        elif report_type == 'wages':
            data = model.get_filtered_wages(site_engineer_id, start_date, end_date, project_id)
        elif report_type == 'material':
            data = model.get_filtered_materials(site_engineer_id, start_date, end_date, project_id)
        elif report_type == 'budget':
            data = model.get_budget_burn_rate(site_engineer_id, start_date, end_date, project_id)
        else:
            data = []

        return render_template(
            'site_engineer/reports/site_engineer_report.html',
            expenses_data=data,
            projects=projects,
            selected_project=selected_project,
            project_id=project_id,
            report_type=report_type,
            period=period,
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d')
        )
    except Exception as e:
        print(f"Error loading financial report: {e}")
        flash("An error occurred while loading the report.", "danger")
        return redirect('/site_engineer/dashboard')
    


@app.route('/site_engineer/logout')
def site_engineer_logout():
    """Log out the site engineer and clear the session"""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect('/login')
# Secret key
app.secret_key = 'your_secret_key_here'


# @app.route('/site_engineer/reports/financial', methods=['GET'])
# def financial_report():
#     user = session.get('user')
#     if not user or user.get('user_type') != 'site_engineer':
#         flash("Unauthorized access. Please log in as a site engineer.", "danger")
#         return redirect('/login')

#     site_engineer_id = session.get('site_engineer_id')
#     if not site_engineer_id:
#         flash("Session expired. Please log in again.", "danger")
#         return redirect('/login')

#     success, model = get_user_model()
#     if not success:
#         flash("Database connection failed.", "danger")
#         return redirect('/login')

#     try:
#         # Get report parameters
#         report_type = request.args.get('report_type', 'expense')
#         period = request.args.get('period', 'daily')
#         start_date_str = request.args.get('start_date')
#         end_date_str = request.args.get('end_date')
#         project_id = request.args.get('project_id', 'all')
        
#         # Get all projects for the dropdown
#         projects = model.get_projects_by_engineer(site_engineer_id)
        
#         # Get selected project details if a specific project is selected
#         selected_project = None
#         if project_id and project_id != 'all':
#             selected_project = next((p for p in projects if str(p['project_id']) == project_id), None)
        
#         # Initialize dates
#         end_date = datetime.now()
#         start_date = end_date  # Default to same day
        
#         # Parse dates if provided
#         if start_date_str:
#             try:
#                 start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
#             except ValueError:
#                 flash("Invalid start date format. Using default date range.", "warning")
                
#         if end_date_str:
#             try:
#                 end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
#             except ValueError:
#                 flash("Invalid end date format. Using default date range.", "warning")
        
#         # Adjust dates based on period if specific dates not provided
#         if not start_date_str and not end_date_str:
#             if period == 'daily':
#                 start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
#             elif period == 'weekly':
#                 start_date = end_date - timedelta(days=7)
#             elif period == 'monthly':
#                 start_date = end_date - timedelta(days=30)
        
#         # Ensure end date includes the entire day
#         end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999)
        
#         # Fetch data based on report type
#         if report_type == 'expense':
#             data = model.get_filtered_expenses(site_engineer_id, start_date, end_date, project_id)
#             columns = ['#', 'Item Name', 'Amount', 'Date', 'Description', 'Project']
#         elif report_type == 'wages':
#             data = model.get_filtered_wages(site_engineer_id, start_date, end_date, project_id)
#             columns = ['#', 'Labour Name', 'Amount', 'Date', 'Type', 'Project']
#         elif report_type == 'material':
#             data = model.get_filtered_materials(site_engineer_id, start_date, end_date, project_id)
#             columns = ['#', 'Item Name', 'Amount', 'Date', 'Type', 'Project']
#         elif report_type == 'budget':
#             data = model.get_budget_burn_rate(site_engineer_id, start_date, end_date, project_id)
#             columns = ['#', 'Project', 'Amount', 'Start Date', 'Type', '']
#         else:
#             data = []
#             columns = []

#         return render_template(
#             'site_engineer/reports/site_engineer_report.html',
#             expenses_data=data,
#             projects=projects,
#             selected_project=selected_project,
#             project_id=project_id,
#             report_type=report_type,
#             period=period,
#             start_date=start_date.strftime('%Y-%m-%d'),
#             end_date=end_date.strftime('%Y-%m-%d'),
#             columns=columns
#         )
#     except Exception as e:
#         print(f"Error loading financial report: {e}")
#         flash("An error occurred while loading the report.", "danger")
#         return redirect('/site_engineer/dashboard')
#         print(f"Error loading financial report: {e}")
#         flash("An error occurred while loading the report.", "danger")
#         return redirect('/site_engineer/dashboard')
