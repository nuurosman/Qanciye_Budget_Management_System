from flask import Flask
# Build your app

app = Flask(__name__)
app.secret_key = 'secret'

# Isbaris applicatoin-kaaga
from App.public import  public_view
# User view
from App.site_engineer import siteEngineerView
# User model
from App.site_engineer import SiteEngineerModel
#admin view
from  App.admin import admin_view
#admin model
# from App.admin import admin_model  # REMOVE or COMMENT OUT this line
# Configuration
from App import configuration
from App.Labour import LabourModal
from App.Labour import LabourView  # Ensure this import is present
# from App.admin import routes
  # This line ensures routes are registered
from App.admin import email_utils
print("LabourView module imported successfully.")  # Debug statement
