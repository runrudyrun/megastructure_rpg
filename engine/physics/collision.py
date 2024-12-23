"""Grid-based collision detection for roguelike movement with continuous collision detection."""
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict, Set
import numpy as np
from ..world.tilemap import TileMap, TileType
from ..ecs.entity import Entity
from ..ecs.component import Position, Collider, Velocity
from .spatial_grid import PhysicsGrid, AABB

@dataclass
class CollisionResult:
    """Result of a collision test."""
    collided: bool = False
    blocked_direction: Optional[Tuple[int, int]] = None
    contact_point: Optional[Tuple[float, float]] = None
    contact_normal: Optional[Tuple[float, float]] = None
    penetration: float = 0.0

@dataclass
class CollisionPair:
    """A pair of entities that might collide."""
    entity_a: Entity
    entity_b: Entity
    distance: float

class CollisionSystem:
    """Handles grid-based and continuous collision detection."""
    
    def __init__(self, tilemap: TileMap, world_width: float, world_height: float):
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
        # Spatial partitioning for continuous collision detection
        self.physics_grid = PhysicsGrid(world_width, world_height)
        # Cache for static collision shapes
        self.static_colliders: List[AABB] = []
        self._build_static_colliders()
        
    def _build_static_colliders(self) -> None:
        """Build collision shapes for static tiles."""
        for x in range(self.tilemap.width):
            for y in range(self.tilemap.height):
                tile = self.tilemap.get_tile(x, y)
                if tile in self.solid_tiles:
                    self.static_colliders.append(AABB(
                        min_x=float(x),
                        min_y=float(y),
                        max_x=float(x + 1),
                        max_y=float(y + 1)
                    ))
    
    def register_entity(self, entity: Entity, position: Tuple[int, int]) -> None:
        """Register an entity's position."""
        self.entity_positions[entity.id] = position
        if entity.has_component(Collider):
            self.physics_grid.add_entity(entity)
    
    def unregister_entity(self, entity: Entity) -> None:
        """Unregister an entity."""
        self.entity_positions.pop(entity.id, None)
        if entity.has_component(Collider):
            self.physics_grid.remove_entity(entity)
    
    def check_move(self, entity_id: int, new_x: int, new_y: int) -> CollisionResult:
        """Check if an entity can move to a new position (grid-based)."""
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
    
    def move_entity(self, entity: Entity, new_x: int, new_y: int) -> bool:
        """Try to move an entity to a new position (grid-based)."""
        result = self.check_move(entity.id, new_x, new_y)
        if not result.collided:
            old_pos = self.entity_positions.get(entity.id)
            self.entity_positions[entity.id] = (new_x, new_y)
            
            # Update physics grid if entity has collider
            if entity.has_component(Collider) and old_pos:
                self.physics_grid.update_entity(
                    entity,
                    (float(old_pos[0]), float(old_pos[1]))
                )
            return True
        return False
    
    def get_entity_position(self, entity_id: int) -> Optional[Tuple[int, int]]:
        """Get an entity's current position."""
        return self.entity_positions.get(entity_id)
        
    def _check_circle_circle(self, pos_a: Position, col_a: Collider,
                           pos_b: Position, col_b: Collider) -> CollisionResult:
        """Check collision between two circles."""
        dx = pos_b.x - pos_a.x
        dy = pos_b.y - pos_a.y
        distance = np.sqrt(dx * dx + dy * dy)
        
        if distance == 0:  # Entities are at the same position
            return CollisionResult(
                collided=True,
                contact_point=(pos_a.x, pos_a.y),
                contact_normal=(1, 0),
                penetration=col_a.radius + col_b.radius
            )
            
        if distance < col_a.radius + col_b.radius:
            normal = (dx / distance, dy / distance)
            penetration = col_a.radius + col_b.radius - distance
            contact_point = (
                pos_a.x + normal[0] * col_a.radius,
                pos_a.y + normal[1] * col_a.radius
            )
            return CollisionResult(
                collided=True,
                contact_point=contact_point,
                contact_normal=normal,
                penetration=penetration
            )
            
        return CollisionResult(collided=False)
        
    def _check_circle_aabb(self, pos: Position, col: Collider,
                          aabb: AABB) -> CollisionResult:
        """Check collision between a circle and an AABB."""
        # Find closest point on AABB to circle center
        closest_x = max(aabb.min_x, min(pos.x, aabb.max_x))
        closest_y = max(aabb.min_y, min(pos.y, aabb.max_y))
        
        # Calculate distance between closest point and circle center
        dx = pos.x - closest_x
        dy = pos.y - closest_y
        distance = np.sqrt(dx * dx + dy * dy)
        
        if distance < col.radius:
            if distance == 0:  # Circle center is inside AABB
                # Push out in x direction
                penetration = col.radius
                normal = (1, 0)
            else:
                penetration = col.radius - distance
                normal = (dx / distance, dy / distance)
                
            return CollisionResult(
                collided=True,
                contact_point=(closest_x, closest_y),
                contact_normal=normal,
                penetration=penetration
            )
            
        return CollisionResult(collided=False)
        
    def check_collision(self, entity_a: Entity, entity_b: Entity) -> CollisionResult:
        """Check collision between two entities."""
        pos_a = entity_a.get_component(Position)
        col_a = entity_a.get_component(Collider)
        pos_b = entity_b.get_component(Position)
        col_b = entity_b.get_component(Collider)
        
        if not all([pos_a, col_a, pos_b, col_b]):
            return CollisionResult(collided=False)
            
        return self._check_circle_circle(pos_a, col_a, pos_b, col_b)
        
    def check_static_collision(self, entity: Entity) -> Optional[CollisionResult]:
        """Check collision between an entity and static geometry."""
        pos = entity.get_component(Position)
        col = entity.get_component(Collider)
        
        if not pos or not col:
            return None
            
        for static_aabb in self.static_colliders:
            result = self._check_circle_aabb(pos, col, static_aabb)
            if result.collided:
                return result
                
        return None
        
    def resolve_collision(self, entity_a: Entity, entity_b: Entity,
                         result: CollisionResult) -> None:
        """Resolve a collision between two entities."""
        pos_a = entity_a.get_component(Position)
        pos_b = entity_b.get_component(Position)
        vel_a = entity_a.get_component(Velocity)
        vel_b = entity_b.get_component(Velocity)
        
        if not all([pos_a, pos_b]):
            return
            
        # Positional correction
        percent = 0.2  # Penetration percentage to correct
        correction = (result.penetration / 2.0) * percent
        
        if vel_a and not vel_b:  # Only A is dynamic
            pos_a.x -= result.contact_normal[0] * result.penetration
            pos_a.y -= result.contact_normal[1] * result.penetration
        elif vel_b and not vel_a:  # Only B is dynamic
            pos_b.x += result.contact_normal[0] * result.penetration
            pos_b.y += result.contact_normal[1] * result.penetration
        else:  # Both are dynamic
            pos_a.x -= result.contact_normal[0] * correction
            pos_a.y -= result.contact_normal[1] * correction
            pos_b.x += result.contact_normal[0] * correction
            pos_b.y += result.contact_normal[1] * correction
            
        # Velocity resolution (if both entities have velocity)
        if vel_a and vel_b:
            # Relative velocity
            rv_x = vel_b.x - vel_a.x
            rv_y = vel_b.y - vel_a.y
            
            # Calculate relative velocity in terms of the normal direction
            velocity_along_normal = (rv_x * result.contact_normal[0] +
                                   rv_y * result.contact_normal[1])
            
            # Do not resolve if velocities are separating
            if velocity_along_normal > 0:
                return
                
            # Calculate restitution (bounciness)
            restitution = min(vel_a.restitution, vel_b.restitution)
            
            # Calculate impulse scalar
            j = -(1 + restitution) * velocity_along_normal
            j /= 1/vel_a.mass + 1/vel_b.mass
            
            # Apply impulse
            impulse_x = j * result.contact_normal[0]
            impulse_y = j * result.contact_normal[1]
            
            vel_a.x -= impulse_x / vel_a.mass
            vel_a.y -= impulse_y / vel_a.mass
            vel_b.x += impulse_x / vel_b.mass
            vel_b.y += impulse_y / vel_b.mass
            
    def update(self, dt: float) -> None:
        """Update the physics system."""
        # Get all entities with colliders
        collider_entities = {
            entity for entity in self.physics_grid.grid.object_cells.keys()
            if entity.has_component(Collider)
        }
        
        # Check dynamic vs dynamic collisions
        checked_pairs = set()
        for entity_a in collider_entities:
            potential_collisions = self.physics_grid.get_potential_collisions(entity_a)
            
            for entity_b in potential_collisions:
                if (entity_a, entity_b) in checked_pairs or (entity_b, entity_a) in checked_pairs:
                    continue
                    
                result = self.check_collision(entity_a, entity_b)
                if result.collided:
                    self.resolve_collision(entity_a, entity_b, result)
                    
                checked_pairs.add((entity_a, entity_b))
                
        # Check dynamic vs static collisions
        for entity in collider_entities:
            result = self.check_static_collision(entity)
            if result:
                pos = entity.get_component(Position)
                if pos:
                    pos.x -= result.contact_normal[0] * result.penetration
                    pos.y -= result.contact_normal[1] * result.penetration
                    
        # Update physics grid
        for entity in collider_entities:
            pos = entity.get_component(Position)
            if pos:
                old_pos = self.entity_positions.get(entity.id, (pos.x, pos.y))
                self.physics_grid.update_entity(entity, old_pos)
                self.entity_positions[entity.id] = (int(pos.x), int(pos.y))
