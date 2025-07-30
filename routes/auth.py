from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

auth_bp = Blueprint('auth', __name__)

# The magical Bearer token that grants access
MAGIC_TOKEN = "Abracadabra"

@auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    """
    Authenticate with the magical Bearer token
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing Bearer token'}), 401
    
    token = auth_header.split('Bearer ')[1].strip()
    
    if token != MAGIC_TOKEN:
        return jsonify({'error': 'Invalid Bearer token'}), 401
    
    # Create JWT token for subsequent requests
    access_token = create_access_token(identity='galaxy_user')
    
    return jsonify({
        'access_token': access_token,
        'message': 'Authentication successful',
        'galaxy_status': 'Access granted to the Galaxy of Consequence'
    })

@auth_bp.route('/verify', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify JWT token is valid
    """
    current_user = get_jwt_identity()
    return jsonify({
        'user': current_user,
        'status': 'authenticated',
        'message': 'Token is valid'
    })

def check_bearer_auth():
    """
    Helper function to check Bearer token in requests
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split('Bearer ')[1].strip()
    return token == MAGIC_TOKEN
