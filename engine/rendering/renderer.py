"""Rendering system for the megastructure visualization."""
import pygame
import numpy as np
from typing import Dict, Tuple, Optional, List
from ..world.tilemap import TileMap, TileType, Room
from .colors import *
from .effects import GlowManager, create_scanline_effect, create_noise_texture, TerminalEffect


class MapRenderer:
    """Renderer for the tilemap."""
    
    def __init__(self, width: int, height: int, tile_size: int = 32, theme: str = 'residential'):
        """Initialize the renderer."""
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.theme = theme
        self.camera_x = 0
        self.camera_y = 0
        self.surface = pygame.Surface((width, height))
        self.selected_room = None
        self.highlight_alpha = 100
        self.highlight_increasing = True
        self.show_grid = True
        
        # Initialize colors
        self._init_colors()
        
        # Initialize scanlines with reduced intensity
        self.scanlines = pygame.Surface((width, height), pygame.SRCALPHA)
        scanline_alpha = 10  # Reduced from original value
        for y in range(0, height, 2):
            pygame.draw.line(self.scanlines, (0, 0, 0, scanline_alpha), (0, y), (width, y))
        
        # Initialize glow manager
        self.glow_manager = GlowManager()
        
        # Initialize noise effect
        self.noise = None  # Disable noise effect for now
    
    def _init_colors(self) -> None:
        """Initialize color mappings."""
        self.colors = {
            TileType.EMPTY: UI_COLORS['background'],
            TileType.FLOOR: THEME_COLORS[self.theme]['floor'],
            TileType.WALL: THEME_COLORS[self.theme]['wall'],
            TileType.DOOR: FEATURE_COLORS['door'],
            TileType.DOORS: FEATURE_COLORS['door'],
            TileType.WINDOW: FEATURE_COLORS['window'],
            TileType.WINDOWS: FEATURE_COLORS['window'],
            TileType.TERMINAL: FEATURE_COLORS['terminal'],
            TileType.TERMINALS: FEATURE_COLORS['terminal'],
            TileType.CONTAINER: FEATURE_COLORS['container'],
            TileType.CONTAINERS: FEATURE_COLORS['container'],
            TileType.MACHINE: FEATURE_COLORS['machine'],
            TileType.MACHINES: FEATURE_COLORS['machine'],
            TileType.PILLAR: FEATURE_COLORS['pillar'],
            TileType.PILLARS: FEATURE_COLORS['pillar'],
            TileType.LIGHT: FEATURE_COLORS['light'],
            TileType.LIGHTS: FEATURE_COLORS['light']
        }
    
    def set_theme(self, theme: str) -> None:
        """Set the current theme."""
        self.theme = theme
        self._init_colors()
    
    def move_camera(self, dx: int, dy: int) -> None:
        """Move the camera by the specified amount."""
        self.camera_x = max(0, min(self.camera_x + dx, 
                                 self.tile_size * 50 - self.width))
        self.camera_y = max(0, min(self.camera_y + dy, 
                                 self.tile_size * 50 - self.height))
    
    def select_room(self, room: Optional[Room]) -> None:
        """Select a room to highlight."""
        self.selected_room = room
        self.highlight_alpha = 0
        self.highlight_increasing = True
    
    def render(self, tilemap: TileMap, show_grid: bool = True) -> None:
        """Render the tilemap with visual effects."""
        if not tilemap or not hasattr(tilemap, 'tiles') or tilemap.tiles is None:
            return
            
        # Clear surface with a dark background
        self.surface.fill(UI_COLORS['background'])
        
        # Calculate visible area
        start_x = max(0, self.camera_x // self.tile_size)
        start_y = max(0, self.camera_y // self.tile_size)
        end_x = min(tilemap.width, (self.camera_x + self.width) // self.tile_size + 1)
        end_y = min(tilemap.height, (self.camera_y + self.height) // self.tile_size + 1)
        
        # Draw tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile_type = tilemap.get_tile(x, y)
                if tile_type is not None and tile_type != TileType.EMPTY:
                    color = self.colors.get(tile_type, UI_COLORS['background'])
                    screen_x = x * self.tile_size - self.camera_x
                    screen_y = y * self.tile_size - self.camera_y
                    
                    # Draw tile with slight padding for better visibility
                    padding = 1
                    pygame.draw.rect(self.surface, color, 
                                   (screen_x + padding, screen_y + padding, 
                                    self.tile_size - padding*2, self.tile_size - padding*2))
                    
                    # Draw grid lines if enabled
                    if show_grid:
                        pygame.draw.rect(self.surface, UI_COLORS['grid'],
                                       (screen_x, screen_y, self.tile_size, self.tile_size), 1)
        
        # Draw room boundaries with stronger visibility
        for room in tilemap.rooms.values():
            screen_x = room.x * self.tile_size - self.camera_x
            screen_y = room.y * self.tile_size - self.camera_y
            width = room.width * self.tile_size
            height = room.height * self.tile_size
            
            # Draw outer glow
            pygame.draw.rect(self.surface, (*THEME_COLORS[self.theme]['glow'], 60),
                           (screen_x-1, screen_y-1, width+2, height+2), 2)
            # Draw inner line
            pygame.draw.rect(self.surface, THEME_COLORS[self.theme]['accent'],
                           (screen_x, screen_y, width, height), 1)
        
        # Draw room highlight with increased visibility
        if self.selected_room:
            # Update highlight alpha
            if self.highlight_increasing:
                self.highlight_alpha = min(160, self.highlight_alpha + 4)  # Increased max alpha
                if self.highlight_alpha >= 160:
                    self.highlight_increasing = False
            else:
                self.highlight_alpha = max(60, self.highlight_alpha - 4)  # Increased min alpha
                if self.highlight_alpha <= 60:
                    self.highlight_increasing = True
            
            # Draw highlight
            highlight = pygame.Surface((self.selected_room.width * self.tile_size,
                                     self.selected_room.height * self.tile_size),
                                    pygame.SRCALPHA)
            highlight.fill((*THEME_COLORS[self.theme]['accent'], self.highlight_alpha))
            
            screen_x = self.selected_room.x * self.tile_size - self.camera_x
            screen_y = self.selected_room.y * self.tile_size - self.camera_y
            self.surface.blit(highlight, (screen_x, screen_y))
        
        # Apply scanlines with reduced intensity
        if self.scanlines:
            self.surface.blit(self.scanlines, (0, 0), special_flags=pygame.BLEND_MULT)


class MinimapRenderer:
    """Renders a minimap with enhanced visual style."""
    
    def __init__(self, width: int, height: int, scale: float = 0.2):
        self.width = width
        self.height = height
        self.scale = scale
        self.theme = 'residential'
        self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Initialize colors
        self._init_colors()
        
        # Create grid overlay
        self.grid = pygame.Surface((width, height), pygame.SRCALPHA)
        self._create_grid()
    
    def _init_colors(self) -> None:
        """Initialize color mappings."""
        self.colors = {
            TileType.EMPTY: (*BLACK, 255),
            TileType.FLOOR: (*THEME_COLORS[self.theme]['floor'], 255),
            TileType.WALL: (*THEME_COLORS[self.theme]['wall'], 255),
            TileType.DOOR: (*FEATURE_COLORS['door'], 255),
            TileType.DOORS: (*FEATURE_COLORS['door'], 255)
        }
    
    def _create_grid(self) -> None:
        """Create a grid overlay."""
        grid_color = (*GRAY, 30)
        grid_spacing = max(1, int(10 * self.scale))
        
        for x in range(0, self.width, grid_spacing):
            pygame.draw.line(self.grid, grid_color, (x, 0), (x, self.height))
        for y in range(0, self.height, grid_spacing):
            pygame.draw.line(self.grid, grid_color, (0, y), (self.width, y))
    
    def set_theme(self, theme: str) -> None:
        """Set the current theme."""
        self.theme = theme
        self._init_colors()
    
    def render(self, tilemap: TileMap) -> None:
        """Render the minimap with visual effects."""
        # Clear surface
        self.surface.fill((*BLACK, 255))
        
        # Calculate scale factors
        scale_x = self.width / (tilemap.width * 32)
        scale_y = self.height / (tilemap.height * 32)
        scale = min(scale_x, scale_y)
        
        # Draw tiles
        for y in range(tilemap.height):
            for x in range(tilemap.width):
                tile_type = tilemap.get_tile(x, y)
                if tile_type is not None:
                    color = self.colors.get(tile_type, (*BLACK, 255))
                    pygame.draw.rect(self.surface, color,
                                   (x * scale, y * scale,
                                    max(1, scale), max(1, scale)))
        
        # Apply grid overlay
        self.surface.blit(self.grid, (0, 0))
