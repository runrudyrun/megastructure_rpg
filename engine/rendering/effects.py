"""Visual effects for the rendering system."""
import pygame
import math
from typing import Tuple, Optional, List
import numpy as np

def create_glow_surface(color: Tuple[int, ...], size: int) -> pygame.Surface:
    """Create a circular glow effect surface."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    
    for x in range(size):
        for y in range(size):
            # Calculate distance from center
            distance = math.sqrt((x - center) ** 2 + (y - center) ** 2)
            
            # Calculate alpha based on distance
            alpha = int(max(0, 255 * (1 - distance / center)))
            
            # Set pixel color with calculated alpha
            if len(color) == 3:
                surface.set_at((x, y), (*color, alpha))
            else:
                surface.set_at((x, y), (*color[:3], min(color[3], alpha)))
    
    return surface

def create_scanline_effect(width: int, height: int, spacing: int = 2) -> pygame.Surface:
    """Create a scanline effect surface."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, spacing):
        pygame.draw.line(surface, (0, 0, 0, 50), (0, y), (width, y))
    return surface

def create_noise_texture(width: int, height: int, alpha: int = 20) -> pygame.Surface:
    """Create a noise texture for visual effect."""
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    noise = np.random.randint(0, 255, (height, width), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            value = noise[y, x]
            surface.set_at((x, y), (value, value, value, alpha))
    
    return surface

class GlowManager:
    """Manages glow effects for different features."""
    
    def __init__(self):
        self.glow_surfaces = {}
        self._init_glow_surfaces()
    
    def _init_glow_surfaces(self):
        """Initialize glow surfaces for different features."""
        from .colors import FEATURE_COLORS
        
        sizes = {
            'light': 64,
            'terminal': 32,
            'machine': 48,
            'door': 32,
            'window': 32,
            'container': 32,
            'pillar': 24,
        }
        
        for feature, size in sizes.items():
            glow_color = FEATURE_COLORS.get(f'{feature}_glow')
            if glow_color:
                self.glow_surfaces[feature] = create_glow_surface(glow_color, size)
    
    def get_glow(self, feature: str) -> Optional[pygame.Surface]:
        """Get the glow surface for a feature."""
        return self.glow_surfaces.get(feature.lower())

class TerminalEffect:
    """Creates a terminal-style text effect."""
    
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self.chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"
        self.char_surfaces = {}
        self._init_char_surfaces()
    
    def _init_char_surfaces(self):
        """Pre-render character surfaces."""
        for char in self.chars:
            self.char_surfaces[char] = self.font.render(char, True, (200, 200, 255))
    
    def render_text(self, text: str, reveal_chars: int) -> List[pygame.Surface]:
        """Render text with a terminal effect."""
        surfaces = []
        for i, char in enumerate(text):
            if i < reveal_chars and char in self.char_surfaces:
                surfaces.append(self.char_surfaces[char])
            elif char.isspace():
                surfaces.append(self.font.render(" ", True, (200, 200, 255)))
            else:
                # Random character for unrevealed text
                rand_char = np.random.choice(list(self.chars))
                surfaces.append(self.font.render(rand_char, True, (100, 100, 140)))
        return surfaces
