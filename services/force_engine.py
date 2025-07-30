from app import db
from models import ForceAlignment, WorldEvent, NPCMemory, SessionState
import json
import random
from datetime import datetime, timedelta

def update_force_alignment(user, action_type, action_description='', force_magnitude=1, witnesses=[], session_id=None):
    """
    Update player Force alignment with cascading consequences following the Final Rule
    """
    # Get or create Force alignment for user
    alignment = ForceAlignment.query.filter_by(user=user).first()
    if not alignment:
        alignment = ForceAlignment(
            user=user,
            session_id=session_id
        )
        db.session.add(alignment)
    
    # Calculate alignment change based on action and magnitude
    alignment_change = 0
    if action_type == 'light':
        alignment_change = force_magnitude * random.randint(3, 8)
        alignment.light_side_points += alignment_change
    elif action_type == 'dark':
        alignment_change = -(force_magnitude * random.randint(3, 8))
        alignment.dark_side_points += abs(alignment_change)
    
    # Record Force event
    force_events = json.loads(alignment.force_events) if alignment.force_events else []
    force_event = {
        'timestamp': datetime.utcnow().isoformat(),
        'action_type': action_type,
        'description': action_description,
        'magnitude': force_magnitude,
        'alignment_change': alignment_change,
        'witnesses': witnesses
    }
    force_events.append(force_event)
    alignment.force_events = json.dumps(force_events[-50:])  # Keep last 50 events
    
    # Update alignment history
    alignment_history = json.loads(alignment.alignment_history) if alignment.alignment_history else []
    alignment_history.append({
        'timestamp': datetime.utcnow().isoformat(),
        'net_alignment': alignment.net_alignment,
        'change': alignment_change
    })
    alignment.alignment_history = json.dumps(alignment_history[-100:])  # Keep last 100 changes
    
    # Update corruption level for Dark Side users
    if alignment.net_alignment < -50:
        corruption_increase = max(0, abs(alignment.net_alignment) - 50) // 10
        alignment.corruption_level = min(100, alignment.corruption_level + corruption_increase)
    elif alignment.net_alignment > 25:
        # Light Side can reduce corruption
        alignment.corruption_level = max(0, alignment.corruption_level - 1)
    
    alignment.last_force_event = datetime.utcnow()
    
    # Check for Force sensitivity awakening
    total_force_points = alignment.light_side_points + alignment.dark_side_points
    if not alignment.force_sensitive and total_force_points >= 15:
        alignment.force_sensitive = True
        force_event['awakening'] = True
    
    # Generate cascading consequences
    consequences = trigger_force_consequences(alignment, action_type, force_magnitude, witnesses, session_id)
    
    # Update NPC reactions to Force events
    npc_reactions = update_npc_force_reactions(user, alignment, action_type, witnesses, session_id)
    
    # Unlock new Force powers based on alignment
    unlocked_powers = check_force_power_unlocks(alignment)
    
    db.session.commit()
    
    return {
        'alignment_change': alignment_change,
        'new_alignment': alignment.net_alignment,
        'alignment_description': alignment.alignment_description,
        'corruption_level': alignment.corruption_level,
        'force_sensitive': alignment.force_sensitive,
        'consequences': consequences,
        'npc_reactions': npc_reactions,
        'unlocked_powers': unlocked_powers
    }

