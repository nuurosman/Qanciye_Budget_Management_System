import mysql.connector
from App.configuration import AdminDbConnetion
import hashlib
from decimal import Decimal  # Import Decimal


class UserDatabase:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    def make_connection(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            self.cursor = self.connection.cursor()
            print("Database connection established.")
        except Exception as e:
            print(f"Connection error: {e}")
            raise e

    def my_cursor(self):
        return self.cursor


class AdminModel:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = self.connection.cursor()

    def register_user(self, full_name, email, password, user_type, type_of_work=None):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        print(f"Hashed Password being stored: {hashed_password}")

        check_sql = "SELECT COUNT(*) FROM {} WHERE email = %s".format(user_type)
        self.cursor.execute(check_sql, (email,))
        count = self.cursor.fetchone()[0]

        if count > 0:
            return False, "Email already exists in {}.".format(user_type)

        if user_type == "admin":
            sql = '''
            INSERT INTO Admin (full_name, email, password, created_at)
            VALUES (%s, %s, %s, NOW())
            '''
            self.cursor.execute(sql, (full_name, email, hashed_password))
        elif user_type == "site_engineer":
            sql = '''
            INSERT INTO site_engineer (full_name, email, password, created_at)
            VALUES (%s, %s, %s, NOW())
            '''
            self.cursor.execute(sql, (full_name, email, hashed_password))
        elif user_type == "labour":
            sql = '''
            INSERT INTO labour (full_name, email, password, type_of_work, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            '''
            self.cursor.execute(sql, (full_name, email, hashed_password, type_of_work))
        else:
            return False, "Invalid user type."

        self.connection.commit()
        return True, "{} registered successfully!".format(user_type.capitalize())

    def authenticate_user(self, email, password, user_type):
        try:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            print(f"Hashed Password for comparison: {hashed_password}")

            # Determine the correct ID column name
            id_column = {
                'admin': 'admin_id',
                'site_engineer': 'site_engineer_id',
                'labour': 'labour_id'
            }.get(user_type)

            if not id_column:
                return False, "Invalid user type."

            # Correct SQL query with dynamic ID column
            sql = f"SELECT {id_column}, full_name FROM {user_type} WHERE email = %s AND password = %s"
            self.cursor.execute(sql, (email, hashed_password))
            result = self.cursor.fetchone()

            if result:
                return True, {"user_id": result[0], "full_name": result[1]}
            else:
                return False, "Invalid email or password."
        except Exception as e:
            print(f"Authentication error: {e}")
            return False, "An internal error occurred during authentication."
    
    

    # Get all the site Engineers
    def get_all_siteEngineers(self):
        try:
            with self.connection.cursor() as cursor:
                # Clear any unread results
                while self.connection.unread_result:
                    self.connection.get_rows()
                    
                cursor.execute("SELECT site_engineer_id, full_name, email, created_at FROM site_engineer")
                return True, cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            return False, str(e)



    def update_siteENgineer(self, site_engineer_id, full_name, email, password):
        """Updates an update_siteENgineer information in the database."""
        try:
            # If password is provided, update it; otherwise, skip password update
            if password:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()  # Ensure password is hashed
                sql = """
                UPDATE site_engineer 
                SET full_name = %s, email = %s, password = %s
                WHERE site_engineer_id = %s
                """
                self.cursor.execute(sql, (full_name, email, hashed_password, site_engineer_id))
            else:
                sql = """
                UPDATE site_engineer 
                SET full_name = %s, email = %s
                WHERE site_engineer_id = %s
                """
                self.cursor.execute(sql, (full_name, email, site_engineer_id))

            self.connection.commit()  # Commit the changes using the correct connection attribute
            print(f"Update successful for site_engineer_id={site_engineer_id}")
            return True, "SiteENgineer updated successfully"
        except Exception as e:
            print(f"Error updating site_engineer_id={site_engineer_id}: {e}")
            return False, f"Error: {e}"
        
    # Check refferencing  
    def check_referenc(self, site_engineer_id, tables):
        """Checks if a site engineer is referenced in the given tables."""
        try:
            for table in tables:
                sql_check = f"SELECT COUNT(*) AS total_references FROM {table} WHERE site_engineer_id = %s"
                self.cursor.execute(sql_check, (site_engineer_id,))
                result = self.cursor.fetchone()

                # Access the count by index (first element in the tuple)
                if result[0] > 0:
                    return False, f"site engineer is referenced in {table}."
            return True, "No references found."
        except Exception as e:
            print(f"Error checking references for site engineer: {e}")
            return False, f"Error: {e}"

        
    # Delete Site engineer
    def delete_siteEngineer(self, site_engineer_id):
        """Deletes a site engineer from the database."""
        try:
            sql = "DELETE FROM site_engineer WHERE site_engineer_id = %s"
            self.cursor.execute(sql, (site_engineer_id,))
            self.connection.commit()
            print(f"Site engineer with ID {site_engineer_id} deleted successfully")
            return True, "Site engineer deleted successfully"
        except Exception as e:
            print(f"Error deleting site_engineer_id={site_engineer_id}: {e}")
            return False, f"Error: {e}"
    
    
    
        # Delete site engineer
    


    # Get all admins
    def get_all_admins(self):
        """Fetches all Admins from the database."""
        try:
            sql = "SELECT * FROM Admin"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()  # Returns a list of dictionaries
            return True, result
        except Exception as e:
            print(f"Error fetching Admins model: {e}")
            return False, f"Error: {e}"

    def update_admin(self, user_id, full_name, email, password):
        """Updates an admin's information in the database."""
        try:
            # If password is provided, update it; otherwise, skip password update
            if password:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()  # Ensure password is hashed
                sql = """
                UPDATE Admin 
                SET full_name = %s, email = %s, password = %s
                WHERE admin_id = %s
                """
                self.cursor.execute(sql, (full_name, email, hashed_password, user_id))
            else:
                sql = """
                UPDATE Admin 
                SET full_name = %s, email = %s
                WHERE admin_id = %s
                """
                self.cursor.execute(sql, (full_name, email, user_id))

            self.connection.commit()  # Commit the changes using the correct connection attribute
            print(f"Update successful for admin_id={user_id}")
            return True, "Admin updated successfully"
        except Exception as e:
            print(f"Error updating admin_id={user_id}: {e}")
            return False, f"Error: {e}"
    # -------

    #  # Check refferencing  
    def check_referen(self, admin_id, tables):
        """Checks if a admin is referenced in the given tables."""
        try:
            for table in tables:
                sql_check = f"SELECT COUNT(*) AS total_references FROM {table} WHERE admin_id = %s"
                self.cursor.execute(sql_check, (admin_id,))
                result = self.cursor.fetchone()

                # Access the count by index (first element in the tuple)
                if result[0] > 0:
                    return False, f"admin is referenced in {table}."
            return True, "No references found."
        except Exception as e:
            print(f"Error checking references for admin: {e}")
            return False, f"Error: {e}"

        # Delete labour
    # Delete labour 
    def delete_admin(self, admin_id):
        """Deletes a admin  from the database."""
        try:
            sql = "DELETE FROM admin WHERE admin_id = %s"
            self.cursor.execute(sql, (admin_id,))
            self.connection.commit()
            print(f"Admin with ID {admin_id} deleted successfully")
            return True, "Admin deleted successfully"
        except Exception as e:
            print(f"Error deleting admin_id={admin_id}: {e}")
            return False, f"Error: {e}"


    # Get all Labours
    def get_all_labours(self):
        """Fetches all Labours from the database."""
        try:
            sql = "SELECT labour_id, full_name, email,type_of_work, created_at FROM labour"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()  # Returns a list of dictionaries
            return True, result
        except Exception as e:
            print(f"Error fetching labour model: {e}")
            return False, f"Error: {e}"

    #Update labour
    
    def update_labour(self, labour_id, full_name, email, password):
        """Updates an update_labour information in the database."""
        try:
            # If password is provided, update it; otherwise, skip password update
            if password:
                hashed_password = hashlib.sha256(password.encode()).hexdigest()  # Ensure password is hashed
                sql = """
                UPDATE labour
                SET full_name = %s, email = %s, password = %s
                WHERE labour_id= %s
                """
                self.cursor.execute(sql, (full_name, email, hashed_password, labour_id))
            else:
                sql = """
                UPDATE labour
                SET full_name = %s, email = %s
                WHERE labour_id= %s
                """
                self.cursor.execute(sql, (full_name, email, labour_id))

            self.connection.commit()  # Commit the changes using the correct connection attribute
            print(f"Update successful for labour_id={labour_id}")
            return True, "Labour updated successfully"
        except Exception as e:
            print(f"Error updating labour_id={labour_id}: {e}")
            return False, f"Error: {e}"
    
    def check_references(self, labour_id, tables):
        """Checks if a labour is referenced in the given tables."""
        try:
            for table in tables:
                sql_check = f"SELECT COUNT(*) AS total_references FROM {table} WHERE labour_id = %s"
                self.cursor.execute(sql_check, (labour_id,))
                result = self.cursor.fetchone()

                # Access the count by index (first element in the tuple)
                if result[0] > 0:
                    return False, f"labour is referenced in {table}."
            return True, "No references found."
        except Exception as e:
            print(f"Error checking references for labour: {e}")
            return False, f"Error: {e}"
    
        
    # Delete labour
    def delete_labour(self, labour_id):
        """Deletes a labour record from the database."""
        try:
            sql = "DELETE FROM labour WHERE labour_id = %s"
            self.cursor.execute(sql, (labour_id,))
            self.connection.commit()
            print(f"Labour with ID {labour_id} deleted successfully")
            return True, "Labour deleted successfully"
        except Exception as e:
            print(f"Error deleting labour_id={labour_id}: {e}")
            return False, f"Error: {e}"
    
    # Project site
      # Register a new project
    def register_project(self, name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id, admin_id):
        try:
            # Convert to float for validation
            total_budget = float(total_budget)
            material_budget = float(material_budget)
            wages_budget = float(wages_budget)
            other_expenses_budget = float(other_expenses_budget)
            # Validation: sum of budgets must not exceed total_budget
            if material_budget + wages_budget + other_expenses_budget > total_budget:
                return False, "The sum of Material, Wages, and Other Expenses budgets cannot exceed the Total Budget."

            sql = '''
            INSERT INTO projects (name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, used_budget, remaining_budget, status, site_engineer_id, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, NOW())
            '''
            remaining_budget = total_budget  # Initially, remaining budget equals total budget
            self.cursor.execute(sql, (name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, remaining_budget, status, site_engineer_id, admin_id))
            self.connection.commit()
            return True, "Project registered successfully!"
        except Exception as e:
            return False, f"Error: {e}"

     # Get all projects
    def get_all_projects(self):
        """Fetch all projects with complete information."""
        try:
            # Consume any unread results
            while self.connection.unread_result:
                self.connection.get_rows()
                
            sql = """
            SELECT p.*, se.full_name as site_engineer_name, a.full_name as admin_name
            FROM projects p
            LEFT JOIN site_engineer se ON p.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin a ON p.admin_id = a.admin_id
            ORDER BY p.name
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            projects = dict_cursor.fetchall()
            dict_cursor.close()
            return True, projects
        except Exception as e:
            print(f"Error in get_all_projects: {e}")
            return False, f"Error: {e}"

    def update_project(self, project_id, name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id):
        try:
            # Convert to float for validation
            total_budget = float(total_budget)
            material_budget = float(material_budget)
            wages_budget = float(wages_budget)
            other_expenses_budget = float(other_expenses_budget)
            # Validation: sum of budgets must not exceed total_budget
            if material_budget + wages_budget + other_expenses_budget > total_budget:
                return False, "The sum of Material, Wages, and Other Expenses budgets cannot exceed the Total Budget."

            sql = '''
            UPDATE projects
            SET name = %s, description = %s, start_date = %s, end_date = %s, total_budget = %s, material_budget = %s, wages_budget = %s, other_expenses_budget = %s, status = %s, site_engineer_id = %s
            WHERE project_id = %s
            '''
            self.cursor.execute(sql, (
                name, description, start_date, end_date, total_budget, material_budget, wages_budget, other_expenses_budget, status, site_engineer_id, project_id
            ))
            self.connection.commit()
            return True, "Project updated successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def check_project_references(self, project_id, tables):
        """Checks if a project is referenced in the given tables."""
        try:
            for table in tables:
                sql_check = f"SELECT COUNT(*) AS total_references FROM {table} WHERE project_id = %s"
                self.cursor.execute(sql_check, (project_id,))
                result = self.cursor.fetchone()

                if result[0] > 0:
                    return False, f"Project is referenced in {table}."
            return True, "No references found."
        except Exception as e:
            print(f"Error checking references for project: {e}")
            return False, f"Error: {e}"

    def delete_project(self, project_id):
        try:
            # Check for references in related tables
            related_tables = ['wages']  # Add more tables as needed
            can_delete, message = self.check_project_references(project_id, related_tables)

            if not can_delete:
                return False, message

            sql = "DELETE FROM projects WHERE project_id = %s"
            self.cursor.execute(sql, (project_id,))
            self.connection.commit()
            return True, "Project deleted successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def get_project_budget(self, project_id):
        try:
            sql = "SELECT project_budget FROM projects WHERE project_id = %s"
            self.cursor.execute(sql, (project_id,))
            project_budget = self.cursor.fetchone()[0]
            return True, project_budget
        except Exception as e:
            return False, f"Error: {e}"

    # Fetch site engineers and admins for dropdowns

    
    # Fetch site engineers
# def get_all_siteEngineers(self):
#     try:
#         sql = "SELECT site_engineer_id, full_name FROM site_engineer"
#         self.cursor.execute(sql)
#         return True, self.cursor.fetchall()
#     except Exception as e:
#         return False, f"Error: {e}"

# # Fetch admins
# def get_all_admins(self):
#     try:
#         sql = "SELECT admin_id, full_name FROM admin"
#         self.cursor.execute(sql)
#         return True, self.cursor.fetchall()
#     except Exception as e:
#         return False, f"Error: {e}"

    def get_site_engineers_with_projects(self):
        try:
            # Remove any pending results before executing a new query
            while self.connection.unread_result:
                self.connection.get_rows()
            # Use a fresh cursor for this query to avoid "commands out of sync"
            dict_cursor = self.connection.cursor(dictionary=True)
            sql = '''
            SELECT DISTINCT se.site_engineer_id, se.full_name
            FROM site_engineer se
            JOIN projects p ON se.site_engineer_id = p.site_engineer_id
            '''
            dict_cursor.execute(sql)
            site_engineers = [{"id": se["site_engineer_id"], "name": se["full_name"]} for se in dict_cursor.fetchall()]
            dict_cursor.close()
            return True, site_engineers
        except Exception as e:
            print(f"Error in get_site_engineers_with_projects: {e}")
            return False, f"Error: {e}"

    def get_projects_for_site_engineer(self, site_engineer_id):
        """Fetch projects assigned to a specific site engineer."""
        try:
            sql = "SELECT project_id, name FROM projects WHERE site_engineer_id = %s"
            self.cursor.execute(sql, (site_engineer_id,))
            return True, self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching projects for site engineer {site_engineer_id}: {e}")
            return False, f"Error: {e}"

    # Materials Manage site

    def safe_decimal(self, value):
        """Safely convert a value to Decimal, defaulting to 0 if invalid."""
        try:
            return Decimal(str(value)) if value is not None else Decimal(0)
        except Exception:
            return Decimal(0)

    def register_material(self, item_name, quantity, unit_price, amount, site_engineer_id, project_id, admin_id):
        try:
            # Validate that item_name is not empty
            if not item_name:
                return False, "Item name is required."

            # Convert amount to Decimal
            amount = self.safe_decimal(amount)

            # Fetch project budgets
            sql_fetch_project = """
            SELECT total_budget, material_budget, used_budget
            FROM projects
            WHERE project_id = %s
            """
            self.cursor.execute(sql_fetch_project, (project_id,))
            project = self.cursor.fetchone()

            if not project:
                return False, "Project not found."

            total_budget, material_budget, used_budget = map(self.safe_decimal, project)

            # Check if the material cost exceeds the available material budget
            if amount > material_budget:
                return False, "Not sufficient material budget for this material."

            # Deduct the material cost from the material budget
            new_material_budget = material_budget - amount

            # Add the material cost to the used budget
            new_used_budget = used_budget + amount

            # Recalculate the remaining budget
            new_remaining_budget = total_budget - new_used_budget   

            # Insert material into the database (site_engineer_id can be None)
            sql_insert_material = """
            INSERT INTO materials (item_name, quantity, unit_price, amount, site_engineer_id, project_id, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql_insert_material, (item_name, quantity, unit_price, amount, site_engineer_id, project_id, admin_id))

            # Update the project budgets
            sql_update_project = """
            UPDATE projects
            SET material_budget = %s, used_budget = %s, remaining_budget = %s
            WHERE project_id = %s
            """
            self.cursor.execute(sql_update_project, (new_material_budget, new_used_budget, new_remaining_budget, project_id))

            self.connection.commit()
            return True, "Material registered successfully!"

        except Exception as e:
            return False, f"Error: {e}"

    def update_material(self, material_id, item_name, quantity, unit_price, amount, project_id, admin_id):
        try:
            # Fetch the old material amount and project_id
            sql_old = "SELECT amount, project_id FROM materials WHERE material_id = %s"
            self.cursor.execute(sql_old, (material_id,))
            old_data = self.cursor.fetchone()
            if not old_data:
                return False, "Material not found."
            old_amount = self.safe_decimal(old_data[0])
            old_project_id = old_data[1]

            amount = self.safe_decimal(amount)

            # Update the material (set site_engineer_id to NULL if not used)
            sql = '''
            UPDATE materials
            SET item_name = %s, quantity = %s, unit_price = %s, amount = %s, project_id = %s, admin_id = %s, site_engineer_id = NULL
            WHERE material_id = %s
            '''
            self.cursor.execute(sql, (item_name, quantity, unit_price, amount, project_id, admin_id, material_id))
            self.connection.commit()

            # If project changed, update both old and new projects' budgets
            if old_project_id != project_id:
                # Recalculate used and remaining budgets for old project
                used_amount_old = self.get_used_amount_for_project(old_project_id)
                sql_update_old = '''
                UPDATE projects
                SET used_budget = %s, remaining_budget = total_budget - %s
                WHERE project_id = %s
                '''
                self.cursor.execute(sql_update_old, (used_amount_old, used_amount_old, old_project_id))

                # Recalculate used and remaining budgets for new project
                used_amount_new = self.get_used_amount_for_project(project_id)
                sql_update_new = '''
                UPDATE projects
                SET used_budget = %s, remaining_budget = total_budget - %s
                WHERE project_id = %s
                '''
                self.cursor.execute(sql_update_new, (used_amount_new, used_amount_new, project_id))
            else:
                # Only one project to update
                used_amount = self.get_used_amount_for_project(project_id)
                sql_update = '''
                UPDATE projects
                SET used_budget = %s, remaining_budget = total_budget - %s
                WHERE project_id = %s
                '''
                self.cursor.execute(sql_update, (used_amount, used_amount, project_id))

            self.connection.commit()
            return True, "Material updated successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def delete_material(self, material_id):
        try:
            sql = "DELETE FROM materials WHERE material_id = %s"
            self.cursor.execute(sql, (material_id,))
            self.connection.commit()
            return True, "Material deleted successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def get_material_by_id(self, material_id):
        try:
            sql = '''
            SELECT m.material_id, m.item_name, m.quantity, m.unit_price, m.amount, 
                m.site_engineer_id, m.project_id, m.created_at
            FROM materials m
            WHERE m.material_id = %s
            '''
            self.cursor.execute(sql, (material_id,))
            material = self.cursor.fetchone()
            return True, material
        except Exception as e:
            return False, f"Error: {e}"
    

    def get_all_materials(self):
        """
        Fetch all materials with related project and user (admin/site engineer) info.
        Returns a list of dicts with keys: material_id, item_name, quantity, unit_price, amount, project_name, admin_name, site_engineer_name, created_at, is_paid
        """
        try:
            sql = """
            SELECT 
                m.material_id,
                m.item_name,
                m.quantity,
                m.unit_price,
                m.amount,
                p.name AS project_name,
                a.full_name AS admin_name,
                se.full_name AS site_engineer_name,
                m.created_at,
                m.is_paid
            FROM materials m
            LEFT JOIN projects p ON m.project_id = p.project_id
            LEFT JOIN admin a ON m.admin_id = a.admin_id
            LEFT JOIN site_engineer se ON m.site_engineer_id = se.site_engineer_id
            ORDER BY m.created_at DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            materials = dict_cursor.fetchall()
            dict_cursor.close()
            return True, materials
        except Exception as e:
            print(f"Error fetching materials: {e}")
            return False, f"Error: {e}"


  

    # --- Admin Wages Management ---
    def register_wage_admin(self, labour_id, project_id, daily_rate, total_days, total_wage, admin_id):
        try:
            # Check for unpaid attendance
            sql_check = """
            SELECT COUNT(*) AS unpaid_count
            FROM attendance
            WHERE labour_id = %s AND project_id = %s AND status = 'Present' AND is_paid = FALSE
            """
            self.cursor.execute(sql_check, (labour_id, project_id))
            unpaid_count = self.cursor.fetchone()[0]
            if unpaid_count == 0:
                return False, "No unpaid attendance records found for this labour in this project."

            # Insert wage record (admin_id)
            sql_insert = """
            INSERT INTO wages 
            (labour_id, project_id, daily_rate, total_days, total_wage, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql_insert, (
                labour_id, project_id, daily_rate, total_days, total_wage, admin_id
            ))

            # Mark attendance as paid
            sql_update_attendance = """
            UPDATE attendance 
            SET is_paid = TRUE
            WHERE labour_id = %s AND project_id = %s AND status = 'Present' AND is_paid = FALSE
            """
            self.cursor.execute(sql_update_attendance, (labour_id, project_id))

            # Update project budgets
            sql_update_project = """
            UPDATE projects 
            SET 
                wages_budget = wages_budget - %s,
                used_budget = used_budget + %s,
                remaining_budget = total_budget - (used_budget + %s)
            WHERE project_id = %s
            """
            self.cursor.execute(sql_update_project, (total_wage, total_wage, total_wage, project_id))

            self.connection.commit()
            return True, "Wage registered successfully, attendance marked as paid, and budgets updated!"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in register_wage_admin: {e}")
            return False, str(e)

    def get_wages_by_admin(self, admin_id=None):
        """
        Fetch all wage records, including those registered by site engineers.
        Always returns fresh data as a list of dictionaries.
        """
        try:
            self.connection.commit()  # Ensure latest data is visible to all
            sql = """
            SELECT 
                w.wage_id,
                l.full_name AS labour_name,
                p.name AS project_name,
                w.daily_rate,
                w.total_days,
                w.total_wage,
                a.full_name AS admin_name,
                se.full_name AS site_engineer_name,
                w.created_at,
                w.labour_id,
                w.project_id,
                w.is_paid  # Add this line to include the payment status
            FROM wages w
            JOIN labour l ON w.labour_id = l.labour_id
            JOIN projects p ON w.project_id = p.project_id
            LEFT JOIN admin a ON w.admin_id = a.admin_id
            LEFT JOIN site_engineer se ON w.site_engineer_id = se.site_engineer_id
            ORDER BY w.created_at DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            return dict_cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            return []

    def update_wage_admin(self, wage_id, labour_id, project_id, daily_rate, total_days, total_wage):
        try:
            # Explicitly commit any pending transactions before starting
            self.connection.commit()
            
            # First check if the wage exists and get its current values
            wage = self.get_wage_by_id_admin(wage_id)
            if not wage:
                return False, "Wage record not found"
            
            # Check if labour is assigned to the new project
            sql_check_assignment = """
            SELECT 1 FROM labour_project 
            WHERE project_id = %s AND labour_id = %s
            """
            self.cursor.execute(sql_check_assignment, (project_id, labour_id))
            if not self.cursor.fetchone():
                return False, "This labour is not assigned to the selected project"
            
            # If wage was created by site engineer, check project belongs to same engineer
            if wage.get('site_engineer_id'):
                sql_check_engineer = """
                SELECT 1 FROM projects 
                WHERE project_id = %s AND site_engineer_id = %s
                """
                self.cursor.execute(sql_check_engineer, (project_id, wage['site_engineer_id']))
                if not self.cursor.fetchone():
                    return False, "Cannot update to a project not managed by the original site engineer"

            sql_update = """
            UPDATE wages 
            SET labour_id = %s, 
                project_id = %s, 
                daily_rate = %s, 
                total_days = %s, 
                total_wage = %s
            WHERE wage_id = %s
            """
            self.cursor.execute(sql_update, (
                labour_id, project_id, daily_rate, total_days, total_wage, wage_id
            ))
            self.connection.commit()
            return True, "Wage updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_wage_admin: {e}")
            return False, str(e)

    def get_wage_by_id_admin(self, wage_id):
        try:
            sql = """
            SELECT wage_id, labour_id, project_id, daily_rate, total_days, total_wage
            FROM wages
            WHERE wage_id = %s
            """
            self.cursor.execute(sql, (wage_id,))
            row = self.cursor.fetchone()
            if row:
                # If using tuple, convert to dict for JSON
                return {
                    "wage_id": row[0],
                    "labour_id": row[1],
                    "project_id": row[2],
                    "daily_rate": row[3],
                    "total_days": row[4],
                    "total_wage": row[5]
                }
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def get_wage_by_id(self, wage_id):
        try:
            sql = """
            SELECT 
                w.wage_id,
                w.labour_id,
                l.full_name AS labour_name,
                w.project_id,
                p.name AS project_name,
                w.daily_rate,
                w.total_days,
                w.total_wage,
                w.is_paid,  # Make sure this is included
                w.admin_id,
                a.full_name AS admin_name,
                w.created_at
            FROM wages w
            JOIN labour l ON w.labour_id = l.labour_id
            JOIN projects p ON w.project_id = p.project_id
            LEFT JOIN admin a ON w.admin_id = a.admin_id
            WHERE w.wage_id = %s
            """
            self.cursor.execute(sql, (wage_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error in get_wage_by_id: {e}")
            return None

    def delete_wage_admin(self, wage_id):
        try:
            sql_delete = "DELETE FROM wages WHERE wage_id = %s"
            self.cursor.execute(sql_delete, (wage_id,))
            self.connection.commit()
            return True, "Wage deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error: {e}")
            return False, str(e)

    def get_present_days_count(self, labour_id, project_id):
        """Get count of days labour was marked as Present for a specific project."""
        try:
            sql = """
            SELECT COUNT(*) AS present_days
            FROM attendance a
            JOIN labour_project lp ON a.labour_id = lp.labour_id AND a.project_id = lp.project_id
            WHERE a.labour_id = %s 
            AND a.project_id = %s
            AND a.status = 'Present'
            """
            self.cursor.execute(sql, (labour_id, project_id))
            result = self.cursor.fetchone()
            return result['present_days'] if result else 0
        except Exception as e:
            print(f"Error in get_present_days_count: {e}")
            return 0
        
    def get_unpaid_present_days_count(self, labour_id, project_id):
        """Get count of unpaid days labour was marked as Present for a specific project."""
        try:
            sql = """
            SELECT COUNT(*) FROM attendance
            WHERE labour_id = %s 
            AND project_id = %s
            AND status = 'Present'
            AND is_paid = FALSE
            """
            self.cursor.execute(sql, (labour_id, project_id))
            result = self.cursor.fetchone()
            return int(result[0]) if result else 0
        except Exception as e:
            print(f"Error in get_unpaid_present_days_count: {e}")
            return 0
        

    def check_existing_wage(self, labour_id, project_id):
        """Check if a wage record already exists for this labour in this project"""
        try:
            sql = """
            SELECT 1 FROM wages 
            WHERE labour_id = %s AND project_id = %s
            LIMIT 1
            """
            self.cursor.execute(sql, (labour_id, project_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"Error in check_existing_wage: {e}")
            return True  # Return True to prevent insertion if error occurs

    # Labour Project Management
    def register_labour_project(self, labour_id, project_id):
        try:
            # Check if the labour is already assigned to the same project
            sql_check = '''
            SELECT COUNT(*) FROM labour_project WHERE labour_id = %s AND project_id = %s
            '''
            self.cursor.execute(sql_check, (labour_id, project_id))
            count = self.cursor.fetchone()[0]

            if count > 0:
                return False, "Labour is already assigned to this project."

            sql = '''
            INSERT INTO labour_project (labour_id, project_id, assigned_date)
            VALUES (%s, %s, NOW())
            '''
            self.cursor.execute(sql, (labour_id, project_id))
            self.connection.commit()
            return True, "Labour assigned to project successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def get_labours_assigned_to_projects(self):
        """Fetches labours assigned to projects."""
        try:
            sql = '''
            SELECT l.labour_id, l.full_name, p.project_id, p.name
            FROM labour_project lp
            JOIN labour l ON lp.labour_id = l.labour_id
            JOIN projects p ON lp.project_id = p.project_id
            '''
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            return True, result
        except Exception as e:
            print(f"Error fetching labours assigned to projects: {e}")
            return False, f"Error: {e}"

    def get_all_labour_projects(self):
        try:
            sql = '''
            SELECT lp.id, l.full_name AS labour_name, p.name AS project_name, lp.assigned_date, lp.labour_id, lp.project_id
            FROM labour_project lp
            LEFT JOIN labour l ON lp.labour_id = l.labour_id
            LEFT JOIN projects p ON lp.project_id = p.project_id
            '''
            self.cursor.execute(sql)
            assignments = self.cursor.fetchall()
            return True, assignments
        except Exception as e:
            print(f"Error fetching assignments: {e}")
            return False, f"Error: {e}"

    def update_labour_project(self, assignment_id, labour_id, project_id):
        try:
            sql = '''
            UPDATE labour_project
            SET labour_id = %s, project_id = %s
            WHERE id = %s
            '''
            self.cursor.execute(sql, (labour_id, project_id, assignment_id))
            self.connection.commit()
            return True, "Assignment updated successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    def delete_labour_project(self, assignment_id):
        try:
            sql = "DELETE FROM labour_project WHERE id = %s"
            self.cursor.execute(sql, (assignment_id,))
            self.connection.commit()
            return True, "Assignment deleted successfully!"
        except Exception as e:
            return False, f"Error: {e}"

    # --- Attendance Management ---
    def register_attendance(self, labour_id, project_id, date, status, site_engineer_id=None, admin_id=None):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            # Check for existing attendance
            if self.check_existing_attendance(labour_id, date):
                return False, f"Attendance already recorded for this labour on {date}"
                
            # Check labour-project assignment
            if not self.check_labour_project_assignment(labour_id, project_id):
                return False, "This labour is not assigned to the selected project"

            # Insert attendance
            sql = '''
            INSERT INTO attendance (labour_id, project_id, date, status, site_engineer_id, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            '''
            self.cursor.execute(sql, (labour_id, project_id, date, status, site_engineer_id, admin_id))
            self.connection.commit()
            return True, "Attendance registered successfully!"
        except Exception as e:
            self.connection.rollback()
            return False, f"Error: {e}"

    def get_all_attendance(self):
        """Fetch all attendance records with related information."""
        try:
            self.ensure_no_active_transaction()
            self.connection.commit()  # Ensure latest data is visible
            
            sql = """
            SELECT 
                a.attendance_id,
                l.full_name AS labour_name,
                p.name AS project_name,
                a.date,
                a.status,
                se.full_name AS site_engineer,
                ad.full_name AS admin_name
            FROM attendance a
            JOIN labour l ON a.labour_id = l.labour_id
            JOIN projects p ON a.project_id = p.project_id
            LEFT JOIN site_engineer se ON a.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin ad ON a.admin_id = ad.admin_id
            ORDER BY a.date DESC, a.created_at DESC
            """
            
            # Use a new cursor each time
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql)
            records = cursor.fetchall()
            cursor.close()  # Explicitly close the cursor
            
            return True, records
        except Exception as e:
            print(f"Error in get_all_attendance: {e}")
            return False, f"Error: {e}"
    

    def check_existing_attendance(self, labour_id, date):
        """Check if attendance already exists for this labour on this date."""
        try:
            sql = """
            SELECT 1 FROM attendance 
            WHERE labour_id = %s AND date = %s
            LIMIT 1
            """
            self.cursor.execute(sql, (labour_id, date))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"Error in check_existing_attendance: {e}")
            return True  # Return True to prevent insertion if error occurs

    def check_existing_attendance_for_update(self, labour_id, date, attendance_id):
        """Check for existing attendance excluding current record."""
        try:
            sql = """
            SELECT 1 FROM attendance 
            WHERE labour_id = %s AND date = %s AND attendance_id != %s
            LIMIT 1
            """
            self.cursor.execute(sql, (labour_id, date, attendance_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"Error in check_existing_attendance_for_update: {e}")
            return True

    def ensure_no_active_transaction(self):
        """Ensure no active transaction is in progress."""
        try:
            if getattr(self.connection, "in_transaction", False):
                self.connection.rollback()
        except Exception as e:
            print(f"Error ensuring no active transaction: {e}")

    def update_attendance(self, attendance_id, labour_id, project_id, date, status, site_engineer_id=None):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            # Check for existing attendance (excluding current record)
            if self.check_existing_attendance_for_update(labour_id, date, attendance_id):
                return False, f"Attendance already recorded for this labour on {date}"
                
            # Check labour-project assignment
            if not self.check_labour_project_assignment(labour_id, project_id):
                return False, "This labour is not assigned to the selected project"

            sql_update = """
            UPDATE attendance
            SET labour_id = %s,
                project_id = %s,
                date = %s,
                status = %s,
                site_engineer_id = %s
            WHERE attendance_id = %s
            """
            self.cursor.execute(sql_update, (
                labour_id,
                project_id,
                date,
                status,
                site_engineer_id,
                attendance_id
            ))
            self.connection.commit()
            return True, "Attendance updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_attendance: {e}")
            return False, str(e)

    def delete_attendance(self, attendance_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            sql_delete = "DELETE FROM attendance WHERE attendance_id = %s"
            self.cursor.execute(sql_delete, (attendance_id,))
            
            self.connection.commit()
            return True, "Attendance deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in delete_attendance: {e}")
            return False, str(e)

    def check_labour_project_assignment(self, labour_id, project_id):
        """
        Check if a labour is assigned to a specific project.
        Returns True if assigned, False otherwise.
        """
        try:
            sql = "SELECT 1 FROM labour_project WHERE labour_id = %s AND project_id = %s LIMIT 1"
            self.cursor.execute(sql, (labour_id, project_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"Error in check_labour_project_assignment: {e}")
            return False

    def get_all_expenses_dict(self):
        """
        Fetch all expenses as a list of dictionaries for up-to-date display.
        """
        try:
            sql = """
            SELECT 
                e.expense_id,
                e.project_id,
                p.name AS project_name,
                e.item_name,
                e.amount,
                e.description,
                se.full_name AS site_engineer_name,
                a.full_name AS admin_name,
                e.expense_type,
                e.created_at,
                e.is_paid
            FROM expenses e
            LEFT JOIN projects p ON e.project_id = p.project_id
            LEFT JOIN site_engineer se ON e.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin a ON e.admin_id = a.admin_id
            ORDER BY e.created_at DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            expenses = dict_cursor.fetchall()
            dict_cursor.close()
            return True, expenses
        except Exception as e:
            print(f"Error fetching expenses: {e}")
            return False, f"Error: {e}"

    def is_valid_project(self, project_id):
        try:
            sql = "SELECT 1 FROM projects WHERE project_id = %s"
            self.cursor.execute(sql, (project_id,))
            return self.cursor.fetchone() is not None
        except Exception:
            return False

    def register_expense(self, project_id, item_name, amount, description, site_engineer_id, expense_type, admin_id):
        try:
            sql = """
            INSERT INTO expenses (project_id, item_name, amount, description, site_engineer_id, expense_type, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql, (project_id, item_name, amount, description, site_engineer_id, expense_type, admin_id))
            self.connection.commit()
            return True, "Expense registered successfully."
        except Exception as e:
            self.connection.rollback()
            return False, f"Error: {e}"

    def update_expense(self, expense_id, item_name, amount, description, project_id, site_engineer_id, expense_type):
        try:
            # If admin is updating, set admin_id, clear site_engineer_id
            sql = """
            UPDATE expenses
            SET item_name = %s,
                amount = %s,
                description = %s,
                project_id = %s,
                site_engineer_id = NULL,
                admin_id = %s,
                expense_type = %s
            WHERE expense_id = %s
            """
            admin_id = None
            # Try to get admin_id from session if available
            from flask import session
            admin_id = session.get('admin_id')
            self.cursor.execute(sql, (
                item_name, amount, description, project_id, admin_id, expense_type, expense_id
            ))
            self.connection.commit()
            return True, "Expense updated successfully."
        except Exception as e:
            self.connection.rollback()
            return False, f"Error: {e}"

    def delete_expense(self, expense_id):
        """Delete an expense by its ID."""
        try:
            sql = "DELETE FROM expenses WHERE expense_id = %s"
            self.cursor.execute(sql, (expense_id,))
            self.connection.commit()
            if self.cursor.rowcount == 0:
                return False, "Expense not found"
            return True, "Expense deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error deleting expense: {e}")
            return False, f"Error: {e}"



# budget tracking and management
    def get_all_budget_transactions_dict(self):
        """
        Fetch all budget transactions as a list of dictionaries for display.
        """
        try:
            sql = """
            SELECT 
                bt.transaction_id,
                bt.project_id,
                p.name AS project_name,
                bt.transaction_type,
                bt.reference_id,
                bt.amount,
                bt.balance,
                bt.transaction_date,
                a.full_name AS admin_name,
                bt.created_at
            FROM budget_tracking bt
            LEFT JOIN projects p ON bt.project_id = p.project_id
            LEFT JOIN admin a ON bt.admin_id = a.admin_id
            ORDER BY bt.transaction_date DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            transactions = dict_cursor.fetchall()
            dict_cursor.close()
            return True, transactions
        except Exception as e:
            print(f"Error fetching budget transactions: {e}")
            return False, f"Error: {e}"

    def validate_reference(self, transaction_type, reference_id):
        """
        Validate that the reference ID exists in the appropriate table
        """
        try:
            if transaction_type == 'payment_wage':
                table = 'wages'
            elif transaction_type == 'material_purchase':
                table = 'materials'
            elif transaction_type == 'expense_payment':
                table = 'expenses'
            elif transaction_type == 'project_funding':
                return True  # No reference validation needed for funding
            else:
                return False
                
            sql = f"SELECT 1 FROM {table} WHERE {'wage_id' if table == 'wages' else 'material_id' if table == 'materials' else 'expense_id'} = %s"
            self.cursor.execute(sql, (reference_id,))
            return self.cursor.fetchone() is not None
        except Exception:
            return False

    def budget_transaction_exists(self, transaction_id):
        """Check if a budget transaction exists"""
        try:
            sql = "SELECT 1 FROM budget_tracking WHERE transaction_id = %s"
            self.cursor.execute(sql, (transaction_id,))
            return self.cursor.fetchone() is not None
        except Exception:
            return False

    def update_budget_transaction(self, transaction_id, project_id, transaction_type, reference_id, amount, remarks):
        """Update an existing budget transaction"""
        try:
            # First get the old transaction details
            sql_get = """
            SELECT amount, transaction_type, project_id 
            FROM budget_tracking 
            WHERE transaction_id = %s
            """
            self.cursor.execute(sql_get, (transaction_id,))
            old_transaction = self.cursor.fetchone()
            
            if not old_transaction:
                return False, "Transaction not found"
                
            old_amount = float(old_transaction[0])
            old_type = old_transaction[1]
            old_project_id = old_transaction[2]

            # If any of the key fields changed, delete and re-insert, else just update remarks/reference
            if (float(amount) != old_amount or transaction_type != old_type or str(project_id) != str(old_project_id)):
                # Remove the old transaction
                self.update_budget_transaction(transaction_id, recalc_only=True)
                # Insert the new transaction
                # Use admin_id from session if available
                from flask import session
                admin_id = session.get('admin_id')
                return self.register_budget_transaction(
                    project_id, transaction_type, reference_id, amount, remarks, admin_id
                )
            else:
                # Only update reference_id (remarks removed)
                sql_update = """
                UPDATE budget_tracking 
                SET reference_id = %s
                WHERE transaction_id = %s
                """
                self.cursor.execute(sql_update, (reference_id, transaction_id))
                self.connection.commit()
                return True, "Budget transaction updated successfully."
        except Exception as e:
            self.connection.rollback()
            return False, f"Error: {e}"

    def register_budget_transaction(self, project_id, transaction_type, reference_id, amount, remarks, admin_id):
        """Register a new budget transaction"""
        try:
            # First get current balance for the project
            sql_balance = """
            SELECT COALESCE(SUM(
                CASE 
                    WHEN transaction_type = 'project_funding' THEN amount
                    ELSE -amount
                END
            ), 0) AS balance 
            FROM budget_tracking 
            WHERE project_id = %s
            """
            self.cursor.execute(sql_balance, (project_id,))
            result = self.cursor.fetchone()
            current_balance = float(result[0]) if result else 0
            
            # Calculate new balance
            if transaction_type == 'project_funding':
                new_balance = current_balance + float(amount)
            else:
                new_balance = current_balance - float(amount)
                
            # Insert the transaction
            sql_insert = """
            INSERT INTO budget_tracking 
            (project_id, transaction_type, reference_id, amount, balance, admin_id, transaction_date, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            self.cursor.execute(sql_insert, (
                project_id, transaction_type, reference_id, amount, new_balance, admin_id
            ))
            self.connection.commit()
            return True, "Budget transaction registered successfully."
        except Exception as e:
            self.connection.rollback()
            return False, f"Error: {e}"



    # Payment Management Section Start
    def register_payment(self, project_id, amount, payment_date, payment_method, payment_status, admin_id, wage_id=None, material_id=None, expense_id=None):
        try:
            # Insert payment record
            sql_insert = """
            INSERT INTO payments 
            (project_id, amount, payment_date, payment_method, payment_status, admin_id, wage_id, material_id, expense_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql_insert, (
                project_id, amount, payment_date, payment_method, payment_status, admin_id, 
                wage_id, material_id, expense_id
            ))
            
            payment_id = self.cursor.lastrowid
            
            # If this is a wage payment, update the wage status
            if wage_id:
                sql_update_wage = """
                UPDATE wages SET is_paid = TRUE WHERE wage_id = %s
                """
                self.cursor.execute(sql_update_wage, (wage_id,))
            
            # If this is a material payment, update the material status
            if material_id:
                sql_update_material = """
                UPDATE materials SET is_paid = TRUE WHERE material_id = %s
                """
                self.cursor.execute(sql_update_material, (material_id,))
            
            # If this is an expense payment, update the expense status
            if expense_id:
                sql_update_expense = """
                UPDATE expenses SET is_paid = TRUE WHERE expense_id = %s
                """
                self.cursor.execute(sql_update_expense, (expense_id,))
            
            self.connection.commit()
            return (True, "Payment registered successfully", payment_id)
        except Exception as e:
            self.connection.rollback()
            print(f"Error in register_payment: {e}")
            return (False, str(e), None)
    
    def get_all_payments(self):
        """
        Fetch all payment records with related wage/material/expense info.
        Returns a list of dictionaries.
        """
        try:
            sql = """
            SELECT 
                p.payment_id,
                p.project_id,
                pr.name AS project_name,
                p.amount,
                p.payment_date,
                p.payment_method,
                p.payment_status,
                a.full_name AS admin_name,
                p.wage_id,
                w.total_wage,
                w.is_paid AS wage_is_paid,
                l.full_name AS labour_name,
                p.material_id,
                m.item_name AS material_name,
                m.amount AS material_amount,
                m.is_paid AS material_is_paid,
                p.expense_id,
                e.item_name AS expense_name,
                e.amount AS expense_amount,
                e.is_paid AS expense_is_paid,
                p.created_at
            FROM payments p
            JOIN projects pr ON p.project_id = pr.project_id
            JOIN admin a ON p.admin_id = a.admin_id
            LEFT JOIN wages w ON p.wage_id = w.wage_id
            LEFT JOIN labour l ON w.labour_id = l.labour_id
            LEFT JOIN materials m ON p.material_id = m.material_id
            LEFT JOIN expenses e ON p.expense_id = e.expense_id
            ORDER BY p.payment_date DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            payments = dict_cursor.fetchall()
            dict_cursor.close()
            return payments
        except Exception as e:
            print(f"Error in get_all_payments: {e}")
            return []
        
    def update_payment(self, payment_id, project_id, amount, payment_date, payment_method, payment_status):
        try:
            # Get previous payment info
            self.cursor.execute("SELECT wage_id, material_id, expense_id FROM payments WHERE payment_id = %s", (payment_id,))
            prev = self.cursor.fetchone()
            if prev:
                wage_id, material_id, expense_id = prev
            else:
                wage_id, material_id, expense_id = None, None, None

            sql = """
            UPDATE payments 
            SET 
                project_id = %s,
                amount = %s,
                payment_date = %s,
                payment_method = %s,
                payment_status = %s
            WHERE payment_id = %s
            """
            self.cursor.execute(sql, (
                project_id, amount, payment_date, payment_method, payment_status, payment_id
            ))

            # Update related records' paid status
            if wage_id:
                self.cursor.execute("UPDATE wages SET is_paid = %s WHERE wage_id = %s", (payment_status == 'Paid', wage_id))
            if material_id:
                self.cursor.execute("UPDATE materials SET is_paid = %s WHERE material_id = %s", (payment_status == 'Paid', material_id))
            if expense_id:
                self.cursor.execute("UPDATE expenses SET is_paid = %s WHERE expense_id = %s", (payment_status == 'Paid', expense_id))
            
            self.connection.commit()
            return (True, "Payment updated successfully")
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_payment: {e}")
            return (False, str(e))

    def delete_payment(self, payment_id):
        try:
            # Get payment info
            self.cursor.execute("SELECT wage_id, material_id, expense_id FROM payments WHERE payment_id = %s", (payment_id,))
            payment = self.cursor.fetchone()
            if payment:
                wage_id, material_id, expense_id = payment
            else:
                wage_id, material_id, expense_id = None, None, None

            # Mark related records as unpaid
            if wage_id:
                self.cursor.execute("UPDATE wages SET is_paid = FALSE WHERE wage_id = %s", (wage_id,))
            if material_id:
                self.cursor.execute("UPDATE materials SET is_paid = FALSE WHERE material_id = %s", (material_id,))
            if expense_id:
                self.cursor.execute("UPDATE expenses SET is_paid = FALSE WHERE expense_id = %s", (expense_id,))

            # Delete payment
            self.cursor.execute("DELETE FROM payments WHERE payment_id = %s", (payment_id,))
            self.connection.commit()
            return (True, "Payment deleted successfully")
        except Exception as e:
            self.connection.rollback()
            print(f"Error in delete_payment: {e}")
            return (False, str(e))
        
        
    def get_unpaid_wages(self):
        """
        Fetch all unpaid wage records (is_paid = FALSE).
        Returns a list of dicts with wage_id, labour_name, project_name, total_wage.
        """
        try:
            sql = """
            SELECT 
                w.wage_id,
                l.full_name AS labour_name,
                p.name AS project_name,
                w.total_wage,
                w.project_id
            FROM wages w
            JOIN labour l ON w.labour_id = l.labour_id
            JOIN projects p ON w.project_id = p.project_id
            WHERE w.is_paid = FALSE
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            unpaid_wages = dict_cursor.fetchall()
            dict_cursor.close()
            return unpaid_wages
        except Exception as e:
            print(f"Error in get_unpaid_wages: {e}")
            return []

    def get_unpaid_materials(self):
        """
        Fetch all unpaid material records (is_paid = FALSE).
        Returns a list of dicts with material_id, material_name, total_cost.
        """
        try:
            sql = """
            SELECT 
                m.material_id,
                m.item_name AS material_name,
                m.amount AS total_cost,
                m.project_id
            FROM materials m
            WHERE m.is_paid = FALSE
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            unpaid_materials = dict_cursor.fetchall()
            dict_cursor.close()
            return unpaid_materials
        except Exception as e:
            print(f"Error in get_unpaid_materials: {e}")
            return []

    def get_unpaid_expenses(self):
        """
        Fetch all unpaid expense records (is_paid = FALSE).
        Returns a list of dicts with expense_id, expense_name, amount.
        """
        try:
            sql = """
            SELECT 
                e.expense_id,
                e.item_name AS expense_name,
                e.amount,
                e.project_id
            FROM expenses e
            WHERE e.is_paid = FALSE
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql)
            unpaid_expenses = dict_cursor.fetchall()
            dict_cursor.close()
            return unpaid_expenses
        except Exception as e:
            print(f"Error in get_unpaid_expenses: {e}")
            return []