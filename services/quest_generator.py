from app import db
from models import QuestLog, ForceAlignment, FactionState, NPCMemory, ThreatLevel
import json
import random
from datetime import datetime

def generate_procedural_quest(user, session_id=None, difficulty_preference='medium', quest_type_preference=None, location=None):
    """
    Generate procedural quest based on current world state, player actions, and Force alignment
    """
    # Get player context
    force_alignment = ForceAlignment.query.filter_by(user=user).first()
    threat_level = ThreatLevel.query.filter_by(user=user).first()
    recent_npc_interactions = NPCMemory.query.filter_by(user=user).order_by(NPCMemory.last_interaction.desc()).limit(5).all()
    
    # Get current faction states
    factions = FactionState.query.all()
    faction_tensions = calculate_faction_tensions(factions)
    
    # Determine quest generation context
    generation_context = {
        'user': user,
        'force_alignment': force_alignment.net_alignment if force_alignment else 0,
        'force_sensitive': force_alignment.force_sensitive if force_alignment else False,
        'threat_level': threat_level.heat_level if threat_level else 1,
        'faction_tensions': faction_tensions,
        'recent_npcs': [npc.npc_name for npc in recent_npc_interactions],
        'location': location,
        'difficulty_preference': difficulty_preference,
        'quest_type_preference': quest_type_preference
    }
    
    # Select quest type based on context and preferences
    quest_type = select_quest_type(generation_context)
    
    # Generate quest based on selected type
    if quest_type == 'faction_conflict':
        return generate_faction_conflict_quest(generation_context)
    elif quest_type == 'force_sensitive':
        return generate_force_quest(generation_context)
    elif quest_type == 'personal_consequence':
        return generate_personal_consequence_quest(generation_context)
    elif quest_type == 'exploration':
        return generate_exploration_quest(generation_context)
    elif quest_type == 'reputation_based':
        return generate_reputation_quest(generation_context)
    else:
        return generate_random_quest(generation_context)

def select_quest_type(context):
    """
    Select appropriate quest type based on player context
    """
    weights = {
        'faction_conflict': 20,
        'exploration': 15,
        'reputation_based': 10,
        'random': 10
    }
    
    # Increase Force quest probability for Force-sensitive characters
    if context['force_sensitive']:
        weights['force_sensitive'] = 25
    else:
        weights['force_sensitive'] = 2
    
    # Increase personal consequence quests based on NPC interactions
    if len(context['recent_npcs']) > 2:
        weights['personal_consequence'] = 20
    else:
        weights['personal_consequence'] = 5
    
    # Increase faction conflict quests based on current tensions
    if context['faction_tensions']['max_tension'] > 0.7:
        weights['faction_conflict'] += 15
    
    # Respect player preference if specified
    if context['quest_type_preference']:
        quest_type = context['quest_type_preference']
        if quest_type in weights:
            return quest_type
    
    # Weighted random selection
    total_weight = sum(weights.values())
    roll = random.randint(1, total_weight)
    
    cumulative = 0
    for quest_type, weight in weights.items():
        cumulative += weight
        if roll <= cumulative:
            return quest_type
    
    return 'random'