def trigger_force_consequences(alignment, action_type, magnitude, witnesses, session_id):
    """
    Trigger cascading consequences based on Force actions - core of immersive logic
    """
    consequences = []
    
    # Magnitude-based consequences
    if magnitude >= 7:  # Major Force event
        if action_type == 'dark':
            consequences.append("Your use of the Dark Side sends ripples through the Force")
            create_force_disturbance_event(alignment.user, 'dark_side_surge', session_id)
        elif action_type == 'light':
            consequences.append("Your connection to the Light Side strengthens")
            create_force_disturbance_event(alignment.user, 'light_side_beacon', session_id)
    
    # Alignment threshold consequences
    net_alignment = alignment.net_alignment
    
    if net_alignment <= -75 and not has_recent_consequence(alignment.user, 'dark_side_corruption'):
        consequences.append("Dark Side corruption manifests physically - your eyes show hints of Sith yellow")
        trigger_environmental_response(alignment.user, 'dark_corruption', session_id)
        mark_consequence(alignment.user, 'dark_side_corruption')
    
    elif net_alignment >= 75 and not has_recent_consequence(alignment.user, 'light_side_aura'):
        consequences.append("Your Light Side presence becomes palpable to Force-sensitives")
        trigger_environmental_response(alignment.user, 'light_aura', session_id)
        mark_consequence(alignment.user, 'light_side_aura')
    
    # Corruption-based consequences
    if alignment.corruption_level >= 50:
        consequences.append("Dark Side corruption affects your judgment and appearance")
        if alignment.corruption_level >= 80:
            consequences.append("Severe corruption: NPCs react with fear or reverence")
    
    # Witness-based consequences
    for witness in witnesses:
        if witness.startswith('Imperial'):
            consequences.append(f"{witness} reports your Force abilities to Imperial Intelligence")
            update_faction_force_awareness('Galactic Empire', alignment.user, magnitude, session_id)
        elif witness.startswith('Rebel'):
            consequences.append(f"{witness} considers recruiting you for the Rebellion")
            update_faction_force_awareness('Rebel Alliance', alignment.user, magnitude, session_id)
    
    return consequences

def create_force_disturbance_event(user, disturbance_type, session_id):
    """
    Create galaxy-wide Force disturbance events
    """
    event_data = {
        'dark_side_surge': {
            'title': 'Dark Side Disturbance Detected',
            'description': 'Force-sensitives across the galaxy feel a tremor in the Force as someone embraces the Dark Side with unusual intensity.',
            'impact': 3
        },
        'light_side_beacon': {
            'title': 'Light Side Resonance',
            'description': 'A beacon of Light Side energy manifests, offering hope to those who can feel the Force.',
            'impact': 2
        }
    }
    
    if disturbance_type in event_data:
        data = event_data[disturbance_type]
        event = WorldEvent(
            event_title=data['title'],
            event_description=data['description'],
            event_type='force',
            galactic_impact=data['impact'],
            triggered_by_player=user,
            session_id=session_id
        )
        db.session.add(event)

def trigger_environmental_response(user, response_type, session_id):
    """
    Trigger environmental changes based on Force alignment
    """
    responses = {
        'dark_corruption': "Wildlife flees your presence. Technology occasionally malfunctions around you.",
        'light_aura': "Animals are drawn to you. Healing occurs faster in your presence."
    }
    
    if response_type in responses:
        # This would integrate with the world state to affect environment
        # For now, we store it as a consequence
        pass

def update_npc_force_reactions(user, alignment, action_type, witnesses, session_id):
    """
    Update NPC reactions based on Force events - reactive NPC system
    """
    reactions = []
    
    # Update all NPCs that have interacted with the player
    npcs = NPCMemory.query.filter_by(user=user).all()
    
    for npc in npcs:
        personality = json.loads(npc.personality_traits) if npc.personality_traits else []
        
        # Force-sensitive NPCs react more strongly
        if 'force_sensitive' in personality:
            if action_type == 'dark':
                if 'jedi' in personality or 'light_side' in personality:
                    npc.fear_level = min(100, npc.fear_level + 20)
                    npc.relationship_level = max(-100, npc.relationship_level - 15)
                    reactions.append(f"{npc.npc_name} senses the darkness growing within you")
                elif 'sith' in personality or 'dark_side' in personality:
                    npc.relationship_level = min(100, npc.relationship_level + 10)
                    reactions.append(f"{npc.npc_name} approves of your embrace of power")
            
            elif action_type == 'light':
                if 'jedi' in personality or 'light_side' in personality:
                    npc.relationship_level = min(100, npc.relationship_level + 10)
                    npc.trust_level = min(100, npc.trust_level + 5)
                    reactions.append(f"{npc.npc_name} feels the Light Side strengthen in you")
                elif 'sith' in personality or 'dark_side' in personality:
                    npc.relationship_level = max(-100, npc.relationship_level - 10)
                    reactions.append(f"{npc.npc_name} is disgusted by your weakness")
        
        # Non-Force sensitive NPCs react to corruption and obvious displays
        else:
            if alignment.corruption_level > 50:
                npc.fear_level = min(100, npc.fear_level + 5)
                if alignment.corruption_level > 80:
                    reactions.append(f"{npc.npc_name} is unsettled by your changed appearance")
        
        # Update NPC memory with Force event
        interaction_history = json.loads(npc.interaction_history) if npc.interaction_history else []
        interaction_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'force_event_witnessed',
            'action_type': action_type,
            'alignment_change': alignment.net_alignment
        })
        npc.interaction_history = json.dumps(interaction_history[-20:])
        npc.last_interaction = datetime.utcnow()
    
    db.session.commit()
    return reactions

