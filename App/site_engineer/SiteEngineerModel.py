import mysql.connector
from App.configuration import UserDbConnection
import decimal
import traceback
import json


class UserDatabase:
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = int(port) 
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
            print("Site_engineer, Database connection established.")
        except Exception as e:
            print(f"Connection error: {e}")
            raise e

    def my_cursor(self):
        return self.cursor


class UserModel:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = self.connection.cursor(dictionary=True)

    def safe_decimal(self, value):
        """Safely convert a value to a Decimal."""
        try:
            return decimal.Decimal(value)
        except (TypeError, ValueError, decimal.InvalidOperation):
            return decimal.Decimal(0)
    
    
    def ensure_no_active_transaction(self):
        """Ensure no active transaction is in progress."""
        try:
            if getattr(self.connection, "in_transaction", False):
                self.connection.rollback()
        except Exception as e:
            print(f"Error ensuring no active transaction: {e}")

    def get_my_projects(self, site_engineer_id):
        """Fetch projects assigned to the given site engineer."""
        try:
            query = """
                SELECT project_id, name, description, status, start_date, end_date,
                    total_budget, material_budget, wages_budget, other_expenses_budget,
                    used_budget, remaining_budget, site_engineer_id, admin_id
                FROM projects
                WHERE site_engineer_id = %s
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching engineer's projects: {e}")
            return []
    
    def register_material(self, item_name, quantity, unit_price, amount, site_engineer_id, project_id):
        try:
            # Note: admin_id is NULL here since it's registered by site engineer
            sql = """
            INSERT INTO materials 
            (item_name, quantity, unit_price, amount, site_engineer_id, project_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql, (item_name, quantity, unit_price, amount, site_engineer_id, project_id))
            self.connection.commit()
            return True, "Material registered successfully!"
        except Exception as e:
            self.connection.rollback()
            return False, str(e)
    
    def safe_decimal(self, value):
        """Convert value to Decimal safely"""
        from decimal import Decimal, InvalidOperation
        try:
            return Decimal(str(value)).quantize(Decimal('0.00'))
        except (TypeError, InvalidOperation):
            return Decimal('0.00')



    def get_material_by_id(self, material_id):
        try:
            sql = """
            SELECT material_id, item_name, quantity, unit_price, amount, project_id
            FROM materials
            WHERE material_id = %s
            """
            self.cursor.execute(sql, (material_id,))
            material = self.cursor.fetchone()
            if material:
                print(f"Material found: {material}")  # Debugging log
                return material  # Return the material directly
            else:
                print(f"No material found with ID: {material_id}")  # Debugging log
                return None  # Return None if no material is found
        except Exception as e:
            print(f"Error in get_material_by_id: {e}")
            return None  # Return None on error

    def get_used_amount_for_project(self, project_id):
        try:
            sql = "SELECT SUM(amount) FROM materials WHERE project_id = %s"
            self.cursor.execute(sql, (project_id,))
            return self.safe_decimal(self.cursor.fetchone()[0] or 0)
        except Exception as e:
            return 0
    

    def get_project_budget_status(self, project_id):
        try:
            sql = """
            SELECT 
                total_budget,
                material_budget,
                wages_budget,
                other_expenses_budget,
                used_budget,
                remaining_budget
            FROM projects 
            WHERE project_id = %s
            """
            self.cursor.execute(sql, (project_id,))
            result = self.cursor.fetchone()
            
            if result:
                return {
                    "success": True,
                    "total_budget": float(result['total_budget']),
                    "material_budget": float(result['material_budget']),
                    "wages_budget": float(result['wages_budget']),
                    "other_expenses_budget": float(result['other_expenses_budget']),
                    "used_budget": float(result['used_budget']),
                    "remaining_budget": float(result['remaining_budget'])
                }
            return {"success": False, "message": "Project not found"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # def get_project_budget(self, project_id):
    #     try:
    #         sql = "SELECT total_budget, project_budget FROM projects WHERE project_id = %s"
    #         self.cursor.execute(sql, (project_id,))
    #         return self.cursor.fetchone()
    #     except Exception as e:
    #         return (0, 0)

    def get_materials_for_site_engineer(self, site_engineer_id):
        """Fetch all materials for projects assigned to the given site engineer, including who registered them."""
        try:
            self.connection.commit()  # Ensure fresh data is read
            query = """
                SELECT 
                    m.material_id, 
                    m.item_name, 
                    m.quantity, 
                    m.unit_price, 
                    m.amount, 
                    COALESCE(se.full_name, NULL) AS site_engineer_name,
                    COALESCE(a.full_name, NULL) AS admin_name,
                    COALESCE(p.name, 'Not Assigned') AS project, 
                    m.created_at,
                    m.project_id,
                    m.site_engineer_id,
                    m.admin_id,
                    CASE 
                        WHEN EXISTS (SELECT 1 FROM payments WHERE material_id = m.material_id AND payment_status = 'Paid') 
                        THEN TRUE 
                        ELSE m.is_paid 
                    END AS is_paid
                FROM materials m
                LEFT JOIN projects p ON m.project_id = p.project_id
                LEFT JOIN site_engineer se ON m.site_engineer_id = se.site_engineer_id
                LEFT JOIN admin a ON m.admin_id = a.admin_id
                WHERE m.project_id IN (
                    SELECT project_id FROM projects WHERE site_engineer_id = %s
                )
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching materials: {e}")
            return []


    def update_materials(self, material_id, item_name, quantity, unit_price, amount, project_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            # 1. Get old material data with FOR UPDATE lock
            sql_old = """
            SELECT amount, project_id AS old_project_id 
            FROM materials 
            WHERE material_id = %s
            FOR UPDATE
            """
            self.cursor.execute(sql_old, (material_id,))
            old_data = self.cursor.fetchone()

            if not old_data:
                self.connection.rollback()
                return False, "Material not found"

            old_amount = float(old_data['amount'])
            old_project_id = old_data['old_project_id']
            amount_change = float(amount) - old_amount

            # 2. Update the material record
            sql_update = """
            UPDATE materials 
            SET item_name = %s, 
                quantity = %s, 
                unit_price = %s, 
                amount = %s, 
                project_id = %s
            WHERE material_id = %s
            """
            self.cursor.execute(sql_update, (
                item_name, quantity, unit_price, amount, project_id, material_id
            ))

            # 3. Handle budget updates for all scenarios
            if old_project_id != project_id:
                # Case 1: Project changed - update both projects
                # Reverse old project
                self.cursor.execute("""
                    UPDATE projects 
                    SET material_budget = material_budget + %s,
                        used_budget = used_budget - %s,
                        remaining_budget = total_budget - (used_budget - %s)
                    WHERE project_id = %s
                """, (old_amount, old_amount, old_amount, old_project_id))

                # Apply to new project
                self.cursor.execute("""
                    UPDATE projects 
                    SET material_budget = material_budget - %s,
                        used_budget = used_budget + %s,
                        remaining_budget = total_budget - (used_budget + %s)
                    WHERE project_id = %s
                """, (amount, amount, amount, project_id))
            else:
                # Case 2: Same project, amount changed
                self.cursor.execute("""
                    UPDATE projects 
                    SET material_budget = material_budget - %s,
                        used_budget = used_budget + %s,
                        remaining_budget = total_budget - (used_budget + %s)
                    WHERE project_id = %s
                """, (amount_change, amount_change, amount_change, project_id))

            self.connection.commit()
            return True, "Material updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error: {e}")
            return False, str(e)

    def get_used_amount_for_project(self, project_id):
        try:
            # Save current transaction state
            had_transaction = self.connection.in_transaction
            
            if had_transaction:
                # Commit any pending operations before our read
                self.connection.commit()

            sql = "SELECT COALESCE(SUM(amount), 0) FROM materials WHERE project_id = %s"
            self.cursor.execute(sql, (project_id,))
            result = self.cursor.fetchone()
            
            # Restore transaction state if needed
            if had_transaction:
                self.connection.start_transaction()
                
            return float(result[0]) if result else 0.0
            
        except Exception as e:
            print(f"Error calculating used amount: {str(e)}")
            return None

    
    def get_project_material_budget(self, project_id):
        try:
            print(f"Debug: Fetching budget for project {project_id}")
            
            if not project_id:
                return {"success": False, "message": "Project ID is required"}
            
            # First check if project exists
            sql_check = "SELECT 1 FROM projects WHERE project_id = %s"
            self.cursor.execute(sql_check, (project_id,))
            if not self.cursor.fetchone():
                return {"success": False, "message": "Project not found"}
            
            # Get budget data
            sql = """
            SELECT 
                COALESCE(total_budget, 0) as total_budget,
                COALESCE(used_budget, 0) as used_budget
            FROM projects 
            WHERE project_id = %s
            """
            self.cursor.execute(sql, (project_id,))
            result = self.cursor.fetchone()
            
            if not result:
                return {"success": False, "message": "No budget data found"}
                
            return {
                "success": True,
                "budget": float(result[0]),
                "used_budget": float(result[1])
            }
            
        except Exception as e:
            error_msg = f"Database error: {str(e)}"
            print(error_msg)
            return {"success": False, "message": error_msg}


    def delete_materials(self, material_id):
        try:
            print(f"Executing delete for material ID: {material_id}")  # Debug log
            sql = "DELETE FROM materials WHERE material_id = %s"
            self.cursor.execute(sql, (material_id,))
            affected_rows = self.cursor.rowcount  # Check how many rows were affected
            self.connection.commit()
            
            if affected_rows == 0:
                return False, "No material found with that ID"
                
            return True, "Material deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Database error: {str(e)}")  # Debug log
            return False, f"Database Error: {str(e)}"
    


    # Example of a method to fetch all materials for a specific project
    # Add these methods to your UserModel class

    def register_expenses(self, item_name, amount, description, expense_type, site_engineer_id, project_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            # Insert expense with site_engineer_id and clear admin_id
            sql_insert = """
            INSERT INTO expenses 
            (item_name, amount, description, expense_type, site_engineer_id, admin_id, project_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NULL, %s, NOW())
            """
            self.cursor.execute(sql_insert, (
                item_name,
                self.safe_decimal(amount),
                description,
                expense_type,
                site_engineer_id,
                project_id
            ))


            # Determine which budget column to update
            budget_column = {
                'material': 'material_budget',
                'wages': 'wages_budget',
                'other': 'other_expenses_budget'
            }.get(expense_type, None)

            if not budget_column:
                self.connection.rollback()
                return False, "Invalid expense type."

            # Update all project budget fields
            sql_update = f"""
            UPDATE projects 
            SET {budget_column} = {budget_column} - %s,
                used_budget = used_budget + %s,
                remaining_budget = total_budget - (used_budget + %s)
            WHERE project_id = %s
            """
            self.cursor.execute(sql_update, (
                self.safe_decimal(amount),
                self.safe_decimal(amount),
                self.safe_decimal(amount),
                project_id
            ))

            self.connection.commit()
            return True, "Expense registered successfully!"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in register_expenses: {e}")
            return False, str(e)


    def get_expense_by_id(self, expense_id):
        try:
            sql = """
            SELECT expense_id, item_name, amount, description, expense_type, project_id
            FROM expenses
            WHERE expense_id = %s
            """
            self.cursor.execute(sql, (expense_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error: {e}")
            return None

    def update_expenses(self, expense_id, item_name, amount, description, expense_type, project_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            # When site engineer updates, set site_engineer_id, clear admin_id
            sql_update = """
            UPDATE expenses 
            SET item_name = %s, 
                amount = %s, 
                description = %s, 
                expense_type = %s, 
                project_id = %s,
                site_engineer_id = %s,
                admin_id = NULL
            WHERE expense_id = %s
            """
            # Get site_engineer_id from session
            from flask import session
            site_engineer_id = session.get('site_engineer_id')
            self.cursor.execute(sql_update, (
                item_name,
                amount,
                description,
                expense_type,
                project_id,
                site_engineer_id,
                expense_id
            ))
            self.connection.commit()
            return True, "Expense updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_expense: {e}")
            return False, str(e)

    def get_all_expenses_dict(self, site_engineer_id):
        """
        Fetch all expenses for the site engineer's assigned projects
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
                se.site_engineer_id,
                a.full_name AS admin_name,
                a.admin_id,
                e.expense_type,
                e.created_at,
                CASE 
                    WHEN EXISTS (SELECT 1 FROM payments WHERE expense_id = e.expense_id AND payment_status = 'Paid') 
                    THEN TRUE 
                    ELSE e.is_paid 
                END AS is_paid
            FROM expenses e
            LEFT JOIN projects p ON e.project_id = p.project_id
            LEFT JOIN site_engineer se ON e.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin a ON e.admin_id = a.admin_id
            WHERE e.project_id IN (
                SELECT project_id FROM projects WHERE site_engineer_id = %s
            )
            ORDER BY e.created_at DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql, (site_engineer_id,))
            expenses = dict_cursor.fetchall()
            dict_cursor.close()
            return True, expenses
        except Exception as e:
            print(f"Error fetching expenses: {e}")
            return False, f"Error: {e}"
    
    def delete_expenses(self, expense_id):
        """Delete an expense record by its ID."""
        try:
            sql = "DELETE FROM expenses WHERE expense_id = %s"
            self.cursor.execute(sql, (expense_id,))
            affected_rows = self.cursor.rowcount
            self.connection.commit()
            if affected_rows == 0:
                return False, "No expense found with that ID"
            return True, "Expense deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Database error in delete_expenses: {str(e)}")
            return False, f"Database Error: {str(e)}"

    # site_engineer_assigned_labour


    def get_site_engineer_assigned_labour(self, site_engineer_id):
        """Fetch labours assigned to the same projects as the site engineer."""
        try:
            query = """
                SELECT DISTINCT l.labour_id, l.full_name,l.created_at, l.email, l.type_of_work, p.project_id, p.name as project_name
                FROM labour_project lp
                JOIN labour l ON lp.labour_id = l.labour_id
                JOIN projects p ON lp.project_id = p.project_id
                WHERE p.project_id IN (
                    SELECT project_id 
                    FROM projects 
                    WHERE site_engineer_id = %s
                )
                ORDER BY p.name, l.full_name
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching labours assigned to projects: {e}")
            return []

# attendance section start
    def register_siteEngineer_attendance(self, labour_id, project_id, date, status, site_engineer_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            # Insert attendance record
            sql_insert = """
            INSERT INTO attendance 
            (labour_id, project_id, date, status, site_engineer_id, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """
            self.cursor.execute(sql_insert, (
                labour_id,
                project_id,
                date,
                status,
                site_engineer_id
            ))

            # Commit immediately to make changes visible
            self.connection.commit()
            return True, "Attendance registered successfully!"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in register_attendance: {e}")
            return False, str(e)

    def check_existing_attendance(self, labour_id, date):
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

    def check_labour_project_assignment(self, labour_id, project_id):
        """Verify if a labour is assigned to a specific project."""
        try:
            sql = """
            SELECT 1 
            FROM labour_project 
            WHERE labour_id = %s AND project_id = %s
            LIMIT 1
            """
            self.cursor.execute(sql, (labour_id, project_id))
            return self.cursor.fetchone() is not None
        except Exception as e:
            print(f"Error in check_labour_project_assignment: {e}")
            return False

    def get_siteEngineer_attendance_by_id(self, attendance_id):
        try:
            sql = """
            SELECT attendance_id, labour_id, project_id, date, status
            FROM attendance
            WHERE attendance_id = %s
            """
            self.cursor.execute(sql, (attendance_id,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error: {e}")
            return None

    def update_siteEngineer_attendance(self, attendance_id, labour_id, project_id, date, status):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            sql_update = """
            UPDATE attendance 
            SET labour_id = %s, 
                project_id = %s, 
                date = %s, 
                status = %s
            WHERE attendance_id = %s
            """
            self.cursor.execute(sql_update, (
                labour_id,
                project_id,
                date,
                status,
                attendance_id
            ))

            self.connection.commit()  # Ensure changes are visible to other sessions
            return True, "Attendance updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_attendance: {e}")
            return False, str(e)

    def delete_siteEngineer_attendance(self, attendance_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()
            
            sql_delete = "DELETE FROM attendance WHERE attendance_id = %s"
            self.cursor.execute(sql_delete, (attendance_id,))
            
            self.connection.commit()  # Ensure changes are visible to other sessions
            return True, "Attendance deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error: {e}")
            return False, str(e)

    def get_attendance_by_site_engineer(self, site_engineer_id):
        try:
            self.connection.commit()  # Ensure latest data is visible to all
            query = """
            SELECT 
                a.attendance_id,
                l.full_name,
                p.name AS project_name,
                a.date,
                a.status,
                se.full_name AS site_engineer_name,
                a.created_at,
                a.labour_id,
                a.project_id
            FROM attendance a
            JOIN labour l ON a.labour_id = l.labour_id
            JOIN projects p ON a.project_id = p.project_id
            JOIN site_engineer se ON a.site_engineer_id = se.site_engineer_id
            WHERE a.site_engineer_id = %s
            ORDER BY a.date DESC, a.created_at DESC
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            return []

    def get_all_attendance_for_site_engineer_projects(self, site_engineer_id):
        """
        Fetch all attendance records for all projects assigned to this site engineer,
        including those registered by admin or site engineer.
        """
        try:
            self.connection.commit()  # Ensure latest data is visible
            query = """
            SELECT 
                a.attendance_id,
                l.full_name,
                p.name AS project_name,
                a.date,
                a.status,
                se.full_name AS site_engineer_name,
                ad.full_name AS admin_name,
                a.created_at,
                a.labour_id,
                a.project_id
            FROM attendance a
            JOIN labour l ON a.labour_id = l.labour_id
            JOIN projects p ON a.project_id = p.project_id
            LEFT JOIN site_engineer se ON a.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin ad ON a.admin_id = ad.admin_id
            WHERE a.project_id IN (
                SELECT project_id FROM projects WHERE site_engineer_id = %s
            )
            ORDER BY a.date DESC, a.created_at DESC
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching all attendance for site engineer projects: {e}")
            return []
    
    # site_engineer_profile section start

    def get_site_engineer_profile(self, site_engineer_id):
        """Fetch profile details of the site engineer."""
        try:
            sql = """
            SELECT profile_picture, profile_picture_filename
            FROM site_engineer
            WHERE site_engineer_id = %s
            """
            self.cursor.execute(sql, (site_engineer_id,))
            result = self.cursor.fetchone()
            return result if result else {}
        except Exception as e:
            print(f"Error fetching site engineer profile: {e}")
            return {}


    def update_site_engineer_profile_picture(self, site_engineer_id, file_data, filename):
        """Update the profile picture of the site engineer without resizing."""
        try:
            sql = """
            UPDATE site_engineer
            SET profile_picture = %s, profile_picture_filename = %s
            WHERE site_engineer_id = %s
            """
            self.cursor.execute(sql, (file_data, filename, site_engineer_id))
            self.connection.commit()
            return True, "Profile picture updated successfully."
        except Exception as e:
            print(f"Error updating profile picture: {e}")
            self.connection.rollback()
            return False, str(e)
    
    # wages section start
    def register_wage(self, labour_id, project_id, daily_rate, total_days, total_wage, site_engineer_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            # Check if there are unpaid attendance records for this labour in this project
            sql_check_unpaid_attendance = """
            SELECT COUNT(*) AS unpaid_count
            FROM attendance
            WHERE labour_id = %s AND project_id = %s AND status = 'Present' AND is_paid = FALSE
            """
            self.cursor.execute(sql_check_unpaid_attendance, (labour_id, project_id))
            unpaid_count = self.cursor.fetchone()['unpaid_count']

            if unpaid_count == 0:
                self.connection.rollback()
                return False, "No unpaid attendance records found for this labour in this project."

            # Insert wage record (admin_id is NULL)
            sql_insert = """
            INSERT INTO wages 
            (labour_id, project_id, daily_rate, total_days, total_wage, site_engineer_id, admin_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NULL, NOW())
            """
            self.cursor.execute(sql_insert, (
                labour_id,
                project_id,
                daily_rate,
                total_days,
                total_wage,
                site_engineer_id
            ))

            # Update attendance records to mark them as "Paid"
            sql_update_attendance = """
            UPDATE attendance 
            SET is_paid = TRUE
            WHERE labour_id = %s AND project_id = %s AND status = 'Present' AND is_paid = FALSE
            """
            self.cursor.execute(sql_update_attendance, (labour_id, project_id))

            # Update project's wages_budget, used_budget, and remaining_budget
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
            print(f"Error in register_wage: {e}")
            return False, str(e)

    def get_wages_by_site_engineer(self, site_engineer_id):
        """
        Fetch all wage records for projects assigned to this site engineer,
        including those registered by admin or by the site engineer.
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
                w.is_paid
            FROM wages w
            JOIN labour l ON w.labour_id = l.labour_id
            JOIN projects p ON w.project_id = p.project_id
            LEFT JOIN admin a ON w.admin_id = a.admin_id
            LEFT JOIN site_engineer se ON w.site_engineer_id = se.site_engineer_id
            WHERE w.project_id IN (
                SELECT project_id FROM projects WHERE site_engineer_id = %s
            )
            ORDER BY w.created_at DESC
            """
            dict_cursor = self.connection.cursor(dictionary=True)
            dict_cursor.execute(sql, (site_engineer_id,))
            return dict_cursor.fetchall()
        except Exception as e:
            print(f"Error: {e}")
            return []

    def get_wage_by_id(self, wage_id):
        try:
            sql = """
            SELECT wage_id, labour_id, project_id, daily_rate, total_days, total_wage, site_engineer_id, admin_id
            FROM wages
            WHERE wage_id = %s
            """
            self.cursor.execute(sql, (wage_id,))
            row = self.cursor.fetchone()
            if row:
                # Return as dict for easy population in update modal
                return {
                    "wage_id": row["wage_id"],
                    "labour_id": row["labour_id"],
                    "project_id": row["project_id"],
                    "daily_rate": row["daily_rate"],
                    "total_days": row["total_days"],
                    "total_wage": row["total_wage"],
                    "site_engineer_id": row.get("site_engineer_id"),
                    "admin_id": row.get("admin_id"),
                }
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
        
    def update_siteEngineer_wage(self, wage_id, labour_id, project_id, daily_rate, total_days, total_wage, site_engineer_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            # Verify the wage belongs to this site engineer's project
            sql_check = """
            SELECT 1 FROM wages w
            JOIN projects p ON w.project_id = p.project_id
            WHERE w.wage_id = %s AND p.site_engineer_id = %s
            """
            self.cursor.execute(sql_check, (wage_id, site_engineer_id))
            if not self.cursor.fetchone():
                return False, "You can only update wages for your assigned projects"

            # Verify the labour is assigned to the project
            sql_check_labour = """
            SELECT 1 FROM labour_project
            WHERE project_id = %s AND labour_id = %s
            """
            self.cursor.execute(sql_check_labour, (project_id, labour_id))
            if not self.cursor.fetchone():
                return False, "This labour is not assigned to the selected project"

            # Get original wage values for budget adjustment
            original_wage = self.get_wage_by_id(wage_id)
            if not original_wage:
                return False, "Wage record not found"

            # Calculate budget difference (ensure both are float)
            budget_diff = float(total_wage) - float(original_wage['total_wage'])

            # Update the wage record
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

            # Update project budgets if wage amount changed
            if budget_diff != 0:
                sql_update_project = """
                UPDATE projects 
                SET 
                    wages_budget = wages_budget - %s,
                    used_budget = used_budget + %s,
                    remaining_budget = total_budget - (used_budget + %s)
                WHERE project_id = %s
                """
                self.cursor.execute(sql_update_project, (
                    budget_diff, budget_diff, budget_diff, project_id
                ))

            self.connection.commit()
            return True, "Wage updated successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in update_siteEngineer_wage: {e}")
            return False, str(e)
        
    def delete_siteEngineer_wage(self, wage_id, site_engineer_id):
        try:
            self.ensure_no_active_transaction()
            self.connection.start_transaction()

            # Explicitly commit any pending transactions before starting
            self.connection.commit()
            
            # Only allow delete if the wage is for a project assigned to this site engineer
            self.cursor.execute(
                """
                SELECT w.project_id FROM wages w
                JOIN projects p ON w.project_id = p.project_id
                WHERE w.wage_id = %s AND p.site_engineer_id = %s
                """, (wage_id, site_engineer_id)
            )
            if not self.cursor.fetchone():
                self.connection.rollback()
                return False, "You can only delete wages for your assigned projects."
            
            sql_delete = "DELETE FROM wages WHERE wage_id = %s"
            self.cursor.execute(sql_delete, (wage_id,))
            self.connection.commit()  # Explicit commit
            return True, "Wage deleted successfully"
        except Exception as e:
            self.connection.rollback()
            print(f"Error in delete_siteEngineer_wage: {e}")
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
            SELECT COUNT(*) AS unpaid_present_days
            FROM attendance
            WHERE labour_id = %s 
            AND project_id = %s
            AND status = 'Present'
            AND is_paid = FALSE
            """
            self.cursor.execute(sql, (labour_id, project_id))
            result = self.cursor.fetchone()
            return result['unpaid_present_days'] if result else 0
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
        
        # report
    def get_projects_by_engineer(self, site_engineer_id):
        try:
            query = """
                SELECT project_id, name 
                FROM projects 
                WHERE site_engineer_id = %s
                ORDER BY name
            """
            self.cursor.execute(query, (site_engineer_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching projects by engineer: {e}")
            return []

    def get_filtered_expenses(self, site_engineer_id, start_date, end_date, project_id='all'):
        try:
            query = """
                SELECT e.expense_id, e.item_name AS name, e.amount, e.description AS expense_type, 
                    e.created_at, p.name AS project
                FROM expenses e
                LEFT JOIN projects p ON e.project_id = p.project_id
                WHERE e.site_engineer_id = %s AND e.created_at BETWEEN %s AND %s
                {project_condition}
                ORDER BY e.created_at DESC
            """
            
            params = [site_engineer_id, start_date, end_date]
            
            if project_id and project_id != 'all':
                query = query.format(project_condition="AND e.project_id = %s")
                params.append(project_id)
            else:
                query = query.format(project_condition="")
                
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching filtered expenses: {e}")
            return []

    def get_filtered_wages(self, site_engineer_id, start_date, end_date, project_id='all'):
        try:
            query = """
                SELECT w.wage_id, l.full_name AS name, w.total_wage AS amount, 
                    w.created_at, p.name AS project, 'Wages' AS expense_type
                FROM wages w
                LEFT JOIN labour l ON w.labour_id = l.labour_id
                LEFT JOIN projects p ON w.project_id = p.project_id
                WHERE w.site_engineer_id = %s AND w.created_at BETWEEN %s AND %s
                {project_condition}
                ORDER BY w.created_at DESC
            """
            
            params = [site_engineer_id, start_date, end_date]
            
            if project_id and project_id != 'all':
                query = query.format(project_condition="AND w.project_id = %s")
                params.append(project_id)
            else:
                query = query.format(project_condition="")
                
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching filtered wages: {e}")
            return []

    def get_filtered_materials(self, site_engineer_id, start_date, end_date, project_id='all'):
        try:
            query = """
                SELECT m.material_id, m.item_name AS name, m.amount, 'Materials' AS expense_type,
                    m.created_at, p.name AS project
                FROM materials m
                LEFT JOIN projects p ON m.project_id = p.project_id
                WHERE m.site_engineer_id = %s AND m.created_at BETWEEN %s AND %s
                {project_condition}
                ORDER BY m.created_at DESC
            """
            
            params = [site_engineer_id, start_date, end_date]
            
            if project_id and project_id != 'all':
                query = query.format(project_condition="AND m.project_id = %s")
                params.append(project_id)
            else:
                query = query.format(project_condition="")
                
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching filtered materials: {e}")
            return []

    def get_budget_burn_rate(self, site_engineer_id, start_date, end_date, project_id='all'):
        try:
            query = """
                SELECT p.project_id, p.name AS project, p.used_budget AS amount, 
                    p.start_date AS created_at, 'Budget' AS expense_type
                FROM projects p
                WHERE p.site_engineer_id = %s AND p.start_date <= %s AND (p.end_date >= %s OR p.end_date IS NULL)
                {project_condition}
                ORDER BY p.start_date DESC
            """
            
            params = [site_engineer_id, end_date, start_date]
            
            if project_id and project_id != 'all':
                query = query.format(project_condition="AND p.project_id = %s")
                params.append(project_id)
            else:
                query = query.format(project_condition="")
                
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching budget burn rate: {e}")
            return []

    def get_attendance_for_site_engineer_view(self, site_engineer_id):
        """
        Fetch attendance for all projects assigned to this site engineer,
        but only if registered by this engineer or by admin (not by other engineers).
        """
        try:
            self.connection.commit()
            query = """
            SELECT 
                a.attendance_id,
                l.full_name,
                p.name AS project_name,
                a.date,
                a.status,
                se.full_name AS site_engineer_name,
                ad.full_name AS admin_name,
                a.created_at,
                a.labour_id,
                a.project_id,
                a.site_engineer_id,
                a.admin_id
            FROM attendance a
            JOIN labour l ON a.labour_id = l.labour_id
            JOIN projects p ON a.project_id = p.project_id
            LEFT JOIN site_engineer se ON a.site_engineer_id = se.site_engineer_id
            LEFT JOIN admin ad ON a.admin_id = ad.admin_id
            WHERE a.project_id IN (
                SELECT project_id FROM projects WHERE site_engineer_id = %s
            )
            AND (
                a.site_engineer_id = %s OR a.admin_id IS NOT NULL
            )
            ORDER BY a.date DESC, a.created_at DESC
            """
            self.cursor.execute(query, (site_engineer_id, site_engineer_id))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching attendance for site engineer view: {e}")
            return []


   
def get_user_model():
    try:
        db_config = UserDbConnection()
        user_db = UserDatabase(
            host=db_config.DB_HOSTNAME,
            port=3300,
            user=db_config.DB_USERNAME,
            password=db_config.DB_PASSWORD,
            database=db_config.DB_NAME,
        )
        user_db.make_connection()
        return True, UserModel(user_db.connection)
    except Exception as e:
        print(f"Error: {e}")
        return False, f"Error: {e}"
