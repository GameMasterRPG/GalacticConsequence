# Galaxy of Consequence - API Testing Guide

## Base URL
```
http://localhost:5000
```

## Authentication
The API uses Bearer token authentication with the magic token: `Abracadabra`

### 1. Authenticate and Get JWT Token
```bash
curl -X POST http://localhost:5000/authenticate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer Abracadabra"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "galaxy_status": "Access granted to the Galaxy of Consequence",
  "message": "Authentication successful"
}
```

### 2. Verify JWT Token
```bash
curl -X GET http://localhost:5000/verify \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Core API Endpoints

### Character Management

#### Save Character Data (Canvas)
```bash
curl -X POST http://localhost:5000/save_canvas \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "canvas": "character_sheet",
    "data": {
      "name": "Luke Skywalker",
      "species": "Human",
      "homeworld": "Tatooine",
      "background": "Moisture Farmer",
      "allegiance": "Rebel Alliance",
      "appearance": "Young human male with blonde hair and blue eyes",
      "primary_weapon": "Lightsaber",
      "secondary_weapon": "DL-44 Blaster",
      "armor": "Jedi Robes",
      "skills": ["Piloting", "Force Sensitivity", "Lightsaber Combat"]
    }
  }'
```

#### Get Character Data
```bash
curl -X GET "http://localhost:5000/get_canvas?user=Luke_Skywalker" \
  -H "Authorization: Bearer Abracadabra"
```

### Force Alignment System

#### Get Force Alignment
```bash
curl -X GET "http://localhost:5000/get_alignment?user=Luke_Skywalker" \
  -H "Authorization: Bearer Abracadabra"
```

#### Update Force Alignment
```bash
# Light Side Action
curl -X POST http://localhost:5000/update_alignment \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "action_type": "light",
    "action_description": "Saved innocent civilians from Imperial attack",
    "alignment_shift": 25
  }'

# Dark Side Action
curl -X POST http://localhost:5000/update_alignment \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Darth_Vader",
    "action_type": "dark",
    "action_description": "Used Force choke on subordinate",
    "alignment_shift": -30
  }'

# Neutral Action
curl -X POST http://localhost:5000/update_alignment \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Han_Solo",
    "action_type": "neutral",
    "action_description": "Negotiated business deal",
    "alignment_shift": 0
  }'
```

### Faction System

#### Get All Faction States
```bash
curl -X GET http://localhost:5000/get_faction_state \
  -H "Authorization: Bearer Abracadabra"
```

#### Trigger Faction AI Turn
```bash
curl -X POST http://localhost:5000/faction_turn \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "faction_name": "Galactic Empire"
  }'
```

#### Update Faction Awareness
```bash
curl -X POST http://localhost:5000/update_faction_awareness \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "faction": "Galactic Empire",
    "action": "Destroyed Death Star",
    "awareness_increase": 50,
    "hostility_increase": 75
  }'
```

### Quest System

#### Generate Quest
```bash
curl -X POST http://localhost:5000/generate_quest \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "session_id": "rebellion_campaign_1"
  }'
```

#### Get Quest List
```bash
curl -X GET "http://localhost:5000/get_quests?user=Luke_Skywalker" \
  -H "Authorization: Bearer Abracadabra"
```

#### Accept Quest
```bash
curl -X POST http://localhost:5000/accept_quest \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "quest_id": 1
  }'
```

#### Complete Quest
```bash
curl -X POST http://localhost:5000/complete_quest \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "quest_id": 1,
    "completion_details": "Successfully delivered cargo without incident"
  }'
```

### Session Management

#### Create Session
```bash
curl -X POST http://localhost:5000/create_session \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "session_name": "Rebellion Campaign",
    "created_by": "GameMaster"
  }'
```

#### Get Session State
```bash
curl -X GET "http://localhost:5000/get_session_state?session_id=YOUR_SESSION_ID" \
  -H "Authorization: Bearer Abracadabra"
```

#### Join Session
```bash
curl -X POST http://localhost:5000/join_session \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "user": "Luke_Skywalker"
  }'