def update_faction_force_awareness(faction_name, user, magnitude, session_id):
    """
    Update faction awareness of player's Force abilities
    """
    from services.faction_ai import update_faction_awareness
    
    awareness_change = magnitude * 5
    relationship_change = 0
    
    # Imperial faction reactions
    if faction_name == 'Galactic Empire':
        relationship_change = -magnitude * 3  # Empire is hostile to unsanctioned Force users
        action_desc = "Unsanctioned Force use detected"
    
    # Rebel faction reactions  
    elif faction_name == 'Rebel Alliance':
        relationship_change = magnitude * 2  # Rebels want to recruit Force users
        action_desc = "Potential Force-sensitive ally identified"
    
    if awareness_change > 0:
        update_faction_awareness(
            faction_name=faction_name,
            user=user,
            relationship_change=relationship_change,
            awareness_change=awareness_change,
            action_description=action_desc,
            session_id=session_id
        )

def check_force_power_unlocks(alignment):
    """
    Check for newly unlocked Force powers based on alignment and experience
    """
    unlocked = []
    current_powers = json.loads(alignment.force_powers) if alignment.force_powers else []
    
    total_force_exp = alignment.light_side_points + alignment.dark_side_points
    net_alignment = alignment.net_alignment
    
    # Basic powers
    if 'Force Sense' not in current_powers and total_force_exp >= 10:
        current_powers.append('Force Sense')
        unlocked.append('Force Sense')
    
    if 'Force Push' not in current_powers and total_force_exp >= 25:
        current_powers.append('Force Push')
        unlocked.append('Force Push')
    
    # Light Side powers
    if net_alignment >= 25:
        if 'Force Heal' not in current_powers and total_force_exp >= 40:
            current_powers.append('Force Heal')
            unlocked.append('Force Heal')
        
        if 'Battle Meditation' not in current_powers and net_alignment >= 60 and total_force_exp >= 80:
            current_powers.append('Battle Meditation')
            unlocked.append('Battle Meditation')
    
    # Dark Side powers
    if net_alignment <= -25:
        if 'Force Choke' not in current_powers and total_force_exp >= 30:
            current_powers.append('Force Choke')
            unlocked.append('Force Choke')
        
        if 'Force Lightning' not in current_powers and net_alignment <= -60 and total_force_exp >= 100:
            current_powers.append('Force Lightning')
            unlocked.append('Force Lightning')
    
    # Gray/Balanced powers
    if -25 <= net_alignment <= 25:
        if 'Force Stealth' not in current_powers and total_force_exp >= 50:
            current_powers.append('Force Stealth')
            unlocked.append('Force Stealth')
    
    # Update powers list
    alignment.force_powers = json.dumps(current_powers)
    
    return unlocked

def generate_force_vision(user, trigger='meditation', session_id=None):
    """
    Generate Force visions based on alignment and galaxy state
    """
    alignment = ForceAlignment.query.filter_by(user=user).first()
    if not alignment or not alignment.force_sensitive:
        return None
    
    # Vision probability based on Force sensitivity and alignment strength
    vision_chance = min(0.8, abs(alignment.net_alignment) / 100 + 0.2)
    if random.random() > vision_chance:
        return None
    
    # Get current galaxy state for vision context
    session = SessionState.query.filter_by(session_id=session_id).first() if session_id else None
    
    vision_types = {
        'future_conflict': generate_conflict_vision(alignment, session),
        'past_echo': generate_past_echo_vision(alignment),
        'force_nexus': generate_nexus_vision(alignment),
        'personal_destiny': generate_destiny_vision(alignment, user),
        'galactic_consequence': generate_consequence_vision(alignment, session)
    }
    
    # Select vision type based on alignment and trigger
    if alignment.net_alignment > 50:
        vision_weights = {'future_conflict': 20, 'past_echo': 30, 'personal_destiny': 30, 'galactic_consequence': 20}
    elif alignment.net_alignment < -50:
        vision_weights = {'future_conflict': 35, 'force_nexus': 25, 'personal_destiny': 25, 'galactic_consequence': 15}
    else:
        vision_weights = {'past_echo': 20, 'force_nexus': 30, 'personal_destiny': 25, 'galactic_consequence': 25}
    
    vision_type = weighted_random_choice(vision_weights)
    vision_data = vision_types[vision_type]
    
    # Record vision in Force events
    force_events = json.loads(alignment.force_events) if alignment.force_events else []
    force_events.append({
        'timestamp': datetime.utcnow().isoformat(),
        'type': 'vision',
        'vision_type': vision_type,
        'trigger': trigger,
        'content': vision_data['vision_text']
    })
    alignment.force_events = json.dumps(force_events[-50:])
    
    db.session.commit()
    
    return vision_data

