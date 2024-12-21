from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import math
from ..ecs.entity import Entity
from ..ecs.component import AI, Position, Physical
from ..config.config_manager import ConfigManager

@dataclass
class BehaviorContext:
    """Context data for behavior execution."""
    entity: Entity
    world: Any  # World instance
    dt: float
    config: Dict[str, Any]
    
class BehaviorState:
    """Base class for behavior states."""
    def __init__(self, context: BehaviorContext):
        self.context = context
        
    def enter(self) -> None:
        """Called when entering this state."""
        pass
        
    def exit(self) -> None:
        """Called when exiting this state."""
        pass
        
    def update(self) -> Optional[str]:
        """
        Update this state.
        Returns: Name of next state if transition should occur, None otherwise.
        """
        return None

class IdleState(BehaviorState):
    """State where entity is idle and periodically checks for new actions."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['idle_time'] = 0.0
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        ai.state['idle_time'] += self.context.dt
        
        # Check transitions based on behavior type
        if ai.behavior_type == 'wander':
            if ai.state['idle_time'] > self.context.config['parameters']['max_idle_time']:
                return 'wandering'
        elif ai.behavior_type == 'hunt':
            # Check for nearby targets
            if self._detect_targets():
                return 'pursuing'
                
        return None
        
    def _detect_targets(self) -> bool:
        ai = self.context.entity.get_component(AI)
        pos = self.context.entity.get_component(Position)
        detection_range = self.context.config['parameters']['detection_range']
        
        # Simple target detection logic - can be expanded
        for target in self.context.world.get_entities_with_components(Position, Physical):
            if target.id == self.context.entity.id:
                continue
                
            target_pos = target.get_component(Position)
            dist = math.sqrt((target_pos.x - pos.x)**2 + (target_pos.y - pos.y)**2)
            
            if dist <= detection_range:
                ai.state['target_id'] = target.id
                ai.state['target_distance'] = dist
                return True
                
        return False

class WanderingState(BehaviorState):
    """State where entity moves randomly within an area."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['wander_time'] = 0.0
        ai.state['wander_direction'] = self._get_random_direction()
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        pos = self.context.entity.get_component(Position)
        
        # Update position based on wander direction
        speed = self.context.config['parameters']['speed']
        dx, dy = ai.state['wander_direction']
        pos.x += dx * speed * self.context.dt
        pos.y += dy * speed * self.context.dt
        
        # Update wander time
        ai.state['wander_time'] += self.context.dt
        
        # Check for state transition
        if ai.state['wander_time'] > self.context.config['parameters']['max_wander_time']:
            return 'idle'
            
        return None
        
    def _get_random_direction(self) -> tuple[float, float]:
        import random
        angle = random.uniform(0, 2 * math.pi)
        return math.cos(angle), math.sin(angle)

class PursuingState(BehaviorState):
    """State where entity pursues a target."""
    
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        pos = self.context.entity.get_component(Position)
        
        target_id = ai.state.get('target_id')
        if target_id is None:
            return 'idle'
            
        target = self.context.world.get_entity(target_id)
        if target is None:
            return 'idle'
            
        target_pos = target.get_component(Position)
        if target_pos is None:
            return 'idle'
            
        # Calculate distance and direction to target
        dx = target_pos.x - pos.x
        dy = target_pos.y - pos.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Update state
        ai.state['target_distance'] = distance
        
        # Check transitions
        if distance > self.context.config['parameters']['detection_range'] * 1.5:
            return 'idle'
        elif distance < self.context.config['parameters']['attack_range']:
            return 'attacking'
            
        # Move toward target
        speed = self.context.config['parameters']['pursuit_speed']
        if distance > 0:
            pos.x += (dx/distance) * speed * self.context.dt
            pos.y += (dy/distance) * speed * self.context.dt
            
        return None

class AttackingState(BehaviorState):
    """State where entity attacks a target."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['attack_cooldown'] = 0.0
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        
        # Update attack cooldown
        ai.state['attack_cooldown'] -= self.context.dt
        
        # Check if target is still in range
        target_distance = ai.state.get('target_distance', float('inf'))
        if target_distance > self.context.config['parameters']['attack_range']:
            return 'pursuing'
            
        # Perform attack if cooldown is ready
        if ai.state['attack_cooldown'] <= 0:
            self._perform_attack()
            ai.state['attack_cooldown'] = self.context.config['parameters']['attack_cooldown']
            
        return None
        
    def _perform_attack(self) -> None:
        # Attack logic will be implemented later
        pass

class BehaviorSystem:
    """System for managing entity behaviors."""
    
    def __init__(self, world: Any, config_manager: ConfigManager):
        self.world = world
        self.config_manager = config_manager
        self.entity_states: Dict[int, BehaviorState] = {}
        
    def update(self, dt: float) -> None:
        """Update all entity behaviors."""
        entities = self.world.get_entities_with_components(AI, Position)
        
        for entity in entities:
            ai = entity.get_component(AI)
            
            # Get behavior configuration
            config = self.config_manager.get_behavior_config(ai.behavior_type)
            if not config:
                continue
                
            # Create context
            context = BehaviorContext(
                entity=entity,
                world=self.world,
                dt=dt,
                config=config
            )
            
            # Get or create state
            current_state = self.entity_states.get(entity.id)
            if current_state is None:
                current_state = IdleState(context)
                current_state.enter()
                self.entity_states[entity.id] = current_state
                
            # Update state
            next_state = current_state.update()
            if next_state:
                current_state.exit()
                new_state = self._create_state(next_state, context)
                new_state.enter()
                self.entity_states[entity.id] = new_state
                
    def _create_state(self, state_name: str, context: BehaviorContext) -> BehaviorState:
        """Create a new behavior state instance."""
        states = {
            'idle': IdleState,
            'wandering': WanderingState,
            'pursuing': PursuingState,
            'attacking': AttackingState
        }
        return states[state_name](context)
