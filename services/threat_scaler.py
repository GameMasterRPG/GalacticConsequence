from app import db
from models import ThreatLevel, FactionState, NPCMemory, WorldEvent
import json
import random
from datetime import datetime, timedelta

def update_threat_level(user, action_type, severity=1, faction_involved=None, witnesses=[], session_id=None):
    """
    Update player threat level with escalating consequences - core of scalable threat system
    """
    # Get or create threat level for user
    threat = ThreatLevel.query.filter_by(user=user).first()
    if not threat:
        threat = ThreatLevel(
            user=user,
            session_id=session_id
        )
        db.session.add(threat)
    
    # Calculate threat increases based on action type
    threat_increases = calculate_threat_increases(action_type, severity, faction_involved)
    
    # Apply threat increases
    threat.notoriety_level = min(100, threat.notoriety_level + threat_increases['notoriety'])
    threat.imperial_awareness = min(100, threat.imperial_awareness + threat_increases['imperial'])
    threat.rebel_awareness = min(100, threat.rebel_awareness + threat_increases['rebel'])
    threat.criminal_reputation = min(100, threat.criminal_reputation + threat_increases['criminal'])
    threat.bounty_amount += threat_increases['bounty']
    
    # Calculate new heat level (1-10 scale)
    old_heat = threat.heat_level
    threat.heat_level = calculate_heat_level(threat)
    
    # Record escalation triggers
    escalation_triggers = json.loads(threat.escalation_triggers) if threat.escalation_triggers else []
    escalation_triggers.append({
        'timestamp': datetime.utcnow().isoformat(),
        'action_type': action_type,
        'severity': severity,
        'faction_involved': faction_involved,
        'witnesses': witnesses,
        'heat_change': threat.heat_level - old_heat
    })
    threat.escalation_triggers = json.dumps(escalation_triggers[-20:])  # Keep last 20
    
    # Trigger escalation responses if heat level increased
    escalation_responses = []
    if threat.heat_level > old_heat:
        escalation_responses = trigger_threat_escalation(threat, action_type, session_id)
        threat.last_escalation = datetime.utcnow()
    
    # Update faction awareness based on witnesses
    faction_responses = update_faction_threat_awareness(user, witnesses, action_type, severity, session_id)
    
    # Generate bounty hunters if bounty is high enough
    bounty_hunters = []
    if threat.bounty_amount >= 5000 and random.random() < 0.3:
        bounty_hunters = deploy_bounty_hunters(threat, session_id)
    
    db.session.commit()
    
    return {
        'new_heat_level': threat.heat_level,
        'heat_increase': threat.heat_level - old_heat,
        'notoriety_change': threat_increases['notoriety'],
        'bounty_increase': threat_increases['bounty'],
        'escalation_responses': escalation_responses,
        'faction_responses': faction_responses,
        'bounty_hunters_deployed': bounty_hunters
    }

def calculate_threat_increases(action_type, severity, faction_involved):
    """
    Calculate threat level increases based on action type and severity
    """
    base_increases = {
        'imperial_crime': {'notoriety': 5, 'imperial': 15, 'rebel': 0, 'criminal': 2, 'bounty': 1000},
        'rebel_activity': {'notoriety': 3, 'imperial': 20, 'rebel': -5, 'criminal': 0, 'bounty': 2000},
        'criminal_activity': {'notoriety': 4, 'imperial': 5, 'rebel': 0, 'criminal': 10, 'bounty': 500},
        'piracy': {'notoriety': 6, 'imperial': 10, 'rebel': 0, 'criminal': 8, 'bounty': 1500},
        'assassination': {'notoriety': 10, 'imperial': 8, 'rebel': 3, 'criminal': 15, 'bounty': 5000},
        'terrorism': {'notoriety': 15, 'imperial': 25, 'rebel': -10, 'criminal': 5, 'bounty': 10000},
        'smuggling': {'notoriety': 2, 'imperial': 8, 'rebel': 0, 'criminal': 5, 'bounty': 300},
        'force_display': {'notoriety': 8, 'imperial': 20, 'rebel': 5, 'criminal': 3, 'bounty': 0}
    }
    
    increases = base_increases.get(action_type, {'notoriety': 1, 'imperial': 1, 'rebel': 0, 'criminal': 1, 'bounty': 100})
    
    # Scale by severity (1-10)
    for key in increases:
        increases[key] = int(increases[key] * severity)
    
    # Faction-specific modifiers
    if faction_involved == 'Galactic Empire':
        increases['imperial'] *= 2
        increases['bounty'] *= 2
    elif faction_involved == 'Rebel Alliance':
        increases['imperial'] *= 1.5
        increases['rebel'] *= -1  # Rebels like anti-Imperial actions
    elif faction_involved in ['Hutt Cartel', 'CSA']:
        increases['criminal'] *= 1.5
    
    return increases

