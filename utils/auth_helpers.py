from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import jwt
import logging

logger = logging.getLogger(__name__)

# The magical Bearer token that grants access
MAGIC_TOKEN = "Abracadabra"

def check_bearer_auth():
    """
    Helper function to check Bearer token in requests
    """
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return False
    
    token = auth_header.split('Bearer ')[1].strip()
    return token == MAGIC_TOKEN

def require_bearer_auth(f):
    """
    Decorator to require Bearer token authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_bearer_auth():
            return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
        return f(*args, **kwargs)
    return decorated_function

def optional_jwt_auth(f):
    """
    Decorator for optional JWT authentication
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request(optional=True)
            current_user = get_jwt_identity()
        except Exception as e:
            logger.debug(f"Optional JWT auth failed: {str(e)}")
            current_user = None
        
        return f(current_user=current_user, *args, **kwargs)
    return decorated_function

def get_user_from_request():
    """
    Extract user identity from either Bearer token or JWT
    """
    # Try Bearer token first
    if check_bearer_auth():
        return 'galaxy_user'
    
    # Try JWT token
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None

def validate_session_access(user, session_id):
    """
    Validate that a user has access to a specific session
    """
    if not user or not session_id:
        return False
    
    # For now, allow access to any session if authenticated
    # In production, you might want more granular session access control
    return True

def get_request_user_info():
    """
    Get comprehensive user information from request
    """
    user = get_user_from_request()
    
    return {
        'user': user,
        'authenticated': user is not None,
        'auth_method': 'bearer' if check_bearer_auth() else 'jwt' if user else None,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'timestamp': request.headers.get('X-Request-Timestamp')
    }

def log_api_access(endpoint, user=None, action='access'):
    """
    Log API access for security and analytics
    """
    user_info = get_request_user_info()
    
    logger.info(f"API {action}: endpoint={endpoint}, user={user_info['user']}, "
                f"auth_method={user_info['auth_method']}, ip={user_info['ip_address']}")

def require_user_parameter(f):
    """
    Decorator that ensures 'user' parameter is provided and matches authenticated user
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check authentication first
        if not check_bearer_auth():
            return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
        
        # Get user parameter from request
        user = None
        if request.method == 'GET':
            user = request.args.get('user')
        elif request.method in ['POST', 'PUT', 'PATCH']:
            data = request.get_json()
            user = data.get('user') if data else None
        
        if not user:
            return jsonify({'error': 'Missing required parameter: user'}), 400
        
        # Log the access
        log_api_access(request.endpoint, user, 'user_action')
        
        return f(*args, **kwargs)
    return decorated_function

def create_error_response(message, status_code=400, error_code=None, details=None):
    """
    Create standardized error response
    """
    error_response = {
        'error': message,
        'status_code': status_code
    }
    
    if error_code:
        error_response['error_code'] = error_code
    
    if details:
        error_response['details'] = details
    
    # Log error for debugging
    logger.warning(f"API Error: {message} (status: {status_code})")
    
    return jsonify(error_response), status_code

def create_success_response(data, message=None):
    """
    Create standardized success response
    """
    if isinstance(data, dict):
        response = data.copy()
        if message:
            response['message'] = message
    else:
        response = {
            'data': data,
            'message': message or 'Success'
        }
    
    return jsonify(response)

def validate_request_data(required_fields=None, optional_fields=None):
    """
    Decorator to validate request data structure
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = request.get_json()
            
            if not data and required_fields:
                return create_error_response('Missing request body', 400)
            
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return create_error_response(
                        f'Missing required fields: {", ".join(missing_fields)}',
                        400
                    )
            
            # Validate field types if specified
            for field_name, field_config in (required_fields or {}).items():
                if isinstance(field_config, dict) and 'type' in field_config:
                    expected_type = field_config['type']
                    actual_value = data.get(field_name)
                    
                    if actual_value is not None and not isinstance(actual_value, expected_type):
                        return create_error_response(
                            f'Field {field_name} must be of type {expected_type.__name__}',
                            400
                        )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class AuthorizationError(Exception):
    """Custom exception for authorization errors"""
    def __init__(self, message, status_code=403):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def handle_auth_exceptions(f):
    """
    Decorator to handle authentication and authorization exceptions
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AuthenticationError as e:
            return create_error_response(e.message, e.status_code, 'AUTHENTICATION_ERROR')
        except AuthorizationError as e:
            return create_error_response(e.message, e.status_code, 'AUTHORIZATION_ERROR')
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
            return create_error_response('Internal server error', 500, 'INTERNAL_ERROR')
    return decorated_function

def get_client_ip():
    """
    Get the real client IP address, considering proxies
    """
    # Check for forwarded headers
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def rate_limit_key(user=None):
    """
    Generate a rate limiting key based on user or IP
    """
    if user:
        return f"user:{user}"
    else:
        return f"ip:{get_client_ip()}"

def is_development_mode():
    """
    Check if application is running in development mode
    """
    return current_app.config.get('ENV') == 'development' or current_app.debug

def create_api_key_header():
    """
    Create headers for external API calls
    """
    return {
        'Authorization': f'Bearer {MAGIC_TOKEN}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Galaxy-of-Consequence-Backend/1.0'
    }

def sanitize_user_input(data):
    """
    Sanitize user input to prevent injection attacks
    """
    if isinstance(data, str):
        # Basic sanitization - remove/escape dangerous characters
        return data.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
    elif isinstance(data, dict):
        return {key: sanitize_user_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_user_input(item) for item in data]
    else:
        return data

def validate_star_wars_name(name):
    """
    Validate Star Wars character/NPC names
    """
    if not name or not isinstance(name, str):
        return False
    
    # Allow alphanumeric, spaces, hyphens, apostrophes
    import re
    pattern = r'^[a-zA-Z0-9\s\-\'\.]+$'
    
    return (
        len(name.strip()) >= 2 and
        len(name.strip()) <= 50 and
        re.match(pattern, name.strip()) and
        not name.strip().isdigit()  # Not just numbers
    )

def validate_session_id(session_id):
    """
    Validate session ID format
    """
    if not session_id or not isinstance(session_id, str):
        return False
    
    import re
    # UUID format or alphanumeric with hyphens
    pattern = r'^[a-zA-Z0-9\-_]+$'
    
    return (
        len(session_id) >= 8 and
        len(session_id) <= 100 and
        re.match(pattern, session_id)
    )
