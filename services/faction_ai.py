from app import db
from models import FactionState, WorldEvent, SessionState
import json
import random
from datetime import datetime, timedelta

def initialize_default_factions():
    """
    Initialize default Star Wars factions if they don't exist
    """
    default_factions = [
        {
            'name': 'Galactic Empire',
            'type': 'Imperial',
            'territory': 70,
            'resources': 10000,
            'influence': 90,
            'goals': ['Maintain Order', 'Suppress Rebellion', 'Expand Territory', 'Develop Superweapons']
        },
        {
            'name': 'Rebel Alliance',
            'type': 'Rebel',
            'territory': 15,
            'resources': 2000,
            'influence': 30,
            'goals': ['Liberate Systems', 'Recruit Allies', 'Sabotage Empire', 'Gather Intelligence']
        },
        {
            'name': 'Hutt Cartel',
            'type': 'Criminal',
            'territory': 10,
            'resources': 5000,
            'influence': 40,
            'goals': ['Control Trade Routes', 'Expand Criminal Empire', 'Maintain Neutrality', 'Accumulate Wealth']
        },
        {
            'name': 'Corporate Sector Authority',
            'type': 'Corporate',
            'territory': 5,
            'resources': 3000,
            'influence': 50,
            'goals': ['Maximize Profits', 'Expand Markets', 'Maintain Autonomy', 'Develop Technology']
        }
    ]
    
    for faction_data in default_factions:
        existing_faction = FactionState.query.filter_by(faction_name=faction_data['name']).first()
        if not existing_faction:
            faction = FactionState(
                faction_name=faction_data['name'],
                faction_type=faction_data['type'],
                territory_control=faction_data['territory'],
                resources=faction_data['resources'],
                influence=faction_data['influence'],
                strategic_goals=json.dumps(faction_data['goals'])
            )
            db.session.add(faction)
    
    db.session.commit()

def run_faction_tick(session_id=None, force_tick=False):
    """
    Execute autonomous faction AI turns - the core of the persistent world simulation
    """
    results = []
    
    # Get all factions
    factions = FactionState.query.all()
    
    for faction in factions:
        # Check if faction needs to take action (daily ticks unless forced)
        time_since_action = datetime.utcnow() - faction.last_action
        if not force_tick and time_since_action < timedelta(hours=24):
            continue
        
        # Execute faction AI logic
        faction_result = execute_faction_strategy(faction, session_id)
        results.append(faction_result)
        
        # Update last action time
        faction.last_action = datetime.utcnow()
        db.session.commit()
    
    # Apply inter-faction conflicts and interactions
    conflict_results = resolve_faction_conflicts(factions, session_id)
    results.extend(conflict_results)
    
    return results

def execute_faction_strategy(faction, session_id):
    """
    Execute strategic AI for a single faction
    """
    goals = faction.get_goals()
    current_operations = faction.get_operations()
    
    # Faction AI decision making based on type and current state
    new_operations = []
    completed_operations = []
    
    # Remove completed operations
    for operation in current_operations:
        if operation.get('completion_date', datetime.utcnow().isoformat()) <= datetime.utcnow().isoformat():
            completed_operations.append(operation)
        else:
            new_operations.append(operation)
    
    # Generate new operations based on faction goals and current state
    for goal in goals[:2]:  # Focus on top 2 priorities
        operation = generate_faction_operation(faction, goal, session_id)
        if operation:
            new_operations.append(operation)
    
    # Update faction state based on operations
    resource_change = 0
    territory_change = 0
    influence_change = 0
    
    for operation in completed_operations:
        success = random.random() < operation.get('success_chance', 0.7)
        if success:
            resource_change += operation.get('resource_gain', 0)
            territory_change += operation.get('territory_gain', 0)
            influence_change += operation.get('influence_gain', 0)
        else:
            resource_change += operation.get('resource_loss', 0)
            influence_change += operation.get('influence_loss', 0)
    
    # Apply changes
    faction.resources = max(0, faction.resources + resource_change)
    faction.territory_control = max(0, min(100, faction.territory_control + territory_change))
    faction.influence = max(0, min(100, faction.influence + influence_change))
    
    # Update operations
    faction.set_operations(new_operations[:5])  # Limit to 5 active operations
    
    # Generate faction events if significant changes occurred
    events = []
    if abs(resource_change) > 500 or abs(territory_change) > 2:
        event = create_faction_event(faction, resource_change, territory_change, session_id)
        if event:
            events.append(event)
    
    db.session.commit()
    
    return {
        'faction': faction.faction_name,
        'completed_operations': completed_operations,
        'new_operations': new_operations,
        'resource_change': resource_change,
        'territory_change': territory_change,
        'influence_change': influence_change,
        'events_generated': events
    }

