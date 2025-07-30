from flask import Blueprint, request, jsonify, Response
from routes.auth import check_bearer_auth
from utils.nvidia_client import query_nemotron_streaming
from services.npc_memory import update_npc_interaction
import json

nemotron_bp = Blueprint('nemotron', __name__)

@nemotron_bp.route('/query_nemotron', methods=['POST'])
def query_nemotron():
    """
    Query NVIDIA Nemotron for immersive NPC dialogue with streaming response
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    # Extract required fields
    model = data.get('model', 'nvidia/nemotron-mini-4b-instruct')
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.2)
    top_p = data.get('top_p', 0.7)
    max_tokens = data.get('max_tokens', 1024)
    stream = data.get('stream', True)
    
    # Optional game context fields
    user = data.get('user')
    npc_name = data.get('npc_name')
    session_id = data.get('session_id')
    
    if not messages:
        return jsonify({'error': 'Missing required field: messages'}), 400
    
    # Prepare payload for NVIDIA API
    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'top_p': top_p,
        'max_tokens': max_tokens,
        'stream': stream
    }
    
    try:
        if stream:
            # Return streaming response
            def generate():
                full_response = ""
                for chunk in query_nemotron_streaming(payload):
                    if chunk:
                        yield f"data: {json.dumps(chunk)}\n\n"
                        # Collect full response for NPC memory update
                        if 'choices' in chunk and chunk['choices']:
                            delta = chunk['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response += content
                
                # Update NPC memory after complete response
                if user and npc_name and full_response:
                    update_npc_interaction(
                        npc_name=npc_name,
                        user=user,
                        interaction_type='dialogue',
                        interaction_data={
                            'player_message': messages[-1].get('content', '') if messages else '',
                            'npc_response': full_response,
                            'context': messages[0].get('content', '') if messages else ''
                        },
                        session_id=session_id
                    )
                
                yield f"data: {json.dumps({'done': True})}\n\n"
            
            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            # Return single response
            response = query_nemotron_streaming(payload, stream=False)
            
            # Update NPC memory
            if user and npc_name and response:
                npc_response = ""
                if 'choices' in response and response['choices']:
                    npc_response = response['choices'][0].get('message', {}).get('content', '')
                
                if npc_response:
                    update_npc_interaction(
                        npc_name=npc_name,
                        user=user,
                        interaction_type='dialogue',
                        interaction_data={
                            'player_message': messages[-1].get('content', '') if messages else '',
                            'npc_response': npc_response,
                            'context': messages[0].get('content', '') if messages else ''
                        },
                        session_id=session_id
                    )
            
            return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to query Nemotron',
            'details': str(e)
        }), 500

@nemotron_bp.route('/generate_npc_dialogue', methods=['POST'])
def generate_npc_dialogue():
    """
    Generate contextual NPC dialogue based on game state and NPC memory
    """
    if not check_bearer_auth():
        return jsonify({'error': 'Unauthorized - Invalid Bearer token'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Missing request body'}), 400
    
    user = data.get('user')
    npc_name = data.get('npc_name')
    situation = data.get('situation', '')
    player_action = data.get('player_action', '')
    session_id = data.get('session_id')
    
    if not all([user, npc_name]):
        return jsonify({'error': 'Missing required fields: user, npc_name'}), 400
    
    # Get NPC memory and build context
    from services.npc_memory import get_npc_memory, build_npc_context
    npc_memory = get_npc_memory(npc_name, user, session_id)
    context = build_npc_context(npc_memory, situation, player_action)
    
    # Build messages for Nemotron
    messages = [
        {
            "role": "system",
            "content": context['system_prompt']
        },
        {
            "role": "user", 
            "content": context['user_prompt']
        }
    ]
    
    # Query Nemotron with context
    payload = {
        'model': 'nvidia/nemotron-mini-4b-instruct',
        'messages': messages,
        'temperature': 0.3,
        'top_p': 0.8,
        'max_tokens': 512,
        'stream': False
    }
    
    try:
        response = query_nemotron_streaming(payload, stream=False)
        
        npc_response = ""
        if 'choices' in response and response['choices']:
            npc_response = response['choices'][0].get('message', {}).get('content', '')
        
        # Update NPC memory with this interaction
        if npc_response:
            update_npc_interaction(
                npc_name=npc_name,
                user=user,
                interaction_type='contextual_dialogue',
                interaction_data={
                    'situation': situation,
                    'player_action': player_action,
                    'npc_response': npc_response,
                    'relationship_change': context.get('relationship_change', 0)
                },
                session_id=session_id
            )
        
        return jsonify({
            'npc_name': npc_name,
            'dialogue': npc_response,
            'context': context['metadata'],
            'relationship_status': npc_memory.relationship_level if npc_memory else 0
        })
    
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate NPC dialogue',
            'details': str(e)
        }), 500
