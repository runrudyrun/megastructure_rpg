"""Grid-based collision detection for roguelike movement."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict

from ..world.tilemap import TileMap, TileType


@dataclass
class CollisionResult:
    """Result of a collision test."""
    collided: bool = False
    blocked_direction: Optional[Tuple[int, int]] = None


class CollisionSystem:
    """Handles grid-based collision detection."""
    
    def __init__(self, tilemap: TileMap):
        self.tilemap = tilemap
        self.solid_tiles = {
            TileType.WALL,
            TileType.MACHINE,
            TileType.MACHINES,
            TileType.CONTAINER,
            TileType.CONTAINERS,
            TileType.PILLAR,
            TileType.PILLARS
        }
        # Dictionary to track entity positions
        self.entity_positions: Dict[int, Tuple[int, int]] = {}
    
    def register_entity(self, entity_id: int, position: Tuple[int, int]) -> None:
        """Register an entity's position."""
        self.entity_positions[entity_id] = position
    
    def unregister_entity(self, entity_id: int) -> None:
        """Unregister an entity."""
        self.entity_positions.pop(entity_id, None)
    
    def check_move(self, entity_id: int, new_x: int, new_y: int) -> CollisionResult:
        """Check if an entity can move to a new position."""
        # Check tile collision
        if not self.tilemap.is_valid_position(new_x, new_y):
            return CollisionResult(True, None)
        
        tile = self.tilemap.get_tile(new_x, new_y)
        if tile in self.solid_tiles:
            return CollisionResult(True, None)
        
        # Check entity collisions
        for other_id, pos in self.entity_positions.items():
            if other_id != entity_id and pos == (new_x, new_y):
                return CollisionResult(True, None)
        
        return CollisionResult(False, None)
    
    def move_entity(self, entity_id: int, new_x: int, new_y: int) -> bool:
        """Try to move an entity to a new position."""
        result = self.check_move(entity_id, new_x, new_y)
        if not result.collided:
            self.entity_positions[entity_id] = (new_x, new_y)
            return True
        return False
    
    def get_entity_position(self, entity_id: int) -> Optional[Tuple[int, int]]:
        """Get an entity's current position."""
        return self.entity_positions.get(entity_id)