def generate_faction_conflict_quest(context):
    """
    Generate quest based on current faction conflicts and tensions
    """
    tensions = context['faction_tensions']
    conflicted_factions = tensions['conflicts']
    
    if not conflicted_factions:
        return generate_random_quest(context)
    
    conflict = random.choice(conflicted_factions)
    faction1_name, faction2_name, tension_level = conflict
    
    quest_templates = [
        {
            'title': f"Diplomatic Intervention in {faction1_name}-{faction2_name} Conflict",
            'description': f"Growing tensions between {faction1_name} and {faction2_name} threaten to destabilize the region. Various parties seek someone to mediate or tip the balance.",
            'giver': f"{faction1_name} Representative",
            'type': 'diplomatic'
        },
        {
            'title': f"Supply Line Disruption",
            'description': f"The conflict between {faction1_name} and {faction2_name} has created opportunities to disrupt supply lines and profit from the chaos.",
            'giver': "Independent Contractor",
            'type': 'sabotage'
        },
        {
            'title': f"Rescue Mission in War Zone",
            'description': f"Civilians are trapped in the crossfire between {faction1_name} and {faction2_name}. Someone needs to extract them before it's too late.",
            'giver': "Humanitarian Contact",
            'type': 'rescue'
        }
    ]
    
    template = random.choice(quest_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=int(tension_level * 8))
    
    # Generate rewards and requirements
    rewards = generate_quest_rewards(context, difficulty, template['type'])
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    # Calculate faction impact
    faction_impact = {
        faction1_name: random.randint(-20, 20),
        faction2_name: random.randint(-20, 20)
    }
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': faction_impact,
        'force_impact': random.randint(-5, 5),
        'generation_reason': f"Generated due to high tension ({tension_level:.2f}) between {faction1_name} and {faction2_name}",
        'prerequisites': [f"Faction conflict: {faction1_name} vs {faction2_name}"]
    }

def generate_force_quest(context):
    """
    Generate Force-related quest based on player's alignment and sensitivity
    """
    alignment = context['force_alignment']
    
    if alignment > 25:  # Light Side leaning
        quest_templates = [
            {
                'title': "Ancient Jedi Holocron Recovery",
                'description': "An ancient Jedi holocron has been discovered in ruins on a distant world. The knowledge within must be preserved and protected from those who would misuse it.",
                'giver': "Jedi Spirit",
                'type': 'light_side'
            },
            {
                'title': "Protect Force-Sensitive Refugees",
                'description': "A group of Force-sensitive individuals seeks protection from Imperial Inquisitors. They need safe passage to a hidden sanctuary.",
                'giver': "Underground Network",
                'type': 'protection'
            }
        ]
    elif alignment < -25:  # Dark Side leaning
        quest_templates = [
            {
                'title': "Sith Artifact Acquisition",
                'description': "A powerful Sith artifact has been uncovered. Its dark power calls to those strong enough to claim it, but the path is fraught with danger and temptation.",
                'giver': "Dark Side Cultist",
                'type': 'dark_side'
            },
            {
                'title': "Eliminate Force-Sensitive Threat",
                'description': "A rogue Force user is disrupting your operations and challenging your authority. They must be dealt with permanently.",
                'giver': "Crime Lord",
                'type': 'elimination'
            }
        ]
    else:  # Balanced/Gray
        quest_templates = [
            {
                'title': "Force Nexus Investigation",
                'description': "Strange Force disturbances have been reported at an ancient site. The cause must be investigated and the balance restored.",
                'giver': "Force-Sensitive Scholar",
                'type': 'investigation'
            },
            {
                'title': "Mediate Force User Conflict",
                'description': "Two Force users with opposing philosophies are locked in conflict. Someone must find a way to resolve their differences before innocents are harmed.",
                'giver': "Local Authority",
                'type': 'mediation'
            }
        ]
    
    template = random.choice(quest_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=6)
    
    rewards = generate_quest_rewards(context, difficulty, 'force_related')
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    # Force quests have higher Force alignment impact
    force_impact = random.randint(-15, 15)
    if template['type'] == 'light_side':
        force_impact = random.randint(5, 20)
    elif template['type'] == 'dark_side':
        force_impact = random.randint(-20, -5)
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': {},
        'force_impact': force_impact,
        'generation_reason': f"Generated for Force-sensitive character with alignment {alignment}",
        'prerequisites': ["Force-sensitive character"]
    }

