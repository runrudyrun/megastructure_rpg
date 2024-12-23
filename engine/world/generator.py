"""Procedural generator for the megastructure environment."""
from typing import Dict, List, Tuple, Optional, Set
import random
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor
from ..config.config_manager import ConfigManager
from .tilemap import TileMap, Room, TileType
from .sector_cache import SectorCache
from .hierarchical_pathfinding import HierarchicalPathfinder
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
        self.current_theme = 'industrial'  # Default theme
        self.sector_cache = SectorCache()
        self.pathfinder = HierarchicalPathfinder()
        self._validate_rules()
        logger.debug(f"Loaded generation rules: {self.rules}")
        
    def generate_sector(
        self,
        width: int,
        height: int,
        theme: Optional[str] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        corridor_ratio: Optional[float] = None,
        sector_x: int = 0,
        sector_y: int = 0
    ) -> TileMap:
        """Generate a sector of the megastructure with the specified theme."""
        # Check cache first
        cached_sector = self.sector_cache.get(sector_x, sector_y, theme or self.current_theme)
        if cached_sector:
            return cached_sector
            
        if width <= 0 or height <= 0:
            raise ValueError("Invalid sector dimensions")
            
        if theme:
            if theme not in self.rules.get('themes', {}):
                logger.warning(f"Unknown theme '{theme}', falling back to '{self.current_theme}'")
            else:
                self.current_theme = theme
                
        logger.info(f"Generating sector: {width}x{height}, theme: {theme}")
        
        try:
            tilemap = TileMap(width, height)
            theme_config = self.rules.get('themes', {}).get(theme)
            if not theme_config:
                logger.error(f"Theme '{theme}' not found in rules")
                theme_config = {'room_weights': {'corridor': 1.0}}
            
            logger.debug(f"Theme config: {theme_config}")
            
            # Update room weights based on corridor ratio if specified
            room_weights = theme_config.get('room_weights', {}).copy()
            if corridor_ratio is not None:
                non_corridor_ratio = (1.0 - corridor_ratio) / (len(room_weights) - 1)
                for room_type in room_weights:
                    room_weights[room_type] = corridor_ratio if room_type == 'corridor' else non_corridor_ratio
            
            # Generate rooms in parallel
            rooms = self._generate_rooms_parallel(
                tilemap,
                room_weights,
                min_rooms or 5,
                max_rooms or 15
            )
            
            # Connect rooms using hierarchical pathfinding
            self._connect_rooms_optimized(tilemap, rooms)
            
            # Add sector connections
            self._add_sector_connections(tilemap, rooms)
            
            # Cache the generated sector
            self.sector_cache.put(sector_x, sector_y, theme or self.current_theme, tilemap)
            
            return tilemap
            
        except Exception as e:
            logger.error(f"Error generating sector: {str(e)}")
            raise
            
    def _generate_rooms_parallel(self, tilemap: TileMap, room_weights: Dict[str, float],
                               min_rooms: int, max_rooms: int) -> List[Room]:
        """Generate rooms in parallel using thread pool."""
        target_rooms = random.randint(min_rooms, max_rooms)
        rooms: List[Room] = []
        failed_attempts = 0
        max_attempts = 100
        
        with ThreadPoolExecutor() as executor:
            while len(rooms) < target_rooms and failed_attempts < max_attempts:
                # Generate multiple room attempts in parallel
                futures = []
                for _ in range(min(4, target_rooms - len(rooms))):
                    futures.append(executor.submit(self._generate_room_attempt,
                                                tilemap, room_weights))
                
                # Collect successful room generations
                for future in futures:
                    room = future.result()
                    if room:
                        rooms.append(room)
                        failed_attempts = 0
                    else:
                        failed_attempts += 1
                        
        return rooms
        
    def _generate_room_attempt(self, tilemap: TileMap,
                             room_weights: Dict[str, float]) -> Optional[Room]:
        """Attempt to generate a single room."""
        room_type = random.choices(list(room_weights.keys()),
                                 weights=list(room_weights.values()))[0]
        rules = self.rules['room_types'][room_type]
        
        min_size = rules['min_size']
        max_size = rules['max_size']
        
        width = random.randint(min_size[0], max_size[0])
        height = random.randint(min_size[1], max_size[1])
        
        # Try to place room
        for _ in range(10):  # Limited placement attempts
            x = random.randint(0, tilemap.width - width)
            y = random.randint(0, tilemap.height - height)
            
            if self._can_place_room(tilemap, x, y, width, height):
                room = Room(x, y, width, height, room_type)
                self._place_room(tilemap, room)
                return room
                
        return None
        
    def _connect_rooms_optimized(self, tilemap: TileMap, rooms: List[Room]) -> None:
        """Connect rooms using hierarchical pathfinding."""
        if not rooms:
            return
            
        # Create minimum spanning tree of rooms
        edges: List[Edge] = []
        for i, room1 in enumerate(rooms):
            for room2 in rooms[i + 1:]:
                distance = abs(room1.center[0] - room2.center[0]) + abs(room1.center[1] - room2.center[1])
                edges.append(Edge(distance, room1, room2))
                
        edges.sort()  # Sort by distance
        
        # Create corridors using hierarchical pathfinding
        connected: Set[Room] = {rooms[0]}
        for edge in edges:
            if edge.room1 in connected and edge.room2 not in connected:
                path = self.pathfinder.find_path(tilemap, edge.room1.center, edge.room2.center)
                if path:
                    self._create_corridor_from_path(tilemap, path)
                    connected.add(edge.room2)
            elif edge.room2 in connected and edge.room1 not in connected:
                path = self.pathfinder.find_path(tilemap, edge.room2.center, edge.room1.center)
                if path:
                    self._create_corridor_from_path(tilemap, path)
                    connected.add(edge.room1)
                    
    def _create_corridor_from_path(self, tilemap: TileMap, path: List[Tuple[int, int]]) -> None:
        """Create a corridor along a path."""
        for x, y in path:
            tilemap.set_tile(x, y, TileType.FLOOR)
            # Add walls around corridor
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < tilemap.width and 0 <= ny < tilemap.height and
                    tilemap.get_tile(nx, ny) == TileType.EMPTY):
                    tilemap.set_tile(nx, ny, TileType.WALL)
                    
    def _can_place_room(self, tilemap: TileMap, x: int, y: int, width: int, height: int) -> bool:
        """Check if a room can be placed at the given position."""
        for dx in range(width):
            for dy in range(height):
                nx, ny = x + dx, y + dy
                if not tilemap.is_valid_position(nx, ny):
                    return False
                if tilemap.get_tile(nx, ny) != TileType.EMPTY:
                    return False
        return True
        
    def _place_room(self, tilemap: TileMap, room: Room) -> None:
        """Place a room on the tilemap."""
        for dx in range(room.width):
            for dy in range(room.height):
                nx, ny = room.x + dx, room.y + dy
                tilemap.set_tile(nx, ny, TileType.FLOOR)
                
        # Add walls around room
        for dx in range(room.width + 2):
            nx, ny = room.x - 1 + dx, room.y - 1
            if tilemap.is_valid_position(nx, ny):
                tilemap.set_tile(nx, ny, TileType.WALL)
            nx, ny = room.x - 1 + dx, room.y + room.height
            if tilemap.is_valid_position(nx, ny):
                tilemap.set_tile(nx, ny, TileType.WALL)
        for dy in range(room.height + 2):
            nx, ny = room.x - 1, room.y - 1 + dy
            if tilemap.is_valid_position(nx, ny):
                tilemap.set_tile(nx, ny, TileType.WALL)
            nx, ny = room.x + room.width, room.y - 1 + dy
            if tilemap.is_valid_position(nx, ny):
                tilemap.set_tile(nx, ny, TileType.WALL)
                
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
            
    def _find_valid_door_position(self, tilemap: TileMap, room: Room) -> Optional[Tuple[int, int]]:
        """Find a valid position for a door on the room's perimeter."""
        try:
            # Get door width for this room type
            room_rules = self.rules['room_types'].get(room.type, {})
            door_width = room_rules.get('min_door_width', 1)  # Default to 1 if not specified
            
            positions = []
            
            # Try each wall
            # Top wall
            for x in range(room.x + 1, room.x + room.width - 1):
                if tilemap.is_valid_position(x, room.y - 1):
                    positions.append((x, room.y - 1))
            
            # Bottom wall
            for x in range(room.x + 1, room.x + room.width - 1):
                if tilemap.is_valid_position(x, room.y + room.height):
                    positions.append((x, room.y + room.height))
            
            # Left wall
            for y in range(room.y + 1, room.y + room.height - 1):
                if tilemap.is_valid_position(room.x - 1, y):
                    positions.append((room.x - 1, y))
            
            # Right wall
            for y in range(room.y + 1, room.y + room.height - 1):
                if tilemap.is_valid_position(room.x + room.width, y):
                    positions.append((room.x + room.width, y))
            
            if positions:
                # Choose a random position
                pos = random.choice(positions)
                
                # Place the door
                tilemap.set_tile(pos[0], pos[1], TileType.DOOR)
                
                # Place floor tiles around the door
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        check_x, check_y = pos[0] + dx, pos[1] + dy
                        if tilemap.is_valid_position(check_x, check_y):
                            current_tile = tilemap.get_tile(check_x, check_y)
                            if current_tile == TileType.EMPTY or current_tile == TileType.WALL:
                                tilemap.set_tile(check_x, check_y, TileType.FLOOR)
                
                return pos
            
            logger.warning(f"No valid door positions found for room {room.id}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding door position: {e}")
            return None