def calculate_heat_level(threat):
    """
    Calculate overall heat level (1-10) based on all threat factors
    """
    # Weighted calculation of heat level
    heat_score = (
        threat.notoriety_level * 0.3 +
        threat.imperial_awareness * 0.25 +
        threat.rebel_awareness * 0.15 +
        threat.criminal_reputation * 0.2 +
        min(100, threat.bounty_amount / 500) * 0.1  # Bounty scaled to 0-100 range
    )
    
    # Convert to 1-10 scale
    heat_level = max(1, min(10, int(heat_score / 10) + 1))
    return heat_level

def trigger_threat_escalation(threat, action_type, session_id):
    """
    Trigger escalating threat responses based on heat level
    """
    responses = []
    
    if threat.heat_level >= 8:
        # Maximum heat - deploy everything
        responses.extend(deploy_imperial_response_team(threat, session_id))
        responses.extend(deploy_bounty_hunter_guild(threat, session_id))
        responses.extend(create_system_wide_alert(threat, session_id))
    
    elif threat.heat_level >= 6:
        # High heat - serious response
        responses.extend(deploy_imperial_investigation(threat, session_id))
        if random.random() < 0.6:
            responses.extend(deploy_bounty_hunters(threat, session_id))
        responses.extend(increase_patrol_frequency(threat, session_id))
    
    elif threat.heat_level >= 4:
        # Medium heat - noticeable response
        responses.extend(deploy_local_security(threat, session_id))
        if random.random() < 0.4:
            responses.extend(deploy_bounty_hunters(threat, session_id))
        responses.extend(increase_surveillance(threat, session_id))
    
    elif threat.heat_level >= 2:
        # Low heat - minimal response
        responses.extend(flag_for_monitoring(threat, session_id))
    
    return responses

def deploy_imperial_response_team(threat, session_id):
    """
    Deploy Imperial response team for high-value targets
    """
    responses = []
    
    # Add ISB investigation team to active bounties
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    
    isb_team = {
        'type': 'Imperial Response Team',
        'threat_level': 'Extreme',
        'resources': 'Unlimited',
        'specialization': 'Counter-terrorism',
        'deployment_date': datetime.utcnow().isoformat(),
        'completion_chance': 0.8,
        'active': True
    }
    
    active_bounties.append(isb_team)
    threat.active_bounties = json.dumps(active_bounties)
    
    responses.append("Imperial Security Bureau has deployed a response team")
    responses.append("System-wide manhunt initiated")
    
    # Create world event
    event = WorldEvent(
        event_title="Imperial Response Team Deployed",
        event_description=f"The Imperial Security Bureau has deployed a specialized response team to hunt down a high-value target. Security across multiple systems has been increased.",
        event_type='military',
        galactic_impact=5,
        triggered_by_player=threat.user,
        session_id=session_id
    )
    db.session.add(event)
    
    return responses

def deploy_bounty_hunter_guild(threat, session_id):
    """
    Deploy multiple bounty hunters from the guild
    """
    responses = []
    
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    
    # Deploy 2-4 bounty hunters
    num_hunters = random.randint(2, 4)
    hunter_names = ["Valance", "Boushh", "Dengar", "IG-88", "4-LOM", "Zuckuss", "Bossk"]
    
    for i in range(num_hunters):
        hunter_name = random.choice(hunter_names)
        hunter_names.remove(hunter_name)
        
        hunter = {
            'type': 'Bounty Hunter',
            'name': hunter_name,
            'threat_level': 'High',
            'specialization': random.choice(['Tracking', 'Combat', 'Technology', 'Stealth']),
            'deployment_date': datetime.utcnow().isoformat(),
            'completion_chance': random.uniform(0.4, 0.7),
            'active': True
        }
        
        active_bounties.append(hunter)
        responses.append(f"Bounty hunter {hunter_name} has accepted the contract")
    
    threat.active_bounties = json.dumps(active_bounties)
    return responses

