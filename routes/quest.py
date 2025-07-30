from flask import Blueprint, request, jsonify
from app import db
from models import QuestLog, ForceAlignment, FactionState
from routes.auth import check_bearer_auth
from services.quest_generator import generate_procedural_quest, evaluate_quest_completion
from datetime import datetime

quest_bp = Blueprint('quest', __name__)

@quest_bp.route('/generate_quest', methods=['POST'])
def generate_quest():
    """
    Generate procedural quest based on player state, faction relations, and Force alignment
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    session_id = data.get('session_id')
    difficulty_preference = data.get('difficulty', 'medium')  # easy, medium, hard, extreme
    quest_type_preference = data.get('quest_type')  # combat, social, exploration, force, faction
    location = data.get('location')  # Current player location
    
    if not user:
        return jsonify({'error': 'Missing required field: user'}), 400
    
    try:
        # Generate quest using procedural system
        quest_data = generate_procedural_quest(
            user=user,
            session_id=session_id,
            difficulty_preference=difficulty_preference,
            quest_type_preference=quest_type_preference,
            location=location
        )
        
        if not quest_data:
            return jsonify({'error': 'No suitable quest could be generated at this time'}), 404
        
        # Create quest log entry
        quest = QuestLog(
            user=user,
            quest_title=quest_data['title'],
            quest_description=quest_data['description'],
            quest_giver=quest_data['giver'],
            reward=str(quest_data['rewards']),
            requirements=str(quest_data['requirements']),
            status='available',
            difficulty=quest_data['difficulty'],
            faction_impact=str(quest_data.get('faction_impact', {})),
            force_impact=quest_data.get('force_impact', 0),
            generated_reason=quest_data['generation_reason'],
            prerequisite_events=str(quest_data.get('prerequisites', [])),
            session_id=session_id
        )
        
        db.session.add(quest)
        db.session.commit()
        
        return jsonify({
            'message': 'Quest generated successfully',
            'quest': {
                'id': quest.id,
                'title': quest.quest_title,
                'description': quest.quest_description,
                'giver': quest.quest_giver,
                'rewards': quest_data['rewards'],
                'requirements': quest_data['requirements'],
                'difficulty': quest.difficulty,
                'faction_impact': quest_data.get('faction_impact', {}),
                'force_impact': quest.force_impact,
                'generation_reason': quest.generated_reason,
                'status': quest.status
            }
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate quest',
            'details': str(e)
        }), 500

@quest_bp.route('/accept_quest', methods=['POST'])
def accept_quest():
    """
    Accept an available quest
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    quest_id = data.get('quest_id')
    user = data.get('user')
    
    if not all([quest_id, user]):
        return jsonify({'error': 'Missing required fields: quest_id, user'}), 400
    
    quest = QuestLog.query.filter_by(id=quest_id, user=user).first()
    
    if not quest:
        return jsonify({'error': 'Quest not found'}), 404
    
    if quest.status != 'available':
        return jsonify({'error': f'Quest is not available (current status: {quest.status})'}), 400
    
    quest.status = 'active'
    db.session.commit()
    
    return jsonify({
        'message': 'Quest accepted',
        'quest_id': quest.id,
        'status': quest.status,
        'title': quest.quest_title
    })

@quest_bp.route('/complete_quest', methods=['POST'])
def complete_quest():
    """
    Complete an active quest and apply rewards/consequences
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    quest_id = data.get('quest_id')
    user = data.get('user')
    completion_method = data.get('completion_method', 'standard')  # How the quest was completed
    player_choices = data.get('player_choices', [])  # Key decisions made during quest
    session_id = data.get('session_id')
    
    if not all([quest_id, user]):
        return jsonify({'error': 'Missing required fields: quest_id, user'}), 400
    
    quest = QuestLog.query.filter_by(id=quest_id, user=user).first()
    
    if not quest:
        return jsonify({'error': 'Quest not found'}), 404
    
    if quest.status != 'active':
        return jsonify({'error': f'Quest is not active (current status: {quest.status})'}), 400
    
    try:
        # Evaluate quest completion and apply consequences
        completion_result = evaluate_quest_completion(
            quest=quest,
            completion_method=completion_method,
            player_choices=player_choices,
            session_id=session_id
        )
        
        # Update quest status
        quest.status = 'completed'
        quest.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Quest completed successfully',
            'quest_id': quest.id,
            'title': quest.quest_title,
            'completion_result': completion_result,
            'rewards_granted': completion_result.get('rewards', []),
            'faction_changes': completion_result.get('faction_changes', {}),
            'force_alignment_change': completion_result.get('force_change', 0),
            'consequences': completion_result.get('consequences', [])
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to complete quest',
            'details': str(e)
        }), 500

@quest_bp.route('/fail_quest', methods=['POST'])
def fail_quest():
    """
    Fail an active quest with consequences
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    quest_id = data.get('quest_id')
    user = data.get('user')
    failure_reason = data.get('failure_reason', 'unknown')
    session_id = data.get('session_id')
    
    if not all([quest_id, user]):
        return jsonify({'error': 'Missing required fields: quest_id, user'}), 400
    
    quest = QuestLog.query.filter_by(id=quest_id, user=user).first()
    
    if not quest:
        return jsonify({'error': 'Quest not found'}), 404
    
    if quest.status not in ['active', 'available']:
        return jsonify({'error': f'Quest cannot be failed (current status: {quest.status})'}), 400
    
    try:
        # Apply failure consequences
        from services.quest_generator import apply_quest_failure_consequences
        failure_result = apply_quest_failure_consequences(
            quest=quest,
            failure_reason=failure_reason,
            session_id=session_id
        )
        
        # Update quest status
        quest.status = 'failed'
        quest.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': 'Quest failed',
            'quest_id': quest.id,
            'title': quest.quest_title,
            'failure_reason': failure_reason,
            'consequences': failure_result.get('consequences', []),
            'faction_changes': failure_result.get('faction_changes', {}),
            'reputation_impact': failure_result.get('reputation_impact', 0)
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to process quest failure',
            'details': str(e)
        }), 500

@quest_bp.route('/get_available_quests', methods=['GET'])
def get_available_quests():
    """
    Get all available quests for a user
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    user = request.args.get('user')
    session_id = request.args.get('session_id')
    status = request.args.get('status', 'available')  # available, active, completed, failed
    
    if not user:
        return jsonify({'error': 'Missing required parameter: user'}), 400
    
    query = QuestLog.query.filter_by(user=user, status=status)
    
    if session_id:
        query = query.filter_by(session_id=session_id)
    
    quests = query.order_by(QuestLog.created_at.desc()).all()
    
    return jsonify({
        'quests': [
            {
                'id': q.id,
                'title': q.quest_title,
                'description': q.quest_description,
                'giver': q.quest_giver,
                'difficulty': q.difficulty,
                'status': q.status,
                'force_impact': q.force_impact,
                'created_at': q.created_at.isoformat(),
                'completed_at': q.completed_at.isoformat() if q.completed_at else None
            }
            for q in quests
        ],
        'total_quests': len(quests),
        'status_filter': status
    })
