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
    Save any RPG canvas type (Force HUD, Summary, etc.)
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    # Validate required fields per RPG HUD API spec
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    required_fields = ['canvas', 'user', 'data', 'meta']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    user = data['user']
    canvas = data['canvas']
    game_data = data['data']
    meta = data['meta']
    
    # Extract campaign from meta if available
    campaign = meta.get('campaign', 'default')
    session_id = data.get('session_id')
    
    # Create new canvas entry
    canvas_entry = CanvasEntry(
        user=user,
        campaign=campaign,
        canvas=canvas,
        data=json.dumps({
            'data': game_data,
            'meta': meta
        }),
        session_id=session_id
    )
    
    db.session.add(canvas_entry)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Canvas saved successfully',
        'id': str(canvas_entry.id)
    })

@canvas_bp.route('/get_canvas', methods=['GET'])
def get_canvas():
    """
    Retrieve the latest saved canvas
    """
    user = request.args.get('user')
    campaign = request.args.get('campaign', 'default')
    canvas_type = request.args.get('canvas')
    
    query = CanvasEntry.query
    
    if user:
        query = query.filter_by(user=user)
    if campaign:
        query = query.filter_by(campaign=campaign)
    if canvas_type:
        query = query.filter_by(canvas=canvas_type)
    
    canvas_entry = query.order_by(CanvasEntry.timestamp.desc()).first()
    
    if not canvas_entry:
        return jsonify({'status': 'error', 'message': 'No canvas found'}), 404
    
    # Parse the stored data
    stored_data = json.loads(canvas_entry.data) if canvas_entry.data else {}
    
    return jsonify({
        'status': 'success',
        'canvas': {
            'id': canvas_entry.id,
            'user': canvas_entry.user,
            'campaign': canvas_entry.campaign,
            'canvas': canvas_entry.canvas,
            'data': stored_data.get('data', {}),
            'meta': stored_data.get('meta', {}),
            'timestamp': canvas_entry.timestamp.isoformat(),
            'session_id': canvas_entry.session_id
        }
    })

@canvas_bp.route('/get_canvas_by_id', methods=['GET'])
def get_canvas_by_id():
    """
    Get a canvas by ID
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    canvas_id = request.args.get('id')
    
    if not canvas_id:
        return jsonify({'error': 'Missing required parameter: id'}), 400
    
    canvas_entry = CanvasEntry.query.get(canvas_id)
    
    if not canvas_entry:
        return jsonify({'status': 'error', 'message': 'Canvas not found'}), 404
    
    # Parse the stored data
    stored_data = json.loads(canvas_entry.data) if canvas_entry.data else {}
    
    return jsonify({
        'status': 'success',
        'canvas': {
            'id': canvas_entry.id,
            'user': canvas_entry.user,
            'campaign': canvas_entry.campaign,
            'canvas': canvas_entry.canvas,
            'data': stored_data.get('data', {}),
            'meta': stored_data.get('meta', {}),
            'timestamp': canvas_entry.timestamp.isoformat(),
            'session_id': canvas_entry.session_id
        }
    })

@canvas_bp.route('/get_canvas_history', methods=['GET'])
def get_canvas_history():
    """
    Retrieve full save history with filters
    """
    user = request.args.get('user')
    campaign = request.args.get('campaign')
    canvas_type = request.args.get('canvas')
    
    query = CanvasEntry.query
    
    if user:
        query = query.filter_by(user=user)
    if campaign:
        query = query.filter_by(campaign=campaign)
    if canvas_type:
        query = query.filter_by(canvas=canvas_type)
    
    entries = query.order_by(CanvasEntry.timestamp.desc()).all()
    
    history = []
    for entry in entries:
        stored_data = json.loads(entry.data) if entry.data else {}
        history.append({
            'id': entry.id,
            'user': entry.user,
            'campaign': entry.campaign,
            'canvas': entry.canvas,
            'data': stored_data.get('data', {}),
            'meta': stored_data.get('meta', {}),
            'timestamp': entry.timestamp.isoformat(),
            'session_id': entry.session_id
        })
    
    return jsonify({
        'status': 'success',
        'history': history
    })

@canvas_bp.route('/get_log', methods=['GET'])
def get_log():
    """
    Get canvas history by type or user
    """
    canvas_type = request.args.get('canvas')
    user = request.args.get('user')
    align = request.args.get('align')
    
    query = CanvasEntry.query
    
    if canvas_type:
        query = query.filter_by(canvas=canvas_type)
    if user:
        query = query.filter_by(user=user)
    
    entries = query.order_by(CanvasEntry.timestamp.desc()).all()
    
    log = []
    for entry in entries:
        stored_data = json.loads(entry.data) if entry.data else {}
        log.append({
            'id': entry.id,
            'user': entry.user,
            'campaign': entry.campaign,
            'canvas': entry.canvas,
            'data': stored_data.get('data', {}),
            'meta': stored_data.get('meta', {}),
            'timestamp': entry.timestamp.isoformat(),
            'session_id': entry.session_id
        })
    
    return jsonify({
        'status': 'success',
        'log': log
    })
    
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
