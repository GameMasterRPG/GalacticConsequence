from flask import Blueprint, request, jsonify
from app import db
from models import FactionState, WorldEvent
from routes.auth import check_bearer_auth
from services.faction_ai import run_faction_tick, get_faction_state
from datetime import datetime, timedelta

faction_bp = Blueprint('faction', __name__)

@faction_bp.route('/faction_tick', methods=['POST'])
def faction_tick():
    """
    Execute real-time faction AI turns - autonomous faction simulation
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    session_id = data.get('session_id') if data else None
    force_tick = data.get('force_tick', False) if data else False
    
    try:
        # Run faction AI simulation
        results = run_faction_tick(session_id, force_tick)
        
        return jsonify({
            'message': 'Faction tick executed successfully',
            'results': results,
            'timestamp': datetime.utcnow().isoformat(),
            'next_tick_in': '24 hours' if not force_tick else 'manual'
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to execute faction tick',
            'details': str(e)
        }), 500

@faction_bp.route('/get_faction_state', methods=['GET'])
def get_faction_state_route():
    """
    Get current state of all factions or specific faction
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    faction_name = request.args.get('faction_name')
    session_id = request.args.get('session_id')
    
    if faction_name:
        # Get specific faction
        faction = get_faction_state(faction_name, session_id)
        if not faction:
            return jsonify({'error': 'Faction not found'}), 404
        
        return jsonify({
            'faction': {
                'name': faction.faction_name,
                'type': faction.faction_type,
                'territory_control': faction.territory_control,
                'resources': faction.resources,
                'influence': faction.influence,
                'awareness_level': faction.awareness_level,
                'hostility_level': faction.hostility_level,
                'active_operations': faction.get_operations(),
                'strategic_goals': faction.get_goals(),
                'last_action': faction.last_action.isoformat()
            }
        })
    else:
        # Get all factions
        factions = FactionState.query.all()
        
        return jsonify({
            'factions': [
                {
                    'name': f.faction_name,
                    'type': f.faction_type,
                    'territory_control': f.territory_control,
                    'resources': f.resources,
                    'influence': f.influence,
                    'awareness_level': f.awareness_level,
                    'hostility_level': f.hostility_level,
                    'active_operations': f.get_operations(),
                    'strategic_goals': f.get_goals(),
                    'last_action': f.last_action.isoformat()
                }
                for f in factions
            ],
            'total_factions': len(factions)
        })

@faction_bp.route('/update_faction_relationship', methods=['POST'])
def update_faction_relationship():
    """
    Update faction relationship based on player actions
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    faction_name = data.get('faction_name')
    user = data.get('user')
    relationship_change = data.get('relationship_change', 0)
    awareness_change = data.get('awareness_change', 0)
    action_description = data.get('action_description', '')
    session_id = data.get('session_id')
    
    if not all([faction_name, user]):
        return jsonify({'error': 'Missing required fields: faction_name, user'}), 400
    
    try:
        from services.faction_ai import update_faction_awareness
        result = update_faction_awareness(
            faction_name=faction_name,
            user=user,
            relationship_change=relationship_change,
            awareness_change=awareness_change,
            action_description=action_description,
            session_id=session_id
        )
        
        return jsonify({
            'message': 'Faction relationship updated',
            'faction': faction_name,
            'new_hostility': result['new_hostility'],
            'new_awareness': result['new_awareness'],
            'consequences': result.get('consequences', [])
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to update faction relationship',
            'details': str(e)
        }), 500

@faction_bp.route('/get_galactic_events', methods=['GET'])
def get_galactic_events():
    """
    Get current galactic events affecting factions
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    session_id = request.args.get('session_id')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = WorldEvent.query
    
    if session_id:
        query = query.filter_by(session_id=session_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    events = query.order_by(WorldEvent.created_at.desc()).limit(20).all()
    
    return jsonify({
        'events': [
            {
                'id': event.id,
                'title': event.event_title,
                'description': event.event_description,
                'type': event.event_type,
                'affected_factions': event.affected_factions,
                'galactic_impact': event.galactic_impact,
                'triggered_by': event.triggered_by_player,
                'consequences': event.consequences,
                'duration_days': event.duration_days,
                'is_active': event.is_active,
                'created_at': event.created_at.isoformat()
            }
            for event in events
        ],
        'total_events': len(events)
    })

@faction_bp.route('/trigger_galactic_event', methods=['POST'])
def trigger_galactic_event():
    """
    Trigger a new galactic event (usually as consequence of player actions)
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    title = data.get('title')
    description = data.get('description')
    event_type = data.get('event_type', 'political')
    affected_factions = data.get('affected_factions', [])
    impact = data.get('galactic_impact', 1)
    triggered_by = data.get('triggered_by_player')
    duration = data.get('duration_days', 1)
    session_id = data.get('session_id')
    
    if not all([title, description]):
        return jsonify({'error': 'Missing required fields: title, description'}), 400
    
    try:
        # Create new world event
        event = WorldEvent(
            event_title=title,
            event_description=description,
            event_type=event_type,
            affected_factions=str(affected_factions),
            galactic_impact=impact,
            triggered_by_player=triggered_by,
            duration_days=duration,
            session_id=session_id
        )
        
        db.session.add(event)
        db.session.commit()
        
        # Apply immediate faction effects
        from services.faction_ai import apply_event_to_factions
        faction_effects = apply_event_to_factions(event)
        
        return jsonify({
            'message': 'Galactic event triggered',
            'event_id': event.id,
            'faction_effects': faction_effects,
            'galactic_impact': impact
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to trigger galactic event',
            'details': str(e)
        }), 500
