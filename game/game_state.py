"""Game state management system."""
from enum import Enum, auto
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..engine.ecs.entity import Entity
from ..engine.ecs.component import Position, Health, Inventory, Stats
from ..engine.world.generator import MegastructureGenerator
from ..engine.physics.collision import CollisionSystem
from ..engine.ai.goap import AIPlanner

class GameState(Enum):
    """Game states."""
    MAIN_MENU = auto()
    PLAYING = auto()
    INVENTORY = auto()
    CHARACTER = auto()
    DIALOG = auto()
    PAUSED = auto()
    GAME_OVER = auto()

@dataclass
class PlayerData:
    """Player character data."""
    entity: Entity
    level: int = 1
    experience: int = 0
    skill_points: int = 0
    discovered_sectors: set = None
    
    def __post_init__(self):
        if self.discovered_sectors is None:
            self.discovered_sectors = set()
            
    def add_experience(self, amount: int) -> bool:
        """Add experience and return True if leveled up."""
        self.experience += amount
        level_threshold = self.level * 1000  # Simple level scaling
        
        if self.experience >= level_threshold:
            self.level_up()
            return True
        return False
        
    def level_up(self) -> None:
        """Level up the player character."""
        self.level += 1
        self.skill_points += 3
        
        # Increase base stats
        stats = self.entity.get_component(Stats)
        if stats:
            stats.max_health += 10
            stats.strength += 2
            stats.defense += 2
            
            # Heal on level up
            health = self.entity.get_component(Health)
            if health:
                health.current = stats.max_health

class GameStateManager:
    """Manages game state and transitions."""
    
    def __init__(self, world_width: float, world_height: float):
        self.current_state = GameState.MAIN_MENU
        self.previous_state = None
        self.world_width = world_width
        self.world_height = world_height
        
        # Core systems
        self.world_generator = MegastructureGenerator()
        self.collision_system = None  # Initialized after world generation
        self.ai_planners: Dict[int, AIPlanner] = {}
        
        # Game data
        self.player: Optional[PlayerData] = None
        self.current_sector = (0, 0)  # Starting sector coordinates
        self.active_quests: Dict[str, Any] = {}
        self.game_time = 0.0
        self.dialog_stack = []
        
    def initialize_new_game(self) -> None:
        """Initialize a new game session."""
        # Generate starting sector
        starting_sector = self.world_generator.generate_sector(0, 0)
        self.collision_system = CollisionSystem(
            starting_sector.tilemap,
            self.world_width,
            self.world_height
        )
        
        # Create player character
        player_entity = Entity()
        player_entity.add_component(Position(x=starting_sector.spawn_point[0],
                                           y=starting_sector.spawn_point[1]))
        player_entity.add_component(Health(current=100, max=100))
        player_entity.add_component(Inventory(capacity=20))
        player_entity.add_component(Stats(
            max_health=100,
            strength=10,
            defense=10,
            agility=10,
            intelligence=10
        ))
        
        self.player = PlayerData(entity=player_entity)
        self.player.discovered_sectors.add((0, 0))
        
        # Register player with collision system
        self.collision_system.register_entity(
            player_entity,
            (int(starting_sector.spawn_point[0]),
             int(starting_sector.spawn_point[1]))
        )
        
        self.current_state = GameState.PLAYING
        
    def change_state(self, new_state: GameState) -> None:
        """Change the current game state."""
        self.previous_state = self.current_state
        self.current_state = new_state
        
    def revert_state(self) -> None:
        """Revert to the previous state."""
        if self.previous_state:
            self.current_state = self.previous_state
            
    def update(self, dt: float) -> None:
        """Update game state."""
        self.game_time += dt
        
        if self.current_state == GameState.PLAYING:
            # Update physics
            if self.collision_system:
                self.collision_system.update(dt)
            
            # Update AI
            for ai_planner in self.ai_planners.values():
                ai_planner.update()
            
            # Check for sector transition
            if self.player:
                pos = self.player.entity.get_component(Position)
                if pos:
                    # Simple sector transition check
                    sector_x = int(pos.x // self.world_width)
                    sector_y = int(pos.y // self.world_height)
                    
                    if (sector_x, sector_y) != self.current_sector:
                        self.transition_sector(sector_x, sector_y)
                        
    def transition_sector(self, new_x: int, new_y: int) -> None:
        """Transition to a new sector."""
        # Generate new sector if needed
        if (new_x, new_y) not in self.player.discovered_sectors:
            self.world_generator.generate_sector(new_x, new_y)
            self.player.discovered_sectors.add((new_x, new_y))
        
        # Update current sector
        self.current_sector = (new_x, new_y)
        
        # Adjust player position within new sector
        pos = self.player.entity.get_component(Position)
        if pos:
            pos.x = pos.x % self.world_width
            pos.y = pos.y % self.world_height
            
        # Update collision system with new sector
        new_sector = self.world_generator.get_sector(new_x, new_y)
        self.collision_system = CollisionSystem(
            new_sector.tilemap,
            self.world_width,
            self.world_height
        )
        
    def save_game(self, filename: str) -> None:
        """Save current game state."""
        # TODO: Implement save game functionality
        pass
        
    def load_game(self, filename: str) -> None:
        """Load a saved game state."""
        # TODO: Implement load game functionality
        pass
