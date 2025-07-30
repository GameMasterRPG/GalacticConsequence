from flask import Blueprint, request, jsonify
from app import db
from models import SessionState
from routes.auth import check_bearer_auth
from datetime import datetime
import json
import uuid

session_bp = Blueprint('session', __name__)

@session_bp.route('/create_session', methods=['POST'])
def create_session():
    """
    Create a new multiplayer session
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    session_name = data.get('session_name')
    created_by = data.get('created_by')
    initial_galaxy_state = data.get('galaxy_state', {})
    
    if not all([session_name, created_by]):
        return jsonify({'error': 'Missing required fields: session_name, created_by'}), 400
    
    # Generate unique session ID
    session_id = str(uuid.uuid4())
    
    # Create default galaxy state if not provided
    if not initial_galaxy_state:
        initial_galaxy_state = {
            'galactic_year': 0,  # Years since Battle of Yavin
            'major_powers': {
                'empire': {'control': 70, 'resources': 10000},
                'rebellion': {'control': 15, 'resources': 2000},
                'hutts': {'control': 10, 'resources': 5000},
                'csa': {'control': 5, 'resources': 3000}
            },
            'trade_routes': ['Corellian Run', 'Hydian Way', 'Perlemian Trade Route'],
            'active_conflicts': [],
            'force_balance': 0  # -100 (Dark) to 100 (Light)
        }
    
    session = SessionState(
        session_id=session_id,
        session_name=session_name,
        galaxy_state=json.dumps(initial_galaxy_state),
        active_players=json.dumps([created_by]),
        current_galactic_year=initial_galaxy_state.get('galactic_year', 0)
    )
    
    db.session.add(session)
    db.session.commit()
    
    return jsonify({
        'message': 'Session created successfully',
        'session_id': session_id,
        'session_name': session_name,
        'created_by': created_by,
        'galaxy_state': initial_galaxy_state
    })

@session_bp.route('/get_session_state', methods=['GET'])
def get_session_state():
    """
    Get current session state for multiplayer synchronization
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    session_id = request.args.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'Missing required parameter: session_id'}), 400
    
    session = SessionState.query.filter_by(session_id=session_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'session_id': session.session_id,
        'session_name': session.session_name,
        'galaxy_state': json.loads(session.galaxy_state),
        'active_players': json.loads(session.active_players),
        'current_galactic_year': session.current_galactic_year,
        'major_events': json.loads(session.major_events),
        'faction_war_status': json.loads(session.faction_war_status),
        'force_nexus_events': json.loads(session.force_nexus_events),
        'threat_escalation_level': session.threat_escalation_level,
        'last_faction_tick': session.last_faction_tick.isoformat(),
        'updated_at': session.updated_at.isoformat()
    })

@session_bp.route('/update_session_state', methods=['POST'])
def update_session_state():
    """
    Update session state with new galaxy changes (for multiplayer sync)
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    session_id = data.get('session_id')
    updated_by = data.get('updated_by')
    
    if not all([session_id, updated_by]):
        return jsonify({'error': 'Missing required fields: session_id, updated_by'}), 400
    
    session = SessionState.query.filter_by(session_id=session_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Update galaxy state fields if provided
    if 'galaxy_state' in data:
        session.galaxy_state = json.dumps(data['galaxy_state'])
    
    if 'galactic_year' in data:
        session.current_galactic_year = data['galactic_year']
    
    if 'major_events' in data:
        session.major_events = json.dumps(data['major_events'])
    
    if 'faction_war_status' in data:
        session.faction_war_status = json.dumps(data['faction_war_status'])
    
    if 'force_nexus_events' in data:
        session.force_nexus_events = json.dumps(data['force_nexus_events'])
    
    if 'threat_escalation_level' in data:
        session.threat_escalation_level = data['threat_escalation_level']
    
    # Update active players list
    current_players = json.loads(session.active_players)
    if updated_by not in current_players:
        current_players.append(updated_by)
        session.active_players = json.dumps(current_players)
    
    session.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Session state updated successfully',
        'session_id': session_id,
        'updated_by': updated_by,
        'updated_at': session.updated_at.isoformat()
    })

@session_bp.route('/join_session', methods=['POST'])
def join_session():
    """
    Join an existing multiplayer session
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    session_id = data.get('session_id')
    player_name = data.get('player_name')
    
    if not all([session_id, player_name]):
        return jsonify({'error': 'Missing required fields: session_id, player_name'}), 400
    
    session = SessionState.query.filter_by(session_id=session_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Add player to active players list
    current_players = json.loads(session.active_players)
    if player_name not in current_players:
        current_players.append(player_name)
        session.active_players = json.dumps(current_players)
        session.updated_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'message': f'Successfully joined session: {session.session_name}',
        'session_id': session_id,
        'session_name': session.session_name,
        'active_players': current_players,
        'galaxy_state': json.loads(session.galaxy_state)
    })

@session_bp.route('/leave_session', methods=['POST'])
def leave_session():
    """
    Leave a multiplayer session
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    session_id = data.get('session_id')
    player_name = data.get('player_name')
    
    if not all([session_id, player_name]):
        return jsonify({'error': 'Missing required fields: session_id, player_name'}), 400
    
    session = SessionState.query.filter_by(session_id=session_id).first()
    
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # Remove player from active players list
    current_players = json.loads(session.active_players)
    if player_name in current_players:
        current_players.remove(player_name)
        session.active_players = json.dumps(current_players)
        session.updated_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify({
        'message': f'Successfully left session: {session.session_name}',
        'session_id': session_id,
        'remaining_players': current_players
    })

@session_bp.route('/list_sessions', methods=['GET'])
def list_sessions():
    """
    List all available sessions
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    sessions = SessionState.query.order_by(SessionState.updated_at.desc()).all()
    
    return jsonify({
        'sessions': [
            {
                'session_id': s.session_id,
                'session_name': s.session_name,
                'active_players': json.loads(s.active_players),
                'player_count': len(json.loads(s.active_players)),
                'galactic_year': s.current_galactic_year,
                'threat_level': s.threat_escalation_level,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat()
            }
            for s in sessions
        ],
        'total_sessions': len(sessions)
    })
