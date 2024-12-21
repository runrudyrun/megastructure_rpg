from typing import Dict, Any
import attrs

@attrs.define
class Component:
    """Base class for all components in the ECS system."""
    entity_id: int = attrs.field(default=None)
    
    def serialize(self) -> Dict[str, Any]:
        """Convert component data to a dictionary for storage."""
        return attrs.asdict(self)
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Component':
        """Create a component instance from stored data."""
        return cls(**data)

@attrs.define
class Position(Component):
    """Component for entities that exist in the world space."""
    x: float = attrs.field(default=0.0)
    y: float = attrs.field(default=0.0)
    z: float = attrs.field(default=0.0)
    level_id: str = attrs.field(default="")

@attrs.define
class Physical(Component):
    """Component for entities with physical properties."""
    size: float = attrs.field(default=1.0)
    solid: bool = attrs.field(default=True)
    blocking: bool = attrs.field(default=True)

@attrs.define
class Health(Component):
    """Component for entities that can take damage and die."""
    current: float = attrs.field(default=100.0)
    maximum: float = attrs.field(default=100.0)
    regeneration: float = attrs.field(default=0.0)

@attrs.define
class AI(Component):
    """Component for entities with artificial intelligence."""
    behavior_type: str = attrs.field(default="idle")
    state: Dict[str, Any] = attrs.field(factory=dict)
    goals: Dict[str, float] = attrs.field(factory=dict)  # goal_name: priority

@attrs.define
class Inventory(Component):
    """Component for entities that can carry items."""
    items: Dict[int, int] = attrs.field(factory=dict)  # item_id: quantity
    capacity: float = attrs.field(default=100.0)
    current_weight: float = attrs.field(default=0.0)
