"""Test tool for physics and movement systems."""
import pygame
import sys
import os
from typing import Dict, List, Optional, Tuple
import pytest
from engine.physics.movement import MovementSystem, MovementState, MovementStats
from engine.physics.collision import CollisionSystem
from engine.world.tilemap import TileMap, TileType

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.physics.collision import CollisionSystem
from engine.physics.movement import MovementSystem, MovementState, MovementStats
from engine.world.generator import MegastructureGenerator
from engine.world.tilemap import TileMap, TileType
from engine.config.config_manager import ConfigManager
from engine.ecs.entity import Entity


# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
BROWN = (139, 69, 19)

# Tile colors
TILE_COLORS = {
    TileType.EMPTY: BLACK,
    TileType.FLOOR: GRAY,
    TileType.WALL: WHITE,
    TileType.DOOR: BROWN,
    TileType.MACHINE: BLUE,
    TileType.CONTAINER: GREEN,
    TileType.PILLAR: RED,
}

class PhysicsVisualizer:
    """Tool for testing physics and movement systems."""
    
    def __init__(self, width: int = 800, height: int = 600, tile_size: int = 20):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Physics Test Tool")
        self.clock = pygame.time.Clock()
        self.tile_size = tile_size
        
        # Initialize game systems
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        self.config_manager = ConfigManager(data_dir)
        self.generator = MegastructureGenerator(self.config_manager)
        
        # Generate test map
        map_width = width // tile_size
        map_height = height // tile_size
        self.tilemap = self.generator.generate_sector(map_width, map_height, "industrial")
        
        # Initialize physics systems
        self.collision_system = CollisionSystem(self.tilemap)
        self.movement_system = MovementSystem(self.collision_system)
        
        # Create test entity
        self.player = Entity()
        start_pos = self._find_valid_start_position()
        self.movement_system.register_entity(
            self.player.id,
            start_pos,
            MovementStats(movement_points=1, diagonal_movement=False)
        )
        
        # Game state
        self.selected_entity = self.player
        self.turn_pending = False
    
    def _find_valid_start_position(self) -> Tuple[int, int]:
        """Find a valid starting position on a floor tile."""
        for y in range(self.tilemap.height):
            for x in range(self.tilemap.width):
                if self.tilemap.get_tile(x, y) == TileType.FLOOR:
                    return (x, y)
        return (1, 1)  # Fallback
    
    def run(self):
        """Main game loop."""
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_input(event.key)
            
            # Execute turn if pending
            if self.turn_pending:
                self.movement_system.execute_turn()
                self.turn_pending = False
            
            # Draw
            self._draw()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
    
    def _handle_input(self, key: int):
        """Handle keyboard input."""
        if not self.selected_entity:
            return
        
        # Movement controls
        dx, dy = 0, 0
        if key == pygame.K_LEFT:
            dx = -1
        elif key == pygame.K_RIGHT:
            dx = 1
        elif key == pygame.K_UP:
            dy = -1
        elif key == pygame.K_DOWN:
            dy = 1
        
        # Request movement
        if dx != 0 or dy != 0:
            if self.movement_system.request_move(self.selected_entity.id, dx, dy):
                self.turn_pending = True
        
        # Other controls
        elif key == pygame.K_SPACE:
            # Skip turn
            self.turn_pending = True
        elif key == pygame.K_r:
            # Regenerate map
            self.tilemap = self.generator.generate_sector(
                self.tilemap.width,
                self.tilemap.height,
                "industrial"
            )
            self.collision_system = CollisionSystem(self.tilemap)
            self.movement_system = MovementSystem(self.collision_system)
            start_pos = self._find_valid_start_position()
            self.movement_system.register_entity(
                self.player.id,
                start_pos,
                MovementStats(movement_points=1, diagonal_movement=False)
            )
    
    def _draw(self):
        """Draw the current state."""
        self.screen.fill(BLACK)
        
        # Draw tilemap
        for y in range(self.tilemap.height):
            for x in range(self.tilemap.width):
                tile = self.tilemap.get_tile(x, y)
                color = TILE_COLORS.get(tile, BLACK)
                rect = pygame.Rect(
                    x * self.tile_size,
                    y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, BLACK, rect, 1)
        
        # Draw entities
        if self.selected_entity:
            pos = self.movement_system.get_position(self.selected_entity.id)
            if pos:
                # Draw entity
                rect = pygame.Rect(
                    pos[0] * self.tile_size,
                    pos[1] * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(self.screen, RED, rect)
                
                # Draw valid moves
                valid_moves = self.movement_system.get_valid_moves(self.selected_entity.id)
                for move in valid_moves:
                    rect = pygame.Rect(
                        move[0] * self.tile_size,
                        move[1] * self.tile_size,
                        self.tile_size,
                        self.tile_size
                    )
                    pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)


