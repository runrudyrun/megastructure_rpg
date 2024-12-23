"""Behavior Tree implementation for advanced AI decision making."""
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import logging
from dataclasses import dataclass, field
from ..ecs.entity import Entity
from ..ecs.component import AI, Position

logger = logging.getLogger(__name__)

class NodeStatus(Enum):
    """Status of a behavior tree node execution."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RUNNING = "RUNNING"

@dataclass
class BlackboardData:
    """Shared data storage for behavior tree nodes."""
    entity: Entity
    world: Any
    memory: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from memory."""
        return self.memory.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Store a value in memory."""
        self.memory[key] = value
        
    def clear(self) -> None:
        """Clear all stored memory."""
        self.memory.clear()

class BehaviorNode:
    """Base class for behavior tree nodes."""
    
    def __init__(self, name: str):
        self.name = name
        self.blackboard: Optional[BlackboardData] = None
        
    def initialize(self, blackboard: BlackboardData) -> None:
        """Initialize the node with blackboard data."""
        self.blackboard = blackboard
        
    def tick(self) -> NodeStatus:
        """Execute the node's behavior."""
        raise NotImplementedError

class Composite(BehaviorNode):
    """Base class for nodes that can have children."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.children: List[BehaviorNode] = []
        
    def add_child(self, child: BehaviorNode) -> 'Composite':
        """Add a child node."""
        self.children.append(child)
        return self
        
    def initialize(self, blackboard: BlackboardData) -> None:
        """Initialize this node and all children."""
        super().initialize(blackboard)
        for child in self.children:
            child.initialize(blackboard)

class Sequence(Composite):
    """Executes children in sequence until one fails."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._current_child = 0
        
    def tick(self) -> NodeStatus:
        while self._current_child < len(self.children):
            status = self.children[self._current_child].tick()
            
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            
            if status == NodeStatus.FAILURE:
                self._current_child = 0
                return NodeStatus.FAILURE
                
            self._current_child += 1
            
        self._current_child = 0
        return NodeStatus.SUCCESS

class Selector(Composite):
    """Executes children in sequence until one succeeds."""
    
    def __init__(self, name: str):
        super().__init__(name)
        self._current_child = 0
        
    def tick(self) -> NodeStatus:
        while self._current_child < len(self.children):
            status = self.children[self._current_child].tick()
            
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            
            if status == NodeStatus.SUCCESS:
                self._current_child = 0
                return NodeStatus.SUCCESS
                
            self._current_child += 1
            
        self._current_child = 0
        return NodeStatus.FAILURE

class Decorator(BehaviorNode):
    """Base class for nodes that modify the behavior of a single child."""
    
    def __init__(self, name: str, child: BehaviorNode):
        super().__init__(name)
        self.child = child
        
    def initialize(self, blackboard: BlackboardData) -> None:
        super().initialize(blackboard)
        self.child.initialize(blackboard)

class Inverter(Decorator):
    """Inverts the result of its child."""
    
    def tick(self) -> NodeStatus:
        status = self.child.tick()
        
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        elif status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
            
        return NodeStatus.RUNNING

class RepeatUntilSuccess(Decorator):
    """Repeats the child until it succeeds."""
    
    def __init__(self, name: str, child: BehaviorNode, max_attempts: int = -1):
        super().__init__(name, child)
        self.max_attempts = max_attempts
        self._attempts = 0
        
    def tick(self) -> NodeStatus:
        if self.max_attempts >= 0 and self._attempts >= self.max_attempts:
            self._attempts = 0
            return NodeStatus.FAILURE
            
        status = self.child.tick()
        
        if status == NodeStatus.SUCCESS:
            self._attempts = 0
            return NodeStatus.SUCCESS
            
        if status == NodeStatus.FAILURE:
            self._attempts += 1
            
        return NodeStatus.RUNNING

class Condition(BehaviorNode):
    """Leaf node that checks a condition."""
    
    def __init__(self, name: str, condition: Callable[[BlackboardData], bool]):
        super().__init__(name)
        self._condition = condition
        
    def tick(self) -> NodeStatus:
        return NodeStatus.SUCCESS if self._condition(self.blackboard) else NodeStatus.FAILURE

