from typing import List, Type
from .world import World
from .component import Component

class System:
    """
    Base class for all systems in the game.
    Systems operate on entities with specific component combinations.
    """
    
    def __init__(self, world: World):
        self.world = world
        self.required_components: List[Type[Component]] = []
        
    def update(self, dt: float) -> None:
        """
        Update this system. Override this method in derived classes.
        
        Args:
            dt: Time elapsed since last update in seconds
        """
        pass
    
    def get_relevant_entities(self) -> List:
        """Get all entities that this system should process."""
        return self.world.get_entities_with_components(*self.required_components)

class MovementSystem(System):
    """System for handling entity movement."""
    
    def __init__(self, world: World):
        super().__init__(world)
        from .component import Position, Physical
        self.required_components = [Position, Physical]
    
    def update(self, dt: float) -> None:
        """Update positions of all entities with Position and Physical components."""
        entities = self.get_relevant_entities()
        # Movement logic will be implemented here
        pass

class AISystem(System):
    """System for processing AI behavior."""
    
    def __init__(self, world: World):
        super().__init__(world)
        from .component import AI, Position
        self.required_components = [AI, Position]
    
    def update(self, dt: float) -> None:
        """Update AI behavior for all entities with AI and Position components."""
        entities = self.get_relevant_entities()
        # AI processing logic will be implemented here
        pass

class HealthSystem(System):
    """System for processing health-related effects."""
    
    def __init__(self, world: World):
        super().__init__(world)
        from .component import Health
        self.required_components = [Health]
    
    def update(self, dt: float) -> None:
        """Update health status for all entities with Health component."""
        entities = self.get_relevant_entities()
        for entity in entities:
            health = entity.get_component(self.required_components[0])
            if health.regeneration > 0:
                health.current = min(health.current + health.regeneration * dt,
                                  health.maximum)
