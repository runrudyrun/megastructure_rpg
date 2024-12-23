"""Spatial awareness and memory system for AI entities."""
from typing import Dict, Set, List, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import time
from ..ecs.entity import Entity
from ..ecs.component import Position

@dataclass
class MemoryRecord:
    """Record of an entity or point of interest."""
    position: Tuple[float, float]
    entity_id: Optional[int]  # None for points of interest
    timestamp: float
    importance: float  # Higher values are more important
    certainty: float  # 1.0 = certain, 0.0 = forgotten
    
    def age(self) -> float:
        """Get age of memory in seconds."""
        return time.time() - self.timestamp
        
    def update_certainty(self, decay_rate: float = 0.1) -> None:
        """Update certainty based on age."""
        self.certainty = max(0.0, self.certainty - (self.age() * decay_rate))

class SpatialGrid:
    """Grid-based spatial partitioning for efficient queries."""
    
    def __init__(self, width: int, height: int, cell_size: float = 5.0):
        self.cell_size = cell_size
        self.grid_width = int(np.ceil(width / cell_size))
        self.grid_height = int(np.ceil(height / cell_size))
        self.grid: Dict[Tuple[int, int], Set[int]] = {}
        
    def _get_cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        return (int(x / self.cell_size), int(y / self.cell_size))
        
    def add_entity(self, entity_id: int, x: float, y: float) -> None:
        """Add an entity to the grid."""
        cell = self._get_cell(x, y)
        if cell not in self.grid:
            self.grid[cell] = set()
        self.grid[cell].add(entity_id)
        
    def remove_entity(self, entity_id: int, x: float, y: float) -> None:
        """Remove an entity from the grid."""
        cell = self._get_cell(x, y)
        if cell in self.grid:
            self.grid[cell].discard(entity_id)
            if not self.grid[cell]:
                del self.grid[cell]
                
    def update_entity(self, entity_id: int, old_x: float, old_y: float,
                     new_x: float, new_y: float) -> None:
        """Update an entity's position in the grid."""
        old_cell = self._get_cell(old_x, old_y)
        new_cell = self._get_cell(new_x, new_y)
        
        if old_cell != new_cell:
            if old_cell in self.grid:
                self.grid[old_cell].discard(entity_id)
                if not self.grid[old_cell]:
                    del self.grid[old_cell]
                    
            if new_cell not in self.grid:
                self.grid[new_cell] = set()
            self.grid[new_cell].add(entity_id)
            
    def get_entities_in_range(self, x: float, y: float, radius: float) -> Set[int]:
        """Get all entities within radius of a point."""
        result = set()
        cell_radius = int(np.ceil(radius / self.cell_size))
        center_cell = self._get_cell(x, y)
        
        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                if cell in self.grid:
                    result.update(self.grid[cell])
                    
        return result

class SpatialMemory:
    """Spatial memory and awareness system for AI entities."""
    
    def __init__(self, decay_rate: float = 0.1, memory_limit: int = 100):
        self.decay_rate = decay_rate
        self.memory_limit = memory_limit
        self.memories: Dict[int, Dict[int, MemoryRecord]] = {}  # entity_id -> {target_id -> record}
        self.points_of_interest: Dict[int, Dict[str, MemoryRecord]] = {}  # entity_id -> {poi_name -> record}
        
    def update_entity_memory(self, observer_id: int, target_id: int,
                           position: Tuple[float, float], importance: float = 1.0) -> None:
        """Update memory of an entity."""
        if observer_id not in self.memories:
            self.memories[observer_id] = {}
            
        self.memories[observer_id][target_id] = MemoryRecord(
            position=position,
            entity_id=target_id,
            timestamp=time.time(),
            importance=importance,
            certainty=1.0
        )
        
        # Enforce memory limit
        if len(self.memories[observer_id]) > self.memory_limit:
            # Remove least important memories
            sorted_memories = sorted(
                self.memories[observer_id].items(),
                key=lambda x: x[1].importance * x[1].certainty
            )
            for target_id, _ in sorted_memories[:len(sorted_memories) - self.memory_limit]:
                del self.memories[observer_id][target_id]
                
    def add_point_of_interest(self, observer_id: int, poi_name: str,
                            position: Tuple[float, float], importance: float = 1.0) -> None:
        """Add or update a point of interest."""
        if observer_id not in self.points_of_interest:
            self.points_of_interest[observer_id] = {}
            
        self.points_of_interest[observer_id][poi_name] = MemoryRecord(
            position=position,
            entity_id=None,
            timestamp=time.time(),
            importance=importance,
            certainty=1.0
        )
        
    def get_recent_memories(self, observer_id: int, max_age: float = float('inf'),
                          min_certainty: float = 0.0) -> List[MemoryRecord]:
        """Get recent memories above certainty threshold."""
        if observer_id not in self.memories:
            return []
            
        current_time = time.time()
        memories = []
        
        for record in self.memories[observer_id].values():
            record.update_certainty(self.decay_rate)
            if (record.age() <= max_age and
                record.certainty >= min_certainty):
                memories.append(record)
                
        return sorted(memories, key=lambda x: x.importance * x.certainty, reverse=True)
        
    def get_nearest_poi(self, observer_id: int, position: Tuple[float, float],
                       min_certainty: float = 0.0) -> Optional[Tuple[str, MemoryRecord]]:
        """Get the nearest point of interest above certainty threshold."""
        if observer_id not in self.points_of_interest:
            return None
            
        nearest = None
        min_dist = float('inf')
        
        for name, record in self.points_of_interest[observer_id].items():
            record.update_certainty(self.decay_rate)
            if record.certainty < min_certainty:
                continue
                
            dist = np.sqrt((position[0] - record.position[0])**2 +
                          (position[1] - record.position[1])**2)
            if dist < min_dist:
                min_dist = dist
                nearest = (name, record)
                
        return nearest
        
    def forget_entity(self, observer_id: int, target_id: int) -> None:
        """Remove memory of an entity."""
        if observer_id in self.memories:
            self.memories[observer_id].pop(target_id, None)
            
    def forget_old_memories(self, max_age: float) -> None:
        """Remove memories older than max_age."""
        current_time = time.time()
        
        for observer_id in list(self.memories.keys()):
            self.memories[observer_id] = {
                target_id: record
                for target_id, record in self.memories[observer_id].items()
                if record.age() <= max_age
            }
            
    def clear_entity_memory(self, observer_id: int) -> None:
        """Clear all memories for an entity."""
        self.memories.pop(observer_id, None)
        self.points_of_interest.pop(observer_id, None)