class Action(BehaviorNode):
    """Leaf node that performs an action."""
    
    def __init__(self, name: str, action: Callable[[BlackboardData], NodeStatus]):
        super().__init__(name)
        self._action = action
        
    def tick(self) -> NodeStatus:
        return self._action(self.blackboard)

class ParallelSequence(Composite):
    """Executes all children simultaneously, succeeds when all succeed."""
    
    def tick(self) -> NodeStatus:
        success_count = 0
        any_running = False
        
        for child in self.children:
            status = child.tick()
            
            if status == NodeStatus.FAILURE:
                return NodeStatus.FAILURE
                
            if status == NodeStatus.RUNNING:
                any_running = True
            else:  # SUCCESS
                success_count += 1
                
        if success_count == len(self.children):
            return NodeStatus.SUCCESS
            
        return NodeStatus.RUNNING if any_running else NodeStatus.FAILURE

class ParallelSelector(Composite):
    """Executes all children simultaneously, succeeds when one succeeds."""
    
    def tick(self) -> NodeStatus:
        any_running = False
        
        for child in self.children:
            status = child.tick()
            
            if status == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
                
            if status == NodeStatus.RUNNING:
                any_running = True
                
        return NodeStatus.RUNNING if any_running else NodeStatus.FAILURE

def create_patrol_behavior(patrol_points: List[tuple]) -> BehaviorNode:
    """Create a behavior tree for patrolling between points."""
    root = Sequence("Patrol")
    
    def get_next_patrol_point(bb: BlackboardData) -> NodeStatus:
        current_index = bb.get('patrol_index', 0)
        bb.set('target_position', patrol_points[current_index])
        bb.set('patrol_index', (current_index + 1) % len(patrol_points))
        return NodeStatus.SUCCESS
    
    def move_to_target(bb: BlackboardData) -> NodeStatus:
        entity_pos = bb.entity.get_component(Position)
        target_pos = bb.get('target_position')
        
        if not entity_pos or not target_pos:
            return NodeStatus.FAILURE
            
        dx = target_pos[0] - entity_pos.x
        dy = target_pos[1] - entity_pos.y
        
        # Check if we've reached the target
        if abs(dx) < 0.1 and abs(dy) < 0.1:
            return NodeStatus.SUCCESS
            
        # Move towards target
        speed = 0.1
        entity_pos.x += dx * speed
        entity_pos.y += dy * speed
        
        return NodeStatus.RUNNING
    
    root.add_child(Action("GetNextPatrolPoint", get_next_patrol_point))
    root.add_child(Action("MoveToTarget", move_to_target))
    
    return root

def create_guard_behavior(detection_range: float) -> BehaviorNode:
    """Create a behavior tree for guarding an area."""
    root = Selector("Guard")
    
    def detect_threats(bb: BlackboardData) -> bool:
        entity_pos = bb.entity.get_component(Position)
        if not entity_pos:
            return False
            
        # Find nearby entities with different faction
        nearby_entities = bb.world.get_entities_in_range(
            entity_pos.x, entity_pos.y, detection_range)
            
        for other in nearby_entities:
            if bb.world.are_hostile(bb.entity, other):
                bb.set('target_entity', other)
                return True
                
        return False
    
    def attack_target(bb: BlackboardData) -> NodeStatus:
        target = bb.get('target_entity')
        if not target:
            return NodeStatus.FAILURE
            
        # Perform attack
        if bb.world.can_attack(bb.entity, target):
            bb.world.perform_attack(bb.entity, target)
            return NodeStatus.SUCCESS
            
        return NodeStatus.RUNNING
    
    # Create chase sequence
    chase_sequence = Sequence("Chase")
    chase_sequence.add_child(Condition("DetectThreats", detect_threats))
    chase_sequence.add_child(Action("AttackTarget", attack_target))
    
    # Add patrol behavior as fallback
    root.add_child(chase_sequence)
    root.add_child(create_patrol_behavior([(0, 0), (10, 0), (10, 10), (0, 10)]))
    
    return root