def generate_faction_operation(faction, goal, session_id):
    """
    Generate specific operations based on faction type and goals
    """
    operation_templates = {
        'Imperial': {
            'Maintain Order': [
                {'name': 'System Patrol', 'duration_days': 7, 'resource_cost': 200, 'success_chance': 0.8},
                {'name': 'Rebel Hunt', 'duration_days': 14, 'resource_cost': 500, 'success_chance': 0.6}
            ],
            'Expand Territory': [
                {'name': 'System Annexation', 'duration_days': 30, 'resource_cost': 1000, 'territory_gain': 1},
                {'name': 'Diplomatic Pressure', 'duration_days': 21, 'resource_cost': 300, 'influence_gain': 5}
            ]
        },
        'Rebel': {
            'Liberate Systems': [
                {'name': 'Liberation Campaign', 'duration_days': 21, 'resource_cost': 800, 'territory_gain': 1},
                {'name': 'Propaganda Operations', 'duration_days': 14, 'resource_cost': 200, 'influence_gain': 3}
            ],
            'Sabotage Empire': [
                {'name': 'Supply Line Disruption', 'duration_days': 7, 'resource_cost': 150, 'success_chance': 0.7},
                {'name': 'Intelligence Gathering', 'duration_days': 10, 'resource_cost': 100, 'success_chance': 0.8}
            ]
        },
        'Criminal': {
            'Control Trade Routes': [
                {'name': 'Route Enforcement', 'duration_days': 14, 'resource_cost': 300, 'resource_gain': 500},
                {'name': 'Competitor Elimination', 'duration_days': 7, 'resource_cost': 200, 'success_chance': 0.6}
            ],
            'Expand Criminal Empire': [
                {'name': 'Territory Expansion', 'duration_days': 21, 'resource_cost': 400, 'territory_gain': 1},
                {'name': 'Corruption Network', 'duration_days': 14, 'resource_cost': 250, 'influence_gain': 2}
            ]
        },
        'Corporate': {
            'Maximize Profits': [
                {'name': 'Market Expansion', 'duration_days': 30, 'resource_cost': 500, 'resource_gain': 800},
                {'name': 'Efficiency Optimization', 'duration_days': 14, 'resource_cost': 200, 'resource_gain': 300}
            ],
            'Develop Technology': [
                {'name': 'R&D Investment', 'duration_days': 45, 'resource_cost': 1000, 'influence_gain': 5},
                {'name': 'Patent Acquisition', 'duration_days': 7, 'resource_cost': 300, 'success_chance': 0.8}
            ]
        }
    }
    
    faction_type = faction.faction_type
    if faction_type not in operation_templates:
        return None
    
    type_operations = operation_templates[faction_type]
    if goal not in type_operations:
        return None
    
    templates = type_operations[goal]
    template = random.choice(templates)
    
    # Create operation with completion date
    completion_date = datetime.utcnow() + timedelta(days=template.get('duration_days', 7))
    
    operation = {
        'name': template['name'],
        'goal': goal,
        'resource_cost': template.get('resource_cost', 0),
        'resource_gain': template.get('resource_gain', 0),
        'territory_gain': template.get('territory_gain', 0),
        'influence_gain': template.get('influence_gain', 0),
        'success_chance': template.get('success_chance', 0.7),
        'completion_date': completion_date.isoformat(),
        'started_date': datetime.utcnow().isoformat()
    }
    
    # Check if faction has resources for operation
    if faction.resources >= operation['resource_cost']:
        faction.resources -= operation['resource_cost']
        return operation
    
    return None

