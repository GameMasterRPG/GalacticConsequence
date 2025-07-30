from flask import Blueprint, request, jsonify
from app import db
from models import CanvasEntry
from routes.auth import check_bearer_auth
import json
from datetime import datetime

canvas_bp = Blueprint('canvas', __name__)

@canvas_bp.route('/save_canvas', methods=['POST'])
def save_canvas():
    """
    Save player game state to persistent storage
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data or 'user' not in data:
        return jsonify({'error': 'Missing required field: user'}), 400
    
    user = data['user']
    campaign = data.get('campaign', 'default')
    canvas = data.get('canvas', 'main')
    game_data = data.get('data', {})
    session_id = data.get('session_id')
    
    # Create new canvas entry
    canvas_entry = CanvasEntry(
        user=user,
        campaign=campaign,
        canvas=canvas,
        data=json.dumps(game_data),
        session_id=session_id
    )
    
    db.session.add(canvas_entry)
    db.session.commit()
    
    return jsonify({
        'message': 'Canvas saved successfully',
        'canvas_id': canvas_entry.id,
        'timestamp': canvas_entry.timestamp.isoformat()
    })

@canvas_bp.route('/get_canvas', methods=['GET'])
def get_canvas():
    """
    Retrieve latest canvas for a user
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    user = request.args.get('user')
    campaign = request.args.get('campaign', 'default')
    
    if not user:
        return jsonify({'error': 'Missing required parameter: user'}), 400
    
    canvas_entry = CanvasEntry.query.filter_by(
        user=user, 
        campaign=campaign
    ).order_by(CanvasEntry.timestamp.desc()).first()
    
    if not canvas_entry:
        return jsonify({'error': 'No canvas found for user'}), 404
    
    return jsonify(canvas_entry.to_dict())

@canvas_bp.route('/get_canvas_by_id', methods=['GET'])
def get_canvas_by_id():
    """
    Retrieve specific canvas by ID
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    canvas_id = request.args.get('id')
    
    if not canvas_id:
        return jsonify({'error': 'Missing required parameter: id'}), 400
    
    canvas_entry = CanvasEntry.query.get(canvas_id)
    
    if not canvas_entry:
        return jsonify({'error': 'Canvas not found'}), 404
    
    return jsonify(canvas_entry.to_dict())

@canvas_bp.route('/get_canvas_history', methods=['GET'])
def get_canvas_history():
    """
    Retrieve canvas history for user/campaign
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    user = request.args.get('user')
    campaign = request.args.get('campaign', 'default')
    canvas = request.args.get('canvas', 'main')
    limit = int(request.args.get('limit', 10))
    
    if not user:
        return jsonify({'error': 'Missing required parameter: user'}), 400
    
    entries = CanvasEntry.query.filter_by(
        user=user,
        campaign=campaign,
        canvas=canvas
    ).order_by(CanvasEntry.timestamp.desc()).limit(limit).all()
    
    return jsonify({
        'history': [entry.to_dict() for entry in entries],
        'total_entries': len(entries)
    })

@canvas_bp.route('/get_log', methods=['GET'])
def get_log():
    """
    Get filtered log entries for canvas/user/alignment
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    canvas = request.args.get('canvas')
    user = request.args.get('user')
    align = request.args.get('align')  # Filter by force alignment if provided
    
    query = CanvasEntry.query
    
    if canvas:
        query = query.filter_by(canvas=canvas)
    if user:
        query = query.filter_by(user=user)
    
    entries = query.order_by(CanvasEntry.timestamp.desc()).limit(50).all()
    
    # If alignment filter is specified, filter the data content
    filtered_entries = []
    for entry in entries:
        entry_dict = entry.to_dict()
        if align:
            # Filter based on Force alignment in the data
            game_data = entry_dict.get('data', {})
            if 'force_alignment' in game_data:
                if align.lower() in game_data['force_alignment'].lower():
                    filtered_entries.append(entry_dict)
            else:
                # Include entries without alignment data if no specific filter
                filtered_entries.append(entry_dict)
        else:
            filtered_entries.append(entry_dict)
    
    return jsonify({
        'log_entries': filtered_entries,
        'total_entries': len(filtered_entries),
        'filters_applied': {
            'canvas': canvas,
            'user': user,
            'alignment': align
        }
    })
