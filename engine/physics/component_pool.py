"""Component pooling system for physics components."""
from typing import Dict, List, Type, TypeVar, Optional
from dataclasses import dataclass, field
from ..ecs.component import Component, Position, Velocity, Collider

T = TypeVar('T', bound=Component)

@dataclass
class ComponentPool(Generic[T]):
    """Pool for reusing component instances."""
    component_type: Type[T]
    initial_size: int = 100
    grow_size: int = 50
    active_components: Dict[int, T] = field(default_factory=dict)
    available_components: List[T] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize the pool with components."""
        self._grow_pool(self.initial_size)
        
    def _grow_pool(self, size: int) -> None:
        """Grow the pool by creating new components."""
        for _ in range(size):
            component = self.component_type()
            self.available_components.append(component)
            
    def acquire(self, entity_id: int) -> T:
        """Get a component from the pool."""
        if not self.available_components:
            self._grow_pool(self.grow_size)
            
        component = self.available_components.pop()
        self.active_components[entity_id] = component
        return component
        
    def release(self, entity_id: int) -> None:
        """Return a component to the pool."""
        if entity_id in self.active_components:
            component = self.active_components.pop(entity_id)
            # Reset component state
            for key, value in component.__dict__.items():
                if isinstance(value, (int, float)):
                    setattr(component, key, 0)
                elif isinstance(value, bool):
                    setattr(component, key, False)
                else:
                    setattr(component, key, None)
            self.available_components.append(component)
            
    def get(self, entity_id: int) -> Optional[T]:
        """Get an active component for an entity."""
        return self.active_components.get(entity_id)
        
    def clear(self) -> None:
        """Clear all components from the pool."""
        self.available_components.extend(self.active_components.values())
        self.active_components.clear()

class PhysicsComponentPools:
    """Manager for physics component pools."""
    
    def __init__(self):
        self.position_pool = ComponentPool(Position)
        self.velocity_pool = ComponentPool(Velocity)
        self.collider_pool = ComponentPool(Collider)
        
    def create_physics_components(self, entity_id: int,
                                has_velocity: bool = True) -> tuple:
        """Create a set of physics components for an entity."""
        position = self.position_pool.acquire(entity_id)
        velocity = self.velocity_pool.acquire(entity_id) if has_velocity else None
        collider = self.collider_pool.acquire(entity_id)
        
        return position, velocity, collider
        
    def release_physics_components(self, entity_id: int) -> None:
        """Release all physics components for an entity."""
        self.position_pool.release(entity_id)
        self.velocity_pool.release(entity_id)
        self.collider_pool.release(entity_id)
        
    def get_position(self, entity_id: int) -> Optional[Position]:
        """Get the position component for an entity."""
        return self.position_pool.get(entity_id)
        
    def get_velocity(self, entity_id: int) -> Optional[Velocity]:
        """Get the velocity component for an entity."""
        return self.velocity_pool.get(entity_id)
        
    def get_collider(self, entity_id: int) -> Optional[Collider]:
        """Get the collider component for an entity."""
        return self.collider_pool.get(entity_id)
        
    def clear(self) -> None:
        """Clear all component pools."""
        self.position_pool.clear()
        self.velocity_pool.clear()
        self.collider_pool.clear()
