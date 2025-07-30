from app import db
from models import NPCMemory, ForceAlignment, ThreatLevel
import json
import random
from datetime import datetime, timedelta

def update_npc_interaction(npc_name, user, interaction_type, interaction_data, session_id=None):
    """
    Update NPC memory with new interaction - core of reactive NPC system
    """
    # Get or create NPC memory
    npc_memory = NPCMemory.query.filter_by(npc_name=npc_name, user=user).first()
    if not npc_memory:
        npc_memory = create_new_npc_memory(npc_name, user, session_id)
    
    # Update interaction history
    interaction_history = json.loads(npc_memory.interaction_history) if npc_memory.interaction_history else []
    
    new_interaction = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': interaction_type,
        'data': interaction_data
    }
    
    interaction_history.append(new_interaction)
    npc_memory.interaction_history = json.dumps(interaction_history[-30:])  # Keep last 30 interactions
    
    # Update relationship levels based on interaction
    relationship_change = calculate_relationship_change(interaction_type, interaction_data, npc_memory)
    npc_memory.relationship_level = max(-100, min(100, npc_memory.relationship_level + relationship_change))
    
    # Update trust and fear levels
    trust_change, fear_change = calculate_trust_fear_changes(interaction_type, interaction_data, npc_memory)
    npc_memory.trust_level = max(0, min(100, npc_memory.trust_level + trust_change))
    npc_memory.fear_level = max(0, min(100, npc_memory.fear_level + fear_change))
    
    # Update known player actions
    update_npc_knowledge(npc_memory, interaction_type, interaction_data, user)
    
    # Update current mood based on recent interactions
    npc_memory.current_mood = calculate_npc_mood(npc_memory)
    
    npc_memory.last_interaction = datetime.utcnow()
    
    db.session.commit()
    
    return {
        'npc_name': npc_name,
        'relationship_change': relationship_change,
        'new_relationship': npc_memory.relationship_level,
        'new_trust': npc_memory.trust_level,
        'new_fear': npc_memory.fear_level,
        'new_mood': npc_memory.current_mood
    }

def create_new_npc_memory(npc_name, user, session_id):
    """
    Create new NPC memory with randomized personality
    """
    # Generate random personality traits
    personality_pool = [
        'friendly', 'suspicious', 'greedy', 'loyal', 'ambitious', 'cowardly', 'brave',
        'honest', 'deceitful', 'curious', 'indifferent', 'aggressive', 'peaceful',
        'force_sensitive', 'imperial_sympathizer', 'rebel_sympathizer', 'criminal',
        'law_abiding', 'xenophobic', 'tolerant', 'religious', 'secular', 'military',
        'civilian', 'merchant', 'noble', 'commoner', 'jedi', 'sith', 'dark_side',
        'light_side', 'bounty_hunter', 'pilot', 'mechanic', 'doctor', 'scholar'
    ]
    
    # Select 2-4 random personality traits
    num_traits = random.randint(2, 4)
    personality_traits = random.sample(personality_pool, num_traits)
    
    # Determine faction based on name patterns and traits
    faction = determine_npc_faction(npc_name, personality_traits)
    
    # Set initial relationship based on personality
    initial_relationship = calculate_initial_relationship(personality_traits)
    
    npc_memory = NPCMemory(
        npc_name=npc_name,
        user=user,
        relationship_level=initial_relationship,
        trust_level=random.randint(10, 40),
        fear_level=random.randint(0, 20),
        npc_faction=faction,
        personality_traits=json.dumps(personality_traits),
        current_mood='neutral',
        session_id=session_id
    )
    
    db.session.add(npc_memory)
    return npc_memory

