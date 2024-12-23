"""NPC behavior system implementation."""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import math
import logging
from ..ecs.entity import Entity
from ..ecs.component import AI, Position, Physical
from ..config.config_manager import ConfigManager
import random
from typing import Tuple

# Set up logging with more verbose output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class BehaviorContext:
    """Context data for behavior execution."""
    entity: Entity
    world: Any
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
        ai.state['current_state'] = 'idle'
        
        # Clear target state
        ai.state['target_id'] = None
        ai.state['target_distance'] = float('inf')
        ai.state['target_detected'] = False
        
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) entering idle state")
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        ai.state['idle_time'] += self.context.dt
        
        # Check transitions based on behavior type
        if ai.behavior_type in ['hunt', 'guard']:
            # Check for nearby targets
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) checking for targets")
            if self._detect_targets():
                logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) detected target")
                return 'pursuing'
        
        # Check for wandering transition
        if ai.state['idle_time'] > self.context.config['parameters']['max_idle_time']:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) idle time exceeded")
            return 'wandering'
                
        return None
        
    def _detect_targets(self) -> bool:
        ai = self.context.entity.get_component(AI)
        pos = self.context.entity.get_component(Position)
        detection_range = self.context.config['parameters']['detection_range']
        
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) checking for targets. Range: {detection_range}")
        
        # Simple target detection logic - can be expanded
        for target in self.context.world.get_entities_with_components(Position, Physical):
            if target.id == self.context.entity.id:
                continue
                
            target_pos = target.get_component(Position)
            dist = math.sqrt((target_pos.x - pos.x)**2 + (target_pos.y - pos.y)**2)
            
            logger.debug(f"  - Checking target {target.id} at distance {dist}")
            
            if dist <= detection_range:
                logger.debug(f"  - Target {target.id} in range!")
                ai.state['target_id'] = target.id
                ai.state['target_distance'] = dist
                ai.state['target_detected'] = True
                return True
                
        logger.debug(f"  - No targets found in range")
        ai.state['target_id'] = None
        ai.state['target_distance'] = float('inf')
        ai.state['target_detected'] = False
        return False

class WanderingState(BehaviorState):
    """State where entity moves randomly within an area."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['wander_time'] = 0.0
        ai.state['wander_direction'] = self._get_random_direction()
        ai.state['current_state'] = 'wandering'
        
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
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) wander time exceeded")
            return 'idle'
            
        return None
        
    def _get_random_direction(self) -> Tuple[float, float]:
        angle = random.random() * 2 * math.pi
        return (math.cos(angle), math.sin(angle))

class PursuingState(BehaviorState):
    """State where entity pursues a target."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['current_state'] = 'pursuing'
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) entering pursuing state")
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        pos = self.context.entity.get_component(Position)
        
        # Get target
        target_id = ai.state.get('target_id')
        if target_id is None:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) has no target")
            return 'idle'
            
        target = self.context.world.get_entity(target_id)
        if not target:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target {target_id} not found")
            return 'idle'
            
        target_pos = target.get_component(Position)
        if not target_pos:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target {target_id} has no position")
            return 'idle'
            
        # Calculate distance to target
        dist = math.sqrt((target_pos.x - pos.x)**2 + (target_pos.y - pos.y)**2)
        ai.state['target_distance'] = dist
        
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) distance to target: {dist}")
        
        # Check for state transitions
        detection_range = self.context.config['parameters']['detection_range']
        attack_range = self.context.config['parameters'].get('attack_range', 1.5)
        
        # If target is too far away, go back to idle
        if dist > detection_range * 1.5:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target out of range")
            # Clear target state
            ai.state['target_id'] = None
            ai.state['target_distance'] = float('inf')
            ai.state['target_detected'] = False
            return 'idle'
            
        # If target is in attack range, switch to attacking
        if dist <= attack_range:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target in attack range")
            return 'attacking'
            
        # Move towards target
        speed = self.context.config['parameters']['speed']
        dx = (target_pos.x - pos.x) / dist
        dy = (target_pos.y - pos.y) / dist
        pos.x += dx * speed * self.context.dt
        pos.y += dy * speed * self.context.dt
        
        return None

class AttackingState(BehaviorState):
    """State where entity attacks a target."""
    
    def enter(self) -> None:
        ai = self.context.entity.get_component(AI)
        ai.state['attack_cooldown'] = 0.0
        ai.state['current_state'] = 'attacking'
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) entering attacking state")
        
    def update(self) -> Optional[str]:
        ai = self.context.entity.get_component(AI)
        
        # Get target
        target_id = ai.state.get('target_id')
        if target_id is None:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) has no target")
            return 'idle'
            
        target = self.context.world.get_entity(target_id)
        if not target:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target {target_id} not found")
            return 'idle'
            
        target_pos = target.get_component(Position)
        if not target_pos:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target {target_id} has no position")
            return 'idle'
            
        # Calculate distance to target
        pos = self.context.entity.get_component(Position)
        dist = math.sqrt((target_pos.x - pos.x)**2 + (target_pos.y - pos.y)**2)
        ai.state['target_distance'] = dist
        
        logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) distance to target: {dist}")
        
        # Check if target is still in range
        attack_range = self.context.config['parameters'].get('attack_range', 1.5)
        if dist > attack_range:
            logger.debug(f"Entity {self.context.entity.id} ({ai.behavior_type}) target out of attack range")
            return 'pursuing'
            
        # Update attack cooldown
        ai.state['attack_cooldown'] -= self.context.dt
        
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
                logger.warning(f"No behavior config found for type: {ai.behavior_type}")
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
                logger.debug(f"Creating initial state for entity {entity.id} ({ai.behavior_type})")
                current_state = IdleState(context)
                current_state.enter()
                self.entity_states[entity.id] = current_state
                
            # Update state
            next_state = current_state.update()
            if next_state:
                logger.debug(f"Entity {entity.id} ({ai.behavior_type}) transitioning from {current_state.__class__.__name__} to {next_state}")
                
                # First exit current state
                current_state.exit()
                
                # Create and enter new state
                new_state = self._create_state(next_state, context)
                new_state.enter()
                
                # Update entity state
                ai.state['current_state'] = next_state
                
                # Store new state
                self.entity_states[entity.id] = new_state
                
                # Log state change
                logger.debug(f"Entity {entity.id} ({ai.behavior_type}) state updated to {next_state}")
                
    def _create_state(self, state_name: str, context: BehaviorContext) -> BehaviorState:
        """Create a new behavior state instance."""
        states = {
            'idle': IdleState,
            'wandering': WanderingState,
            'pursuing': PursuingState,
            'attacking': AttackingState
        }
        return states[state_name](context)