def generate_conflict_vision(alignment, session):
    """Generate vision of future conflicts"""
    visions = [
        "You see flashes of starships engaged in fierce battle, the outcome uncertain.",
        "A vision of worlds in flames, empires rising and falling in the galactic dance.",
        "You witness a confrontation between Force users, lightsabers clashing in darkness."
    ]
    
    return {
        'vision_text': random.choice(visions),
        'vision_type': 'future_conflict',
        'future_hints': ['Prepare for battle', 'Allies will be crucial', 'Choices matter'],
        'force_magnitude': random.randint(3, 7)
    }

def generate_past_echo_vision(alignment):
    """Generate vision of past events"""
    visions = [
        "Ancient Jedi walk the halls of a temple long since fallen to ruin.",
        "You feel the echo of a great betrayal, Jedi turning against their masters.",
        "Sith Lords of old whisper secrets of power and domination."
    ]
    
    return {
        'vision_text': random.choice(visions),
        'vision_type': 'past_echo',
        'force_magnitude': random.randint(2, 5)
    }

def generate_nexus_vision(alignment):
    """Generate vision related to Force nexus points"""
    visions = [
        "A hidden temple calls to you, its location just beyond clear memory.",
        "You sense a disturbance in the Force, centered on a place of great power.",
        "Dark energies swirl around an ancient stronghold, begging investigation."
    ]
    
    return {
        'vision_text': random.choice(visions),
        'vision_type': 'force_nexus',
        'future_hints': ['Seek the hidden temple', 'Power awaits the worthy'],
        'force_magnitude': random.randint(4, 8)
    }

def generate_destiny_vision(alignment, user):
    """Generate personal destiny vision"""
    if alignment.net_alignment > 25:
        visions = [
            "You see yourself standing as a beacon of hope in dark times.",
            "A vision of you training others in the ways of the Light.",
            "You witness yourself making a choice that saves countless lives."
        ]
    elif alignment.net_alignment < -25:
        visions = [
            "You see yourself wielding power over others, bending them to your will.",
            "A vision of conquest, systems falling before your might.",
            "You witness yourself standing triumphant over fallen enemies."
        ]
    else:
        visions = [
            "You see yourself walking a path between light and darkness.",
            "A vision of you making choices that will define your legacy.",
            "You witness yourself bringing balance to a divided galaxy."
        ]
    
    return {
        'vision_text': random.choice(visions),
        'vision_type': 'personal_destiny',
        'alignment_requirement': alignment.net_alignment,
        'force_magnitude': random.randint(3, 6)
    }

def generate_consequence_vision(alignment, session):
    """Generate vision of galactic consequences"""
    visions = [
        "You see the ripple effects of your actions spreading across star systems.",
        "A vision of how your choices shape the fate of countless beings.",
        "You witness the long-term consequences of decisions yet to be made."
    ]
    
    return {
        'vision_text': random.choice(visions),
        'vision_type': 'galactic_consequence',
        'future_hints': ['Every action has consequences', 'Think beyond the immediate'],
        'force_magnitude': random.randint(2, 6)
    }