def determine_npc_faction(npc_name, personality_traits):
    """
    Determine NPC faction based on name and personality
    """
    name_lower = npc_name.lower()
    
    # Check for obvious faction indicators in name
    if any(title in name_lower for title in ['captain', 'admiral', 'commander', 'lieutenant']):
        if 'imperial' in name_lower or 'empire' in name_lower:
            return 'Galactic Empire'
        elif 'rebel' in name_lower or 'alliance' in name_lower:
            return 'Rebel Alliance'
    
    if any(title in name_lower for title in ['lord', 'jabba', 'hutt']):
        return 'Hutt Cartel'
    
    if 'corporate' in name_lower or 'csa' in name_lower:
        return 'Corporate Sector Authority'
    
    # Check personality traits
    if 'imperial_sympathizer' in personality_traits:
        return 'Galactic Empire'
    elif 'rebel_sympathizer' in personality_traits:
        return 'Rebel Alliance'
    elif 'criminal' in personality_traits:
        return 'Hutt Cartel'
    elif 'merchant' in personality_traits:
        return 'Corporate Sector Authority'
    
    return 'Independent'

def calculate_initial_relationship(personality_traits):
    """
    Calculate initial relationship level based on personality
    """
    relationship = 0
    
    if 'friendly' in personality_traits:
        relationship += 20
    if 'suspicious' in personality_traits:
        relationship -= 15
    if 'honest' in personality_traits:
        relationship += 10
    if 'deceitful' in personality_traits:
        relationship -= 10
    if 'tolerant' in personality_traits:
        relationship += 15
    if 'xenophobic' in personality_traits:
        relationship -= 20
    
    return max(-50, min(50, relationship))

def calculate_relationship_change(interaction_type, interaction_data, npc_memory):
    """
    Calculate relationship change based on interaction type and NPC personality
    """
    personality_traits = json.loads(npc_memory.personality_traits) if npc_memory.personality_traits else []
    base_change = 0
    
    # Base changes by interaction type
    interaction_effects = {
        'dialogue': 2,
        'trade': 5,
        'quest_completion': 10,
        'quest_failure': -15,
        'betrayal': -50,
        'rescue': 25,
        'threat': -20,
        'bribe': 8,
        'lie_detected': -12,
        'truth_telling': 5,
        'force_power_witnessed': 0,  # Depends on power and NPC personality
        'combat_assistance': 20,
        'combat_against': -30
    }
    
    base_change = interaction_effects.get(interaction_type, 0)
    
    # Modify based on personality traits
    if interaction_type == 'bribe':
        if 'greedy' in personality_traits:
            base_change += 10
        elif 'honest' in personality_traits:
            base_change -= 15
    
    elif interaction_type == 'force_power_witnessed':
        power_used = interaction_data.get('power', '')
        if 'force_sensitive' in personality_traits:
            if 'jedi' in personality_traits or 'light_side' in personality_traits:
                if power_used in ['Force Heal', 'Force Sense']:
                    base_change += 10
                elif power_used in ['Force Choke', 'Force Lightning']:
                    base_change -= 20
            elif 'sith' in personality_traits or 'dark_side' in personality_traits:
                if power_used in ['Force Choke', 'Force Lightning']:
                    base_change += 15
                elif power_used in ['Force Heal']:
                    base_change -= 10
        else:
            # Non-Force sensitive NPCs fear Force powers
            base_change -= 5
    
    elif interaction_type == 'trade':
        if 'merchant' in personality_traits:
            base_change += 5
        if 'greedy' in personality_traits and interaction_data.get('profit', 0) > 100:
            base_change += 8
    
    elif interaction_type == 'dialogue':
        dialogue_tone = interaction_data.get('tone', 'neutral')
        if dialogue_tone == 'respectful' and 'noble' in personality_traits:
            base_change += 5
        elif dialogue_tone == 'threatening' and 'cowardly' in personality_traits:
            base_change -= 10
        elif dialogue_tone == 'friendly' and 'friendly' in personality_traits:
            base_change += 3
    
    # Apply modifiers based on current relationship
    if npc_memory.relationship_level < -50:
        # Hostile NPCs are harder to improve relations with
        if base_change > 0:
            base_change = int(base_change * 0.5)
    elif npc_memory.relationship_level > 50:
        # Friendly NPCs are easier to maintain good relations with
        if base_change < 0:
            base_change = int(base_change * 0.7)
    
    return base_change

