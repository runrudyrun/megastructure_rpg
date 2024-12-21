"""Movement system for the ECS."""
from typing import Tuple, Optional
import numpy as np

from ..entity import Entity
from ..entity_manager import EntityManager
from ..components.movement import MovementComponent, TransformComponent
from ...physics.movement import MovementState


class MovementSystem:
    """System for handling entity movement."""
    
    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
    
    def update(self, dt: float) -> None:
        """Update movement for all relevant entities."""
        # Get all entities with movement components
        moving_entities = self.entity_manager.get_entities_with_components(
            MovementComponent, TransformComponent
        )
        
        for entity in moving_entities:
            movement = self.entity_manager.get_component(entity, MovementComponent)
            transform = self.entity_manager.get_component(entity, TransformComponent)
            
            # Handle movement to target position
            if movement.target_x is not None and movement.target_y is not None:
                dx = movement.target_x - transform.x
                dy = movement.target_y - transform.y
                distance = np.sqrt(dx * dx + dy * dy)
                
                if distance > 0.1:  # Movement threshold
                    # Calculate direction
                    direction_x = dx / distance
                    direction_y = dy / distance
                    
                    # Set velocity based on state
                    speed = (movement.stats.run_speed 
                            if movement.state == MovementState.RUNNING
                            else movement.stats.walk_speed)
                    
                    movement.velocity_x = direction_x * speed
                    movement.velocity_y = direction_y * speed
                    movement.state = MovementState.WALKING
                else:
                    # Reached target
                    transform.x = movement.target_x
                    transform.y = movement.target_y
                    movement.target_x = None
                    movement.target_y = None
                    movement.velocity_x = 0
                    movement.velocity_y = 0
                    movement.state = MovementState.IDLE
            
            # Handle rotation to target
            if movement.target_rotation is not None:
                current_rotation = transform.rotation % 360
                target_rotation = movement.target_rotation % 360
                
                # Calculate shortest rotation path
                diff = target_rotation - current_rotation
                if diff > 180:
                    diff -= 360
                elif diff < -180:
                    diff += 360
                
                # Apply rotation
                if abs(diff) > 0.1:  # Rotation threshold
                    rotation_speed = movement.stats.turn_speed * dt
                    if abs(diff) < rotation_speed:
                        transform.rotation = target_rotation
                    else:
                        transform.rotation += np.sign(diff) * rotation_speed
                else:
                    transform.rotation = target_rotation
                    movement.target_rotation = None
            
            # Apply movement
            transform.x += movement.velocity_x * dt
            transform.y += movement.velocity_y * dt
    
    def set_movement_target(
        self,
        entity: Entity,
        target_x: float,
        target_y: float,
        running: bool = False
    ) -> None:
        """Set a target position for an entity to move to."""
        movement = self.entity_manager.get_component(entity, MovementComponent)
        if movement:
            movement.target_x = target_x
            movement.target_y = target_y
            movement.state = MovementState.RUNNING if running else MovementState.WALKING
    
    def set_rotation_target(self, entity: Entity, target_rotation: float) -> None:
        """Set a target rotation for an entity."""
        movement = self.entity_manager.get_component(entity, MovementComponent)
        if movement:
            movement.target_rotation = target_rotation
    
    def stop_movement(self, entity: Entity) -> None:
        """Stop an entity's movement."""
        movement = self.entity_manager.get_component(entity, MovementComponent)
        if movement:
            movement.target_x = None
            movement.target_y = None
            movement.velocity_x = 0
            movement.velocity_y = 0
            movement.state = MovementState.IDLE
    
    def set_direct_movement(
        self,
        entity: Entity,
        direction: Tuple[float, float],
        running: bool = False
    ) -> None:
        """Set direct movement input for an entity."""
        movement = self.entity_manager.get_component(entity, MovementComponent)
        if movement:
            # Clear any target position
            movement.target_x = None
            movement.target_y = None
            
            # Calculate velocity
            length = np.sqrt(direction[0]**2 + direction[1]**2)
            if length > 0:
                # Normalize and scale by speed
                speed = (movement.stats.run_speed if running
                        else movement.stats.walk_speed)
                movement.velocity_x = direction[0] / length * speed
                movement.velocity_y = direction[1] / length * speed
                movement.state = (MovementState.RUNNING if running
                                else MovementState.WALKING)
            else:
                movement.velocity_x = 0
                movement.velocity_y = 0
                movement.state = MovementState.IDLE
