"""Procedural generator for the megastructure environment."""
from typing import Dict, List, Tuple, Optional, Set
import random
import numpy as np
import logging
from ..config.config_manager import ConfigManager
from .tilemap import TileMap, Room, TileType
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Edge:
    """Edge between two rooms."""
    distance: float
    room1: Room
    room2: Room
    
    def __lt__(self, other):
        return self.distance < other.distance


class MegastructureGenerator:
    """Procedural generator for the megastructure environment."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.rules = config_manager.get_generation_rules()
        logger.debug(f"Loaded generation rules: {self.rules}")
    
    def generate_sector(self, width: int, height: int, theme: str) -> TileMap:
        """Generate a sector of the megastructure with the specified theme."""
        logger.info(f"Generating sector: {width}x{height}, theme: {theme}")
        
        try:
            tilemap = TileMap(width, height)
            theme_config = self.rules.get('themes', {}).get(theme)
            if not theme_config:
                logger.error(f"Theme '{theme}' not found in rules")
                theme_config = {'room_weights': {'corridor': 1.0}}
            
            logger.debug(f"Theme config: {theme_config}")
            
            # Generate rooms based on theme weights
            rooms = self._generate_rooms(tilemap, theme_config.get('room_weights', {}))
            
            # Connect rooms with corridors
            self._connect_rooms(tilemap, rooms)
            
            # Add entrances and exits
            if len(rooms) >= 2:
                self._add_sector_connections(tilemap, rooms)
            
            logger.info(f"Sector generation complete. Generated {len(rooms)} rooms")
            return tilemap
            
        except Exception as e:
            logger.error(f"Error generating sector: {e}")
            # Return an empty tilemap as fallback
            return TileMap(width, height)
    
    def _generate_rooms(self, tilemap: TileMap, room_weights: Dict[str, float]) -> List[Room]:
        """Generate rooms according to weight distribution."""
        logger.info("Generating rooms")
        rooms = []
        attempts = 100  # Limit attempts to prevent infinite loops
        
        try:
            while attempts > 0:
                # Select room type based on weights
                if not room_weights:
                    logger.warning("No room weights defined, using default")
                    room_weights = {'corridor': 1.0}
                
                room_type = random.choices(
                    list(room_weights.keys()),
                    weights=list(room_weights.values())
                )[0]
                
                logger.debug(f"Selected room type: {room_type}")
                
                # Get room size constraints
                size_rules = self.rules.get('room_types', {}).get(room_type, {
                    'min_size': [5, 5],
                    'max_size': [10, 10]
                })
                
                # Adjust size constraints to ensure room fits with walls
                min_width = min(size_rules.get('min_size', [5, 5])[0], tilemap.width - 4)
                min_height = min(size_rules.get('min_size', [5, 5])[1], tilemap.height - 4)
                max_width = min(size_rules.get('max_size', [10, 10])[0], tilemap.width - 4)
                max_height = min(size_rules.get('max_size', [10, 10])[1], tilemap.height - 4)
                
                logger.debug(f"Room size constraints: {min_width}x{min_height} to {max_width}x{max_height}")
                
                # Ensure valid size range
                if min_width > max_width:
                    min_width = max_width
                if min_height > max_height:
                    min_height = max_height
                
                # Generate room size
                width = random.randint(min_width, max_width)
                height = random.randint(min_height, max_height)
                
                # Try to place room with padding for corridors
                x = random.randint(2, tilemap.width - width - 3)
                y = random.randint(2, tilemap.height - height - 3)
                
                logger.debug(f"Attempting to place {room_type} room at ({x}, {y}) with size {width}x{height}")
                
                # Check if space is available including padding
                can_place = True
                for check_y in range(y - 1, y + height + 2):  # Include space for walls
                    for check_x in range(x - 1, x + width + 2):  # Include space for walls
                        if not tilemap.is_valid_position(check_x, check_y):
                            can_place = False
                            break
                        tile = tilemap.get_tile(check_x, check_y)
                        if tile != TileType.EMPTY:
                            can_place = False
                            break
                    if not can_place:
                        break
                
                if can_place:
                    logger.debug(f"Placing {room_type} room at ({x}, {y})")
                    
                    # Create room first
                    room = Room(tilemap.next_room_id, room_type, x, y, width, height)
                    tilemap.next_room_id += 1
                    
                    # Set walls first
                    for wall_y in range(y - 1, y + height + 1):
                        tilemap.set_tile(x - 1, wall_y, TileType.WALL)
                        tilemap.set_tile(x + width, wall_y, TileType.WALL)
                    for wall_x in range(x - 1, x + width + 1):
                        tilemap.set_tile(wall_x, y - 1, TileType.WALL)
                        tilemap.set_tile(wall_x, y + height, TileType.WALL)
                    
                    # Then set floor tiles
                    for floor_y in range(y, y + height):
                        for floor_x in range(x, x + width):
                            tilemap.set_tile(floor_x, floor_y, TileType.FLOOR)
                    
                    # Add room to tilemap
                    tilemap.rooms[room.id] = room
                    rooms.append(room)
                    
                    logger.debug(f"Successfully placed room {room.id}")
                else:
                    logger.debug("Could not place room - space occupied")
                
                attempts -= 1
                if len(rooms) >= 10:  # Limit number of rooms
                    break
            
            logger.info(f"Generated {len(rooms)} rooms after {100 - attempts} attempts")
            return rooms
            
        except Exception as e:
            logger.error(f"Error generating rooms: {e}")
            return rooms
    
    def _is_valid_path(self, tilemap: TileMap, x1: int, y1: int, x2: int, y2: int) -> bool:
        """Check if a path between two points is valid."""
        try:
            # Check horizontal segment
            x = x1
            while x != x2:
                dx = 1 if x2 > x else -1
                if not tilemap.is_valid_position(x, y1):
                    return False
                if tilemap.get_tile(x, y1) not in [TileType.EMPTY, TileType.WALL, TileType.FLOOR]:
                    return False
                x += dx
            
            # Check vertical segment
            y = y1
            while y != y2:
                dy = 1 if y2 > y else -1
                if not tilemap.is_valid_position(x2, y):
                    return False
                if tilemap.get_tile(x2, y) not in [TileType.EMPTY, TileType.WALL, TileType.FLOOR]:
                    return False
                y += dy
            
            return True
        except Exception as e:
            logger.error(f"Error checking path validity: {e}")
            return False
    
    def _connect_rooms(self, tilemap: TileMap, rooms: List[Room]) -> None:
        """Connect rooms with corridors using a minimum spanning tree."""
        if not rooms:
            return
        
        try:
            logger.info("Connecting rooms")
            
            # Calculate distances between all rooms
            edges = []
            for i, room1 in enumerate(rooms):
                for j, room2 in enumerate(rooms[i+1:], i+1):
                    # Calculate center points
                    center1 = (room1.x + room1.width // 2, room1.y + room1.height // 2)
                    center2 = (room2.x + room2.width // 2, room2.y + room2.height // 2)
                    distance = abs(center1[0] - center2[0]) + abs(center1[1] - center2[1])
                    
                    # Only add edge if path is valid
                    if self._is_valid_path(tilemap, center1[0], center1[1], center2[0], center2[1]):
                        edges.append(Edge(distance, room1, room2))
            
            logger.debug(f"Found {len(edges)} valid connections between rooms")
            
            # Sort edges by distance
            edges.sort()
            
            # Create minimum spanning tree
            connected_rooms = {rooms[0]}
            while len(connected_rooms) < len(rooms):
                for edge in edges:
                    if (edge.room1 in connected_rooms) != (edge.room2 in connected_rooms):
                        # Connect these rooms
                        logger.debug(f"Connecting rooms: {edge.room1.id} -> {edge.room2.id}")
                        if self._create_corridor(tilemap, edge.room1, edge.room2):
                            connected_rooms.add(edge.room1)
                            connected_rooms.add(edge.room2)
                            edge.room1.connections.add(edge.room2.id)
                            edge.room2.connections.add(edge.room1.id)
                        break
            
            logger.info(f"Connected {len(connected_rooms)} rooms")
            
        except Exception as e:
            logger.error(f"Error connecting rooms: {e}")
    
    def _place_corridor_tile(self, tilemap: TileMap, x: int, y: int) -> bool:
        """Place a corridor tile and its walls."""
        if not tilemap.is_valid_position(x, y):
            return False
            
        current_tile = tilemap.get_tile(x, y)
        if current_tile == TileType.FLOOR:
            return True
        if current_tile == TileType.WALL:
            # Can convert walls to floor for doorways
            tilemap.set_tile(x, y, TileType.FLOOR)
            return True
            
        # Place floor tile
        tilemap.set_tile(x, y, TileType.FLOOR)
        
        # Add walls around the corridor
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if tilemap.is_valid_position(nx, ny):
                tile = tilemap.get_tile(nx, ny)
                if tile == TileType.EMPTY:
                    tilemap.set_tile(nx, ny, TileType.WALL)
        
        return True

    def _create_corridor(self, tilemap: TileMap, room1: Room, room2: Room) -> bool:
        """Create a corridor between two rooms."""
        # Find door positions
        door1_x, door1_y = self._find_valid_door_position(tilemap, room1)
        door2_x, door2_y = self._find_valid_door_position(tilemap, room2)
        
        if not (door1_x and door1_y and door2_x and door2_y):
            logger.warning(f"Could not find valid door positions for rooms {room1.id} and {room2.id}")
            return False
        
        # Create L-shaped corridor
        success = True
        
        # First segment
        current_x = door1_x
        target_x = door2_x
        
        while current_x != target_x:
            if current_x < target_x:
                current_x += 1
            else:
                current_x -= 1
            if not self._place_corridor_tile(tilemap, current_x, door1_y):
                success = False
                break
        
        # Second segment
        current_y = door1_y
        target_y = door2_y
        
        while current_y != target_y:
            if current_y < target_y:
                current_y += 1
            else:
                current_y -= 1
            if not self._place_corridor_tile(tilemap, target_x, current_y):
                success = False
                break
        
        # If corridor was created successfully, add doors
        if success:
            tilemap.add_door(door1_x, door1_y)
            tilemap.add_door(door2_x, door2_y)
            tilemap.connect_rooms(room1, room2)
            logger.debug(f"Created corridor between rooms {room1.id} and {room2.id}")
        else:
            logger.warning(f"Failed to create corridor between rooms {room1.id} and {room2.id}")
        
        return success
    
    def _find_valid_door_position(self, tilemap: TileMap, room: Room) -> Optional[Tuple[int, int]]:
        """Find a valid position for a door on the room's perimeter."""
        try:
            # Check all walls for adjacent corridors
            positions = []
            
            # Check top and bottom walls
            for x in range(room.x, room.x + room.width):
                # Top wall
                if (tilemap.is_valid_position(x, room.y - 2) and 
                    tilemap.get_tile(x, room.y - 2) == TileType.FLOOR):
                    positions.append((x, room.y - 1))
                # Bottom wall
                if (tilemap.is_valid_position(x, room.y + room.height + 1) and 
                    tilemap.get_tile(x, room.y + room.height + 1) == TileType.FLOOR):
                    positions.append((x, room.y + room.height))
            
            # Check left and right walls
            for y in range(room.y, room.y + room.height):
                # Left wall
                if (tilemap.is_valid_position(room.x - 2, y) and 
                    tilemap.get_tile(room.x - 2, y) == TileType.FLOOR):
                    positions.append((room.x - 1, y))
                # Right wall
                if (tilemap.is_valid_position(room.x + room.width + 1, y) and 
                    tilemap.get_tile(room.x + room.width + 1, y) == TileType.FLOOR):
                    positions.append((room.x + room.width, y))
            
            logger.debug(f"Found {len(positions)} valid door positions for room {room.id}")
            return random.choice(positions) if positions else None
            
        except Exception as e:
            logger.error(f"Error finding door position for room {room.id}: {e}")
            return None
    
    def _add_sector_connections(self, tilemap: TileMap, rooms: List[Room]) -> None:
        """Add entrance and exit points to the sector."""
        if not rooms:
            return
        
        try:
            logger.info("Adding sector connections")
            
            # Select entrance and exit rooms
            entrance_room = random.choice(rooms)
            exit_room = random.choice([r for r in rooms if r != entrance_room])
            
            logger.debug(f"Selected entrance room {entrance_room.id} and exit room {exit_room.id}")
            
            # Add entrance
            if entrance_pos := self._find_valid_door_position(tilemap, entrance_room):
                logger.debug(f"Placing entrance at {entrance_pos}")
                tilemap.set_tile(entrance_pos[0], entrance_pos[1], TileType.DOOR)
            
            # Add exit
            if exit_pos := self._find_valid_door_position(tilemap, exit_room):
                logger.debug(f"Placing exit at {exit_pos}")
                tilemap.set_tile(exit_pos[0], exit_pos[1], TileType.DOOR)
                
            logger.info("Sector connections added")
            
        except Exception as e:
            logger.error(f"Error adding sector connections: {e}")