def use_force_power(user, power_name, target='', intent='neutral', power_level=1, session_id=None):
    """
    Use a Force power with alignment and narrative consequences
    """
    alignment = ForceAlignment.query.filter_by(user=user).first()
    if not alignment or not alignment.force_sensitive:
        return {'success': False, 'effect_description': 'You are not Force-sensitive'}
    
    available_powers = json.loads(alignment.force_powers) if alignment.force_powers else []
    if power_name not in available_powers:
        return {'success': False, 'effect_description': f'You have not learned {power_name}'}
    
    # Calculate success based on alignment and power level
    success_chance = calculate_power_success_chance(alignment, power_name, power_level)
    success = random.random() < success_chance
    
    # Generate effect description
    effect_description = generate_power_effect(power_name, target, intent, power_level, success)
    
    # Calculate alignment impact
    alignment_change = calculate_power_alignment_impact(power_name, intent, power_level, success)
    
    # Apply Force cost (fatigue/corruption)
    force_cost = power_level * 2
    if intent == 'dark':
        force_cost += 3
        alignment.corruption_level = min(100, alignment.corruption_level + 1)
    
    # Update alignment if significant impact
    if abs(alignment_change) >= 3:
        update_force_alignment(
            user=user,
            action_type='dark' if alignment_change < 0 else 'light',
            action_description=f"Used {power_name} with {intent} intent",
            force_magnitude=abs(alignment_change) // 3,
            session_id=session_id
        )
    
    # Generate consequences based on power use
    consequences = generate_power_consequences(power_name, intent, power_level, target, success)
    
    # Check for witnesses and their reactions
    witnesses_affected = []
    if target and target != 'self':
        witnesses_affected = update_power_witnesses(user, power_name, target, session_id)
    
    db.session.commit()
    
    return {
        'success': success,
        'effect_description': effect_description,
        'alignment_change': alignment_change,
        'force_cost': force_cost,
        'consequences': consequences,
        'witnesses_affected': witnesses_affected
    }

def calculate_power_success_chance(alignment, power_name, power_level):
    """Calculate success chance for Force power use"""
    base_chances = {
        'Force Sense': 0.9,
        'Force Push': 0.8,
        'Force Heal': 0.7,
        'Force Choke': 0.6,
        'Force Lightning': 0.5,
        'Battle Meditation': 0.4,
        'Force Stealth': 0.7
    }
    
    base_chance = base_chances.get(power_name, 0.6)
    
    # Adjust for power level (higher level = harder)
    chance = base_chance - (power_level - 1) * 0.1
    
    # Adjust for alignment compatibility
    dark_powers = ['Force Choke', 'Force Lightning']
    light_powers = ['Force Heal', 'Battle Meditation']
    
    if power_name in dark_powers and alignment.net_alignment < -25:
        chance += 0.2
    elif power_name in light_powers and alignment.net_alignment > 25:
        chance += 0.2
    elif power_name in dark_powers and alignment.net_alignment > 25:
        chance -= 0.3
    elif power_name in light_powers and alignment.net_alignment < -25:
        chance -= 0.3
    
    return max(0.1, min(0.95, chance))

def generate_power_effect(power_name, target, intent, power_level, success):
    """Generate descriptive text for Force power effects"""
    if not success:
        return f"Your attempt to use {power_name} fails. The Force does not bend to your will."
    
    effects = {
        'Force Sense': f"You extend your senses through the Force, gaining awareness of your surroundings.",
        'Force Push': f"You unleash kinetic energy through the Force, pushing {target or 'objects'} away with tremendous force.",
        'Force Heal': f"Healing energy flows through the Force, mending wounds and restoring vitality.",
        'Force Choke': f"You constrict {target}'s windpipe through the Force, demonstrating your power over life and death.",
        'Force Lightning': f"Dark Side energy crackles from your fingertips, striking {target} with deadly lightning.",
        'Battle Meditation': f"You reach out through the Force, bolstering allies and undermining enemies in combat.",
        'Force Stealth': f"You bend light and perception around yourself, becoming nearly invisible to observers."
    }
    
    base_effect = effects.get(power_name, f"You successfully use {power_name}")
    
    # Modify based on power level
    if power_level >= 7:
        base_effect += " The power you channel is extraordinary."
    elif power_level >= 4:
        base_effect += " The effect is strong and focused."
    
    return base_effect