class TestPhysics:
    @pytest.fixture
    def setup(self):
        tilemap = TileMap(10, 10)
        collision_system = CollisionSystem(tilemap)
        movement_system = MovementSystem(collision_system)
        entity = Entity()
        movement_system.register_entity(entity.id, (5, 5))
        return movement_system, collision_system, entity
    
    def test_basic_movement(self, setup):
        movement_system, collision_system, entity = setup
        # Test valid move
        dx, dy = 1, 0  # Move right
        assert movement_system.request_move(entity.id, dx, dy)
        movement_system.execute_turn()
        assert movement_system.get_position(entity.id) == (6, 5)
        
        # Test invalid move (too far)
        dx, dy = 3, 3  # Try to move too far
        assert not movement_system.request_move(entity.id, dx, dy)
    
    def test_collision(self, setup):
        movement_system, collision_system, entity = setup
        # Create wall
        collision_system.tilemap.set_tile(6, 5, TileType.WALL)
        
        # Test entity collision with wall
        dx, dy = 1, 0  # Try to move into wall
        assert not movement_system.request_move(entity.id, dx, dy)
        
    def test_diagonal_movement(self, setup):
        movement_system, collision_system, entity = setup
        stats = MovementStats(movement_points=2, diagonal_movement=True)
        movement_system.register_entity(entity.id, (5, 5), stats)
        
        # Test diagonal move
        dx, dy = 1, 1  # Move diagonally
        assert movement_system.request_move(entity.id, dx, dy)
        movement_system.execute_turn()
        assert movement_system.get_position(entity.id) == (6, 6)
    
    def test_boundary_collision(self, setup):
        """Test collision detection at map boundaries."""
        movement_system, collision_system, entity = setup
        
        # Try to move beyond map boundaries
        original_pos = movement_system.get_position(entity.id)
        movement_system.request_move(entity.id, -1, 0)  # Try moving left off map
        assert movement_system.get_position(entity.id) == original_pos
        
        # Try moving to map edge
        movement_system.request_move(entity.id, collision_system.tilemap.width, collision_system.tilemap.height)
        new_pos = movement_system.get_position(entity.id)
        assert new_pos[0] < collision_system.tilemap.width and new_pos[1] < collision_system.tilemap.height

    def test_movement_interruption(self, setup):
        """Test handling of interrupted movement."""
        movement_system, collision_system, entity = setup
        
        # Simulate obstacle appearing during movement
        start_pos = movement_system.get_position(entity.id)
        
        # Request move right by 2 tiles
        movement_system.request_move(entity.id, 2, 0)
        
        # Place obstacle in path
        mid_x = start_pos[0] + 1
        collision_system.tilemap.set_tile(mid_x, start_pos[1], TileType.WALL)
        
        # Verify movement stops at obstacle
        final_pos = movement_system.get_position(entity.id)
        assert final_pos[0] < mid_x


if __name__ == "__main__":
    visualizer = PhysicsVisualizer()
    visualizer.run()
