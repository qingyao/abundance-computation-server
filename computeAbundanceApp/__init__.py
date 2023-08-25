from flask import Flask, render_template
from dotenv import load_dotenv
import os
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')
# app.debug = True

cors = CORS(app)#, supports_credentials=True)
cors.init_app(app, resource={r"/api/*": {"origins": "*", "expose_headers": "*"}})

@app.route('/api/')
def index():
    return render_template('index.html')
