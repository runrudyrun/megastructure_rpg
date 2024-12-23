"""Component pool implementation for efficient memory management."""
from typing import Dict, Type, List, Optional
import attrs
from .component import Component

class ComponentPool:
    """Pool for managing component instances efficiently."""
    
    def __init__(self, component_type: Type[Component]):
        self.component_type = component_type
        self._active_components: Dict[int, Component] = {}  # entity_id -> component
        self._free_components: List[Component] = []
        self._chunk_size = 100  # Number of components to pre-allocate
        
    def acquire(self, entity_id: int, **kwargs) -> Component:
        """Get a component instance, either from pool or create new."""
        if self._free_components:
            component = self._free_components.pop()
            # Reset component state with new parameters
            for key, value in kwargs.items():
                setattr(component, key, value)
            component.entity_id = entity_id
        else:
            component = self.component_type(entity_id=entity_id, **kwargs)
            
        self._active_components[entity_id] = component
        return component
    
    def release(self, entity_id: int) -> None:
        """Return a component to the pool."""
        if entity_id in self._active_components:
            component = self._active_components.pop(entity_id)
            component.entity_id = None
            self._free_components.append(component)
    
    def get(self, entity_id: int) -> Optional[Component]:
        """Get the component for an entity if it exists."""
        return self._active_components.get(entity_id)
    
    def clear(self) -> None:
        """Clear all components from the pool."""
        self._active_components.clear()
        self._free_components.clear()

    def pre_allocate(self, count: int) -> None:
        """Pre-allocate components to reduce runtime allocations."""
        for _ in range(count):
            self._free_components.append(self.component_type())
            
    def _grow_pool(self) -> None:
        """Grow the pool by allocating more components."""
        self.pre_allocate(self._chunk_size)