def calculate_trust_fear_changes(interaction_type, interaction_data, npc_memory):
    """
    Calculate changes to trust and fear levels
    """
    personality_traits = json.loads(npc_memory.personality_traits) if npc_memory.personality_traits else []
    trust_change = 0
    fear_change = 0
    
    # Trust changes
    if interaction_type == 'quest_completion':
        trust_change += 8
    elif interaction_type == 'quest_failure':
        trust_change -= 5
    elif interaction_type == 'betrayal':
        trust_change -= 30
    elif interaction_type == 'truth_telling':
        trust_change += 5
    elif interaction_type == 'lie_detected':
        trust_change -= 10
    elif interaction_type == 'rescue':
        trust_change += 15
    
    # Fear changes
    if interaction_type == 'threat':
        fear_change += 15
        if 'cowardly' in personality_traits:
            fear_change += 10
    elif interaction_type == 'force_power_witnessed':
        power_used = interaction_data.get('power', '')
        if power_used in ['Force Choke', 'Force Lightning']:
            fear_change += 20
            if 'force_sensitive' not in personality_traits:
                fear_change += 10
        elif power_used == 'Force Heal':
            fear_change -= 5
    elif interaction_type == 'combat_against':
        fear_change += 25
    elif interaction_type == 'rescue':
        fear_change -= 10
    
    # Personality modifiers
    if 'brave' in personality_traits:
        fear_change = int(fear_change * 0.7)
    elif 'cowardly' in personality_traits:
        fear_change = int(fear_change * 1.3)
    
    if 'suspicious' in personality_traits:
        trust_change = int(trust_change * 0.8)
    elif 'loyal' in personality_traits:
        trust_change = int(trust_change * 1.2)
    
    return trust_change, fear_change

def update_npc_knowledge(npc_memory, interaction_type, interaction_data, user):
    """
    Update NPC's knowledge about the player's actions and reputation
    """
    known_actions = json.loads(npc_memory.known_player_actions) if npc_memory.known_player_actions else []
    
    # Get player's current threat level and Force alignment for context
    threat_level = ThreatLevel.query.filter_by(user=user).first()
    force_alignment = ForceAlignment.query.filter_by(user=user).first()
    
    new_knowledge = {
        'timestamp': datetime.utcnow().isoformat(),
        'interaction_type': interaction_type,
        'learned_info': []
    }
    
    # What the NPC learns depends on interaction type and their connections
    personality_traits = json.loads(npc_memory.personality_traits) if npc_memory.personality_traits else []
    
    if interaction_type == 'force_power_witnessed':
        new_knowledge['learned_info'].append(f"Player is Force-sensitive")
        if force_alignment and abs(force_alignment.net_alignment) > 50:
            alignment_desc = "strongly aligned to the Dark Side" if force_alignment.net_alignment < -50 else "strongly aligned to the Light Side"
            new_knowledge['learned_info'].append(f"Player is {alignment_desc}")
    
    elif interaction_type == 'dialogue' and 'criminal' in personality_traits:
        # Criminal NPCs learn about player's reputation in underworld
        if threat_level and threat_level.criminal_reputation > 30:
            new_knowledge['learned_info'].append("Player has criminal connections")
        if threat_level and threat_level.bounty_amount > 1000:
            new_knowledge['learned_info'].append("Player has active bounties")
    
    elif interaction_type == 'trade' and 'merchant' in personality_traits:
        # Merchants learn about player's resources and connections
        trade_value = interaction_data.get('value', 0)
        if trade_value > 5000:
            new_knowledge['learned_info'].append("Player has significant resources")
    
    elif 'imperial_sympathizer' in personality_traits:
        # Imperial sympathizers report to authorities
        if threat_level and threat_level.imperial_awareness > 20:
            new_knowledge['learned_info'].append("Player is wanted by Imperial authorities")
            # NPC might report this information
            if random.random() < 0.3:  # 30% chance to report
                new_knowledge['learned_info'].append("Reported player location to Imperials")
                
                # This would trigger threat escalation
                from services.threat_scaler import update_threat_level
                update_threat_level(
                    user=user,
                    action_type='reported_by_npc',
                    severity=2,
                    witnesses=[npc_memory.npc_name],
                    session_id=npc_memory.session_id
                )
    
    # Add faction-specific knowledge
    if npc_memory.npc_faction and npc_memory.npc_faction != 'Independent':
        faction_knowledge = get_faction_specific_knowledge(npc_memory.npc_faction, user, threat_level)
        new_knowledge['learned_info'].extend(faction_knowledge)
    
    # Only add if NPC learned something new
    if new_knowledge['learned_info']:
        known_actions.append(new_knowledge)
        npc_memory.known_player_actions = json.dumps(known_actions[-20:])  # Keep last 20 pieces of knowledge

