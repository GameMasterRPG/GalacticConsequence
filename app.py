import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-abracadabra")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure JWT
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-abracadabra")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # Tokens don't expire for persistent sessions
jwt = JWTManager(app)

# Configure CORS
CORS(app)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///galaxy_of_consequence.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize extensions
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    
    # Create all database tables
    db.create_all()
    
    # Initialize default data
    from services.faction_ai import initialize_default_factions
    initialize_default_factions()

# Register blueprints
from routes.auth import auth_bp
from routes.canvas import canvas_bp
from routes.nemotron import nemotron_bp
from routes.faction import faction_bp
from routes.quest import quest_bp
from routes.session import session_bp
from routes.force import force_bp
from routes.api_docs import docs_bp

app.register_blueprint(auth_bp)
app.register_blueprint(canvas_bp)
app.register_blueprint(nemotron_bp)
app.register_blueprint(faction_bp)
app.register_blueprint(quest_bp)
app.register_blueprint(session_bp)
app.register_blueprint(force_bp)
app.register_blueprint(docs_bp)

@app.route('/')
def index():
    return {
        "message": "Galaxy of Consequence RPG Backend",
        "version": "1.0.0",
        "documentation": "/docs",
        "openapi_schema": "/openapi.yaml",
        "status": "operational"
    }

@app.route('/health')
def health_check():
    return {"status": "healthy", "database": "connected"}
