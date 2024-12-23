"""Rendering system for the megastructure visualization."""
import pygame
import numpy as np
from typing import Dict, Tuple, Optional, List
from ..world.tilemap import TileMap, TileType, Room
from .colors import *
from .effects import GlowManager, create_scanline_effect, create_noise_texture, TerminalEffect


class MapRenderer:
    """Renderer for the main map view."""
    
    def __init__(self, width: int, height: int, tile_size: int = 32, theme: str = 'residential'):
        """Initialize the map renderer."""
        self.width = width
        self.height = height
        self.base_tile_size = tile_size
        self.tile_size = tile_size
        self.theme = theme
        self.camera_x = 0
        self.camera_y = 0
        self.zoom_level = 1.0
        self.surface = pygame.Surface((width, height))
        self.grid_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._init_colors()
    
    def _init_colors(self):
        """Initialize color mappings."""
        self.colors = {
            TileType.EMPTY: BLACK,
            TileType.FLOOR: THEME_COLORS[self.theme]['floor'],
            TileType.WALL: THEME_COLORS[self.theme]['wall'],
            TileType.DOOR: FEATURE_COLORS['door'],
            TileType.TERMINAL: FEATURE_COLORS['terminal'],
            TileType.CONTAINER: FEATURE_COLORS['container'],
            TileType.MACHINE: FEATURE_COLORS['machine'],
            TileType.PILLAR: DARK_GRAY,
            TileType.LIGHT: FEATURE_COLORS['terminal']
        }
    
    def set_theme(self, theme: str):
        """Set the current theme."""
        self.theme = theme
        self._init_colors()
    
    def set_zoom(self, zoom_level: float):
        """Set the zoom level."""
        self.zoom_level = max(0.25, min(4.0, zoom_level))
        self.tile_size = int(self.base_tile_size * self.zoom_level)
    
    def get_viewport_rect(self) -> pygame.Rect:
        """Get the current viewport rectangle in tile coordinates."""
        tiles_x = self.width / self.tile_size
        tiles_y = self.height / self.tile_size
        return pygame.Rect(
            self.camera_x / self.tile_size,
            self.camera_y / self.tile_size,
            tiles_x,
            tiles_y
        )
    
    def render(self, tilemap, show_grid: bool = True, show_features: bool = True, show_spacing: bool = False) -> pygame.Surface:
        """Render the map view with enhanced features."""
        self.surface.fill(BLACK)
        
        if not tilemap:
            return self.surface
        
        # Calculate visible range
        start_x = max(0, int(self.camera_x / self.tile_size))
        start_y = max(0, int(self.camera_y / self.tile_size))
        end_x = min(tilemap.width, int((self.camera_x + self.width) / self.tile_size) + 1)
        end_y = min(tilemap.height, int((self.camera_y + self.height) / self.tile_size) + 1)
        
        # Draw spacing grid if enabled
        if show_spacing:
            spacing_color = (50, 50, 50)  # Dark gray
            for x in range(start_x, end_x):
                for y in range(start_y, end_y):
                    screen_x = x * self.tile_size - self.camera_x
                    screen_y = y * self.tile_size - self.camera_y
                    pygame.draw.rect(self.surface, spacing_color, 
                                  pygame.Rect(screen_x, screen_y, self.tile_size, self.tile_size), 1)
        
        # Draw base tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = tilemap.get_tile(x, y)
                if tile != TileType.EMPTY:
                    screen_x = x * self.tile_size - self.camera_x
                    screen_y = y * self.tile_size - self.camera_y
                    rect = pygame.Rect(screen_x, screen_y, self.tile_size, self.tile_size)
                    
                    # Draw base tile
                    pygame.draw.rect(self.surface, self.colors[tile], rect)
                    
                    # Draw feature decorations if enabled
                    if show_features:
                        if tile == TileType.PILLAR:
                            # Draw pillar with 3D effect
                            pillar_color = self.colors[tile]
                            highlight = tuple(min(255, c + 50) for c in pillar_color)
                            shadow = tuple(max(0, c - 50) for c in pillar_color)
                            
                            # Draw main pillar
                            smaller_rect = rect.inflate(-4, -4)
                            pygame.draw.rect(self.surface, pillar_color, smaller_rect)
                            
                            # Draw highlights
                            pygame.draw.line(self.surface, highlight, smaller_rect.topleft, smaller_rect.topright)
                            pygame.draw.line(self.surface, highlight, smaller_rect.topleft, smaller_rect.bottomleft)
                            
                            # Draw shadows
                            pygame.draw.line(self.surface, shadow, smaller_rect.bottomright, smaller_rect.topright)
                            pygame.draw.line(self.surface, shadow, smaller_rect.bottomright, smaller_rect.bottomleft)
                            
                        elif tile in [TileType.MACHINE, TileType.CONTAINER]:
                            # Draw machines/containers with distinctive patterns
                            feature_color = self.colors[tile]
                            pattern_color = tuple(min(255, c + 30) for c in feature_color)
                            
                            smaller_rect = rect.inflate(-6, -6)
                            pygame.draw.rect(self.surface, feature_color, smaller_rect)
                            
                            if tile == TileType.MACHINE:
                                # Draw gear pattern for machines
                                center = smaller_rect.center
                                radius = min(smaller_rect.width, smaller_rect.height) // 3
                                pygame.draw.circle(self.surface, pattern_color, center, radius)
                                pygame.draw.circle(self.surface, feature_color, center, radius - 2)
                            else:
                                # Draw container pattern
                                pygame.draw.rect(self.surface, pattern_color, 
                                              smaller_rect.inflate(-4, -smaller_rect.height//2))
                    
                    # Draw tile border
                    if show_grid:
                        pygame.draw.rect(self.surface, DARK_GRAY, rect, 1)
        
        # Draw room borders and connections
        for room in tilemap.rooms.values():
            screen_x = room.x * self.tile_size - self.camera_x
            screen_y = room.y * self.tile_size - self.camera_y
            width = room.width * self.tile_size
            height = room.height * self.tile_size
            rect = pygame.Rect(screen_x, screen_y, width, height)
            
            # Only draw if room is at least partially visible
            if (rect.right > 0 and rect.left < self.width and
                rect.bottom > 0 and rect.top < self.height):
                
                # Draw room border with theme-specific color
                border_color = THEME_COLORS[self.theme]['accent']
                pygame.draw.rect(self.surface, border_color, rect, 2)
                
                # Draw room connections
                if show_features:
                    for connected_room_id in room.connections:
                        if connected_room_id in tilemap.rooms:
                            connected_room = tilemap.rooms[connected_room_id]
                            # Draw line between room centers
                            start_pos = (
                                (room.x + room.width/2) * self.tile_size - self.camera_x,
                                (room.y + room.height/2) * self.tile_size - self.camera_y
                            )
                            end_pos = (
                                (connected_room.x + connected_room.width/2) * self.tile_size - self.camera_x,
                                (connected_room.y + connected_room.height/2) * self.tile_size - self.camera_y
                            )
                            pygame.draw.line(self.surface, border_color, start_pos, end_pos, 1)
        
        return self.surface


class MinimapRenderer:
    """Renderer for the minimap view."""
    
    def __init__(self, width: int, height: int):
        """Initialize the minimap renderer."""
        self.width = width
        self.height = height
        self.surface = pygame.Surface((width, height))
        self.tile_colors = {
            TileType.EMPTY: BLACK,
            TileType.FLOOR: LIGHT_GRAY,
            TileType.WALL: DARK_GRAY,
            TileType.DOOR: NEON_BLUE,
            TileType.TERMINAL: NEON_GREEN,
            TileType.CONTAINER: NEON_YELLOW,
            TileType.MACHINE: NEON_RED,
            TileType.PILLAR: NEON_MAGENTA,
            TileType.LIGHT: NEON_CYAN
        }
    
    def render(self, tilemap) -> pygame.Surface:
        """Render the minimap view."""
        self.surface.fill(BLACK)
        
        if not tilemap:
            return self.surface
        
        # Calculate scale to fit the map in the minimap
        scale_x = self.width / tilemap.width
        scale_y = self.height / tilemap.height
        scale = min(scale_x, scale_y)
        
        # Calculate offset to center the map
        offset_x = (self.width - tilemap.width * scale) / 2
        offset_y = (self.height - tilemap.height * scale) / 2
        
        # Draw tiles
        for y in range(tilemap.height):
            for x in range(tilemap.width):
                tile = tilemap.get_tile(x, y)
                if tile != TileType.EMPTY:
                    rect = pygame.Rect(
                        offset_x + x * scale,
                        offset_y + y * scale,
                        max(1, scale),
                        max(1, scale)
                    )
                    pygame.draw.rect(self.surface, self.tile_colors[tile], rect)
        
        return self.surface