def generate_personal_consequence_quest(context):
    """
    Generate quest based on previous NPC interactions and player choices
    """
    recent_npcs = context['recent_npcs']
    
    if not recent_npcs:
        return generate_random_quest(context)
    
    npc_name = random.choice(recent_npcs)
    npc_memory = NPCMemory.query.filter_by(npc_name=npc_name, user=context['user']).first()
    
    if not npc_memory:
        return generate_random_quest(context)
    
    relationship = npc_memory.relationship_level
    
    if relationship > 30:  # Friendly NPC
        quest_templates = [
            {
                'title': f"Aid {npc_name}'s Family Crisis",
                'description': f"{npc_name} reaches out to you in desperation. Their family is in danger and they need someone they trust to help resolve the situation.",
                'giver': npc_name,
                'type': 'assistance'
            },
            {
                'title': f"Business Opportunity with {npc_name}",
                'description': f"{npc_name} has discovered a profitable opportunity but needs a reliable partner. They're offering you a chance to join their venture.",
                'giver': npc_name,
                'type': 'partnership'
            }
        ]
    elif relationship < -30:  # Hostile NPC
        quest_templates = [
            {
                'title': f"Confrontation with {npc_name}",
                'description': f"{npc_name} has had enough of your interference. They've issued a challenge that cannot be ignored without losing face.",
                'giver': "Neutral Messenger",
                'type': 'confrontation'
            },
            {
                'title': f"Sabotage {npc_name}'s Operations",
                'description': f"Your conflict with {npc_name} has escalated. An opportunity has arisen to strike at their operations and settle the score.",
                'giver': "Anonymous Contact",
                'type': 'sabotage'
            }
        ]
    else:  # Neutral relationship
        quest_templates = [
            {
                'title': f"Test of Trust from {npc_name}",
                'description': f"{npc_name} is considering working with you but needs proof of your reliability. They've proposed a test of your abilities and trustworthiness.",
                'giver': npc_name,
                'type': 'test'
            }
        ]
    
    template = random.choice(quest_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=4)
    
    rewards = generate_quest_rewards(context, difficulty, template['type'])
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': {},
        'force_impact': random.randint(-3, 3),
        'generation_reason': f"Generated based on relationship with {npc_name} (level: {relationship})",
        'prerequisites': [f"Previous interaction with {npc_name}"]
    }

def generate_exploration_quest(context):
    """
    Generate exploration-based quest
    """
    locations = [
        "Ancient Sith Temple", "Abandoned Space Station", "Uncharted Planet",
        "Derelict Star Destroyer", "Hidden Rebel Base", "Mysterious Asteroid",
        "Lost Jedi Enclave", "Corporate Research Facility", "Pirate Stronghold"
    ]
    
    location = random.choice(locations)
    
    quest_templates = [
        {
            'title': f"Explore the {location}",
            'description': f"Sensors have detected unusual activity at {location}. Someone needs to investigate and report back on what they find.",
            'giver': "Information Broker",
            'type': 'exploration'
        },
        {
            'title': f"Salvage Operation at {location}",
            'description': f"The {location} contains valuable salvage, but it's in a dangerous area. Skilled operators are needed to extract the goods.",
            'giver': "Salvage Company",
            'type': 'salvage'
        },
        {
            'title': f"Archaeological Survey of {location}",
            'description': f"The {location} may contain artifacts of historical significance. A thorough survey is needed to catalog any discoveries.",
            'giver': "University Researcher",
            'type': 'archaeology'
        }
    ]
    
    template = random.choice(quest_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=5)
    
    rewards = generate_quest_rewards(context, difficulty, template['type'])
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': {},
        'force_impact': random.randint(-2, 2),
        'generation_reason': f"Generated exploration quest for {location}",
        'prerequisites': []
    }

