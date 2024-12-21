from typing import Dict, Type, Optional
from .component import Component
import uuid

class Entity:
    """
    Base class for all entities in the game world.
    An entity is essentially just an ID that components can attach to.
    """
    
    def __init__(self, entity_id: Optional[int] = None):
        self.id = entity_id if entity_id is not None else uuid.uuid4().int
        self.components: Dict[Type[Component], Component] = {}
        
    def add_component(self, component: Component) -> None:
        """Add a component to this entity."""
        component.entity_id = self.id
        self.components[type(component)] = component
        
    def remove_component(self, component_type: Type[Component]) -> None:
        """Remove a component from this entity."""
        if component_type in self.components:
            del self.components[component_type]
            
    def get_component(self, component_type: Type[Component]) -> Optional[Component]:
        """Get a component of the specified type if it exists."""
        return self.components.get(component_type)
    
    def has_component(self, component_type: Type[Component]) -> bool:
        """Check if the entity has a component of the specified type."""
        return component_type in self.components
    
    def serialize(self) -> Dict:
        """Convert entity data to a dictionary for storage."""
        return {
            'id': self.id,
            'components': {
                component.__class__.__name__: component.serialize()
                for component in self.components.values()
            }
        }
