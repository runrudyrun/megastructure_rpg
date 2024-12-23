"""Pathfinding implementation for NPCs."""
from typing import List, Tuple, Optional, Set, Dict
from ..world.tilemap import TileMap, TileType
import heapq

class PathFinder:
    """A* pathfinding implementation."""
    
    def __init__(self, tilemap: TileMap):
        """Initialize pathfinder with tilemap."""
        self.tilemap = tilemap
    
    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """Find a path from start to goal using A* algorithm."""
        if not self._is_valid_position(start) or not self._is_valid_position(goal):
            return None
        
        # Initialize data structures
        frontier = []  # Priority queue
        heapq.heappush(frontier, (0, start))
        came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
        cost_so_far: Dict[Tuple[int, int], float] = {start: 0}
        
        while frontier:
            current = heapq.heappop(frontier)[1]
            
            if current == goal:
                break
            
            # Check all neighbors
            for next_pos in self._get_neighbors(current):
                new_cost = cost_so_far[current] + 1
                
                if next_pos not in cost_so_far or new_cost < cost_so_far[next_pos]:
                    cost_so_far[next_pos] = new_cost
                    priority = new_cost + self._heuristic(next_pos, goal)
                    heapq.heappush(frontier, (priority, next_pos))
                    came_from[next_pos] = current
        
        # Reconstruct path
        if goal not in came_from:
            return None
            
        current = goal
        path = []
        
        while current is not None:
            path.append(current)
            current = came_from[current]
        
        path.reverse()
        return path
    
    def _is_valid_position(self, pos: Tuple[int, int]) -> bool:
        """Check if a position is valid and walkable."""
        if not self.tilemap.is_valid_position(pos[0], pos[1]):
            return False
            
        tile = self.tilemap.get_tile(pos[0], pos[1])
        return tile in [TileType.FLOOR, TileType.DOOR]
    
    def _get_neighbors(self, pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        neighbors = []
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:  # 4-directional movement
            next_pos = (pos[0] + dx, pos[1] + dy)
            if self._is_valid_position(next_pos):
                neighbors.append(next_pos)
        return neighbors
    
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance heuristic."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