def get_faction_specific_knowledge(faction, user, threat_level):
    """
    Get faction-specific knowledge about the player
    """
    knowledge = []
    
    if faction == 'Galactic Empire' and threat_level:
        if threat_level.imperial_awareness > 50:
            knowledge.append("Player is a high-priority Imperial target")
        elif threat_level.imperial_awareness > 20:
            knowledge.append("Player is known to Imperial Intelligence")
    
    elif faction == 'Rebel Alliance' and threat_level:
        if threat_level.rebel_awareness > 30:
            knowledge.append("Player is known to Rebel Intelligence")
        if threat_level.imperial_awareness > 40:
            knowledge.append("Player might be useful to the Rebellion")
    
    elif faction == 'Hutt Cartel' and threat_level:
        if threat_level.criminal_reputation > 40:
            knowledge.append("Player has significant underworld reputation")
        if threat_level.bounty_amount > 5000:
            knowledge.append("Player has valuable bounties")
    
    return knowledge

def calculate_npc_mood(npc_memory):
    """
    Calculate NPC's current mood based on recent interactions
    """
    relationship = npc_memory.relationship_level
    trust = npc_memory.trust_level
    fear = npc_memory.fear_level
    
    # Get recent interactions (last 5)
    interaction_history = json.loads(npc_memory.interaction_history) if npc_memory.interaction_history else []
    recent_interactions = interaction_history[-5:]
    
    # Count positive vs negative recent interactions
    positive_interactions = sum(1 for i in recent_interactions if i['type'] in ['dialogue', 'trade', 'quest_completion', 'rescue', 'truth_telling'])
    negative_interactions = sum(1 for i in recent_interactions if i['type'] in ['betrayal', 'threat', 'quest_failure', 'lie_detected', 'combat_against'])
    
    # Calculate mood based on relationship, trust, fear, and recent interactions
    mood_score = relationship + trust - fear + (positive_interactions * 10) - (negative_interactions * 15)
    
    if mood_score >= 60:
        return 'enthusiastic'
    elif mood_score >= 30:
        return 'friendly'
    elif mood_score >= 10:
        return 'pleased'
    elif mood_score >= -10:
        return 'neutral'
    elif mood_score >= -30:
        return 'wary'
    elif mood_score >= -60:
        return 'hostile'
    else:
        return 'vengeful'

def get_npc_memory(npc_name, user, session_id=None):
    """
    Get NPC memory for a specific NPC and user
    """
    return NPCMemory.query.filter_by(npc_name=npc_name, user=user).first()

def build_npc_context(npc_memory, situation='', player_action=''):
    """
    Build context for NPC dialogue generation based on memory and current situation
    """
    if not npc_memory:
        return {
            'system_prompt': "You are a neutral NPC in the Star Wars universe. Respond appropriately to the situation.",
            'user_prompt': f"Situation: {situation}. Player action: {player_action}",
            'metadata': {'relationship': 0, 'mood': 'neutral'}
        }
    
    personality_traits = json.loads(npc_memory.personality_traits) if npc_memory.personality_traits else []
    known_actions = json.loads(npc_memory.known_player_actions) if npc_memory.known_player_actions else []
    
    # Build personality description
    personality_desc = build_personality_description(personality_traits)
    
    # Build relationship context
    relationship_context = build_relationship_context(npc_memory)
    
    # Build knowledge context
    knowledge_context = build_knowledge_context(known_actions)
    
    # Build system prompt
    system_prompt = f"""You are {npc_memory.npc_name}, an NPC in the Star Wars universe.
    
Personality: {personality_desc}
Faction: {npc_memory.npc_faction}
Current mood: {npc_memory.current_mood}

Relationship with player: {relationship_context}
Knowledge about player: {knowledge_context}

Respond in character, taking into account your personality, relationship with the player, and what you know about them. Keep responses concise and immersive."""
    
    # Build user prompt
    user_prompt = f"""Current situation: {situation}
Player's recent action: {player_action}

How do you respond?"""
    
    # Calculate relationship change potential
    relationship_change = 0
    if npc_memory.current_mood in ['enthusiastic', 'friendly']:
        relationship_change = 2
    elif npc_memory.current_mood in ['hostile', 'vengeful']:
        relationship_change = -3
    
    return {
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'metadata': {
            'relationship': npc_memory.relationship_level,
            'trust': npc_memory.trust_level,
            'fear': npc_memory.fear_level,
            'mood': npc_memory.current_mood,
            'faction': npc_memory.npc_faction
        },
        'relationship_change': relationship_change
    }

