"""Turn-based grid movement system."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Tuple, Optional, List
import numpy as np

from .collision import CollisionSystem


class MovementState(Enum):
    """States of entity movement."""
    IDLE = auto()
    MOVING = auto()
    WAITING = auto()


@dataclass
class MovementStats:
    """Movement-related statistics for an entity."""
    movement_points: int = 1  # Number of tiles that can be moved per turn
    diagonal_movement: bool = False  # Whether diagonal movement is allowed


class MovementSystem:
    """Handles turn-based grid movement."""
    
    def __init__(self, collision_system: CollisionSystem):
        self.collision_system = collision_system
        self.movement_stats: Dict[int, MovementStats] = {}
        self.states: Dict[int, MovementState] = {}
        self.pending_moves: Dict[int, Tuple[int, int]] = {}  # Target positions for this turn
        self.current_turn = 0
    
    def register_entity(
        self,
        entity_id: int,
        position: Tuple[int, int],
        stats: Optional[MovementStats] = None
    ) -> None:
        """Register an entity with the movement system."""
        self.collision_system.register_entity(entity_id, position)
        self.movement_stats[entity_id] = stats or MovementStats()
        self.states[entity_id] = MovementState.IDLE
    
    def unregister_entity(self, entity_id: int) -> None:
        """Unregister an entity from the movement system."""
        self.collision_system.unregister_entity(entity_id)
        self.movement_stats.pop(entity_id, None)
        self.states.pop(entity_id, None)
        self.pending_moves.pop(entity_id, None)
    
    def request_move(self, entity_id: int, dx: int, dy: int) -> bool:
        """Request a move for an entity in the next turn."""
        if entity_id not in self.movement_stats:
            return False
        
        # Get current position
        current_pos = self.collision_system.get_entity_position(entity_id)
        if not current_pos:
            return False
        
        # Check if move is valid
        stats = self.movement_stats[entity_id]
        if not stats.diagonal_movement and dx != 0 and dy != 0:
            return False
        
        # Calculate new position
        new_x = current_pos[0] + dx
        new_y = current_pos[1] + dy
        
        # Check if move is within movement points
        distance = abs(dx) + abs(dy)
        if distance > stats.movement_points:
            return False
        
        # Check for collisions
        if not self.collision_system.check_move(entity_id, new_x, new_y).collided:
            self.pending_moves[entity_id] = (new_x, new_y)
            self.states[entity_id] = MovementState.MOVING
            return True
        
        return False
    
    def execute_turn(self) -> None:
        """Execute all pending moves for this turn."""
        # Execute all pending moves
        executed_moves = []
        for entity_id, target_pos in self.pending_moves.items():
            # Check if move is still valid
            if not self.collision_system.check_move(entity_id, target_pos[0], target_pos[1]).collided:
                self.collision_system.move_entity(entity_id, target_pos[0], target_pos[1])
                executed_moves.append(entity_id)
        
        # Clear executed moves
        for entity_id in executed_moves:
            self.pending_moves.pop(entity_id)
            self.states[entity_id] = MovementState.IDLE
        
        # Increment turn counter
        self.current_turn += 1
    
    def get_position(self, entity_id: int) -> Optional[Tuple[int, int]]:
        """Get the current position of an entity."""
        return self.collision_system.get_entity_position(entity_id)
    
    def get_state(self, entity_id: int) -> Optional[MovementState]:
        """Get the current movement state of an entity."""
        return self.states.get(entity_id)
    
    def get_valid_moves(self, entity_id: int) -> List[Tuple[int, int]]:
        """Get all valid moves for an entity."""
        valid_moves = []
        current_pos = self.get_position(entity_id)
        if not current_pos or entity_id not in self.movement_stats:
            return valid_moves
        
        stats = self.movement_stats[entity_id]
        moves = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        if stats.diagonal_movement:
            moves.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
        
        for dx, dy in moves:
            new_x = current_pos[0] + dx
            new_y = current_pos[1] + dy
            if not self.collision_system.check_move(entity_id, new_x, new_y).collided:
                valid_moves.append((new_x, new_y))
        
        return valid_moves