def create_system_wide_alert(threat, session_id):
    """
    Create system-wide security alert
    """
    responses = []
    
    responses.append("System-wide security alert issued")
    responses.append("All starports placed on high alert")
    responses.append("Travel restrictions implemented")
    
    # Create world event
    event = WorldEvent(
        event_title="System-Wide Security Alert",
        event_description=f"Imperial authorities have issued a system-wide security alert. All travel is being monitored and restricted.",
        event_type='political',
        galactic_impact=3,
        triggered_by_player=threat.user,
        session_id=session_id
    )
    db.session.add(event)
    
    return responses

def deploy_imperial_investigation(threat, session_id):
    """
    Deploy Imperial investigation team
    """
    responses = []
    
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    
    investigation = {
        'type': 'Imperial Investigation',
        'threat_level': 'High',
        'resources': 'Substantial',
        'specialization': 'Intelligence gathering',
        'deployment_date': datetime.utcnow().isoformat(),
        'completion_chance': 0.6,
        'active': True
    }
    
    active_bounties.append(investigation)
    threat.active_bounties = json.dumps(active_bounties)
    
    responses.append("Imperial Intelligence has opened an investigation")
    responses.append("Your known associates are being questioned")
    
    return responses

def deploy_bounty_hunters(threat, session_id):
    """
    Deploy individual bounty hunters
    """
    responses = []
    
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    
    # Check if bounty hunters already deployed recently
    recent_hunters = [b for b in active_bounties if b.get('type') == 'Bounty Hunter' and b.get('active', True)]
    if len(recent_hunters) >= 3:
        return ["Bounty hunter activity continues"]
    
    hunter_types = [
        {'name': 'Freelance Tracker', 'skill': 'Medium', 'chance': 0.4},
        {'name': 'Guild Hunter', 'skill': 'High', 'chance': 0.6},
        {'name': 'Amateur Bounty Hunter', 'skill': 'Low', 'chance': 0.2}
    ]
    
    hunter = random.choice(hunter_types)
    
    bounty_hunter = {
        'type': 'Bounty Hunter',
        'name': hunter['name'],
        'threat_level': hunter['skill'],
        'deployment_date': datetime.utcnow().isoformat(),
        'completion_chance': hunter['chance'],
        'active': True
    }
    
    active_bounties.append(bounty_hunter)
    threat.active_bounties = json.dumps(active_bounties)
    
    responses.append(f"{hunter['name']} has taken the bounty contract")
    
    return responses

def deploy_local_security(threat, session_id):
    """
    Deploy local security forces
    """
    responses = []
    
    responses.append("Local security forces increase patrols")
    responses.append("Checkpoint frequency has increased")
    
    return responses

def increase_patrol_frequency(threat, session_id):
    """
    Increase Imperial patrol frequency
    """
    responses = []
    
    responses.append("Imperial patrol frequency increased")
    responses.append("Starship inspections become more common")
    
    return responses

def increase_surveillance(threat, session_id):
    """
    Increase surveillance on player
    """
    responses = []
    
    responses.append("Electronic surveillance has increased")
    responses.append("Your communications may be monitored")
    
    return responses

def flag_for_monitoring(threat, session_id):
    """
    Flag player for monitoring
    """
    responses = []
    
    responses.append("You have been flagged for monitoring")
    responses.append("Imperial databases now contain your profile")
    
    return responses

def update_faction_threat_awareness(user, witnesses, action_type, severity, session_id):
    """
    Update faction awareness based on witnesses to player actions
    """
    responses = []
    
    for witness in witnesses:
        if witness.startswith('Imperial'):
            # Imperial witness
            from services.faction_ai import update_faction_awareness
            result = update_faction_awareness(
                faction_name='Galactic Empire',
                user=user,
                relationship_change=-severity * 3,
                awareness_change=severity * 5,
                action_description=f"Witnessed {action_type}",
                session_id=session_id
            )
            responses.append(f"{witness} reports to Imperial authorities")
        
        elif witness.startswith('Rebel'):
            # Rebel witness
            relationship_change = severity * 2 if action_type in ['imperial_crime', 'terrorism'] else -severity
            from services.faction_ai import update_faction_awareness
            result = update_faction_awareness(
                faction_name='Rebel Alliance',
                user=user,
                relationship_change=relationship_change,
                awareness_change=severity * 3,
                action_description=f"Witnessed {action_type}",
                session_id=session_id
            )
            responses.append(f"{witness} takes note of your actions")
        
        elif 'Criminal' in witness or 'Smuggler' in witness:
            # Criminal witness
            from services.faction_ai import update_faction_awareness
            result = update_faction_awareness(
                faction_name='Hutt Cartel',
                user=user,
                relationship_change=severity if action_type in ['criminal_activity', 'smuggling'] else -severity,
                awareness_change=severity * 2,
                action_description=f"Witnessed {action_type}",
                session_id=session_id
            )
            responses.append(f"{witness} spreads word in the underworld")
    
    return responses