def generate_reputation_quest(context):
    """
    Generate quest based on player's threat level and reputation
    """
    threat = context['threat_level']
    
    if threat > 5:  # High threat level
        quest_templates = [
            {
                'title': "Eliminate Bounty Hunter Threat",
                'description': "Your activities have attracted the attention of professional bounty hunters. They must be dealt with before they become a serious problem.",
                'giver': "Criminal Contact",
                'type': 'elimination'
            },
            {
                'title': "Lay Low Operation",
                'description': "The heat is getting too intense. You need to find a way to reduce your profile and let things cool down.",
                'giver': "Underground Network",
                'type': 'stealth'
            }
        ]
    elif threat < 2:  # Low threat level
        quest_templates = [
            {
                'title': "Build Criminal Reputation",
                'description': "You're still small-time in the criminal underworld. An opportunity has arisen to make a name for yourself with the right people.",
                'giver': "Crime Boss",
                'type': 'reputation_building'
            },
            {
                'title': "Prove Your Worth",
                'description': "A potential employer wants to test your skills before offering you more lucrative work. This is your chance to prove yourself.",
                'giver': "Potential Employer",
                'type': 'test'
            }
        ]
    else:  # Medium threat level
        quest_templates = [
            {
                'title': "Maintain the Balance",
                'description': "You've reached a comfortable level of notoriety, but maintaining it requires careful management of your activities.",
                'giver': "Strategic Advisor",
                'type': 'balance'
            }
        ]
    
    template = random.choice(quest_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=threat)
    
    rewards = generate_quest_rewards(context, difficulty, template['type'])
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': {},
        'force_impact': random.randint(-5, 5),
        'generation_reason': f"Generated based on threat level {threat}",
        'prerequisites': [f"Threat level {threat}"]
    }

def generate_random_quest(context):
    """
    Generate a random quest when no specific context applies
    """
    random_templates = [
        {
            'title': "Cargo Delivery Run",
            'description': "A shipment needs to be delivered to a remote location. The cargo is valuable and the route may be dangerous.",
            'giver': "Shipping Company",
            'type': 'delivery'
        },
        {
            'title': "Missing Person Investigation",
            'description': "Someone has gone missing under mysterious circumstances. Their family is willing to pay well for information about their whereabouts.",
            'giver': "Worried Family",
            'type': 'investigation'
        },
        {
            'title': "Equipment Recovery Mission",
            'description': "Valuable equipment was lost during a recent incident. It needs to be recovered before it falls into the wrong hands.",
            'giver': "Equipment Owner",
            'type': 'recovery'
        }
    ]
    
    template = random.choice(random_templates)
    difficulty = calculate_quest_difficulty(context, base_difficulty=3)
    
    rewards = generate_quest_rewards(context, difficulty, template['type'])
    requirements = generate_quest_requirements(template['type'], difficulty)
    
    return {
        'title': template['title'],
        'description': template['description'],
        'giver': template['giver'],
        'rewards': rewards,
        'requirements': requirements,
        'difficulty': difficulty,
        'faction_impact': {},
        'force_impact': 0,
        'generation_reason': "Random quest generation",
        'prerequisites': []
    }

def calculate_quest_difficulty(context, base_difficulty=3):
    """
    Calculate appropriate quest difficulty based on player context
    """
    difficulty = base_difficulty
    
    # Adjust based on difficulty preference
    preferences = {'easy': -2, 'medium': 0, 'hard': 2, 'extreme': 4}
    difficulty += preferences.get(context['difficulty_preference'], 0)
    
    # Adjust based on threat level
    difficulty += context['threat_level'] // 2
    
    # Ensure difficulty is within valid range (1-10)
    return max(1, min(10, difficulty))

def generate_quest_rewards(context, difficulty, quest_type):
    """
    Generate appropriate rewards for quest
    """
    base_credits = difficulty * 1000
    
    rewards = {
        'credits': base_credits + random.randint(-200, 500),
        'reputation': f"+{difficulty} reputation with quest giver",
        'experience': f"{difficulty * 100} experience points"
    }
    
    # Add type-specific rewards
    if quest_type in ['force_related', 'light_side', 'dark_side']:
        rewards['force_knowledge'] = "Force technique or knowledge"
    elif quest_type in ['faction_conflict', 'diplomatic']:
        rewards['faction_standing'] = "Improved standing with sponsoring faction"
    elif quest_type in ['exploration', 'archaeology']:
        rewards['artifacts'] = "Potential valuable artifacts or data"
    elif quest_type in ['elimination', 'sabotage']:
        rewards['underworld_rep'] = "Increased criminal reputation"
    
    # High difficulty quests get special rewards
    if difficulty >= 7:
        special_rewards = ["Rare equipment", "Ship upgrades", "Unique contact", "Valuable information"]
        rewards['special'] = random.choice(special_rewards)
    
    return rewards

