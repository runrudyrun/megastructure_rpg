from typing import List, Tuple, Dict, Optional, Set
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto

class TileType(Enum):
    """Basic tile types for the megastructure."""
    EMPTY = auto()
    FLOOR = auto()
    WALL = auto()
    DOOR = auto()
    DOORS = auto()     # Plural form for config compatibility
    WINDOW = auto()
    WINDOWS = auto()   # Plural form for config compatibility
    TERMINAL = auto()
    TERMINALS = auto() # Plural form for config compatibility
    CONTAINER = auto()
    CONTAINERS = auto() # Plural form for config compatibility
    MACHINE = auto()
    MACHINES = auto()  # Plural form for config compatibility
    PILLAR = auto()
    PILLARS = auto()   # Plural form for config compatibility
    LIGHT = auto()
    LIGHTS = auto()    # Plural form for config compatibility

@dataclass
class Room:
    """Represents a room in the megastructure."""
    id: int
    type: str
    x: int
    y: int
    width: int
    height: int
    connections: Set[int] = None  # Set of connected room IDs
    features: Dict[str, List[Tuple[int, int]]] = None  # Feature positions
    
    def __post_init__(self):
        if self.connections is None:
            self.connections = set()
        if self.features is None:
            self.features = {}
    
    def __eq__(self, other):
        if not isinstance(other, Room):
            return False
        return self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
    def get_bounds(self) -> Tuple[int, int, int, int]:
        """Get room boundaries (x1, y1, x2, y2)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is inside the room."""
        return (self.x <= x < self.x + self.width and 
                self.y <= y < self.y + self.height)
    
    def overlaps(self, other: 'Room') -> bool:
        """Check if this room overlaps with another room."""
        x1, y1, x2, y2 = self.get_bounds()
        ox1, oy1, ox2, oy2 = other.get_bounds()
        return not (x2 < ox1 or x1 > ox2 or y2 < oy1 or y1 > oy2)

class TileMap:
    """2D tile-based map representation."""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles = np.full((height, width), TileType.EMPTY, dtype=object)
        self.rooms: Dict[int, Room] = {}
        self.next_room_id = 0
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if a position is within map bounds."""
        return 0 <= x < self.width and 0 <= y < self.height
    
    def get_tile(self, x: int, y: int) -> Optional[TileType]:
        """Get tile type at position."""
        if self.is_valid_position(x, y):
            return self.tiles[y, x]
        return None
    
    def set_tile(self, x: int, y: int, tile_type: TileType) -> bool:
        """Set tile type at position."""
        if self.is_valid_position(x, y):
            self.tiles[y, x] = tile_type
            return True
        return False
    
    def add_room(self, room_type: str, x: int, y: int, width: int, height: int) -> Optional[Room]:
        """Add a new room to the map."""
        # Check bounds
        if not (self.is_valid_position(x, y) and 
                self.is_valid_position(x + width - 1, y + height - 1)):
            return None
        
        # Create room
        room = Room(self.next_room_id, room_type, x, y, width, height)
        self.next_room_id += 1
        
        # Check for overlaps
        for existing_room in self.rooms.values():
            if room.overlaps(existing_room):
                return None
        
        # Add room
        self.rooms[room.id] = room
        
        # Set tiles
        for dy in range(height):
            for dx in range(width):
                if dx == 0 or dx == width-1 or dy == 0 or dy == height-1:
                    self.set_tile(x + dx, y + dy, TileType.WALL)
                else:
                    self.set_tile(x + dx, y + dy, TileType.FLOOR)
        
        return room
    
    def add_door(self, x: int, y: int) -> bool:
        """Add a door at the specified position."""
        if not self.is_valid_position(x, y):
            return False
        
        # Check if position is on a wall
        if self.get_tile(x, y) != TileType.WALL:
            return False
        
        self.set_tile(x, y, TileType.DOOR)
        return True
    
    def add_feature(self, room: Room, feature_type: TileType, x: int, y: int) -> bool:
        """Add a feature to a room."""
        if not (room.contains_point(x, y) and self.get_tile(x, y) == TileType.FLOOR):
            return False
            
        self.set_tile(x, y, feature_type)
        feature_name = feature_type.name.lower()
        if feature_name not in room.features:
            room.features[feature_name] = []
        room.features[feature_name].append((x, y))
        return True
    
    def connect_rooms(self, room1: Room, room2: Room) -> bool:
        """Create a connection between two rooms."""
        if room1.id == room2.id:
            return False
            
        room1.connections.add(room2.id)
        room2.connections.add(room1.id)
        return True
    
    def get_room_at(self, x: int, y: int) -> Optional[Room]:
        """Get the room at the specified position."""
        for room in self.rooms.values():
            if room.contains_point(x, y):
                return room
        return None
    
    def get_neighbors(self, x: int, y: int) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if self.is_valid_position(nx, ny):
                neighbors.append((nx, ny))
        return neighbors