def get_current_threats(user):
    """
    Get current active threats against the player
    """
    threat = ThreatLevel.query.filter_by(user=user).first()
    if not threat:
        return {
            'heat_level': 1,
            'active_bounties': [],
            'threat_summary': 'No significant threats detected'
        }
    
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    
    # Filter for currently active threats
    current_threats = [b for b in active_bounties if b.get('active', True)]
    
    # Generate threat summary
    if threat.heat_level >= 8:
        summary = "EXTREME DANGER: Multiple high-level threats active"
    elif threat.heat_level >= 6:
        summary = "HIGH THREAT: Serious opposition mobilized"
    elif threat.heat_level >= 4:
        summary = "MODERATE THREAT: Noticeable heat from authorities"
    elif threat.heat_level >= 2:
        summary = "LOW THREAT: Minimal law enforcement interest"
    else:
        summary = "MINIMAL THREAT: Operating under the radar"
    
    return {
        'heat_level': threat.heat_level,
        'notoriety_level': threat.notoriety_level,
        'bounty_amount': threat.bounty_amount,
        'imperial_awareness': threat.imperial_awareness,
        'rebel_awareness': threat.rebel_awareness,
        'criminal_reputation': threat.criminal_reputation,
        'active_bounties': current_threats,
        'threat_summary': summary
    }

def reduce_heat_level(user, method='laying_low', duration_days=7):
    """
    Reduce threat level through various methods
    """
    threat = ThreatLevel.query.filter_by(user=user).first()
    if not threat:
        return {'message': 'No threat level to reduce'}
    
    reduction_methods = {
        'laying_low': {
            'notoriety_reduction': 5,
            'imperial_reduction': 8,
            'bounty_reduction': 0,
            'description': 'Staying out of sight and avoiding attention'
        },
        'bribing_officials': {
            'notoriety_reduction': 10,
            'imperial_reduction': 15,
            'bounty_reduction': 1000,
            'description': 'Paying off key officials to look the other way'
        },
        'fake_death': {
            'notoriety_reduction': 25,
            'imperial_reduction': 30,
            'bounty_reduction': 5000,
            'description': 'Faking your death to throw off pursuers'
        },
        'faction_protection': {
            'notoriety_reduction': 8,
            'imperial_reduction': 20,
            'bounty_reduction': 2000,
            'description': 'Gaining protection from a powerful faction'
        }
    }
    
    if method not in reduction_methods:
        return {'error': 'Invalid heat reduction method'}
    
    reductions = reduction_methods[method]
    
    # Apply reductions (scaled by duration)
    duration_multiplier = min(2.0, duration_days / 7)  # Max 2x for 2+ weeks
    
    threat.notoriety_level = max(0, threat.notoriety_level - int(reductions['notoriety_reduction'] * duration_multiplier))
    threat.imperial_awareness = max(0, threat.imperial_awareness - int(reductions['imperial_reduction'] * duration_multiplier))
    threat.bounty_amount = max(0, threat.bounty_amount - int(reductions['bounty_reduction'] * duration_multiplier))
    
    # Recalculate heat level
    old_heat = threat.heat_level
    threat.heat_level = calculate_heat_level(threat)
    
    # Deactivate some bounty hunters if heat reduced significantly
    if threat.heat_level < old_heat - 1:
        active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
        for bounty in active_bounties:
            if bounty.get('threat_level') == 'Low' and random.random() < 0.5:
                bounty['active'] = False
        threat.active_bounties = json.dumps(active_bounties)
    
    db.session.commit()
    
    return {
        'method': method,
        'description': reductions['description'],
        'heat_reduction': old_heat - threat.heat_level,
        'new_heat_level': threat.heat_level,
        'notoriety_reduction': reductions['notoriety_reduction'],
        'bounty_reduction': reductions['bounty_reduction']
    }

