import requests
import json
import os
import logging
from typing import Dict, Any, Iterator, Optional

# Configure logging
logger = logging.getLogger(__name__)

# NVIDIA API configuration
NVIDIA_API_BASE_URL = "https://integrate.api.nvidia.com/v1"
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "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")

def query_nemotron_streaming(payload: Dict[str, Any], stream: bool = True) -> Iterator[Dict[str, Any]]:
    """
    Query NVIDIA Nemotron API with streaming or single response
    
    Args:
        payload: The request payload for the API
        stream: Whether to stream the response or return single response
        
    Yields:
        Dict containing API response chunks for streaming
        
    Returns:
        Dict containing full API response for non-streaming
    """
    url = f"{NVIDIA_API_BASE_URL}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Ensure payload has required fields with defaults
    payload = prepare_payload(payload, stream)
    
    try:
        logger.debug(f"Sending request to NVIDIA API: {url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            stream=stream,
            timeout=60
        )
        
        logger.debug(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            error_message = f"NVIDIA API error: {response.status_code} - {response.text}"
            logger.error(error_message)
            raise Exception(error_message)
        
        if stream:
            return parse_streaming_response(response)
        else:
            return response.json()
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error when calling NVIDIA API: {str(e)}")
        raise Exception(f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error when calling NVIDIA API: {str(e)}")
        raise

def prepare_payload(payload: Dict[str, Any], stream: bool) -> Dict[str, Any]:
    """
    Prepare and validate the payload for NVIDIA API
    """
    prepared_payload = {
        "model": payload.get("model", "nvidia/nemotron-mini-4b-instruct"),
        "messages": payload.get("messages", []),
        "temperature": payload.get("temperature", 0.2),
        "top_p": payload.get("top_p", 0.7),
        "max_tokens": payload.get("max_tokens", 1024),
        "stream": stream
    }
    
    # Validate messages
    if not prepared_payload["messages"]:
        raise ValueError("Messages array cannot be empty")
    
    for message in prepared_payload["messages"]:
        if "role" not in message or "content" not in message:
            raise ValueError("Each message must have 'role' and 'content' fields")
        
        if message["role"] not in ["system", "user", "assistant"]:
            raise ValueError("Message role must be 'system', 'user', or 'assistant'")
    
    # Validate parameters
    if not (0.0 <= prepared_payload["temperature"] <= 2.0):
        prepared_payload["temperature"] = max(0.0, min(2.0, prepared_payload["temperature"]))
    
    if not (0.0 <= prepared_payload["top_p"] <= 1.0):
        prepared_payload["top_p"] = max(0.0, min(1.0, prepared_payload["top_p"]))
    
    if not (1 <= prepared_payload["max_tokens"] <= 4096):
        prepared_payload["max_tokens"] = max(1, min(4096, prepared_payload["max_tokens"]))
    
    return prepared_payload

def parse_streaming_response(response: requests.Response) -> Iterator[Dict[str, Any]]:
    """
    Parse streaming response from NVIDIA API
    """
    try:
        for line in response.iter_lines():
            if not line:
                continue
            
            line = line.decode('utf-8')
            
            # Skip empty lines and comments
            if not line.strip() or line.startswith('#'):
                continue
            
            # Parse server-sent events format
            if line.startswith('data: '):
                data_str = line[6:]  # Remove 'data: ' prefix
                
                # Check for end of stream
                if data_str.strip() == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    yield data
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse streaming response line: {data_str} - {str(e)}")
                    continue
    
    except Exception as e:
        logger.error(f"Error parsing streaming response: {str(e)}")
        raise Exception(f"Streaming response parsing failed: {str(e)}")

def generate_star_wars_dialogue(character_description: str, situation: str, player_input: str, context: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Generate Star Wars themed NPC dialogue using Nemotron
    
    Args:
        character_description: Description of the NPC character
        situation: Current situation/context
        player_input: What the player said or did
        context: Additional context (relationship, mood, etc.)
        
    Returns:
        Dict containing the generated dialogue response
    """
    # Build system prompt for Star Wars context
    system_prompt = f"""You are roleplaying as an NPC in the Star Wars universe. 

Character: {character_description}

Current situation: {situation}

Speak in character and respond authentically to the player's words and actions. Keep responses concise (1-3 sentences) and immersive. Use appropriate Star Wars terminology and maintain the character's personality and motivations."""
    
    # Add context if provided
    if context:
        if context.get('relationship'):
            relationship = context['relationship']
            if relationship > 50:
                system_prompt += f"\nYou have a very positive relationship with this person (relationship: {relationship})."
            elif relationship < -50:
                system_prompt += f"\nYou strongly dislike or distrust this person (relationship: {relationship})."
            elif relationship < -20:
                system_prompt += f"\nYou are wary of this person (relationship: {relationship})."
            elif relationship > 20:
                system_prompt += f"\nYou are friendly towards this person (relationship: {relationship})."
        
        if context.get('mood'):
            system_prompt += f"\nCurrent mood: {context['mood']}"
        
        if context.get('faction'):
            system_prompt += f"\nYour faction allegiance: {context['faction']}"
    
    # Build user prompt
    user_prompt = f"Player says or does: {player_input}\n\nHow do you respond?"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    payload = {
        "model": "nvidia/nemotron-mini-4b-instruct",
        "messages": messages,
        "temperature": 0.3,  # Slightly higher for more creative dialogue
        "top_p": 0.8,
        "max_tokens": 256,  # Shorter for dialogue
        "stream": False
    }
    
    try:
        response = query_nemotron_streaming(payload, stream=False)
        
        if 'choices' in response and response['choices']:
            dialogue = response['choices'][0].get('message', {}).get('content', '')
            return {
                'success': True,
                'dialogue': dialogue.strip(),
                'character': character_description,
                'raw_response': response
            }
        else:
            logger.error(f"Unexpected response format from NVIDIA API: {response}")
            return {
                'success': False,
                'dialogue': "I... I'm not sure what to say.",
                'error': 'Unexpected API response format'
            }
    
    except Exception as e:
        logger.error(f"Failed to generate dialogue: {str(e)}")
        return {
            'success': False,
            'dialogue': "The words escape me at the moment.",
            'error': str(e)
        }

def generate_force_vision(alignment_context: str, galaxy_state: str, vision_type: str = 'future') -> Dict[str, Any]:
    """
    Generate Force vision using Nemotron
    
    Args:
        alignment_context: Player's Force alignment and history
        galaxy_state: Current state of the galaxy
        vision_type: Type of vision (future, past, nexus, etc.)
        
    Returns:
        Dict containing the generated vision
    """
    system_prompt = f"""You are the Force itself, speaking through visions to a Force-sensitive individual. 

Generate a mystical, cryptic vision that fits the Star Wars universe. The vision should be:
- Symbolic and metaphorical, not literal
- Brief but impactful (2-4 sentences)
- Relevant to the character's Force alignment and current galactic situation
- Appropriately mysterious and open to interpretation

Force alignment context: {alignment_context}
Galaxy state: {galaxy_state}
Vision type: {vision_type}

Speak as the Force, showing glimpses of possibility, echoes of the past, or disturbances in the cosmic balance."""
    
    user_prompt = f"Show me a {vision_type} vision through the Force."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    payload = {
        "model": "nvidia/nemotron-mini-4b-instruct",
        "messages": messages,
        "temperature": 0.6,  # Higher for creative, mystical content
        "top_p": 0.9,
        "max_tokens": 300,
        "stream": False
    }
    
    try:
        response = query_nemotron_streaming(payload, stream=False)
        
        if 'choices' in response and response['choices']:
            vision_text = response['choices'][0].get('message', {}).get('content', '')
            return {
                'success': True,
                'vision_text': vision_text.strip(),
                'vision_type': vision_type,
                'raw_response': response
            }
        else:
            return {
                'success': False,
                'vision_text': "The Force remains silent, its mysteries hidden.",
                'error': 'Unexpected API response format'
            }
    
    except Exception as e:
        logger.error(f"Failed to generate Force vision: {str(e)}")
        return {
            'success': False,
            'vision_text': "The visions are clouded, difficult to see.",
            'error': str(e)
        }

def generate_quest_description(quest_context: str, faction_state: str, player_history: str) -> Dict[str, Any]:
    """
    Generate procedural quest description using Nemotron
    
    Args:
        quest_context: Type and context of the quest
        faction_state: Current faction tensions and conflicts
        player_history: Player's past actions and reputation
        
    Returns:
        Dict containing the generated quest details
    """
    system_prompt = f"""You are a quest generator for a Star Wars RPG. Create an immersive, lore-accurate quest that fits the current galactic situation and player context.

The quest should:
- Have clear objectives and stakes
- Fit within Star Wars canon and feel authentic
- Consider current faction tensions and conflicts
- Account for the player's reputation and past actions
- Be engaging and offer meaningful choices

Current galactic context: {faction_state}
Player context: {player_history}
Quest type and context: {quest_context}

Generate a quest title and compelling description that fits this context."""
    
    user_prompt = "Generate a quest that fits the current situation and player context."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    payload = {
        "model": "nvidia/nemotron-mini-4b-instruct",
        "messages": messages,
        "temperature": 0.4,
        "top_p": 0.8,
        "max_tokens": 512,
        "stream": False
    }
    
    try:
        response = query_nemotron_streaming(payload, stream=False)
        
        if 'choices' in response and response['choices']:
            quest_content = response['choices'][0].get('message', {}).get('content', '')
            
            # Try to extract title and description
            lines = quest_content.strip().split('\n')
            if len(lines) >= 2:
                title = lines[0].replace('Title:', '').replace('Quest:', '').strip()
                description = '\n'.join(lines[1:]).replace('Description:', '').strip()
            else:
                title = "Generated Quest"
                description = quest_content.strip()
            
            return {
                'success': True,
                'title': title,
                'description': description,
                'raw_response': response
            }
        else:
            return {
                'success': False,
                'title': "Emergency Assignment",
                'description': "A situation has arisen that requires immediate attention.",
                'error': 'Unexpected API response format'
            }
    
    except Exception as e:
        logger.error(f"Failed to generate quest description: {str(e)}")
        return {
            'success': False,
            'title': "Urgent Matter",
            'description': "Someone needs your help with an important task.",
            'error': str(e)
        }

def test_nvidia_api_connection() -> Dict[str, Any]:
    """
    Test connection to NVIDIA API
    
    Returns:
        Dict containing test results
    """
    test_payload = {
        "model": "nvidia/nemotron-mini-4b-instruct",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Connection successful' if you can hear me."}
        ],
        "temperature": 0.1,
        "max_tokens": 50,
        "stream": False
    }
    
    try:
        response = query_nemotron_streaming(test_payload, stream=False)
        
        if 'choices' in response and response['choices']:
            content = response['choices'][0].get('message', {}).get('content', '')
            return {
                'success': True,
                'message': 'NVIDIA API connection successful',
                'response_content': content,
                'api_key_valid': True
            }
        else:
            return {
                'success': False,
                'message': 'NVIDIA API returned unexpected response format',
                'api_key_valid': True,
                'response': response
            }
    
    except Exception as e:
        error_message = str(e)
        if '401' in error_message or 'unauthorized' in error_message.lower():
            return {
                'success': False,
                'message': 'NVIDIA API key is invalid or expired',
                'api_key_valid': False,
                'error': error_message
            }
        else:
            return {
                'success': False,
                'message': f'NVIDIA API connection failed: {error_message}',
                'api_key_valid': None,
                'error': error_message
            }

# Helper function for backward compatibility
def query_nvidia_nemotron(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Legacy function name for backward compatibility
    """
    return query_nemotron_streaming(payload, stream=False)
