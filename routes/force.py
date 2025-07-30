from flask import Blueprint, request, jsonify
from app import db
from models import ForceAlignment, WorldEvent
from routes.auth import check_bearer_auth
from services.force_engine import update_force_alignment, trigger_force_consequences, get_force_powers
from datetime import datetime

force_bp = Blueprint('force', __name__)

@force_bp.route('/update_alignment', methods=['POST'])
def update_alignment():
    """
    Update player Force alignment based on actions with cascading consequences
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    action_type = data.get('action_type')  # 'light', 'dark', 'neutral'
    action_description = data.get('action_description', '')
    force_magnitude = data.get('force_magnitude', 1)  # 1-10 scale of Force impact
    witnesses = data.get('witnesses', [])  # NPCs or factions who witnessed the action
    session_id = data.get('session_id')
    
    if not all([user, action_type]):
        return jsonify({'error': 'Missing required fields: user, action_type'}), 400
    
    if action_type not in ['light', 'dark', 'neutral']:
        return jsonify({'error': 'action_type must be one of: light, dark, neutral'}), 400
    
    try:
        # Update Force alignment
        result = update_force_alignment(
            user=user,
            action_type=action_type,
            action_description=action_description,
            force_magnitude=force_magnitude,
            witnesses=witnesses,
            session_id=session_id
        )
        
        return jsonify({
            'message': 'Force alignment updated',
            'alignment_change': result['alignment_change'],
            'new_alignment': result['new_alignment'],
            'alignment_description': result['alignment_description'],
            'force_consequences': result.get('consequences', []),
            'unlocked_powers': result.get('unlocked_powers', []),
            'corruption_level': result.get('corruption_level', 0),
            'npc_reactions': result.get('npc_reactions', [])
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to update Force alignment',
            'details': str(e)
        }), 500

@force_bp.route('/get_alignment', methods=['GET'])
def get_alignment():
    """
    Get player's current Force alignment and history
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    user = request.args.get('user')
    session_id = request.args.get('session_id')
    
    if not user:
        return jsonify({'error': 'Missing required parameter: user'}), 400
    
    alignment = ForceAlignment.query.filter_by(user=user).first()
    
    if not alignment:
        # Create default Force alignment for new user
        alignment = ForceAlignment(
            user=user,
            session_id=session_id
        )
        db.session.add(alignment)
        db.session.commit()
    
    import json
    
    return jsonify({
        'user': user,
        'force_sensitive': alignment.force_sensitive,
        'light_side_points': alignment.light_side_points,
        'dark_side_points': alignment.dark_side_points,
        'net_alignment': alignment.net_alignment,
        'alignment_description': alignment.alignment_description,
        'corruption_level': alignment.corruption_level,
        'force_events': json.loads(alignment.force_events),
        'alignment_history': json.loads(alignment.alignment_history),
        'force_powers': json.loads(alignment.force_powers),
        'last_force_event': alignment.last_force_event.isoformat() if alignment.last_force_event else None
    })

@force_bp.route('/trigger_force_vision', methods=['POST'])
def trigger_force_vision():
    """
    Trigger Force vision based on current alignment and galaxy state
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    vision_trigger = data.get('trigger', 'meditation')  # meditation, stress, combat, location
    session_id = data.get('session_id')
    
    if not user:
        return jsonify({'error': 'Missing required field: user'}), 400
    
    try:
        from services.force_engine import generate_force_vision
        vision_result = generate_force_vision(
            user=user,
            trigger=vision_trigger,
            session_id=session_id
        )
        
        if not vision_result:
            return jsonify({'message': 'No Force vision manifested at this time'}), 200
        
        return jsonify({
            'message': 'Force vision experienced',
            'vision': vision_result['vision_text'],
            'vision_type': vision_result['vision_type'],
            'future_hints': vision_result.get('future_hints', []),
            'alignment_requirement': vision_result.get('alignment_requirement'),
            'force_magnitude': vision_result.get('force_magnitude', 1)
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to trigger Force vision',
            'details': str(e)
        }), 500

@force_bp.route('/use_force_power', methods=['POST'])
def use_force_power():
    """
    Use a Force power with alignment consequences
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    power_name = data.get('power_name')
    target = data.get('target', '')  # Target of the power (NPC, object, etc.)
    intent = data.get('intent', 'neutral')  # 'light', 'dark', 'neutral'
    power_level = data.get('power_level', 1)  # 1-10 intensity
    session_id = data.get('session_id')
    
    if not all([user, power_name]):
        return jsonify({'error': 'Missing required fields: user, power_name'}), 400
    
    try:
        from services.force_engine import use_force_power
        power_result = use_force_power(
            user=user,
            power_name=power_name,
            target=target,
            intent=intent,
            power_level=power_level,
            session_id=session_id
        )
        
        return jsonify({
            'message': f'Force power "{power_name}" used',
            'success': power_result['success'],
            'effect_description': power_result['effect_description'],
            'alignment_change': power_result.get('alignment_change', 0),
            'force_cost': power_result.get('force_cost', 0),
            'consequences': power_result.get('consequences', []),
            'witnesses_affected': power_result.get('witnesses_affected', [])
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to use Force power',
            'details': str(e)
        }), 500

@force_bp.route('/get_available_powers', methods=['GET'])
def get_available_powers():
    """
    Get Force powers available to player based on alignment and experience
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    user = request.args.get('user')
    
    if not user:
        return jsonify({'error': 'Missing required parameter: user'}), 400
    
    try:
        powers = get_force_powers(user)
        
        return jsonify({
            'available_powers': powers['available'],
            'locked_powers': powers['locked'],
            'alignment_requirements': powers['requirements'],
            'force_sensitive': powers['force_sensitive']
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to get Force powers',
            'details': str(e)
        }), 500

@force_bp.route('/get_force_nexus_events', methods=['GET'])
def get_force_nexus_events():
    """
    Get Force-related galactic events affecting the galaxy
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    session_id = request.args.get('session_id')
    
    # Get Force-related world events
    query = WorldEvent.query.filter_by(event_type='force', is_active=True)
    
    if session_id:
        query = query.filter_by(session_id=session_id)
    
    events = query.order_by(WorldEvent.created_at.desc()).limit(10).all()
    
    return jsonify({
        'force_events': [
            {
                'id': event.id,
                'title': event.event_title,
                'description': event.event_description,
                'galactic_impact': event.galactic_impact,
                'triggered_by': event.triggered_by_player,
                'consequences': event.consequences,
                'created_at': event.created_at.isoformat()
            }
            for event in events
        ],
        'total_events': len(events)
    })

@force_bp.route('/meditate', methods=['POST'])
def meditate():
    """
    Force meditation for alignment balancing and visions
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    meditation_type = data.get('type', 'balance')  # balance, light, dark, vision_seeking
    duration = data.get('duration', 'short')  # short, medium, long
    location = data.get('location', 'unknown')  # Force nexus affects meditation
    session_id = data.get('session_id')
    
    if not user:
        return jsonify({'error': 'Missing required field: user'}), 400
    
    try:
        from services.force_engine import meditate
        meditation_result = meditate(
            user=user,
            meditation_type=meditation_type,
            duration=duration,
            location=location,
            session_id=session_id
        )
        
        return jsonify({
            'message': 'Meditation completed',
            'meditation_outcome': meditation_result['outcome'],
            'alignment_change': meditation_result.get('alignment_change', 0),
            'visions_received': meditation_result.get('visions', []),
            'force_clarity': meditation_result.get('force_clarity', 0),
            'location_bonus': meditation_result.get('location_bonus', 0)
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to complete meditation',
            'details': str(e)
        }), 500
