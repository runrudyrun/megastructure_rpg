"""Spatial partitioning system for efficient physics and collision detection."""
from typing import Dict, Set, List, Tuple, Optional, TypeVar, Generic
from dataclasses import dataclass
import numpy as np
from ..ecs.entity import Entity
from ..ecs.component import Position, Collider

T = TypeVar('T')

@dataclass
class AABB:
    """Axis-Aligned Bounding Box."""
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    
    def intersects(self, other: 'AABB') -> bool:
        """Check if this AABB intersects with another."""
        return (self.min_x <= other.max_x and self.max_x >= other.min_x and
                self.min_y <= other.max_y and self.max_y >= other.min_y)
                
    def contains_point(self, x: float, y: float) -> bool:
        """Check if this AABB contains a point."""
        return (self.min_x <= x <= self.max_x and
                self.min_y <= y <= self.max_y)
                
    @property
    def center(self) -> Tuple[float, float]:
        """Get the center point of the AABB."""
        return ((self.min_x + self.max_x) / 2,
                (self.min_y + self.max_y) / 2)
                
    @property
    def width(self) -> float:
        """Get the width of the AABB."""
        return self.max_x - self.min_x
        
    @property
    def height(self) -> float:
        """Get the height of the AABB."""
        return self.max_y - self.min_y

class SpatialCell(Generic[T]):
    """A cell in the spatial grid containing objects."""
    
    def __init__(self):
        self.static_objects: Set[T] = set()
        self.dynamic_objects: Set[T] = set()
        
    def add_object(self, obj: T, is_static: bool = False) -> None:
        """Add an object to the cell."""
        if is_static:
            self.static_objects.add(obj)
        else:
            self.dynamic_objects.add(obj)
            
    def remove_object(self, obj: T, is_static: bool = False) -> None:
        """Remove an object from the cell."""
        if is_static:
            self.static_objects.discard(obj)
        else:
            self.dynamic_objects.discard(obj)
            
    def get_all_objects(self) -> Set[T]:
        """Get all objects in the cell."""
        return self.static_objects | self.dynamic_objects
        
    def clear_dynamic(self) -> None:
        """Clear all dynamic objects from the cell."""
        self.dynamic_objects.clear()