def resolve_faction_conflicts(factions, session_id):
    """
    Resolve conflicts and interactions between factions
    """
    conflicts = []
    
    # Define faction relationships and conflict probabilities
    hostile_relationships = [
        ('Galactic Empire', 'Rebel Alliance', 0.8),
        ('Hutt Cartel', 'Corporate Sector Authority', 0.3),
        ('Galactic Empire', 'Hutt Cartel', 0.2)
    ]
    
    for faction1_name, faction2_name, conflict_chance in hostile_relationships:
        if random.random() < conflict_chance * 0.1:  # 10% of base chance per tick
            faction1 = next((f for f in factions if f.faction_name == faction1_name), None)
            faction2 = next((f for f in factions if f.faction_name == faction2_name), None)
            
            if faction1 and faction2:
                conflict_result = resolve_conflict(faction1, faction2, session_id)
                conflicts.append(conflict_result)
    
    return conflicts

def resolve_conflict(faction1, faction2, session_id):
    """
    Resolve a specific conflict between two factions
    """
    # Calculate conflict strength based on resources and influence
    strength1 = faction1.resources * 0.7 + faction1.influence * 0.3
    strength2 = faction2.resources * 0.7 + faction2.influence * 0.3
    
    # Add randomness
    strength1 *= random.uniform(0.8, 1.2)
    strength2 *= random.uniform(0.8, 1.2)
    
    if strength1 > strength2:
        winner = faction1
        loser = faction2
        victory_margin = (strength1 - strength2) / strength2
    else:
        winner = faction2
        loser = faction1
        victory_margin = (strength2 - strength1) / strength1
    
    # Apply conflict results
    resource_transfer = int(loser.resources * min(0.1, victory_margin * 0.05))
    territory_transfer = int(loser.territory_control * min(0.05, victory_margin * 0.02))
    
    winner.resources += resource_transfer
    winner.territory_control += territory_transfer
    loser.resources -= resource_transfer
    loser.territory_control -= territory_transfer
    
    # Ensure minimums
    loser.resources = max(100, loser.resources)
    loser.territory_control = max(1, loser.territory_control)
    
    # Create world event for significant conflicts
    if resource_transfer > 200 or territory_transfer > 1:
        event = WorldEvent(
            event_title=f"{winner.faction_name} Gains Ground Against {loser.faction_name}",
            event_description=f"In a recent conflict, {winner.faction_name} has successfully gained {resource_transfer} resources and {territory_transfer} systems from {loser.faction_name}.",
            event_type='military',
            affected_factions=json.dumps([winner.faction_name, loser.faction_name]),
            galactic_impact=int(victory_margin * 5),
            session_id=session_id
        )
        db.session.add(event)
    
    db.session.commit()
    
    return {
        'conflict_type': 'territorial_dispute',
        'winner': winner.faction_name,
        'loser': loser.faction_name,
        'resource_transfer': resource_transfer,
        'territory_transfer': territory_transfer,
        'victory_margin': victory_margin
    }

def get_faction_state(faction_name, session_id=None):
    """
    Get current state of a specific faction
    """
    return FactionState.query.filter_by(faction_name=faction_name).first()

