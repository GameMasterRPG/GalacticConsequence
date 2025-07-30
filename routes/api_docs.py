from flask import Blueprint, render_template, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
import os

docs_bp = Blueprint('docs', __name__)

# Swagger UI configuration
SWAGGER_URL = '/docs'
API_URL = '/openapi.yaml'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Galaxy of Consequence RPG API",
        'dom_id': '#swagger-ui',
        'url_prefix': SWAGGER_URL,
        'layout': 'StandaloneLayout'
    }
)

@docs_bp.route('/openapi.yaml')
def get_openapi_spec():
    """
    Serve the OpenAPI specification
    """
    return send_from_directory('.', 'openapi.yaml')

@docs_bp.route('/docs')
def swagger_ui():
    """
    Swagger UI documentation page
    """
    return render_template('swagger.html')

# Register the Swagger UI blueprint
docs_bp.register_blueprint(swaggerui_blueprint)
