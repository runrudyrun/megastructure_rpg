"""Test suite for procedural generation systems."""
import pytest
import os
import sys
import logging
from typing import List, Dict, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.world.generator import MegastructureGenerator
from engine.world.tilemap import TileMap, TileType, Room
from engine.config.config_manager import ConfigManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestGeneration:
    """Test cases for procedural generation."""
    
    @pytest.fixture
    def setup(self):
        """Set up test environment."""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        config_manager = ConfigManager(data_dir)
        generator = MegastructureGenerator(config_manager)
        return generator
    
    def test_room_placement(self, setup):
        """Test that rooms are placed without overlapping."""
        generator = setup
        
        # Generate a test sector
        width, height = 50, 50
        tilemap = generator.generate_sector(width, height, "industrial")
        
        # Check that rooms exist
        assert len(tilemap.rooms) > 0, "No rooms were generated"
        
        # Check for room overlaps
        for room1_id, room1 in tilemap.rooms.items():
            for room2_id, room2 in tilemap.rooms.items():
                if room1_id != room2_id:
                    assert not room1.overlaps(room2), f"Room {room1_id} overlaps with room {room2_id}"
        
        # Check room boundaries
        for room in tilemap.rooms.values():
            assert room.x >= 0 and room.y >= 0, "Room placed outside map bounds"
            assert room.x + room.width <= width, "Room extends beyond map width"
            assert room.y + room.height <= height, "Room extends beyond map height"
    
    def test_room_connectivity(self, setup):
        """Test that all rooms are connected."""
        generator = setup
        
        # Generate a test sector
        tilemap = generator.generate_sector(50, 50, "industrial")
        
        # Helper function to find all connected rooms
        def find_connected_rooms(start_room: Room, visited=None) -> set:
            if visited is None:
                visited = set()
            visited.add(start_room.id)
            
            for connected_id in start_room.connections:
                if connected_id not in visited:
                    connected_room = tilemap.rooms[connected_id]
                    find_connected_rooms(connected_room, visited)
            return visited
        
        # Start from first room and check if all rooms are reachable
        if tilemap.rooms:
            start_room = next(iter(tilemap.rooms.values()))
            connected = find_connected_rooms(start_room)
            assert len(connected) == len(tilemap.rooms), "Not all rooms are connected"
    
    def test_door_placement(self, setup):
        """Test that doors are placed correctly."""
        generator = setup
        
        # Generate a test sector
        tilemap = generator.generate_sector(50, 50, "industrial")
        
        # Check each room has at least one door
        for room in tilemap.rooms.values():
            # Look for doors around room perimeter
            found_door = False
            door_positions = []
            
            # Check horizontal walls
            for x in range(room.x - 1, room.x + room.width + 1):
                if tilemap.get_tile(x, room.y - 1) == TileType.DOOR:
                    found_door = True
                    door_positions.append((x, room.y - 1))
                if tilemap.get_tile(x, room.y + room.height) == TileType.DOOR:
                    found_door = True
                    door_positions.append((x, room.y + room.height))
            
            # Check vertical walls
            for y in range(room.y - 1, room.y + room.height + 1):
                if tilemap.get_tile(room.x - 1, y) == TileType.DOOR:
                    found_door = True
                    door_positions.append((room.x - 1, y))
                if tilemap.get_tile(room.x + room.width, y) == TileType.DOOR:
                    found_door = True
                    door_positions.append((room.x + room.width, y))
            
            # Print room and door information
            if not found_door:
                print(f"\nRoom {room.id} ({room.type}) has no doors:")
                print(f"Position: ({room.x}, {room.y}), Size: {room.width}x{room.height}")
                print("Tiles around room:")
                for y in range(room.y - 1, room.y + room.height + 2):
                    row = ""
                    for x in range(room.x - 1, room.x + room.width + 2):
                        tile = tilemap.get_tile(x, y)
                        if tile == TileType.FLOOR:
                            row += "."
                        elif tile == TileType.WALL:
                            row += "#"
                        elif tile == TileType.DOOR:
                            row += "D"
                        else:
                            row += " "
                    print(row)
            
            assert found_door, f"Room {room.id} has no doors"

    def test_theme_generation(self, setup):
        """Test that different themes produce different results."""
        generator = setup
        
        # Generate sectors with different themes
        industrial = generator.generate_sector(50, 50, "industrial")
        residential = generator.generate_sector(50, 50, "residential")
        
        # Compare room type distributions
        def get_room_type_distribution(tilemap: TileMap) -> Dict[str, int]:
            distribution = {}
            for room in tilemap.rooms.values():
                distribution[room.type] = distribution.get(room.type, 0) + 1
            return distribution
        
        industrial_dist = get_room_type_distribution(industrial)
        residential_dist = get_room_type_distribution(residential)
        
        # Themes should have different room type distributions
        assert industrial_dist != residential_dist, "Different themes produced identical room distributions"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
