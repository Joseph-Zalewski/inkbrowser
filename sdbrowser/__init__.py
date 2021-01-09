import os
from flask import Flask, render_template

#__init__ file for Stage 1, which is only intended to be able to
#use SPARQLWrapper successfully in some way.

#This is Flask app factory boilerplate. No value is configured to
#DATABASE (a property of <<<app>>>), because this simple application doesn't
#need to store data on the server. We don't really need the instance folder
#at all.
def create_app():
    app = Flask(__name__,instance_relative_config = True)
    app.config.from_mapping(
        SECRET_KEY = 'dev'
    )
        
    @app.route('/test')
    def hello():
        return 'Hello, World!'
        
    @app.route('/query/<q>')
    def query(q):
        return q
        
    @app.route('/interface', methods = ('GET', 'POST'))
    def interface():
        return render_template('interface.html')
            
    return app