```

### NVIDIA Nemotron AI Integration

#### Query Nemotron for NPC Dialogue
```bash
curl -X POST http://localhost:5000/query_nemotron \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "npc_name": "Obi-Wan Kenobi",
    "query": "Tell me about the Force",
    "context": {
      "location": "Tatooine",
      "setting": "Ben Kenobi hut",
      "situation": "Training session"
    }
  }'
```

#### Stream Nemotron Response (WebSocket-like)
```bash
curl -X POST http://localhost:5000/stream_nemotron \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "npc_name": "Yoda",
    "query": "How do I become a Jedi?",
    "context": {
      "location": "Dagobah",
      "setting": "Swamp training ground"
    }
  }'
```

### NPC Memory System

#### Update NPC Memory
```bash
curl -X POST http://localhost:5000/update_npc_memory \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{
    "user": "Luke_Skywalker",
    "npc_name": "Han_Solo",
    "interaction_type": "conversation",
    "content": "Discussed smuggling routes and Imperial patrols",
    "trust_change": 10,
    "location": "Mos Eisley Cantina"
  }'
```

#### Get NPC Memory
```bash
curl -X GET "http://localhost:5000/get_npc_memory?user=Luke_Skywalker&npc_name=Han_Solo" \
  -H "Authorization: Bearer Abracadabra"
```

## Testing Workflow Examples

### Complete Character Journey
```bash
# 1. Create character
curl -X POST http://localhost:5000/save_canvas \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"user": "Rey", "canvas": "character_sheet", "data": {"name": "Rey", "homeworld": "Jakku"}}'

# 2. Discover Force sensitivity
curl -X POST http://localhost:5000/update_alignment \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"user": "Rey", "action_type": "light", "action_description": "Used Force to pull lightsaber", "alignment_shift": 15}'

# 3. Generate quest based on Force discovery
curl -X POST http://localhost:5000/generate_quest \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"user": "Rey", "session_id": "sequel_trilogy"}'

# 4. Chat with Force ghost
curl -X POST http://localhost:5000/query_nemotron \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"user": "Rey", "npc_name": "Luke_Skywalker_Ghost", "query": "How do I control my Force powers?"}'
```

### Faction Conflict Simulation
```bash
# 1. Check initial faction state
curl -X GET http://localhost:5000/get_faction_state \
  -H "Authorization: Bearer Abracadabra"

# 2. Trigger major action that affects factions
curl -X POST http://localhost:5000/update_faction_awareness \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"user": "Luke_Skywalker", "faction": "Galactic Empire", "action": "Destroyed Death Star", "awareness_increase": 90, "hostility_increase": 95}'

# 3. Run faction AI turn to see reaction
curl -X POST http://localhost:5000/faction_turn \
  -H "Authorization: Bearer Abracadabra" \
  -H "Content-Type: application/json" \
  -d '{"faction_name": "Galactic Empire"}'

# 4. Check updated faction state
curl -X GET http://localhost:5000/get_faction_state \
  -H "Authorization: Bearer Abracadabra"
```

## API Documentation
- **Swagger UI**: http://localhost:5000/docs
- **OpenAPI Schema**: http://localhost:5000/openapi.yaml
- **Health Check**: http://localhost:5000/health

## Testing Tips

1. **Always use Bearer token**: `Authorization: Bearer Abracadabra`
2. **Force action types**: Must be "light", "dark", or "neutral"
3. **Session IDs**: Keep track of session IDs for multiplayer features
4. **Character consistency**: Use consistent usernames across endpoints
5. **NPC names**: Use underscores instead of spaces (e.g., "Obi_Wan_Kenobi")

## Error Handling
All endpoints return standard HTTP status codes:
- **200**: Success
- **400**: Bad Request (missing parameters)
- **401**: Unauthorized (invalid Bearer token)
- **404**: Not Found
- **500**: Internal Server Error

Error responses include detailed messages:
```json
{
  "error": "Missing required fields: user, action_type",
  "status": "error"
}
```