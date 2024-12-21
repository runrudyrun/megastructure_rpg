"""Entity management system for the ECS."""
from typing import Dict, Set, Type, List, Optional, TypeVar
from .entity import Entity
from .component import Component

T = TypeVar('T', bound=Component)

class EntityManager:
    """Manages entities and their components."""
    
    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.component_to_entities: Dict[Type[Component], Set[Entity]] = {}
    
    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the manager."""
        self.entities[entity.id] = entity
    
    def remove_entity(self, entity: Entity) -> None:
        """Remove an entity and all its components."""
        if entity.id in self.entities:
            # Remove from component mappings
            for component_type in entity.components:
                if component_type in self.component_to_entities:
                    self.component_to_entities[component_type].discard(entity)
            
            # Remove entity
            del self.entities[entity.id]
    
    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)
    
    def add_component(self, entity: Entity, component: Component) -> None:
        """Add a component to an entity."""
        # Add component to entity
        entity.add_component(component)
        
        # Update component mapping
        component_type = type(component)
        if component_type not in self.component_to_entities:
            self.component_to_entities[component_type] = set()
        self.component_to_entities[component_type].add(entity)
    
    def remove_component(self, entity: Entity, component_type: Type[Component]) -> None:
        """Remove a component from an entity."""
        if entity.has_component(component_type):
            # Remove from entity
            entity.remove_component(component_type)
            
            # Update component mapping
            if component_type in self.component_to_entities:
                self.component_to_entities[component_type].discard(entity)
    
    def get_component(self, entity: Entity, component_type: Type[T]) -> Optional[T]:
        """Get a component of specified type from an entity."""
        return entity.get_component(component_type)
    
    def get_entities_with_component(self, component_type: Type[Component]) -> Set[Entity]:
        """Get all entities that have a specific component type."""
        return self.component_to_entities.get(component_type, set())
    
    def get_entities_with_components(self, *component_types: Type[Component]) -> Set[Entity]:
        """Get all entities that have all the specified component types."""
        if not component_types:
            return set()
        
        # Start with entities having the first component type
        entities = self.get_entities_with_component(component_types[0])
        
        # Filter for entities having all other component types
        for component_type in component_types[1:]:
            entities &= self.get_entities_with_component(component_type)
        
        return entities
    
    def clear(self) -> None:
        """Remove all entities and components."""
        self.entities.clear()
        self.component_to_entities.clear()
