# Galaxy of Consequence RPG Backend

## Overview

Galaxy of Consequence is a Flask-based Star Wars-inspired RPG backend system featuring autonomous faction AI, Force morality mechanics, procedural quest generation, and NVIDIA Nemotron integration for immersive NPC dialogue. The system emphasizes persistent consequences where player actions create cascading effects throughout the galaxy.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Framework
- **Flask**: Core web framework with modular blueprint architecture
- **SQLAlchemy**: ORM for database operations with declarative base
- **SQLite**: Default database with configurable database URI support
- **JWT Extended**: Token-based authentication system
- **CORS**: Cross-origin resource sharing enabled

### Authentication Strategy
- **Bearer Token System**: Uses a magic token "Abracadabra" for initial authentication
- **JWT Tokens**: Persistent sessions with non-expiring access tokens
- **Dual Authentication**: Bearer token for initial access, JWT for subsequent requests

## Key Components

### Database Models
- **CanvasEntry**: Persistent game state storage for player sessions
- **FactionState**: Autonomous faction AI state with territory control, resources, and strategic goals
- **ForceAlignment**: Player Force morality tracking with light/dark side progression
- **NPCMemory**: Interactive NPC relationship and memory system
- **QuestLog**: Procedural quest generation and tracking
- **ThreatLevel**: Escalating consequence system based on player actions
- **SessionState**: Multiplayer session management
- **WorldEvent**: Galaxy-wide event tracking and history

### Core Services
- **Faction AI Engine**: Autonomous faction behavior with territory expansion, resource management, and strategic decision-making
- **Force Engine**: Morality system with cascading consequences for Force-sensitive actions
- **Quest Generator**: Procedural quest creation based on player history, faction relations, and Force alignment
- **Threat Scaler**: Dynamic difficulty scaling based on player notoriety and actions
- **NPC Memory System**: Persistent NPC relationships with trust, fear, and interaction history

### API Routes
- **Authentication** (`/auth`): Bearer token and JWT authentication endpoints
- **Canvas** (`/canvas`): Game state persistence and retrieval
- **Faction** (`/faction`): Faction AI simulation and state management
- **Force** (`/force`): Force alignment updates and consequence triggering
- **Nemotron** (`/nemotron`): NVIDIA AI integration for NPC dialogue
- **Quest** (`/quest`): Procedural quest generation and management
- **Session** (`/session`): Multiplayer session creation and management

## Data Flow

### Player Action Processing
1. Player performs action via API endpoint
2. System updates relevant character state (Force alignment, threat level, NPC relationships)
3. Faction AI evaluates action impact and adjusts strategies
4. Consequences propagate through interconnected systems
5. World events are generated based on cumulative changes

### Faction AI Simulation
1. Periodic faction tick execution (24-hour cycles or manual triggers)
2. Each faction evaluates current state and strategic goals
3. Actions are selected based on resources, territory, and player interactions
4. Cross-faction relationships are updated based on conflicting interests
5. World events are generated from faction activities

### NPC Interaction Flow
1. Player interacts with NPC via Nemotron endpoint
2. NPC memory system retrieves interaction history and relationship data
3. NVIDIA Nemotron generates contextual dialogue response
4. Interaction updates NPC memory, trust levels, and relationship dynamics
5. Changes may trigger faction awareness or world event generation

## External Dependencies

### NVIDIA Integration
- **API Endpoint**: `https://integrate.api.nvidia.com/v1/chat/completions`
- **Model**: nvidia/nemotron-mini-4b-instruct (default)
- **Features**: Streaming responses, contextual NPC dialogue, RAG capabilities
- **Authentication**: Bearer token authentication with NVIDIA API key

### Python Dependencies
- Flask ecosystem (Flask, SQLAlchemy, JWT-Extended, CORS)
- Requests library for external API communication
- Marshmallow for schema validation
- Flask-Swagger-UI for API documentation

## Deployment Strategy

### Configuration Management
- Environment variables for sensitive data (JWT secrets, API keys, database URIs)
- Default SQLite database with PostgreSQL support ready
- ProxyFix middleware for production deployment
- CORS enabled for frontend integration

### Database Strategy
- SQLAlchemy with declarative base for easy model management
- Automatic table creation on application startup
- Connection pooling and health checks configured
- Default faction initialization on first run

### API Documentation
- OpenAPI 3.1 specification with Swagger UI at `/docs`
- Comprehensive endpoint documentation with request/response schemas
- Star Wars themed UI styling for immersive documentation experience

### Production Considerations
- Gunicorn WSGI server support
- Logging configuration with debug level
- Session secret and JWT key management via environment variables
- Database URL configuration for different environments

The system is designed to be modular and extensible, with each component handling specific aspects of the RPG experience while maintaining interconnected relationships that create meaningful consequences for player actions.