def calculate_power_alignment_impact(power_name, intent, power_level, success):
    """Calculate Force alignment impact from power use"""
    if not success:
        return 0
    
    base_impacts = {
        'Force Heal': 5,
        'Battle Meditation': 3,
        'Force Choke': -8,
        'Force Lightning': -12,
        'Force Sense': 0,
        'Force Push': 0,
        'Force Stealth': 0
    }
    
    impact = base_impacts.get(power_name, 0)
    
    # Modify based on intent
    if intent == 'dark' and impact >= 0:
        impact -= 3
    elif intent == 'light' and impact <= 0:
        impact += 2
    elif intent == 'selfish':
        impact -= 1
    elif intent == 'selfless':
        impact += 2
    
    # Scale with power level
    impact = int(impact * (power_level / 5))
    
    return impact

def generate_power_consequences(power_name, intent, power_level, target, success):
    """Generate narrative consequences for Force power use"""
    consequences = []
    
    if not success:
        consequences.append("Your failed attempt draws unwanted attention")
        return consequences
    
    # Power-specific consequences
    if power_name == 'Force Lightning' and power_level >= 5:
        consequences.append("The destructive display marks you as a dangerous Force user")
    elif power_name == 'Force Heal' and power_level >= 6:
        consequences.append("Your healing abilities become known to those in need")
    elif power_name == 'Force Choke':
        consequences.append("Your display of deadly power intimidates witnesses")
    
    # Intent-based consequences
    if intent == 'dark':
        consequences.append("The Dark Side strengthens its hold on you")
    elif intent == 'light':
        consequences.append("Your connection to the Light Side deepens")
    
    # Power level consequences
    if power_level >= 8:
        consequences.append("Such displays of Force power rarely go unnoticed")
    
    return consequences

def update_power_witnesses(user, power_name, target, session_id):
    """Update NPCs who witnessed Force power use"""
    # This would integrate with the NPC system to find nearby NPCs
    # For now, return placeholder
    witnesses = []
    
    # Find NPCs that might have witnessed this
    recent_npcs = NPCMemory.query.filter_by(user=user).filter(
        NPCMemory.last_interaction > datetime.utcnow() - timedelta(hours=1)
    ).all()
    
    for npc in recent_npcs:
        if random.random() < 0.3:  # 30% chance NPC witnessed
            npc.fear_level = min(100, npc.fear_level + 10)
            witnesses.append(npc.npc_name)
            
            # Record in interaction history
            interaction_history = json.loads(npc.interaction_history) if npc.interaction_history else []
            interaction_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'force_power_witnessed',
                'power': power_name,
                'target': target
            })
            npc.interaction_history = json.dumps(interaction_history[-20:])
    
    db.session.commit()
    return witnesses

def get_force_powers(user):
    """Get available and locked Force powers for a user"""
    alignment = ForceAlignment.query.filter_by(user=user).first()
    
    if not alignment:
        return {
            'available': [],
            'locked': ['All powers locked - not Force-sensitive'],
            'requirements': {},
            'force_sensitive': False
        }
    
    if not alignment.force_sensitive:
        return {
            'available': [],
            'locked': ['All powers locked - Force sensitivity not awakened'],
            'requirements': {'Force Sensitivity': 'Perform 15 Force-related actions'},
            'force_sensitive': False
        }
    
    available = json.loads(alignment.force_powers) if alignment.force_powers else []
    total_exp = alignment.light_side_points + alignment.dark_side_points
    net_alignment = alignment.net_alignment
    
    # Define all possible powers with requirements
    all_powers = {
        'Force Sense': {'exp': 10, 'alignment': None},
        'Force Push': {'exp': 25, 'alignment': None},
        'Force Heal': {'exp': 40, 'alignment': 25},
        'Battle Meditation': {'exp': 80, 'alignment': 60},
        'Force Choke': {'exp': 30, 'alignment': -25},
        'Force Lightning': {'exp': 100, 'alignment': -60},
        'Force Stealth': {'exp': 50, 'alignment': 'balanced'}
    }
    
    locked = []
    requirements = {}
    
    for power, reqs in all_powers.items():
        if power not in available:
            if total_exp < reqs['exp']:
                locked.append(power)
                requirements[power] = f"Requires {reqs['exp']} Force experience (current: {total_exp})"
            elif reqs['alignment'] == 'balanced' and abs(net_alignment) > 25:
                locked.append(power)
                requirements[power] = "Requires balanced alignment (-25 to +25)"
            elif isinstance(reqs['alignment'], int):
                if reqs['alignment'] > 0 and net_alignment < reqs['alignment']:
                    locked.append(power)
                    requirements[power] = f"Requires Light Side alignment (+{reqs['alignment']} or higher)"
                elif reqs['alignment'] < 0 and net_alignment > reqs['alignment']:
                    locked.append(power)
                    requirements[power] = f"Requires Dark Side alignment ({reqs['alignment']} or lower)"
    
    return {
        'available': available,
        'locked': locked,
        'requirements': requirements,
        'force_sensitive': True
    }

