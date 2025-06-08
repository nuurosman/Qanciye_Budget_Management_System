import mysql.connector
from App.configuration import LabourDbConnetion
import decimal
import traceback
import json


class Labour_UserDatabase:
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


class User_labour_Model:
    """Model for managing labour-related data."""
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
            if self.connection.in_transaction:
                self.connection.rollback()
                print("Rolled back an active transaction.")
        except Exception as e:
            print(f"Error ensuring no active transaction: {e}")

    def get_assigned_site_engineer(self, labour_id):
        """Get the site_engineer assigned to this labour"""
        try:

            query = """
                SELECT se.full_name 
                FROM site_engineer se
                JOIN labour_project la ON se.site_engineer_id = la.site_engineer_id
                WHERE la.labour_id = %s
            """
            self.cursor.execute(query, (labour_id,))
            result = self.cursor.fetchone()
            return result['full_name'] if result else None
        except Exception as e:
            print(f"Error fetching site engineer: {e}")
            return None

    def get_my_projects(self, labour_id):
        """Fetch projects this labour is assigned to"""
        try:
            query = """
                SELECT p.*, se.full_name AS site_engineer_name
                FROM projects p
                JOIN labour_project pla ON p.project_id = pla.project_id
                LEFT JOIN site_engineer se ON p.site_engineer_id = se.site_engineer_id
                WHERE pla.labour_id = %s
            """
            self.cursor.execute(query, (labour_id,))
            projects = self.cursor.fetchall()
            # Debug print to verify fetched projects
            # print(f"Fetched projects for labour_id={labour_id}: {projects}")
            return projects
        except Exception as e:
            print(f"Error fetching labour's projects: {e}")
            return []
    
    def get_attendance_stats(self, labour_id, project_id=None):
        """Get attendance stats for all/specific projects"""
        try:
            query = """
                SELECT 
                    p.project_id,
                    p.name AS project_name,
                    COALESCE(SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END), 0) AS present_days,
                    COALESCE(SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END), 0) AS absent_days
                FROM projects p
                JOIN labour_project lp ON p.project_id = lp.project_id
                LEFT JOIN attendance a ON p.project_id = a.project_id AND a.labour_id = %s
                WHERE lp.labour_id = %s
            """
            params = [labour_id, labour_id]
            if project_id:
                query += " AND p.project_id = %s"
                params.append(project_id)
            query += " GROUP BY p.project_id, p.name"
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching attendance stats: {e}")
            return []

    def get_wage_stats(self, labour_id, project_id=None):
        """Get wage stats for all/specific projects"""
        try:
            query = """
                SELECT 
                    p.project_id,
                    p.name AS project_name,
                    COALESCE(w.daily_rate, 0) AS daily_rate,
                    COALESCE(w.total_days, 0) AS total_days,
                    COALESCE(w.total_wage, 0) AS total_wage
                FROM projects p
                JOIN labour_project lp ON p.project_id = lp.project_id
                LEFT JOIN wages w ON w.project_id = p.project_id AND w.labour_id = %s
                WHERE lp.labour_id = %s
            """
            params = [labour_id, labour_id]
            if project_id:
                query += " AND p.project_id = %s"
                params.append(project_id)
            query += " GROUP BY p.project_id, p.name, w.daily_rate, w.total_days, w.total_wage"
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error fetching wage stats: {e}")
            return []
    


    def get_labour_profile(self, labour_id):
        """Fetch profile details of the labour."""
        try:
            sql = """
            SELECT profile_picture, profile_picture_filename
            FROM labour
            WHERE labour_id = %s
            """
            self.cursor.execute(sql, (labour_id,))
            result = self.cursor.fetchone()
            return result if result else {}
        except Exception as e:
            print(f"Error fetching labour profile: {e}")
            return {}

    def update_labour_profile_picture(self, labour_id, file_data, filename):
        """Update the profile picture of the labour."""
        try:
            sql = """
            UPDATE labour
            SET profile_picture = %s, profile_picture_filename = %s
            WHERE labour_id = %s
            """
            self.cursor.execute(sql, (file_data, filename, labour_id))
            self.connection.commit()
            return True, "Profile picture updated successfully."
        except Exception as e:
            print(f"Error updating labour profile picture: {e}")
            self.connection.rollback()
            return False, str(e)

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
        """Update the profile picture of the site engineer."""
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
            print(f"Error updating site engineer profile picture: {e}")
            self.connection.rollback()
            return False, str(e)

    def get_admin_profile(self, admin_id):
        """Fetch profile details of the admin."""
        try:
            sql = """
            SELECT profile_picture, profile_picture_filename
            FROM admin
            WHERE admin_id = %s
            """
            self.cursor.execute(sql, (admin_id,))
            result = self.cursor.fetchone()
            return result if result else {}
        except Exception as e:
            print(f"Error fetching admin profile: {e}")
            return {}

    def update_admin_profile_picture(self, admin_id, file_data, filename):
        """Update the profile picture of the admin."""
        try:
            sql = """
            UPDATE admin
            SET profile_picture = %s, profile_picture_filename = %s
            WHERE admin_id = %s
            """
            self.cursor.execute(sql, (file_data, filename, admin_id))
            self.connection.commit()
            return True, "Profile picture updated successfully."
        except Exception as e:
            print(f"Error updating admin profile picture: {e}")
            self.connection.rollback()
            return False, str(e)

def get_labour_model():
    try:
        db_config = LabourDbConnetion()
        user_db = Labour_UserDatabase(
            host=db_config.DB_HOSTNAME,
            port=3300,
            user=db_config.DB_USERNAME,
            password=db_config.DB_PASSWORD,
            database=db_config.DB_NAME,
        )
        user_db.make_connection()
        return True, User_labour_Model(user_db.connection)
    except Exception as e:
        print(f"Error: {e}")
        return False, f"Error: {e}"