def build_personality_description(personality_traits):
    """
    Build human-readable personality description from traits
    """
    if not personality_traits:
        return "A typical individual with no distinctive personality traits."
    
    # Group traits by category
    social_traits = [t for t in personality_traits if t in ['friendly', 'suspicious', 'honest', 'deceitful', 'tolerant', 'xenophobic']]
    behavioral_traits = [t for t in personality_traits if t in ['greedy', 'loyal', 'ambitious', 'cowardly', 'brave', 'aggressive', 'peaceful']]
    affiliation_traits = [t for t in personality_traits if t in ['imperial_sympathizer', 'rebel_sympathizer', 'criminal', 'law_abiding']]
    force_traits = [t for t in personality_traits if t in ['force_sensitive', 'jedi', 'sith', 'dark_side', 'light_side']]
    profession_traits = [t for t in personality_traits if t in ['merchant', 'noble', 'bounty_hunter', 'pilot', 'mechanic', 'doctor', 'scholar']]
    
    description_parts = []
    
    if social_traits:
        description_parts.append(f"Socially: {', '.join(social_traits)}")
    if behavioral_traits:
        description_parts.append(f"Behavior: {', '.join(behavioral_traits)}")
    if affiliation_traits:
        description_parts.append(f"Affiliations: {', '.join(affiliation_traits)}")
    if force_traits:
        description_parts.append(f"Force connection: {', '.join(force_traits)}")
    if profession_traits:
        description_parts.append(f"Profession: {', '.join(profession_traits)}")
    
    return ". ".join(description_parts) + "."

def build_relationship_context(npc_memory):
    """
    Build relationship context description
    """
    relationship = npc_memory.relationship_level
    trust = npc_memory.trust_level
    fear = npc_memory.fear_level
    
    relationship_desc = ""
    if relationship >= 50:
        relationship_desc = "Very positive relationship - considers player a close ally"
    elif relationship >= 20:
        relationship_desc = "Positive relationship - friendly towards player"
    elif relationship >= -20:
        relationship_desc = "Neutral relationship - no strong feelings either way"
    elif relationship >= -50:
        relationship_desc = "Negative relationship - distrusts or dislikes player"
    else:
        relationship_desc = "Very negative relationship - considers player an enemy"
    
    trust_desc = ""
    if trust >= 70:
        trust_desc = "Trusts player completely"
    elif trust >= 40:
        trust_desc = "Generally trusts player"
    elif trust >= 20:
        trust_desc = "Somewhat trusts player"
    else:
        trust_desc = "Does not trust player"
    
    fear_desc = ""
    if fear >= 70:
        fear_desc = "Terrified of player"
    elif fear >= 40:
        fear_desc = "Afraid of player"
    elif fear >= 20:
        fear_desc = "Wary of player"
    else:
        fear_desc = "Not afraid of player"
    
    return f"{relationship_desc}. {trust_desc}. {fear_desc}."

