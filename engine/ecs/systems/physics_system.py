"""Physics system for the ECS."""
from typing import Dict, Set, Tuple
import numpy as np

from ..entity import Entity
from ..entity_manager import EntityManager
from ..components.physics import ColliderComponent, RigidbodyComponent
from ..components.movement import TransformComponent
from ...physics.collision import CollisionSystem, CollisionResult


class PhysicsSystem:
    """System for handling physics simulation and collision detection."""
    
    def __init__(self, entity_manager: EntityManager, collision_system: CollisionSystem):
        self.entity_manager = entity_manager
        self.collision_system = collision_system
        self.gravity = (0.0, -9.81)  # Default gravity
    
    def update(self, dt: float) -> None:
        """Update physics for all relevant entities."""
        # Get all entities with physics components
        physics_entities = self.entity_manager.get_entities_with_components(
            RigidbodyComponent, ColliderComponent, TransformComponent
        )
        
        for entity in physics_entities:
            rigidbody = self.entity_manager.get_component(entity, RigidbodyComponent)
            collider = self.entity_manager.get_component(entity, ColliderComponent)
            transform = self.entity_manager.get_component(entity, TransformComponent)
            
            if not rigidbody.is_kinematic:
                # Apply gravity
                gravity_force = (
                    self.gravity[0] * rigidbody.gravity_scale,
                    self.gravity[1] * rigidbody.gravity_scale
                )
                
                # Update velocity
                velocity_x = transform.velocity_x + gravity_force[0] * dt
                velocity_y = transform.velocity_y + gravity_force[1] * dt
                
                # Apply drag
                drag_factor = 1.0 - (rigidbody.drag * dt)
                velocity_x *= drag_factor
                velocity_y *= drag_factor
                
                # Calculate new position
                new_x = transform.x + velocity_x * dt
                new_y = transform.y + velocity_y * dt
                
                # Check for collisions
                collision = self.collision_system.check_tile_collision(
                    collider.shape,
                    new_x,
                    new_y
                )
                
                if collision.collided and not collider.is_trigger:
                    # Resolve collision
                    new_x = transform.x + velocity_x * dt - collision.penetration_x
                    new_y = transform.y + velocity_y * dt - collision.penetration_y
                    
                    # Adjust velocity based on collision normal
                    if collision.normal_x != 0:
                        velocity_x = 0
                    if collision.normal_y != 0:
                        velocity_y = 0
                
                # Update transform
                transform.x = new_x
                transform.y = new_y
                transform.velocity_x = velocity_x
                transform.velocity_y = velocity_y
    
    def check_collision(
        self,
        entity: Entity,
        offset_x: float = 0.0,
        offset_y: float = 0.0
    ) -> Tuple[bool, Set[Entity]]:
        """Check if an entity would collide at an offset from its current position."""
        collider = self.entity_manager.get_component(entity, ColliderComponent)
        transform = self.entity_manager.get_component(entity, TransformComponent)
        
        if not collider or not transform:
            return False, set()
        
        # Check tile collision
        tile_collision = self.collision_system.check_tile_collision(
            collider.shape,
            transform.x + offset_x,
            transform.y + offset_y
        )
        
        if tile_collision.collided and not collider.is_trigger:
            return True, set()
        
        # Check entity collisions
        collided_entities = set()
        entity_collisions = self.collision_system.check_entity_collision(
            entity.id,
            transform.x + offset_x,
            transform.y + offset_y
        )
        
        for other_id, collision in entity_collisions:
            other_entity = self.entity_manager.get_entity(other_id)
            if other_entity:
                other_collider = self.entity_manager.get_component(
                    other_entity, ColliderComponent
                )
                if other_collider and not other_collider.is_trigger:
                    collided_entities.add(other_entity)
        
        return len(collided_entities) > 0, collided_entities
    
    def set_gravity(self, x: float, y: float) -> None:
        """Set the global gravity vector."""
        self.gravity = (x, y)
