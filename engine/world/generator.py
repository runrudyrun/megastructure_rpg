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
        self.current_theme = 'industrial'  # Default theme
        self._validate_rules()
        logger.debug(f"Loaded generation rules: {self.rules}")

    def _validate_rules(self):
        """Validate generation rules for correctness."""
        try:
            required_sections = ['room_types', 'connection_rules']
            for section in required_sections:
                if section not in self.rules:
                    raise ValueError(f"Missing required section '{section}' in generation rules")
            
            # Validate room types
            for room_type, rules in self.rules['room_types'].items():
                required_fields = ['min_size', 'max_size', 'min_door_width']
                for field in required_fields:
                    if field not in rules:
                        raise ValueError(f"Missing required field '{field}' for room type '{room_type}'")
                
                # Validate size constraints
                min_size = rules['min_size']
                max_size = rules['max_size']
                if len(min_size) != 2 or len(max_size) != 2:
                    raise ValueError(f"Invalid size dimensions for room type '{room_type}'")
                if min_size[0] > max_size[0] or min_size[1] > max_size[1]:
                    raise ValueError(f"Min size larger than max size for room type '{room_type}'")
            
            logger.info("Generation rules validated successfully")
        except Exception as e:
            logger.error(f"Error validating generation rules: {str(e)}")
            raise

    def generate_sector(
        self,
        width: int,
        height: int,
        theme: Optional[str] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        corridor_ratio: Optional[float] = None
    ) -> TileMap:
        """Generate a sector of the megastructure with the specified theme."""
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
            
            # Generate rooms based on theme weights
            rooms = self._generate_rooms(
                tilemap,
                room_weights,
                min_rooms=min_rooms or 5,
                max_rooms=max_rooms or 15
            )
            
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
    
    def _generate_rooms(
            self,
            tilemap: TileMap,
            room_weights: Dict[str, float],
            min_rooms: int = 5,
            max_rooms: int = 15,
            max_attempts: int = 100
        ) -> List[Room]:
        """Generate rooms based on theme weights and size constraints."""
        rooms = []
        attempts = 0
        room_id = 0
        
        try:
            logger.info(f"Generating between {min_rooms} and {max_rooms} rooms")
            
            while len(rooms) < max_rooms and attempts < max_attempts:
                # Select room type based on weights
                room_type = random.choices(list(room_weights.keys()), 
                                        weights=list(room_weights.values()))[0]
                
                # Get size constraints for this room type
                room_rules = self.rules['room_types'][room_type]
                min_size = room_rules['min_size']
                max_size = room_rules['max_size']
                
                # Generate random size within constraints
                width = random.randint(min_size[0], max_size[0])
                height = random.randint(min_size[1], max_size[1])
                
                # Add padding for doors and corridors
                padding = 2
                
                # Generate random position with padding
                x = random.randint(padding, tilemap.width - width - padding)
                y = random.randint(padding, tilemap.height - height - padding)
                
                # Check if this position overlaps with existing rooms
                overlaps = False
                for room in rooms:
                    # Add padding around rooms for doors and corridors
                    if (x - padding < room.x + room.width + padding and 
                        x + width + padding > room.x - padding and
                        y - padding < room.y + room.height + padding and 
                        y + height + padding > room.y - padding):
                        overlaps = True
                        break
                
                if not overlaps:
                    # Create room
                    room = Room(room_id, room_type, x, y, width, height)
                    rooms.append(room)
                    room_id += 1
                    
                    # Place room in tilemap
                    for rx in range(x, x + width):
                        for ry in range(y, y + height):
                            tilemap.set_tile(rx, ry, TileType.FLOOR)
                    
                    # Place walls around room
                    for rx in range(x - 1, x + width + 1):
                        if tilemap.is_valid_position(rx, y - 1):
                            tilemap.set_tile(rx, y - 1, TileType.WALL)
                        if tilemap.is_valid_position(rx, y + height):
                            tilemap.set_tile(rx, y + height, TileType.WALL)
                    
                    for ry in range(y - 1, y + height + 1):
                        if tilemap.is_valid_position(x - 1, ry):
                            tilemap.set_tile(x - 1, ry, TileType.WALL)
                        if tilemap.is_valid_position(x + width, ry):
                            tilemap.set_tile(x + width, ry, TileType.WALL)
                    
                    # Add room to tilemap
                    tilemap.rooms[room.id] = room
                    
                    if len(rooms) >= min_rooms:
                        # Add some randomness to stop generating rooms
                        if random.random() < 0.2:  # 20% chance to stop
                            break
                
                attempts += 1
            
            logger.info(f"Generated {len(rooms)} rooms in {attempts} attempts")
            return rooms
            
        except Exception as e:
            logger.error(f"Error generating rooms: {e}")
            return rooms

    def _get_size_modifier(self, theme_features: Dict) -> float:
        """Calculate room size modifier based on theme features."""
        base_modifier = 1.0
        
        # Adjust size based on tech level
        tech_level = theme_features.get('tech_level', 'medium')
        tech_modifiers = {'low': 0.9, 'medium': 1.0, 'high': 1.1}
        base_modifier *= tech_modifiers.get(tech_level, 1.0)
        
        # Adjust size based on decay level
        decay_level = theme_features.get('decay', 'medium')
        decay_modifiers = {'low': 1.1, 'medium': 1.0, 'high': 0.9}
        base_modifier *= decay_modifiers.get(decay_level, 1.0)
        
        return base_modifier

    def _add_room_features(self, tilemap: TileMap, room: Room, theme_features: Dict) -> None:
        """Add theme-specific features to a room."""
        # Add pillars for structural support in large rooms
        if room.width >= 8 and room.height >= 8:
            self._add_pillars(tilemap, room)
        
        # Add machines/containers based on room type and tech level
        if room.type in ['laboratory', 'maintenance']:
            self._add_machines(tilemap, room, theme_features.get('tech_level', 'medium'))

    def _add_pillars(self, tilemap: TileMap, room: Room) -> None:
        """Add structural pillars to a large room."""
        # Calculate pillar positions
        pillar_spacing = 4  # Space between pillars
        
        # Start 2 tiles in from walls
        start_x = room.x + 2
        start_y = room.y + 2
        end_x = room.x + room.width - 2
        end_y = room.y + room.height - 2
        
        for x in range(start_x, end_x + 1, pillar_spacing):
            for y in range(start_y, end_y + 1, pillar_spacing):
                # Skip if too close to walls
                if (x <= start_x + 1 or x >= end_x - 1 or 
                    y <= start_y + 1 or y >= end_y - 1):
                    continue
                
                # Add pillar
                tilemap.set_tile(x, y, TileType.PILLAR)
                
                # Add decorative tiles around pillar
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    nx, ny = x + dx, y + dy
                    if tilemap.get_tile(nx, ny) == TileType.FLOOR:
                        tilemap.set_tile(nx, ny, TileType.PILLARS)

    def _add_machines(self, tilemap: TileMap, room: Room, tech_level: str) -> None:
        """Add machines and containers based on room type and tech level."""
        # Calculate number of features based on room size and tech level
        area = room.width * room.height
        tech_multiplier = {'low': 0.05, 'medium': 0.08, 'high': 0.12}
        num_features = int(area * tech_multiplier.get(tech_level, 0.08))
        
        # Get available positions (floor tiles not adjacent to walls)
        positions = []
        for y in range(room.y + 2, room.y + room.height - 2):
            for x in range(room.x + 2, room.x + room.width - 2):
                if tilemap.get_tile(x, y) == TileType.FLOOR:
                    # Check surrounding tiles
                    valid = True
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        nx, ny = x + dx, y + dy
                        tile = tilemap.get_tile(nx, ny)
                        if tile not in [TileType.FLOOR, TileType.MACHINE, TileType.CONTAINER]:
                            valid = False
                            break
                    if valid:
                        positions.append((x, y))
        
        # Randomly place features
        random.shuffle(positions)
        for i, pos in enumerate(positions[:num_features]):
            # Alternate between machines and containers
            feature_type = TileType.MACHINE if i % 2 == 0 else TileType.CONTAINER
            
            # Place main feature
            tilemap.set_tile(pos[0], pos[1], feature_type)
            
            # Add decorative tiles around feature
            decorative_type = TileType.MACHINES if feature_type == TileType.MACHINE else TileType.CONTAINERS
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = pos[0] + dx, pos[1] + dy
                if tilemap.get_tile(nx, ny) == TileType.FLOOR:
                    # 50% chance to add decorative tile
                    if random.random() < 0.5:
                        tilemap.set_tile(nx, ny, decorative_type)

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
                for room2 in rooms[i + 1:]:
                    # Calculate distance between room centers
                    center1 = (room1.x + room1.width // 2, room1.y + room1.height // 2)
                    center2 = (room2.x + room2.width // 2, room2.y + room2.height // 2)
                    distance = ((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2) ** 0.5
                    edges.append(Edge(distance, room1, room2))
            
            # Sort edges by distance
            edges.sort()
            
            # Create minimum spanning tree
            connected_rooms = {rooms[0]}
            remaining_rooms = set(rooms[1:])
            
            # Keep trying until all rooms are connected
            while remaining_rooms:
                best_edge = None
                best_door1 = None
                best_door2 = None
                
                # Try to find a valid connection
                for edge in edges:
                    if (edge.room1 in connected_rooms) != (edge.room2 in connected_rooms):
                        # Try to find door positions for both rooms
                        door1_pos = self._find_valid_door_position(tilemap, edge.room1)
                        if not door1_pos:
                            continue
                            
                        door2_pos = self._find_valid_door_position(tilemap, edge.room2)
                        if not door2_pos:
                            continue
                            
                        # Check if we can create a path between doors
                        if self._find_path(tilemap, door1_pos, door2_pos):
                            best_edge = edge
                            best_door1 = door1_pos
                            best_door2 = door2_pos
                            break
                
                if best_edge and best_door1 and best_door2:
                    # Create corridor between doors
                    path = self._find_path(tilemap, best_door1, best_door2)
                    if path:
                        # Place corridor tiles
                        for x, y in path:
                            if not any(self._is_inside_room(x, y, r) for r in rooms):
                                tilemap.set_tile(x, y, TileType.FLOOR)
                                
                                # Place walls around corridor
                                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                                    wall_x, wall_y = x + dx, y + dy
                                    if (tilemap.is_valid_position(wall_x, wall_y) and
                                        not any(self._is_inside_room(wall_x, wall_y, r) for r in rooms) and
                                        tilemap.get_tile(wall_x, wall_y) == TileType.EMPTY):
                                        tilemap.set_tile(wall_x, wall_y, TileType.WALL)
                        
                        # Place doors
                        tilemap.set_tile(best_door1[0], best_door1[1], TileType.DOOR)
                        tilemap.set_tile(best_door2[0], best_door2[1], TileType.DOOR)
                        
                        # Update room connections
                        best_edge.room1.connections.add(best_edge.room2.id)
                        best_edge.room2.connections.add(best_edge.room1.id)
                        
                        # Update connected sets
                        if best_edge.room1 in remaining_rooms:
                            remaining_rooms.remove(best_edge.room1)
                            connected_rooms.add(best_edge.room1)
                        if best_edge.room2 in remaining_rooms:
                            remaining_rooms.remove(best_edge.room2)
                            connected_rooms.add(best_edge.room2)
                else:
                    # If we can't find a valid connection, just place a door in each room
                    for room in remaining_rooms:
                        if door_pos := self._find_valid_door_position(tilemap, room):
                            tilemap.set_tile(door_pos[0], door_pos[1], TileType.DOOR)
                    break
            
            # Add some redundant connections for better navigation
            for edge in edges[:len(rooms) // 2]:  # Add about 50% more connections
                if random.random() < 0.5:  # 50% chance to add each connection
                    door1_pos = self._find_valid_door_position(tilemap, edge.room1)
                    door2_pos = self._find_valid_door_position(tilemap, edge.room2)
                    if door1_pos and door2_pos:
                        path = self._find_path(tilemap, door1_pos, door2_pos)
                        if path:
                            for x, y in path:
                                if not any(self._is_inside_room(x, y, r) for r in rooms):
                                    tilemap.set_tile(x, y, TileType.FLOOR)
            
            logger.info(f"Connected {len(connected_rooms)} rooms")
            
        except Exception as e:
            logger.error(f"Error connecting rooms: {e}")

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

    def _is_valid_door_position(self, tilemap: TileMap, x: int, y: int, door_width: int, orientation: str) -> bool:
        """Check if a position is valid for door placement."""
        if not tilemap.is_valid_position(x, y):
            return False
        
        # Check if there's already a door nearby
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                check_x, check_y = x + dx, y + dy
                if (tilemap.is_valid_position(check_x, check_y) and 
                    tilemap.get_tile(check_x, check_y) == TileType.DOOR):
                    return False
        
        # Check space for door and adjacent tiles
        if orientation == 'vertical':
            # Check door position and sides
            for dx in range(-door_width + 1, door_width):
                if not tilemap.is_valid_position(x + dx, y):
                    return False
                
                # Check tiles above and below
                if not tilemap.is_valid_position(x + dx, y - 1) or not tilemap.is_valid_position(x + dx, y + 1):
                    return False
                
                # Ensure one side is room floor and other side can be corridor
                tile_above = tilemap.get_tile(x + dx, y - 1)
                tile_below = tilemap.get_tile(x + dx, y + 1)
                if not ((tile_above == TileType.FLOOR and tile_below == TileType.EMPTY) or
                       (tile_above == TileType.EMPTY and tile_below == TileType.FLOOR)):
                    return False
        else:  # horizontal
            # Check door position and sides
            for dy in range(-door_width + 1, door_width):
                if not tilemap.is_valid_position(x, y + dy):
                    return False
                
                # Check tiles to left and right
                if not tilemap.is_valid_position(x - 1, y + dy) or not tilemap.is_valid_position(x + 1, y + dy):
                    return False
                
                # Ensure one side is room floor and other side can be corridor
                tile_left = tilemap.get_tile(x - 1, y + dy)
                tile_right = tilemap.get_tile(x + 1, y + dy)
                if not ((tile_left == TileType.FLOOR and tile_right == TileType.EMPTY) or
                       (tile_left == TileType.EMPTY and tile_right == TileType.FLOOR)):
                    return False
        
        return True

    def _create_corridor(self, tilemap: TileMap, room1: Room, room2: Room) -> bool:
        """Create a corridor between two rooms using improved pathing."""
        try:
            # Get room centers
            center1 = (room1.x + room1.width // 2, room1.y + room1.height // 2)
            center2 = (room2.x + room2.width // 2, room2.y + room2.height // 2)
            
            # Find door positions for both rooms
            door1_pos = self._find_valid_door_position(tilemap, room1)
            if not door1_pos:
                logger.debug(f"Could not find valid door position for room {room1.id}")
                return False
                
            door2_pos = self._find_valid_door_position(tilemap, room2)
            if not door2_pos:
                logger.debug(f"Could not find valid door position for room {room2.id}")
                return False
            
            # Create path between doors
            path = self._find_path(tilemap, door1_pos, door2_pos)
            if not path:
                logger.debug(f"Could not find valid path between rooms {room1.id} and {room2.id}")
                return False
            
            # Place doors
            tilemap.set_tile(door1_pos[0], door1_pos[1], TileType.DOOR)
            tilemap.set_tile(door2_pos[0], door2_pos[1], TileType.DOOR)
            
            # Place corridor tiles
            for x, y in path:
                # Don't place floor tiles inside rooms
                if not any(self._is_inside_room(x, y, r) for r in tilemap.rooms.values()):
                    tilemap.set_tile(x, y, TileType.FLOOR)
                    
                    # Place walls around corridor
                    for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        wall_x, wall_y = x + dx, y + dy
                        if (tilemap.is_valid_position(wall_x, wall_y) and
                            not any(self._is_inside_room(wall_x, wall_y, r) for r in tilemap.rooms.values()) and
                            tilemap.get_tile(wall_x, wall_y) == TileType.EMPTY):
                            tilemap.set_tile(wall_x, wall_y, TileType.WALL)
            
            # Connect the rooms in the data structure
            room1.connections.add(room2.id)
            room2.connections.add(room1.id)
            
            logger.debug(f"Created corridor between rooms {room1.id} and {room2.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating corridor: {e}")
            return False

    def _find_entry_point(self, tilemap: TileMap, room: Room, target_center: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Find a valid entry point near the room's edge closest to the target."""
        room_center = (room.x + room.width // 2, room.y + room.height // 2)
        dx = target_center[0] - room_center[0]
        dy = target_center[1] - room_center[1]
        
        # Try all four sides of the room
        sides = []
        
        # Add sides in order of preference based on target direction
        if abs(dx) > abs(dy):
            # Prefer horizontal sides
            sides.extend([
                ('right' if dx > 0 else 'left', 1.0),
                ('top', 0.8),
                ('bottom', 0.8),
                ('left' if dx > 0 else 'right', 0.6)
            ])
        else:
            # Prefer vertical sides
            sides.extend([
                ('bottom' if dy > 0 else 'top', 1.0),
                ('left', 0.8),
                ('right', 0.8),
                ('top' if dy > 0 else 'bottom', 0.6)
            ])
        
        # Try each side in order of preference
        for side, preference in sides:
            if random.random() > preference:
                continue
                
            if side == 'left':
                x = room.x - 1
                # Try multiple points along the wall
                positions = [(x, room.y + i) for i in range(1, room.height)]
            elif side == 'right':
                x = room.x + room.width
                positions = [(x, room.y + i) for i in range(1, room.height)]
            elif side == 'top':
                y = room.y - 1
                positions = [(room.x + i, y) for i in range(1, room.width)]
            else:  # bottom
                y = room.y + room.height
                positions = [(room.x + i, y) for i in range(1, room.width)]
            
            # Randomize position order to avoid predictable patterns
            random.shuffle(positions)
            
            # Try each position
            for x, y in positions:
                if (tilemap.is_valid_position(x, y) and 
                    tilemap.get_tile(x, y) == TileType.EMPTY and
                    not any(self._is_inside_room(x, y, r) for r in tilemap.rooms.values())):
                    
                    # Check if we can place walls around this point
                    can_place_walls = True
                    for wall_dx, wall_dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                        wall_x, wall_y = x + wall_dx, y + wall_dy
                        if not tilemap.is_valid_position(wall_x, wall_y):
                            can_place_walls = False
                            break
                        tile = tilemap.get_tile(wall_x, wall_y)
                        if tile != TileType.EMPTY and tile != TileType.WALL:
                            can_place_walls = False
                            break
                    
                    if can_place_walls:
                        return (x, y)
        
        return None

    def _find_path(self, tilemap: TileMap, start: Tuple[int, int], end: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Find a path between two points using A* pathfinding."""
        if not (tilemap.is_valid_position(start[0], start[1]) and tilemap.is_valid_position(end[0], end[1])):
            return None
            
        # Define possible movements (only cardinal directions)
        movements = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        # Define heuristic function (Manhattan distance)
        def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        # Initialize open and closed lists
        open_list = [(heuristic(start, end), 0, start)]  # (f_score, g_score, position)
        closed_list = set()
        
        # Initialize cost and previous node dictionaries
        g_score = {start: 0}
        previous = {}
        
        while open_list:
            # Get node with lowest f_score
            current_f, current_g, current = min(open_list, key=lambda x: (x[0], x[1]))
            
            if current == end:
                # Reconstruct path
                path = []
                while current in previous:
                    path.append(current)
                    current = previous[current]
                path.append(start)
                path.reverse()
                return path
            
            # Move current to closed list
            open_list = [(f, g, n) for f, g, n in open_list if n != current]
            closed_list.add(current)
            
            # Check each neighbor
            for dx, dy in movements:
                neighbor = (current[0] + dx, current[1] + dy)
                
                # Skip if neighbor is in closed list or out of bounds
                if (neighbor in closed_list or 
                    not tilemap.is_valid_position(neighbor[0], neighbor[1])):
                    continue
                
                # Skip if neighbor is inside a room (except start and end points)
                if (neighbor != start and neighbor != end and 
                    any(self._is_inside_room(neighbor[0], neighbor[1], r) for r in tilemap.rooms.values())):
                    continue
                
                # Calculate tentative g score
                tentative_g = current_g + 1
                
                # Add cost for going through walls
                tile_type = tilemap.get_tile(neighbor[0], neighbor[1])
                if tile_type == TileType.WALL:
                    tentative_g += 10
                
                # If this path is better than any previous one
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    previous[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + heuristic(neighbor, end)
                    
                    # Add to open list if not already there
                    if not any(n == neighbor for _, _, n in open_list):
                        open_list.append((f_score, tentative_g, neighbor))
        
        return None

    def _is_inside_room(self, x: int, y: int, room: Room) -> bool:
        """Check if a point is inside a room."""
        return (room.x <= x < room.x + room.width and 
                room.y <= y < room.y + room.height)

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