def meditate(user, meditation_type='balance', duration='short', location='unknown', session_id=None):
    """
    Force meditation for alignment balancing and visions
    """
    alignment = ForceAlignment.query.filter_by(user=user).first()
    if not alignment:
        return {'outcome': 'You are not Force-sensitive and gain no benefit from meditation'}
    
    # Calculate meditation effectiveness
    base_effectiveness = {'short': 1, 'medium': 2, 'long': 3}[duration]
    
    # Location bonuses
    location_bonuses = {
        'jedi_temple': 3,
        'sith_temple': 3,
        'force_nexus': 2,
        'peaceful_nature': 1,
        'starship': 0,
        'cantina': -1,
        'unknown': 0
    }
    
    location_bonus = location_bonuses.get(location.lower(), 0)
    total_effectiveness = base_effectiveness + location_bonus
    
    # Apply meditation effects
    alignment_change = 0
    outcome_text = "You center yourself through meditation."
    
    if meditation_type == 'balance':
        # Move alignment toward center
        if alignment.net_alignment > 0:
            alignment_change = -min(5, alignment.net_alignment // 10) * total_effectiveness
        elif alignment.net_alignment < 0:
            alignment_change = min(5, abs(alignment.net_alignment) // 10) * total_effectiveness
        outcome_text += " You feel more balanced in the Force."
    
    elif meditation_type == 'light':
        alignment_change = total_effectiveness * 3
        outcome_text += " You strengthen your connection to the Light Side."
    
    elif meditation_type == 'dark':
        alignment_change = -total_effectiveness * 3
        outcome_text += " You delve deeper into the Dark Side's power."
    
    elif meditation_type == 'vision_seeking':
        # Attempt to trigger a vision
        vision_chance = min(0.8, total_effectiveness * 0.2)
        if random.random() < vision_chance:
            vision = generate_force_vision(user, 'meditation', session_id)
            if vision:
                outcome_text += f" A vision comes to you: {vision['vision_text']}"
                return {
                    'outcome': outcome_text,
                    'alignment_change': 0,
                    'visions': [vision],
                    'force_clarity': total_effectiveness,
                    'location_bonus': location_bonus
                }
        outcome_text += " You seek visions but the Force remains silent."
    
    # Apply alignment change if any
    if alignment_change != 0:
        if alignment_change > 0:
            alignment.light_side_points += abs(alignment_change)
        else:
            alignment.dark_side_points += abs(alignment_change)
        
        # Record meditation in Force events
        force_events = json.loads(alignment.force_events) if alignment.force_events else []
        force_events.append({
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'meditation',
            'meditation_type': meditation_type,
            'duration': duration,
            'location': location,
            'alignment_change': alignment_change
        })
        alignment.force_events = json.dumps(force_events[-50:])
        alignment.last_force_event = datetime.utcnow()
    
    db.session.commit()
    
    return {
        'outcome': outcome_text,
        'alignment_change': alignment_change,
        'force_clarity': total_effectiveness,
        'location_bonus': location_bonus,
        'visions': []
    }

# Helper functions
def has_recent_consequence(user, consequence_type):
    """Check if user has had a specific consequence recently"""
    # This would check a consequences table or cache
    # For now, return False to allow consequences
    return False

def mark_consequence(user, consequence_type):
    """Mark that a user has experienced a specific consequence"""
    # This would store the consequence with timestamp
    # For now, just pass
    pass

def weighted_random_choice(weights):
    """Select a random choice based on weights dictionary"""
    total_weight = sum(weights.values())
    roll = random.randint(1, total_weight)
    
    cumulative = 0
    for choice, weight in weights.items():
        cumulative += weight
        if roll <= cumulative:
            return choice
    
    return list(weights.keys())[0]  # Fallback