def build_knowledge_context(known_actions):
    """
    Build context of what the NPC knows about the player
    """
    if not known_actions:
        return "Knows very little about the player's background or activities."
    
    # Extract key knowledge points
    force_sensitive = any("Force-sensitive" in str(action.get('learned_info', [])) for action in known_actions)
    imperial_target = any("Imperial" in str(action.get('learned_info', [])) for action in known_actions)
    criminal_rep = any("criminal" in str(action.get('learned_info', [])) for action in known_actions)
    has_resources = any("resources" in str(action.get('learned_info', [])) for action in known_actions)
    
    knowledge_points = []
    if force_sensitive:
        knowledge_points.append("knows player is Force-sensitive")
    if imperial_target:
        knowledge_points.append("aware of player's Imperial entanglements")
    if criminal_rep:
        knowledge_points.append("knows about player's criminal connections")
    if has_resources:
        knowledge_points.append("believes player has significant resources")
    
    if knowledge_points:
        return f"Knows the following about the player: {', '.join(knowledge_points)}."
    else:
        return "Has some knowledge about the player but nothing particularly significant."

def get_npc_dialogue_history(npc_name, user, limit=10):
    """
    Get recent dialogue history with an NPC
    """
    npc_memory = get_npc_memory(npc_name, user)
    if not npc_memory:
        return []
    
    interaction_history = json.loads(npc_memory.interaction_history) if npc_memory.interaction_history else []
    
    # Filter for dialogue interactions
    dialogue_history = [
        interaction for interaction in interaction_history 
        if interaction.get('type') in ['dialogue', 'contextual_dialogue']
    ]
    
    return dialogue_history[-limit:]

def simulate_npc_network_effects(user, action_type, involved_npc, session_id=None):
    """
    Simulate how actions with one NPC affect relationships with other NPCs in their network
    """
    involved_memory = get_npc_memory(involved_npc, user)
    if not involved_memory:
        return []
    
    # Find NPCs in the same faction or with similar personality traits
    similar_npcs = NPCMemory.query.filter_by(user=user).filter(
        NPCMemory.npc_name != involved_npc
    ).all()
    
    network_effects = []
    
    for npc in similar_npcs:
        if npc.npc_faction == involved_memory.npc_faction and npc.npc_faction != 'Independent':
            # Same faction NPCs are affected by actions against their faction members
            relationship_change = 0
            
            if action_type in ['betrayal', 'combat_against', 'threat']:
                relationship_change = -random.randint(5, 15)
            elif action_type in ['rescue', 'quest_completion', 'trade']:
                relationship_change = random.randint(2, 8)
            
            if relationship_change != 0:
                npc.relationship_level = max(-100, min(100, npc.relationship_level + relationship_change))
                
                # Record the network effect
                interaction_history = json.loads(npc.interaction_history) if npc.interaction_history else []
                interaction_history.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'type': 'network_effect',
                    'data': {
                        'source_npc': involved_npc,
                        'action_type': action_type,
                        'relationship_change': relationship_change
                    }
                })
                npc.interaction_history = json.dumps(interaction_history[-30:])
                
                network_effects.append({
                    'npc_name': npc.npc_name,
                    'relationship_change': relationship_change,
                    'reason': f"Faction loyalty to {involved_npc}"
                })
    
    db.session.commit()
    return network_effects

def get_faction_npc_summary(faction_name, user):
    """
    Get summary of relationships with all NPCs in a faction
    """
    faction_npcs = NPCMemory.query.filter_by(user=user, npc_faction=faction_name).all()
    
    if not faction_npcs:
        return {'faction': faction_name, 'npc_count': 0, 'average_relationship': 0, 'npcs': []}
    
    total_relationship = sum(npc.relationship_level for npc in faction_npcs)
    average_relationship = total_relationship / len(faction_npcs)
    
    npc_summaries = []
    for npc in faction_npcs:
        npc_summaries.append({
            'name': npc.npc_name,
            'relationship': npc.relationship_level,
            'trust': npc.trust_level,
            'fear': npc.fear_level,
            'mood': npc.current_mood,
            'last_interaction': npc.last_interaction.isoformat() if npc.last_interaction else None
        })
    
    return {
        'faction': faction_name,
        'npc_count': len(faction_npcs),
        'average_relationship': round(average_relationship, 1),
        'npcs': npc_summaries
    }
