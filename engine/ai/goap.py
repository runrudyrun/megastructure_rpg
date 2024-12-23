"""Goal-Oriented Action Planning (GOAP) system for advanced AI decision making."""
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import heapq
from ..ecs.entity import Entity

WorldState = Dict[str, bool]

@dataclass
class Action:
    """Represents an action that can be performed by an AI agent."""
    name: str
    cost: float
    preconditions: WorldState
    effects: WorldState
    
    def __init__(self, name: str, cost: float = 1.0):
        self.name = name
        self.cost = cost
        self.preconditions = {}
        self.effects = {}
        
    def check_preconditions(self, world_state: WorldState) -> bool:
        """Check if preconditions are met in the current world state."""
        return all(world_state.get(key) == value 
                  for key, value in self.preconditions.items())
                  
    def apply_effects(self, world_state: WorldState) -> WorldState:
        """Apply action effects to create new world state."""
        new_state = world_state.copy()
        new_state.update(self.effects)
        return new_state

@dataclass(order=True)
class PlanNode:
    """Node in the planning graph."""
    f_score: float
    g_score: float = field(compare=False)
    world_state: WorldState = field(compare=False)
    action: Optional[Action] = field(compare=False, default=None)
    parent: Optional['PlanNode'] = field(compare=False, default=None)

class GOAP:
    """Goal-Oriented Action Planning system."""
    
    def __init__(self):
        self.actions: List[Action] = []
        
    def add_action(self, action: Action) -> None:
        """Add an action to the planner."""
        self.actions.append(action)
        
    def _heuristic(self, state: WorldState, goal: WorldState) -> float:
        """Estimate cost to reach goal from current state."""
        differences = sum(1 for key, value in goal.items()
                         if state.get(key) != value)
        return differences
        
    def _reconstruct_plan(self, node: PlanNode) -> List[Action]:
        """Reconstruct plan from goal node."""
        plan = []
        current = node
        
        while current.action is not None:
            plan.append(current.action)
            current = current.parent
            
        return list(reversed(plan))
        
    def plan(self, initial_state: WorldState, goal_state: WorldState,
             max_iterations: int = 1000) -> Optional[List[Action]]:
        """Find sequence of actions to reach goal state."""
        start_node = PlanNode(
            f_score=self._heuristic(initial_state, goal_state),
            g_score=0.0,
            world_state=initial_state
        )
        
        open_set: List[PlanNode] = [start_node]
        closed_set: Set[str] = set()
        
        iterations = 0
        
        while open_set and iterations < max_iterations:
            current = heapq.heappop(open_set)
            
            # Check if goal reached
            if all(current.world_state.get(key) == value 
                  for key, value in goal_state.items()):
                return self._reconstruct_plan(current)
                
            # Add current state to closed set
            state_hash = str(sorted(current.world_state.items()))
            if state_hash in closed_set:
                continue
            closed_set.add(state_hash)
            
            # Try each action
            for action in self.actions:
                if not action.check_preconditions(current.world_state):
                    continue
                    
                new_state = action.apply_effects(current.world_state)
                new_g_score = current.g_score + action.cost
                new_f_score = new_g_score + self._heuristic(new_state, goal_state)
                
                new_node = PlanNode(
                    f_score=new_f_score,
                    g_score=new_g_score,
                    world_state=new_state,
                    action=action,
                    parent=current
                )
                
                heapq.heappush(open_set, new_node)
                
            iterations += 1
            
        return None  # No plan found

def create_combat_actions() -> List[Action]:
    """Create common combat-related actions."""
    actions = []
    
    # Attack action
    attack = Action("Attack", cost=1.0)
    attack.preconditions = {
        "has_weapon": True,
        "in_range": True,
        "target_visible": True
    }
    attack.effects = {
        "target_damaged": True
    }
    actions.append(attack)
    
    # Move to range action
    move_to_range = Action("MoveToRange", cost=2.0)
    move_to_range.preconditions = {
        "target_visible": True,
        "path_exists": True
    }
    move_to_range.effects = {
        "in_range": True
    }
    actions.append(move_to_range)
    
    # Take cover action
    take_cover = Action("TakeCover", cost=3.0)
    take_cover.preconditions = {
        "cover_available": True,
        "not_in_cover": True
    }
    take_cover.effects = {
        "in_cover": True,
        "protected": True
    }
    actions.append(take_cover)
    
    # Reload action
    reload = Action("Reload", cost=2.0)
    reload.preconditions = {
        "has_ammo": True,
        "needs_reload": True
    }
    reload.effects = {
        "weapon_loaded": True,
        "needs_reload": False
    }
    actions.append(reload)
    
    # Search for target action
    search = Action("Search", cost=4.0)
    search.preconditions = {
        "target_lost": True
    }
    search.effects = {
        "target_visible": True,
        "target_lost": False
    }
    actions.append(search)
    
    return actions

def create_exploration_actions() -> List[Action]:
    """Create common exploration-related actions."""
    actions = []
    
    # Explore room action
    explore_room = Action("ExploreRoom", cost=3.0)
    explore_room.preconditions = {
        "room_visible": True,
        "room_unexplored": True
    }
    explore_room.effects = {
        "room_explored": True,
        "room_unexplored": False
    }
    actions.append(explore_room)
    
    # Find door action
    find_door = Action("FindDoor", cost=2.0)
    find_door.preconditions = {
        "room_explored": True,
        "door_unknown": True
    }
    find_door.effects = {
        "door_found": True,
        "door_unknown": False
    }
    actions.append(find_door)
    
    # Open door action
    open_door = Action("OpenDoor", cost=1.0)
    open_door.preconditions = {
        "door_found": True,
        "door_closed": True
    }
    open_door.effects = {
        "door_open": True,
        "door_closed": False,
        "new_room_visible": True
    }
    actions.append(open_door)
    
    # Mark waypoint action
    mark_waypoint = Action("MarkWaypoint", cost=1.0)
    mark_waypoint.preconditions = {
        "location_interesting": True,
        "not_marked": True
    }
    mark_waypoint.effects = {
        "waypoint_marked": True,
        "not_marked": False
    }
    actions.append(mark_waypoint)
    
    return actions

class AIPlanner:
    """High-level AI planning system combining GOAP with other AI systems."""
    
    def __init__(self, entity: Entity):
        self.entity = entity
        self.goap = GOAP()
        self.current_plan: Optional[List[Action]] = None
        self.current_action_index: int = 0
        
        # Add default actions
        for action in create_combat_actions():
            self.goap.add_action(action)
        for action in create_exploration_actions():
            self.goap.add_action(action)
            
    def update_world_state(self) -> WorldState:
        """Get current world state for the entity."""
        # This should be implemented based on your game's specific needs
        return {}
        
    def get_current_goals(self) -> WorldState:
        """Determine current goals based on entity state and context."""
        # This should be implemented based on your game's specific needs
        return {}
        
    def update(self) -> Optional[Action]:
        """Update AI planning and get next action."""
        # Check if we need a new plan
        if self.current_plan is None or self.current_action_index >= len(self.current_plan):
            world_state = self.update_world_state()
            goals = self.get_current_goals()
            
            self.current_plan = self.goap.plan(world_state, goals)
            self.current_action_index = 0
            
            if self.current_plan is None:
                return None
                
        # Get current action
        if self.current_plan and self.current_action_index < len(self.current_plan):
            action = self.current_plan[self.current_action_index]
            self.current_action_index += 1
            return action
            
        return None
