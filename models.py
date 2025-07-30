from app import db
from sqlalchemy import func
from datetime import datetime
import json

class CanvasEntry(db.Model):
    """Persistent game state storage for player sessions"""
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(255), nullable=False, index=True)
    campaign = db.Column(db.String(255), nullable=True, index=True)
    canvas = db.Column(db.String(255), nullable=True, index=True)
    data = db.Column(db.Text, nullable=False)  # JSON serialized game state
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(255), nullable=True, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user': self.user,
            'campaign': self.campaign,
            'canvas': self.canvas,
            'data': json.loads(self.data) if self.data else {},
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id
        }

class FactionState(db.Model):
    """Autonomous faction AI state and history"""
    id = db.Column(db.Integer, primary_key=True)
    faction_name = db.Column(db.String(255), nullable=False, unique=True)
    territory_control = db.Column(db.Integer, default=0)  # Number of systems controlled
    resources = db.Column(db.Integer, default=1000)  # Economic/military resources
    influence = db.Column(db.Integer, default=50)  # Political influence (0-100)
    awareness_level = db.Column(db.Integer, default=0)  # Player awareness (0-100)
    hostility_level = db.Column(db.Integer, default=0)  # Hostility towards player (-100 to 100)
    active_operations = db.Column(db.Text, default='[]')  # JSON list of current operations
    strategic_goals = db.Column(db.Text, nullable=False)  # JSON list of faction objectives
    last_action = db.Column(db.DateTime, default=datetime.utcnow)
    faction_type = db.Column(db.String(100), nullable=False)  # Imperial, Rebel, CSA, Hutt, etc.
    
    def get_operations(self):
        return json.loads(self.active_operations) if self.active_operations else []
    
    def set_operations(self, operations):
        self.active_operations = json.dumps(operations)
    
    def get_goals(self):
        return json.loads(self.strategic_goals) if self.strategic_goals else []
    
    def set_goals(self, goals):
        self.strategic_goals = json.dumps(goals)

class QuestLog(db.Model):
    """Procedurally generated and player-accepted quests"""
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(255), nullable=False, index=True)
    quest_title = db.Column(db.String(500), nullable=False)
    quest_description = db.Column(db.Text, nullable=False)
    quest_giver = db.Column(db.String(255), nullable=False)  # NPC or faction
    reward = db.Column(db.Text, nullable=False)  # JSON serialized rewards
    requirements = db.Column(db.Text, nullable=False)  # JSON serialized requirements
    status = db.Column(db.String(50), default='available')  # available, active, completed, failed
    difficulty = db.Column(db.Integer, default=1)  # 1-10 scale
    faction_impact = db.Column(db.Text, default='{}')  # JSON faction standing changes
    force_impact = db.Column(db.Integer, default=0)  # Force alignment impact (-100 to 100)
    generated_reason = db.Column(db.Text, nullable=False)  # Why this quest was generated
    prerequisite_events = db.Column(db.Text, default='[]')  # JSON list of required events
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    session_id = db.Column(db.String(255), nullable=True, index=True)