def generate_quest_requirements(quest_type, difficulty):
    """
    Generate quest requirements and objectives
    """
    base_requirements = [
        f"Complete within {7 + difficulty} days",
        "Maintain operational security"
    ]
    
    type_requirements = {
        'combat': ["Combat capability required", "Weapons permitted"],
        'stealth': ["Stealth approach recommended", "Avoid detection"],
        'diplomatic': ["Social skills advantageous", "Non-violent resolution preferred"],
        'force_related': ["Force sensitivity helpful", "Mental preparation required"],
        'exploration': ["Navigation equipment needed", "Survey equipment recommended"],
        'delivery': ["Reliable transportation required", "Cargo protection essential"]
    }
    
    if quest_type in type_requirements:
        base_requirements.extend(type_requirements[quest_type])
    
    return base_requirements

def calculate_faction_tensions(factions):
    """
    Calculate current tensions between factions
    """
    conflicts = []
    max_tension = 0
    
    # Define base faction relationships
    faction_relationships = {
        ('Galactic Empire', 'Rebel Alliance'): 0.9,
        ('Galactic Empire', 'Hutt Cartel'): 0.3,
        ('Galactic Empire', 'Corporate Sector Authority'): 0.2,
        ('Rebel Alliance', 'Hutt Cartel'): 0.1,
        ('Rebel Alliance', 'Corporate Sector Authority'): 0.2,
        ('Hutt Cartel', 'Corporate Sector Authority'): 0.4
    }
    
    for (faction1_name, faction2_name), base_tension in faction_relationships.items():
        faction1 = next((f for f in factions if f.faction_name == faction1_name), None)
        faction2 = next((f for f in factions if f.faction_name == faction2_name), None)
        
        if faction1 and faction2:
            # Calculate dynamic tension based on faction states
            resource_competition = abs(faction1.resources - faction2.resources) / 10000
            territory_competition = abs(faction1.territory_control - faction2.territory_control) / 100
            
            dynamic_tension = base_tension + (resource_competition * 0.3) + (territory_competition * 0.2)
            dynamic_tension = min(1.0, dynamic_tension)
            
            conflicts.append((faction1_name, faction2_name, dynamic_tension))
            max_tension = max(max_tension, dynamic_tension)
    
    return {
        'conflicts': conflicts,
        'max_tension': max_tension
    }

def evaluate_quest_completion(quest, completion_method='standard', player_choices=[], session_id=None):
    """
    Evaluate quest completion and apply rewards/consequences
    """
    # Parse quest data
    rewards = json.loads(quest.reward) if isinstance(quest.reward, str) else quest.reward
    faction_impact = json.loads(quest.faction_impact) if isinstance(quest.faction_impact, str) else quest.faction_impact
    
    # Calculate completion quality based on method and choices
    completion_quality = calculate_completion_quality(completion_method, player_choices, quest.difficulty)
    
    # Apply rewards (modified by completion quality)
    final_rewards = apply_quest_rewards(rewards, completion_quality)
    
    # Apply faction changes
    faction_changes = apply_faction_changes(faction_impact, quest.user, session_id)
    
    # Apply Force alignment change
    force_change = quest.force_impact
    if completion_method in ['dark_side', 'ruthless']:
        force_change -= 5
    elif completion_method in ['light_side', 'merciful']:
        force_change += 5
    
    if force_change != 0:
        from services.force_engine import update_force_alignment
        alignment_result = update_force_alignment(
            user=quest.user,
            action_type='light' if force_change > 0 else 'dark',
            action_description=f"Completed quest: {quest.quest_title}",
            force_magnitude=abs(force_change) // 5,
            session_id=session_id
        )
    
    # Generate consequences based on choices
    consequences = generate_quest_consequences(quest, completion_method, player_choices, session_id)
    
    return {
        'completion_quality': completion_quality,
        'rewards': final_rewards,
        'faction_changes': faction_changes,
        'force_change': force_change,
        'consequences': consequences
    }