def update_faction_awareness(faction_name, user, relationship_change=0, awareness_change=0, action_description='', session_id=None):
    """
    Update faction awareness and relationship with player
    """
    faction = get_faction_state(faction_name, session_id)
    if not faction:
        return {'error': 'Faction not found'}
    
    # Update awareness and hostility
    faction.awareness_level = min(100, max(0, faction.awareness_level + awareness_change))
    faction.hostility_level = min(100, max(-100, faction.hostility_level + relationship_change))
    
    consequences = []
    
    # Trigger faction responses based on awareness/hostility levels
    if faction.awareness_level > 50 and faction.hostility_level > 30:
        # Faction becomes actively hostile
        consequences.append(f"{faction_name} has marked you as a priority target")
        
        # Add bounty or pursuit operation
        operations = faction.get_operations()
        pursuit_op = {
            'name': f'Pursue {user}',
            'target': user,
            'resource_cost': 200,
            'completion_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'started_date': datetime.utcnow().isoformat()
        }
        operations.append(pursuit_op)
        faction.set_operations(operations)
    
    elif faction.awareness_level > 75:
        consequences.append(f"{faction_name} intelligence networks are actively tracking your movements")
    
    db.session.commit()
    
    return {
        'new_awareness': faction.awareness_level,
        'new_hostility': faction.hostility_level,
        'consequences': consequences
    }

def apply_event_to_factions(event):
    """
    Apply world event effects to relevant factions
    """
    affected_factions = json.loads(event.affected_factions) if isinstance(event.affected_factions, str) else event.affected_factions
    effects = []
    
    for faction_name in affected_factions:
        faction = get_faction_state(faction_name)
        if faction:
            # Apply event effects based on event type and impact
            if event.event_type == 'military':
                faction.resources -= event.galactic_impact * 50
                faction.influence -= event.galactic_impact
            elif event.event_type == 'economic':
                faction.resources += event.galactic_impact * 100
            elif event.event_type == 'political':
                faction.influence += event.galactic_impact * 2
            
            # Ensure minimums
            faction.resources = max(100, faction.resources)
            faction.influence = max(0, min(100, faction.influence))
            
            effects.append({
                'faction': faction_name,
                'resource_change': event.galactic_impact * (-50 if event.event_type == 'military' else 100 if event.event_type == 'economic' else 0),
                'influence_change': event.galactic_impact * (-1 if event.event_type == 'military' else 2 if event.event_type == 'political' else 0)
            })
    
    db.session.commit()
    return effects

def create_faction_event(faction, resource_change, territory_change, session_id):
    """
    Create a world event based on faction activities
    """
    if abs(resource_change) < 200 and abs(territory_change) < 1:
        return None
    
    event_titles = {
        'Imperial': [
            f"{faction.faction_name} Consolidates Power",
            f"Imperial Forces Expand Operations",
            f"{faction.faction_name} Demonstrates Military Might"
        ],
        'Rebel': [
            f"{faction.faction_name} Strikes Back",
            f"Rebellion Gains Momentum",
            f"{faction.faction_name} Liberates Systems"
        ],
        'Criminal': [
            f"{faction.faction_name} Expands Territory",
            f"Criminal Empire Grows Stronger",
            f"{faction.faction_name} Consolidates Control"
        ],
        'Corporate': [
            f"{faction.faction_name} Reports Record Profits",
            f"Corporate Expansion Continues",
            f"{faction.faction_name} Announces New Ventures"
        ]
    }
    
    titles = event_titles.get(faction.faction_type, [f"{faction.faction_name} Activities"])
    title = random.choice(titles)
    
    description = f"{faction.faction_name} has been actively expanding their operations. "
    if resource_change > 0:
        description += f"They have gained {resource_change} resources through successful operations. "
    if territory_change > 0:
        description += f"They have expanded their territorial control by {territory_change} systems. "
    
    event = WorldEvent(
        event_title=title,
        event_description=description,
        event_type='political',
        affected_factions=json.dumps([faction.faction_name]),
        galactic_impact=max(1, (abs(resource_change) // 200) + abs(territory_change)),
        session_id=session_id
    )
    
    db.session.add(event)
    db.session.commit()
    
    return {
        'event_id': event.id,
        'title': title,
        'description': description
    }