class SessionState(db.Model):
    """Multiplayer session synchronization and world state"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, unique=True)
    session_name = db.Column(db.String(255), nullable=False)
    galaxy_state = db.Column(db.Text, nullable=False)  # JSON serialized galaxy state
    active_players = db.Column(db.Text, default='[]')  # JSON list of active players
    current_galactic_year = db.Column(db.Integer, default=0)  # Years since Battle of Yavin
    major_events = db.Column(db.Text, default='[]')  # JSON list of galactic events
    faction_war_status = db.Column(db.Text, default='{}')  # JSON faction relationships
    force_nexus_events = db.Column(db.Text, default='[]')  # JSON Force-related events
    threat_escalation_level = db.Column(db.Integer, default=1)  # Galaxy-wide threat level
    last_faction_tick = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ForceAlignment(db.Model):
    """Player Force sensitivity and moral choices tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(255), nullable=False, unique=True)
    light_side_points = db.Column(db.Integer, default=0)
    dark_side_points = db.Column(db.Integer, default=0)
    force_sensitive = db.Column(db.Boolean, default=False)
    force_events = db.Column(db.Text, default='[]')  # JSON list of Force-related actions
    alignment_history = db.Column(db.Text, default='[]')  # JSON history of alignment changes
    force_powers = db.Column(db.Text, default='[]')  # JSON list of unlocked powers
    corruption_level = db.Column(db.Integer, default=0)  # Physical/mental corruption from Dark Side
    last_force_event = db.Column(db.DateTime, nullable=True)
    session_id = db.Column(db.String(255), nullable=True, index=True)
    
    @property
    def net_alignment(self):
        """Calculate net Force alignment (-100 to 100)"""
        total_points = max(1, self.light_side_points + self.dark_side_points)
        return int(((self.light_side_points - self.dark_side_points) / total_points) * 100)
    
    @property
    def alignment_description(self):
        """Human-readable alignment description"""
        net = self.net_alignment
        if net >= 75:
            return "Light Side Paragon"
        elif net >= 25:
            return "Light Side Leaning"
        elif net >= -25:
            return "Balanced/Gray"
        elif net >= -75:
            return "Dark Side Leaning"
        else:
            return "Dark Side Corruption"

class NPCMemory(db.Model):
    """NPC relationship and interaction history for reactive behavior"""
    id = db.Column(db.Integer, primary_key=True)
    npc_name = db.Column(db.String(255), nullable=False, index=True)
    user = db.Column(db.String(255), nullable=False, index=True)
    relationship_level = db.Column(db.Integer, default=0)  # -100 to 100
    trust_level = db.Column(db.Integer, default=0)  # 0 to 100
    fear_level = db.Column(db.Integer, default=0)  # 0 to 100
    interaction_history = db.Column(db.Text, default='[]')  # JSON list of interactions
    known_player_actions = db.Column(db.Text, default='[]')  # JSON list of player actions NPC knows about
    npc_faction = db.Column(db.String(255), nullable=True)
    last_interaction = db.Column(db.DateTime, default=datetime.utcnow)
    personality_traits = db.Column(db.Text, default='[]')  # JSON list of NPC traits
    current_mood = db.Column(db.String(100), default='neutral')
    session_id = db.Column(db.String(255), nullable=True, index=True)

class ThreatLevel(db.Model):
    """Dynamic threat escalation tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(255), nullable=False, unique=True)
    notoriety_level = db.Column(db.Integer, default=0)  # 0 to 100
    bounty_amount = db.Column(db.Integer, default=0)  # Credits
    imperial_awareness = db.Column(db.Integer, default=0)  # 0 to 100
    rebel_awareness = db.Column(db.Integer, default=0)  # 0 to 100
    criminal_reputation = db.Column(db.Integer, default=0)  # 0 to 100
    active_bounties = db.Column(db.Text, default='[]')  # JSON list of bounty hunters
    escalation_triggers = db.Column(db.Text, default='[]')  # JSON list of threat escalations
    heat_level = db.Column(db.Integer, default=1)  # Current overall threat level (1-10)
    last_escalation = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(255), nullable=True, index=True)

class WorldEvent(db.Model):
    """Galaxy-wide events affecting all players"""
    id = db.Column(db.Integer, primary_key=True)
    event_title = db.Column(db.String(500), nullable=False)
    event_description = db.Column(db.Text, nullable=False)
    event_type = db.Column(db.String(100), nullable=False)  # political, military, force, economic
    affected_factions = db.Column(db.Text, default='[]')  # JSON list of affected factions
    galactic_impact = db.Column(db.Integer, default=1)  # 1-10 scale of impact
    triggered_by_player = db.Column(db.String(255), nullable=True)  # Which player triggered this
    consequences = db.Column(db.Text, default='[]')  # JSON list of ongoing consequences
    duration_days = db.Column(db.Integer, default=1)  # How long the event lasts
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(255), nullable=True, index=True)