def calculate_completion_quality(method, choices, difficulty):
    """
    Calculate quality of quest completion (0.0 to 1.5)
    """
    base_quality = 1.0
    
    # Method modifiers
    method_modifiers = {
        'perfect': 0.5,
        'efficient': 0.3,
        'standard': 0.0,
        'sloppy': -0.2,
        'barely': -0.4
    }
    
    base_quality += method_modifiers.get(method, 0.0)
    
    # Choice modifiers (simplified)
    if 'creative_solution' in choices:
        base_quality += 0.2
    if 'helped_innocents' in choices:
        base_quality += 0.1
    if 'caused_collateral_damage' in choices:
        base_quality -= 0.2
    
    return max(0.1, min(1.5, base_quality))

def apply_quest_rewards(rewards, quality_modifier):
    """
    Apply quest rewards modified by completion quality
    """
    final_rewards = []
    
    if 'credits' in rewards:
        credits = int(rewards['credits'] * quality_modifier)
        final_rewards.append(f"{credits} credits")
    
    if 'reputation' in rewards:
        final_rewards.append(rewards['reputation'])
    
    if 'experience' in rewards:
        final_rewards.append(rewards['experience'])
    
    # Quality bonus rewards
    if quality_modifier > 1.2:
        final_rewards.append("Bonus reward for exceptional performance")
    
    return final_rewards

def apply_faction_changes(faction_impact, user, session_id):
    """
    Apply faction relationship changes from quest completion
    """
    changes = {}
    
    for faction_name, impact in faction_impact.items():
        if impact != 0:
            from services.faction_ai import update_faction_awareness
            result = update_faction_awareness(
                faction_name=faction_name,
                user=user,
                relationship_change=impact,
                awareness_change=abs(impact) // 2,
                action_description="Quest completion",
                session_id=session_id
            )
            changes[faction_name] = impact
    
    return changes

def generate_quest_consequences(quest, completion_method, player_choices, session_id):
    """
    Generate ongoing consequences from quest completion
    """
    consequences = []
    
    # Method-based consequences
    if completion_method == 'ruthless':
        consequences.append("Your ruthless methods have been noted by local authorities")
    elif completion_method == 'merciful':
        consequences.append("Your merciful approach has earned you respect among civilians")
    
    # Choice-based consequences
    if 'betrayed_ally' in player_choices:
        consequences.append("Your betrayal will have lasting repercussions")
    if 'saved_innocents' in player_choices:
        consequences.append("The people you saved will remember your kindness")
    
    # Generate follow-up quest hooks
    if quest.difficulty >= 7:
        consequences.append(f"Your actions in '{quest.quest_title}' have attracted the attention of powerful individuals")
    
    return consequences

def apply_quest_failure_consequences(quest, failure_reason, session_id):
    """
    Apply consequences for quest failure
    """
    consequences = []
    faction_changes = {}
    reputation_impact = -10
    
    # Base failure consequences
    consequences.append(f"Failed to complete '{quest.quest_title}'")
    
    # Failure reason specific consequences
    if failure_reason == 'timeout':
        consequences.append("Deadline missed - reliability questioned")
        reputation_impact -= 5
    elif failure_reason == 'player_death':
        consequences.append("Mission failure due to casualties")
        reputation_impact -= 15
    elif failure_reason == 'betrayal':
        consequences.append("Quest giver feels betrayed")
        reputation_impact -= 20
    
    # Apply faction consequences if any
    faction_impact = json.loads(quest.faction_impact) if isinstance(quest.faction_impact, str) else quest.faction_impact
    for faction_name, impact in faction_impact.items():
        if impact != 0:
            # Reverse and worsen the intended impact
            failure_impact = -(abs(impact) + 5)
            from services.faction_ai import update_faction_awareness
            result = update_faction_awareness(
                faction_name=faction_name,
                user=quest.user,
                relationship_change=failure_impact,
                awareness_change=5,
                action_description=f"Failed quest: {quest.quest_title}",
                session_id=session_id
            )
            faction_changes[faction_name] = failure_impact
    
    return {
        'consequences': consequences,
        'faction_changes': faction_changes,
        'reputation_impact': reputation_impact
    }
