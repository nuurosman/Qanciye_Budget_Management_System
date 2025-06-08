from App import app
if __name__ =='__main__':
    app.run(host='localhost', port=2002, debug=True)


# This prints all registered routes



def list_routes(app):
    print("\n🔍 Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        print(f"{rule.endpoint:30s} => {rule.rule} [{methods}]")

# If app is already created:
list_routes(app)  # This will print all registered routes