class SpatialGrid(Generic[T]):
    """Grid-based spatial partitioning system."""
    
    def __init__(self, width: float, height: float, cell_size: float):
        self.width = width
        self.height = height
        self.cell_size = cell_size
        
        self.grid_width = int(np.ceil(width / cell_size))
        self.grid_height = int(np.ceil(height / cell_size))
        self.grid: Dict[Tuple[int, int], SpatialCell[T]] = {}
        
        # Cache for object cell mappings
        self.object_cells: Dict[T, Set[Tuple[int, int]]] = {}
        
    def _get_cell_coords(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        cell_x = max(0, min(self.grid_width - 1, int(x / self.cell_size)))
        cell_y = max(0, min(self.grid_height - 1, int(y / self.cell_size)))
        return (cell_x, cell_y)
        
    def _get_overlapping_cells(self, aabb: AABB) -> List[Tuple[int, int]]:
        """Get all cells that overlap with an AABB."""
        min_cell = self._get_cell_coords(aabb.min_x, aabb.min_y)
        max_cell = self._get_cell_coords(aabb.max_x, aabb.max_y)
        
        cells = []
        for x in range(min_cell[0], max_cell[0] + 1):
            for y in range(min_cell[1], max_cell[1] + 1):
                cells.append((x, y))
        return cells
        
    def _ensure_cell(self, cell_coords: Tuple[int, int]) -> SpatialCell[T]:
        """Get or create a cell at the given coordinates."""
        if cell_coords not in self.grid:
            self.grid[cell_coords] = SpatialCell()
        return self.grid[cell_coords]
        
    def add_object(self, obj: T, aabb: AABB, is_static: bool = False) -> None:
        """Add an object to all relevant grid cells."""
        cells = self._get_overlapping_cells(aabb)
        
        for cell_coords in cells:
            cell = self._ensure_cell(cell_coords)
            cell.add_object(obj, is_static)
            
        self.object_cells[obj] = set(cells)
        
    def remove_object(self, obj: T, is_static: bool = False) -> None:
        """Remove an object from all its grid cells."""
        if obj in self.object_cells:
            for cell_coords in self.object_cells[obj]:
                if cell_coords in self.grid:
                    self.grid[cell_coords].remove_object(obj, is_static)
            del self.object_cells[obj]
            
    def update_object(self, obj: T, old_aabb: AABB, new_aabb: AABB,
                     is_static: bool = False) -> None:
        """Update an object's position in the grid."""
        old_cells = set(self._get_overlapping_cells(old_aabb))
        new_cells = set(self._get_overlapping_cells(new_aabb))
        
        # Remove from cells no longer overlapping
        for cell_coords in (old_cells - new_cells):
            if cell_coords in self.grid:
                self.grid[cell_coords].remove_object(obj, is_static)
                
        # Add to new overlapping cells
        for cell_coords in (new_cells - old_cells):
            cell = self._ensure_cell(cell_coords)
            cell.add_object(obj, is_static)
            
        self.object_cells[obj] = new_cells
        
    def get_nearby_objects(self, aabb: AABB) -> Set[T]:
        """Get all objects that might intersect with an AABB."""
        nearby = set()
        cells = self._get_overlapping_cells(aabb)
        
        for cell_coords in cells:
            if cell_coords in self.grid:
                nearby.update(self.grid[cell_coords].get_all_objects())
                
        return nearby
        
    def get_objects_in_range(self, x: float, y: float, radius: float) -> Set[T]:
        """Get all objects within a radius of a point."""
        aabb = AABB(
            min_x=x - radius,
            min_y=y - radius,
            max_x=x + radius,
            max_y=y + radius
        )
        return self.get_nearby_objects(aabb)
        
    def clear_dynamic_objects(self) -> None:
        """Clear all dynamic objects from the grid."""
        for cell in self.grid.values():
            cell.clear_dynamic()
        
        # Remove dynamic objects from cache
        self.object_cells = {
            obj: cells
            for obj, cells in self.object_cells.items()
            if obj in self.static_objects
        }

class PhysicsGrid:
    """Specialized spatial grid for physics entities."""
    
    def __init__(self, width: float, height: float, cell_size: float = 32.0):
        self.grid = SpatialGrid[Entity](width, height, cell_size)
        
    def _get_entity_aabb(self, entity: Entity) -> AABB:
        """Get AABB for an entity."""
        pos = entity.get_component(Position)
        col = entity.get_component(Collider)
        
        if not pos or not col:
            raise ValueError(f"Entity {entity.id} missing Position or Collider")
            
        return AABB(
            min_x=pos.x - col.radius,
            min_y=pos.y - col.radius,
            max_x=pos.x + col.radius,
            max_y=pos.y + col.radius
        )
        
    def add_entity(self, entity: Entity, is_static: bool = False) -> None:
        """Add an entity to the physics grid."""
        aabb = self._get_entity_aabb(entity)
        self.grid.add_object(entity, aabb, is_static)
        
    def remove_entity(self, entity: Entity, is_static: bool = False) -> None:
        """Remove an entity from the physics grid."""
        self.grid.remove_object(entity, is_static)
        
    def update_entity(self, entity: Entity, old_pos: Tuple[float, float],
                     is_static: bool = False) -> None:
        """Update an entity's position in the physics grid."""
        col = entity.get_component(Collider)
        if not col:
            return
            
        old_aabb = AABB(
            min_x=old_pos[0] - col.radius,
            min_y=old_pos[1] - col.radius,
            max_x=old_pos[0] + col.radius,
            max_y=old_pos[1] + col.radius
        )
        
        new_aabb = self._get_entity_aabb(entity)
        self.grid.update_object(entity, old_aabb, new_aabb, is_static)
        
    def get_potential_collisions(self, entity: Entity) -> Set[Entity]:
        """Get all entities that might collide with the given entity."""
        aabb = self._get_entity_aabb(entity)
        return self.grid.get_nearby_objects(aabb) - {entity}
        
    def get_entities_in_range(self, x: float, y: float,
                            radius: float) -> Set[Entity]:
        """Get all entities within a radius of a point."""
        return self.grid.get_objects_in_range(x, y, radius)
        
    def clear_dynamic_entities(self) -> None:
        """Clear all dynamic entities from the grid."""
        self.grid.clear_dynamic_objects()