def escalate_faction_response(faction_name, user, escalation_reason, session_id=None):
    """
    Escalate faction response to player actions
    """
    threat = ThreatLevel.query.filter_by(user=user).first()
    if not threat:
        return {'error': 'No threat level found for user'}
    
    escalation_responses = {
        'Galactic Empire': {
            'wanted_poster': {
                'description': 'Imperial wanted posters distributed across systems',
                'awareness_increase': 15,
                'bounty_increase': 3000
            },
            'asset_freeze': {
                'description': 'Imperial Banking Clan freezes your known assets',
                'awareness_increase': 10,
                'bounty_increase': 0
            },
            'travel_restrictions': {
                'description': 'Travel restrictions imposed on Imperial systems',
                'awareness_increase': 8,
                'bounty_increase': 1000
            }
        },
        'Rebel Alliance': {
            'recruitment_attempt': {
                'description': 'Rebel agents attempt to recruit you',
                'awareness_increase': 5,
                'bounty_increase': 0
            },
            'intelligence_sharing': {
                'description': 'Rebels share intelligence about Imperial movements',
                'awareness_increase': 10,
                'bounty_increase': 0
            }
        },
        'Hutt Cartel': {
            'cartel_bounty': {
                'description': 'Hutt Cartel places private bounty on your head',
                'awareness_increase': 5,
                'bounty_increase': 5000
            },
            'territory_ban': {
                'description': 'Banned from Hutt-controlled territories',
                'awareness_increase': 8,
                'bounty_increase': 1000
            }
        }
    }
    
    if faction_name not in escalation_responses:
        return {'error': 'Unknown faction'}
    
    faction_escalations = escalation_responses[faction_name]
    escalation_type = random.choice(list(faction_escalations.keys()))
    escalation = faction_escalations[escalation_type]
    
    # Apply escalation effects
    if faction_name == 'Galactic Empire':
        threat.imperial_awareness = min(100, threat.imperial_awareness + escalation['awareness_increase'])
    elif faction_name == 'Rebel Alliance':
        threat.rebel_awareness = min(100, threat.rebel_awareness + escalation['awareness_increase'])
    elif faction_name == 'Hutt Cartel':
        threat.criminal_reputation = min(100, threat.criminal_reputation + escalation['awareness_increase'])
    
    threat.bounty_amount += escalation['bounty_increase']
    
    # Recalculate heat level
    threat.heat_level = calculate_heat_level(threat)
    
    # Record escalation
    escalation_triggers = json.loads(threat.escalation_triggers) if threat.escalation_triggers else []
    escalation_triggers.append({
        'timestamp': datetime.utcnow().isoformat(),
        'faction': faction_name,
        'escalation_type': escalation_type,
        'reason': escalation_reason,
        'effects': escalation
    })
    threat.escalation_triggers = json.dumps(escalation_triggers[-20:])
    
    db.session.commit()
    
    return {
        'faction': faction_name,
        'escalation_type': escalation_type,
        'description': escalation['description'],
        'new_heat_level': threat.heat_level,
        'bounty_increase': escalation['bounty_increase']
    }

def check_bounty_hunter_success(user):
    """
    Check if any bounty hunters have succeeded in tracking the player
    """
    threat = ThreatLevel.query.filter_by(user=user).first()
    if not threat:
        return []
    
    active_bounties = json.loads(threat.active_bounties) if threat.active_bounties else []
    encounters = []
    
    for bounty in active_bounties:
        if not bounty.get('active', True):
            continue
        
        # Check if bounty hunter succeeds based on completion chance
        if random.random() < bounty.get('completion_chance', 0.5):
            encounter = {
                'hunter_type': bounty.get('type', 'Unknown'),
                'hunter_name': bounty.get('name', 'Unknown Hunter'),
                'threat_level': bounty.get('threat_level', 'Medium'),
                'encounter_type': random.choice(['confrontation', 'ambush', 'chase', 'negotiation']),
                'timestamp': datetime.utcnow().isoformat()
            }
            encounters.append(encounter)
            
            # Mark bounty as completed (successful or not)
            bounty['active'] = False
            bounty['completed_date'] = datetime.utcnow().isoformat()
    
    # Update active bounties
    threat.active_bounties = json.dumps(active_bounties)
    db.session.commit()
    
    return encounters
