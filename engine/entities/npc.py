"""NPC entity implementation."""
from typing import Optional, Tuple, Dict, Any
import logging
from ..world.tilemap import TileMap, TileType, Room
from ..ecs.entity import Entity
from ..ecs.component import AI, Position, Physical, Health, Inventory

logger = logging.getLogger(__name__)

class NPC(Entity):
    """NPC entity class."""
    def __init__(self, id: int, x: int, y: int, behavior_type: str):
        """Initialize NPC with required components."""
        super().__init__(id)
        
        # Add required components
        self.add_component(Position(x=float(x), y=float(y)))
        self.add_component(Physical(solid=True, blocking=True))
        self.add_component(AI(behavior_type=behavior_type))
        self.add_component(Health(current=100.0, maximum=100.0))
        self.add_component(Inventory())
        
        # Initialize AI state
        ai = self.get_component(AI)
        if ai:
            ai.state = {
                'current_state': 'idle',
                'idle_time': 0.0,
                'wander_time': 0.0,
                'target_id': None,
                'target_distance': float('inf'),
                'target_detected': False
            }
            logger.debug(f"NPC {id} ({behavior_type}) initialized with state: {ai.state}")
    
    def update(self, world: Any, dt: float, config: Dict[str, Any]) -> None:
        """Update NPC state."""
        # The behavior system will handle state updates
        ai = self.get_component(AI)
        if not ai:
            return
            
        # Update AI state if needed
        if not ai.state:
            ai.state = {
                'current_state': 'idle',
                'idle_time': 0.0,
                'wander_time': 0.0,
                'target_id': None,
                'target_distance': float('inf'),
                'target_detected': False
            }
            logger.debug(f"NPC {self.id} ({ai.behavior_type}) state reset to: {ai.state}")
    
    def get_current_task(self) -> Optional[str]:
        """Get the current behavior state."""
        ai = self.get_component(AI)
        if not ai or not ai.state:
            return None
            
        current_state = ai.state.get('current_state')
        logger.debug(f"NPC {self.id} ({ai.behavior_type}) current state: {current_state}")
        
        # Check if we should be in attacking state
        if current_state == 'attacking':
            target_id = ai.state.get('target_id')
            target_distance = ai.state.get('target_distance', float('inf'))
            logger.debug(f"NPC {self.id} ({ai.behavior_type}) target_id: {target_id}, target_distance: {target_distance}")
            
            # If we have no target or target is too far, go back to idle
            if target_id is None or target_distance > 10.0:  # Use a reasonable fallback distance
                logger.debug(f"NPC {self.id} ({ai.behavior_type}) invalid attacking state, resetting to idle")
                ai.state['current_state'] = 'idle'
                ai.state['target_id'] = None
                ai.state['target_distance'] = float('inf')
                ai.state['target_detected'] = False
                return 'idle'
                
        return current_state
    
    def can_interact_with(self, tilemap: TileMap, x: int, y: int) -> bool:
        """Check if NPC can interact with a tile."""
        pos = self.get_component(Position)
        if not pos:
            return False
            
        # Check if position is valid
        if not tilemap.is_valid_position(x, y):
            return False
        
        # Check if tile is within interaction range (adjacent)
        if abs(pos.x - x) > 1 or abs(pos.y - y) > 1:
            return False
        
        # Check if tile is interactable
        tile = tilemap.get_tile(x, y)
        return tile in [TileType.DOOR, TileType.FLOOR]
    
    def get_current_room(self, tilemap: TileMap) -> Optional[Room]:
        """Get the room the NPC is currently in."""
        pos = self.get_component(Position)
        if not pos:
            return None
            
        for room in tilemap.rooms.values():
            if (room.x <= pos.x < room.x + room.width and 
                room.y <= pos.y < room.y + room.height):
                return room
        return None
    
    def move_to(self, x: int, y: int, tilemap: TileMap) -> bool:
        """Move NPC towards target position."""
        pos = self.get_component(Position)
        if not pos:
            return False
            
        # Check if position is valid
        if not tilemap.is_valid_position(x, y):
            return False
        
        # Check if tile is walkable
        tile = tilemap.get_tile(x, y)
        if tile not in [TileType.FLOOR, TileType.DOOR]:
            return False
        
        # Update position
        pos.x = float(x)
        pos.y = float(y)
        return True
    
    def interact_with(self, target: 'NPC') -> None:
        """Interact with another NPC."""
        ai = self.get_component(AI)
        if not ai:
            return
            
        if ai.behavior_type == "merchant":
            # Trading logic
            self._trade_with(target)
        elif ai.behavior_type == "guard":
            # Guard interaction logic
            self._investigate(target)
    
    def _trade_with(self, target: 'NPC') -> None:
        """Trading logic."""
        my_inventory = self.get_component(Inventory)
        target_inventory = target.get_component(Inventory)
        
        if not my_inventory or not target_inventory:
            return
            
        # Implement trading mechanics here
        # For now, just log the interaction
        ai = self.get_component(AI)
        if ai:
            ai.state['last_trade'] = target.id
    
    def _investigate(self, target: 'NPC') -> None:
        """Guard investigation logic."""
        ai = self.get_component(AI)
        if not ai:
            return
            
        # Set target for investigation
        ai.state['investigation_target'] = target.id
        ai.state['current_state'] = 'pursuing'
