"""Query system for efficient entity and component iteration."""
from typing import Type, Set, Iterator, Tuple, Dict, List
from .component import Component
from .entity_manager import EntityManager

class Query:
    """Query for entities with specific component combinations."""
    
    def __init__(self, entity_manager: EntityManager, *component_types: Type[Component]):
        self.entity_manager = entity_manager
        self.component_types = component_types
        self._cached_entities: Set[int] = set()
        self._is_cache_valid = False
        
    def _update_cache(self) -> None:
        """Update the cached set of matching entities."""
        self._cached_entities = self.entity_manager.get_entities_with_components(*self.component_types)
        self._is_cache_valid = True
        
    def invalidate(self) -> None:
        """Mark the cache as invalid."""
        self._is_cache_valid = False
        
    def iter_entities(self) -> Iterator[int]:
        """Iterate over entity IDs that match the query."""
        if not self._is_cache_valid:
            self._update_cache()
        yield from self._cached_entities
        
    def iter_components(self) -> Iterator[Tuple[int, List[Component]]]:
        """Iterate over matching entities and their requested components."""
        for entity_id in self.iter_entities():
            components = []
            for component_type in self.component_types:
                component = self.entity_manager.get_component(entity_id, component_type)
                if component is None:  # This shouldn't happen if cache is valid
                    continue
                components.append(component)
            yield entity_id, components
            
    def __iter__(self) -> Iterator[Tuple[int, List[Component]]]:
        """Make the query iterable."""
        return self.iter_components()
        
    def __len__(self) -> int:
        """Get the number of matching entities."""
        if not self._is_cache_valid:
            self._update_cache()
        return len(self._cached_entities)
