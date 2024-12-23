"""Test suite for NPC AI behavior."""
import pytest
import os
import sys
import logging
import math
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.world.tilemap import TileMap, TileType
from engine.world.generator import MegastructureGenerator
from engine.config.config_manager import ConfigManager
from engine.entities.npc import NPC
from engine.ai.pathfinding import PathFinder
from engine.ai.behavior import BehaviorSystem
from engine.ecs.world import World
from engine.ecs.component import Position, AI, Physical, Health, Inventory

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestNPC:
    """Test cases for NPC behavior."""
    
    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        config_manager = ConfigManager(data_dir)
        generator = MegastructureGenerator(config_manager)
        tilemap = generator.generate_sector(30, 30, "industrial")
        pathfinder = PathFinder(tilemap)
        world = World()
        behavior_system = BehaviorSystem(world, config_manager)
        
        return tilemap, pathfinder, world, behavior_system, config_manager
    
    def _find_floor_tile(self, tilemap: TileMap) -> Tuple[int, int]:
        """Find a valid floor tile in the tilemap."""
        for room in tilemap.rooms.values():
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    if tilemap.get_tile(x, y) == TileType.FLOOR:
                        return x, y
        raise ValueError("No floor tile found in tilemap")
    
    def test_pathfinding(self, setup):
        """Test NPC pathfinding capabilities."""
        tilemap, pathfinder, world, behavior_system, config = setup
        
        # Find a valid starting position
        start_x, start_y = self._find_floor_tile(tilemap)
        
        # Create an NPC
        npc = NPC(id=0, x=start_x, y=start_y, behavior_type="guard")
        world.entities[npc.id] = npc
        
        # Add components to world
        for component in npc.components.values():
            world.add_component(npc.id, component)
        
        # Find a valid target position in a different room
        target_pos = None
        npc_room = npc.get_current_room(tilemap)
        for room in tilemap.rooms.values():
            if room == npc_room:
                continue
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    if tilemap.get_tile(x, y) == TileType.FLOOR:
                        target_pos = (x, y)
                        break
                if target_pos:
                    break
            if target_pos:
                break
        
        assert target_pos is not None, "No valid target position found"
        
        # Test pathfinding
        pos = npc.get_component(Position)
        path = pathfinder.find_path((int(pos.x), int(pos.y)), target_pos)
        assert path is not None, "No path found"
        assert len(path) > 0, "Path is empty"
        assert path[-1] == target_pos, "Path does not reach target"
        
        # Test path validity
        for x, y in path:
            tile = tilemap.get_tile(x, y)
            assert tile in [TileType.FLOOR, TileType.DOOR], f"Invalid tile in path: {tile}"
    
    def test_behavior_states(self, setup):
        """Test NPC behavior states."""
        tilemap, _, world, behavior_system, config = setup
        
        # Find valid positions for NPCs that are far apart
        pos1 = self._find_floor_tile(tilemap)
        pos2 = None
        pos3 = None
        
        # Find position for merchant at least 10 tiles away from guard
        for room in tilemap.rooms.values():
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    if tilemap.get_tile(x, y) == TileType.FLOOR:
                        dist = math.sqrt((x - pos1[0])**2 + (y - pos1[1])**2)
                        if dist > 10:
                            pos2 = (x, y)
                            break
                if pos2:
                    break
            if pos2:
                break
                
        # Find position for wanderer at least 10 tiles away from both guard and merchant
        for room in tilemap.rooms.values():
            for x in range(room.x, room.x + room.width):
                for y in range(room.y, room.y + room.height):
                    if tilemap.get_tile(x, y) == TileType.FLOOR:
                        dist1 = math.sqrt((x - pos1[0])**2 + (y - pos1[1])**2)
                        dist2 = math.sqrt((x - pos2[0])**2 + (y - pos2[1])**2)
                        if dist1 > 10 and dist2 > 10:
                            pos3 = (x, y)
                            break
                if pos3:
                    break
            if pos3:
                break
                
        assert pos2 is not None, "Could not find suitable position for merchant"
        assert pos3 is not None, "Could not find suitable position for wanderer"
        
        # Create NPCs with different behavior types
        guard = NPC(id=0, x=pos1[0], y=pos1[1], behavior_type="guard")
        merchant = NPC(id=1, x=pos2[0], y=pos2[1], behavior_type="merchant")
        wanderer = NPC(id=2, x=pos3[0], y=pos3[1], behavior_type="wander")
        
        # Add NPCs to world
        world.entities[guard.id] = guard
        world.entities[merchant.id] = merchant
        world.entities[wanderer.id] = wanderer
        
        # Add components to world
        for npc in [guard, merchant, wanderer]:
            for component in npc.components.values():
                world.add_component(npc.id, component)
        
        # Update behavior system multiple times to ensure state transitions
        dt = 0.016  # Simulate 60 FPS
        for _ in range(10):  # Update for 10 frames
            behavior_system.update(dt)
        
        # Test guard behavior
        guard_state = guard.get_current_task()
        assert guard_state is not None, "Guard has no state"
        assert guard_state in ["idle", "wandering"], f"Guard should be idle or wandering when no targets are nearby: {guard_state}"
        
        # Test merchant behavior
        merchant_state = merchant.get_current_task()
        assert merchant_state is not None, "Merchant has no state"
        assert merchant_state in ["idle", "wandering"], f"Invalid merchant state: {merchant_state}"
        
        # Test wanderer behavior
        wanderer_state = wanderer.get_current_task()
        assert wanderer_state is not None, "Wanderer has no state"
        assert wanderer_state in ["idle", "wandering"], f"Invalid wanderer state: {wanderer_state}"
        
        # Test state transitions
        # Move wanderer next to guard
        logger.debug("Moving wanderer next to guard")
        guard_pos = guard.get_component(Position)
        wanderer_pos = wanderer.get_component(Position)
        wanderer_pos.x = guard_pos.x + 1  # Move wanderer next to guard
        wanderer_pos.y = guard_pos.y
        
        # Update multiple times to ensure state transition
        for _ in range(5):  # Update for 5 frames
            behavior_system.update(dt)
            
            # Log current state
            guard_ai = guard.get_component(AI)
            logger.debug(f"Guard state: {guard_ai.state}")
            
            # Break early if we've reached pursuing state
            guard_state = guard.get_current_task()
            if guard_state == "pursuing":
                break
        
        # Verify guard is pursuing
        guard_state = guard.get_current_task()
        assert guard_state == "pursuing", "Guard did not transition to pursuing state"
        
        # Move wanderer away from guard
        logger.debug("Moving wanderer away from guard")
        wanderer_pos.x = guard_pos.x + 10  # Move wanderer far from guard
        wanderer_pos.y = guard_pos.y + 10
        
        # Update to reset guard state
        for _ in range(5):  # Update for 5 frames
            behavior_system.update(dt)
            
            # Log current state
            guard_ai = guard.get_component(AI)
            logger.debug(f"Guard state: {guard_ai.state}")
            
            # Break early if we've reached idle state
            guard_state = guard.get_current_task()
            if guard_state in ["idle", "wandering"]:
                break
        
        # Verify guard is not pursuing or attacking
        guard_state = guard.get_current_task()
        assert guard_state in ["idle", "wandering"], f"Guard should not be pursuing distant target: {guard_state}"
    
    def test_environment_interaction(self, setup):
        """Test NPC interaction with environment."""
        tilemap, _, world, behavior_system, config = setup
        
        # Find a door
        door_pos = None
        for x in range(tilemap.width):
            for y in range(tilemap.height):
                if tilemap.get_tile(x, y) == TileType.DOOR:
                    door_pos = (x, y)
                    break
            if door_pos:
                break
        
        assert door_pos is not None, "No door found in tilemap"
        
        # Create an NPC next to the door
        npc = NPC(id=0, x=door_pos[0], y=door_pos[1] + 1, behavior_type="guard")
        world.entities[npc.id] = npc
        
        # Add components to world
        for component in npc.components.values():
            world.add_component(npc.id, component)
        
        # Test if NPC can interact with door
        can_interact = npc.can_interact_with(tilemap, door_pos[0], door_pos[1])
        assert can_interact, "NPC cannot interact with door"
        
        # Test room awareness
        room = None
        pos = npc.get_component(Position)
        for r in tilemap.rooms.values():
            if (r.x <= pos.x < r.x + r.width and 
                r.y <= pos.y < r.y + r.height):
                room = r
                break
        
        current_room = npc.get_current_room(tilemap)
        assert current_room == room, "NPC room awareness incorrect"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
