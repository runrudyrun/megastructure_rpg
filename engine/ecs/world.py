from typing import Dict, List, Type, Set, Optional
from .entity import Entity
from .component import Component

class World:
    """
    The World class manages all entities and provides efficient access to entities
    with specific component combinations.
    """
    
    def __init__(self):
        self.entities: Dict[int, Entity] = {}
        self.component_to_entities: Dict[Type[Component], Set[int]] = {}
        
    def create_entity(self) -> Entity:
        """Create a new entity and add it to the world."""
        entity = Entity()
        self.entities[entity.id] = entity
        return entity
    
    def remove_entity(self, entity_id: int) -> None:
        """Remove an entity and all its components from the world."""
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            # Remove entity from component mappings
            for component_type in entity.components:
                if component_type in self.component_to_entities:
                    self.component_to_entities[component_type].discard(entity_id)
            # Remove the entity itself
            del self.entities[entity_id]
    
    def add_component(self, entity_id: int, component: Component) -> None:
        """Add a component to an entity."""
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            component_type = type(component)
            
            # Add component to entity
            entity.add_component(component)
            
            # Update component mapping
            if component_type not in self.component_to_entities:
                self.component_to_entities[component_type] = set()
            self.component_to_entities[component_type].add(entity_id)
    
    def remove_component(self, entity_id: int, component_type: Type[Component]) -> None:
        """Remove a component from an entity."""
        if entity_id in self.entities:
            entity = self.entities[entity_id]
            entity.remove_component(component_type)
            
            if component_type in self.component_to_entities:
                self.component_to_entities[component_type].discard(entity_id)
    
    def get_entities_with_components(self, *component_types: Type[Component]) -> List[Entity]:
        """Get all entities that have all of the specified component types."""
        if not component_types:
            return list(self.entities.values())
        
        # Start with entities that have the first component type
        if component_types[0] not in self.component_to_entities:
            return []
        
        entity_ids = self.component_to_entities[component_types[0]].copy()
        
        # Intersect with entities that have each additional component type
        for component_type in component_types[1:]:
            if component_type not in self.component_to_entities:
                return []
            entity_ids &= self.component_to_entities[component_type]
            
        return [self.entities[entity_id] for entity_id in entity_ids]
    
    def get_entity(self, entity_id: int) -> Optional[Entity]:
        """Get an entity by its ID."""
        return self.entities.get(entity_id)
