from typing import Dict, Type, Optional, Set
from .entity import Entity
from .component import Component
from .component_pool import ComponentPool

class EntityManager:
    """Manages entities and their components."""
    
    def __init__(self):
        self._next_entity_id = 1
        self._entities: Dict[int, Entity] = {}
        self._component_pools: Dict[Type[Component], ComponentPool] = {}
        self._entity_components: Dict[int, Set[Type[Component]]] = {}
        
    def create_entity(self) -> Entity:
        """Create a new entity."""
        entity_id = self._next_entity_id
        self._next_entity_id += 1
        entity = Entity(entity_id)
        self._entities[entity_id] = entity
        self._entity_components[entity_id] = set()
        return entity
        
    def destroy_entity(self, entity_id: int) -> None:
        """Destroy an entity and all its components."""
        if entity_id in self._entities:
            # Release all components back to their pools
            component_types = self._entity_components.pop(entity_id, set())
            for comp_type in component_types:
                self._component_pools[comp_type].release(entity_id)
            del self._entities[entity_id]
            
    def add_component(self, entity_id: int, component_type: Type[Component], **kwargs) -> Component:
        """Add a component to an entity."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} does not exist")
            
        # Get or create component pool
        if component_type not in self._component_pools:
            self._component_pools[component_type] = ComponentPool(component_type)
            
        # Get component from pool
        component = self._component_pools[component_type].acquire(entity_id, **kwargs)
        self._entity_components[entity_id].add(component_type)
        return component
        
    def remove_component(self, entity_id: int, component_type: Type[Component]) -> None:
        """Remove a component from an entity."""
        if entity_id in self._entities and component_type in self._component_pools:
            self._component_pools[component_type].release(entity_id)
            self._entity_components[entity_id].discard(component_type)
            
    def get_component(self, entity_id: int, component_type: Type[Component]) -> Optional[Component]:
        """Get a component from an entity."""
        if component_type in self._component_pools:
            return self._component_pools[component_type].get(entity_id)
        return None
        
    def has_component(self, entity_id: int, component_type: Type[Component]) -> bool:
        """Check if an entity has a component."""
        return component_type in self._entity_components.get(entity_id, set())
        
    def get_entities_with_components(self, *component_types: Type[Component]) -> Set[int]:
        """Get all entities that have all the specified component types."""
        if not component_types:
            return set()
            
        result = set()
        for entity_id, components in self._entity_components.items():
            if all(comp_type in components for comp_type in component_types):
                result.add(entity_id)
        return result
