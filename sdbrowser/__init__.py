import os
from flask import Flask, render_template, request
from SPARQLWrapper import SPARQLWrapper, JSON
from . import parse

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
    
    @app.route('/iframeDiv/<title>/<name>')
    def graphFrame(title, name):
        return render_template('iframeDiv.html', frameTitle=title, divName=name)
        
    @app.route('/iframeTest')
    def iframeTest():
        return render_template('iframeTest.html')
    
    @app.route('/parsetest')
    def parseTest():
        return render_template('parseTest.html')
        
    @app.route('/graphView')
    def graphView():
        return render_template('graphView.html')
        
    @app.route('/client')
    def client():
        return render_template('client.html')
        
    @app.route('/query', methods = ('GET', 'POST'))
    def query():
        if request.method == 'POST':
            q = request.form['query']
            endpoint = request.form['endpoint']
            wrapper = SPARQLWrapper(endpoint)
            wrapper.setQuery(q)
            wrapper.setReturnFormat(JSON)
            results = wrapper.query().convert()
            return results
            
    
    return app