# Megastructure RPG

A *Blame!*-inspired roguelike RPG set in an infinite megastructure, featuring procedural generation, modular lore, and intelligent NPCs.

## Features
- Component-Entity System architecture for modular game design
- Data-driven game mechanics and quest systems
- Procedurally generated environments
- Advanced NPC AI with independent behavior
- Dynamic lore and story generation

## Setup
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure
- `engine/`: Core game engine components
  - `ecs/`: Component-Entity System framework
  - `world/`: World generation and management
  - `ai/`: NPC AI systems
- `data/`: Game data and configuration files
- `game/`: Game-specific implementations
- `utils/`: Utility functions and helpers
- `tests/`: Test suite
