"""Entity class for the ECS system."""
from typing import Dict, Type, Optional
import attrs

@attrs.define
class Entity:
    """Base class for all entities in the game."""
    id: int = attrs.field()
    
    def __hash__(self) -> int:
        return self.id
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id
