"""Hierarchical A* pathfinding implementation."""
from typing import List, Tuple, Set, Dict, Optional
import heapq
import numpy as np
from dataclasses import dataclass, field
from .tilemap import TileMap, TileType

@dataclass(order=True)
class PathNode:
    """Node for A* pathfinding."""
    f_score: float
    position: Tuple[int, int] = field(compare=False)
    g_score: float = field(compare=False)
    parent: Optional['PathNode'] = field(default=None, compare=False)
    
class HierarchicalPathfinder:
    """Hierarchical A* pathfinding system."""
    
    def __init__(self, chunk_size: int = 16):
        self.chunk_size = chunk_size
        self._abstract_cache: Dict[TileMap, np.ndarray] = {}
        
    def _create_abstract_grid(self, tilemap: TileMap) -> np.ndarray:
        """
        Create an abstract grid by dividing the map into chunks.
        
        Args:
            tilemap: The tilemap to create abstract grid for
            
        Returns:
            numpy array representing walkability of chunks
        """
        height, width = tilemap.height, tilemap.width
        chunk_h = (height + self.chunk_size - 1) // self.chunk_size
        chunk_w = (width + self.chunk_size - 1) // self.chunk_size
        
        abstract = np.ones((chunk_h, chunk_w), dtype=bool)
        
        # Mark chunks as unwalkable if they contain too many obstacles
        for cy in range(chunk_h):
            for cx in range(chunk_w):
                # Get chunk bounds
                x1 = cx * self.chunk_size
                y1 = cy * self.chunk_size
                x2 = min(x1 + self.chunk_size, width)
                y2 = min(y1 + self.chunk_size, height)
                
                # Count obstacles in chunk
                obstacles = 0
                total = 0
                for y in range(y1, y2):
                    for x in range(x1, x2):
                        if tilemap.get_tile(x, y) == TileType.WALL:
                            obstacles += 1
                        total += 1
                
                # Mark as unwalkable if more than 25% is obstacles
                if obstacles / total > 0.25:
                    abstract[cy, cx] = False
                    
        return abstract
        
    def _get_abstract_grid(self, tilemap: TileMap) -> np.ndarray:
        """Get or create abstract grid for tilemap."""
        if tilemap not in self._abstract_cache:
            self._abstract_cache[tilemap] = self._create_abstract_grid(tilemap)
        return self._abstract_cache[tilemap]
        
    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Calculate heuristic distance between points."""
        return abs(b[0] - a[0]) + abs(b[1] - a[1])
        
    def _get_neighbors(self, pos: Tuple[int, int], grid: np.ndarray) -> List[Tuple[int, int]]:
        """Get valid neighboring positions."""
        x, y = pos
        height, width = grid.shape
        neighbors = []
        
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and grid[ny, nx]:
                neighbors.append((nx, ny))
                
        return neighbors
        
    def _abstract_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                      abstract_grid: np.ndarray) -> List[Tuple[int, int]]:
        """Find path in abstract grid using A*."""
        start_node = PathNode(0, start, 0)
        open_set = [start_node]
        closed_set: Set[Tuple[int, int]] = set()
        g_scores: Dict[Tuple[int, int], float] = {start: 0}
        
        while open_set:
            current = heapq.heappop(open_set)
            
            if current.position == goal:
                # Reconstruct path
                path = []
                while current:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]
                
            closed_set.add(current.position)
            
            for neighbor_pos in self._get_neighbors(current.position, abstract_grid):
                if neighbor_pos in closed_set:
                    continue
                    
                tentative_g = g_scores[current.position] + 1
                
                if neighbor_pos not in g_scores or tentative_g < g_scores[neighbor_pos]:
                    g_scores[neighbor_pos] = tentative_g
                    f_score = tentative_g + self._heuristic(neighbor_pos, goal)
                    neighbor_node = PathNode(f_score, neighbor_pos, tentative_g, current)
                    heapq.heappush(open_set, neighbor_node)
                    
        return []
        
    def find_path(self, tilemap: TileMap, start: Tuple[int, int],
                 goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Find a path between two points using hierarchical A*.
        
        Args:
            tilemap: TileMap to pathfind in
            start: Starting position (x, y)
            goal: Goal position (x, y)
            
        Returns:
            List of positions forming the path
        """
        # Convert to abstract coordinates
        abstract_start = (start[0] // self.chunk_size, start[1] // self.chunk_size)
        abstract_goal = (goal[0] // self.chunk_size, goal[1] // self.chunk_size)
        
        # Get abstract grid
        abstract_grid = self._get_abstract_grid(tilemap)
        
        # Find path in abstract grid
        abstract_path = self._abstract_path(abstract_start, abstract_goal, abstract_grid)
        if not abstract_path:
            return []
            
        # Refine path through chunks
        final_path = [start]
        current_pos = start
        
        for i in range(len(abstract_path) - 1):
            # Get chunk boundaries
            current_chunk = abstract_path[i]
            next_chunk = abstract_path[i + 1]
            
            # Find best crossing point between chunks
            crossing_points = self._find_crossing_points(tilemap, current_chunk,
                                                       next_chunk, current_pos)
            if not crossing_points:
                continue
                
            # Find best crossing point based on distance to goal
            best_point = min(crossing_points,
                           key=lambda p: self._heuristic(p, goal))
                           
            # Find detailed path to crossing point
            chunk_path = self._detailed_path(tilemap, current_pos, best_point)
            if chunk_path:
                final_path.extend(chunk_path[1:])
                current_pos = best_point
                
        # Find final detailed path to goal
        final_chunk_path = self._detailed_path(tilemap, current_pos, goal)
        if final_chunk_path:
            final_path.extend(final_chunk_path[1:])
            
        return final_path
        
    def _find_crossing_points(self, tilemap: TileMap, chunk1: Tuple[int, int],
                            chunk2: Tuple[int, int],
                            current_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find valid crossing points between adjacent chunks."""
        points = []
        x1, y1 = chunk1
        x2, y2 = chunk2
        
        # Determine shared edge
        if x1 == x2:  # Vertical edge
            edge_x = (x1 + 1) * self.chunk_size
            y_start = max(y1 * self.chunk_size, 0)
            y_end = min((y1 + 1) * self.chunk_size, tilemap.height)
            
            for y in range(y_start, y_end):
                if (tilemap.get_tile(edge_x - 1, y) != TileType.WALL and
                    tilemap.get_tile(edge_x, y) != TileType.WALL):
                    points.append((edge_x, y))
        else:  # Horizontal edge
            edge_y = (y1 + 1) * self.chunk_size
            x_start = max(x1 * self.chunk_size, 0)
            x_end = min((x1 + 1) * self.chunk_size, tilemap.width)
            
            for x in range(x_start, x_end):
                if (tilemap.get_tile(x, edge_y - 1) != TileType.WALL and
                    tilemap.get_tile(x, edge_y) != TileType.WALL):
                    points.append((x, edge_y))
                    
        return points
        
    def _detailed_path(self, tilemap: TileMap, start: Tuple[int, int],
                      goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Find detailed path within a chunk using A*."""
        start_node = PathNode(0, start, 0)
        open_set = [start_node]
        closed_set: Set[Tuple[int, int]] = set()
        g_scores: Dict[Tuple[int, int], float] = {start: 0}
        
        while open_set:
            current = heapq.heappop(open_set)
            
            if current.position == goal:
                # Reconstruct path
                path = []
                while current:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]
                
            closed_set.add(current.position)
            
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                nx = current.position[0] + dx
                ny = current.position[1] + dy
                
                if (nx < 0 or nx >= tilemap.width or
                    ny < 0 or ny >= tilemap.height or
                    tilemap.get_tile(nx, ny) == TileType.WALL):
                    continue
                    
                neighbor_pos = (nx, ny)
                if neighbor_pos in closed_set:
                    continue
                    
                # Use diagonal distance for better paths
                tentative_g = g_scores[current.position] + (1.4 if dx and dy else 1.0)
                
                if neighbor_pos not in g_scores or tentative_g < g_scores[neighbor_pos]:
                    g_scores[neighbor_pos] = tentative_g
                    f_score = tentative_g + self._heuristic(neighbor_pos, goal)
                    neighbor_node = PathNode(f_score, neighbor_pos, tentative_g, current)
                    heapq.heappush(open_set, neighbor_node)
                    
        return []
