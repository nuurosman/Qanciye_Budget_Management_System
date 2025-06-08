from App import  app

from flask import  render_template

# Route or API or URL

@app.route('/index')
def index():
    return render_template('/public/index.html')

# about page
@app.route('/about')
def about_page():
    return render_template('public/about.html')
