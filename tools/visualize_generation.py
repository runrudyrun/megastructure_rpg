"""Visualization tool for the procedural generation system."""
import pygame
import sys
import logging
from typing import Optional, Tuple
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import engine modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

try:
    from engine.world.generator import MegastructureGenerator
    from engine.world.tilemap import Room, TileType
    from engine.config.config_manager import ConfigManager
    from engine.rendering.renderer import MapRenderer, MinimapRenderer
    from engine.rendering.colors import UI_COLORS, THEME_COLORS, BLACK, WHITE, NEON_GREEN
    logger.info("Successfully imported all required modules")
except Exception as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

class GenerationVisualizer:
    """Interactive visualization tool for the procedural generation system."""
    
    def __init__(self, width: int = 1280, height: int = 720):
        """Initialize the visualizer with the given dimensions."""
        try:
            # Initialize pygame
            pygame.init()
            pygame.font.init()
            
            # Initialize display with double buffering
            self.width = width
            self.height = height
            self.screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF)
            pygame.display.set_caption("Megastructure Generator Visualizer")
            
            # Initialize fonts
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 32)
            
            # Initialize components
            data_dir = os.path.join(parent_dir, "data")
            self.config = ConfigManager(data_dir)
            self.generator = MegastructureGenerator(self.config)
            
            # Initialize renderers with smaller initial size
            self.map_renderer = MapRenderer(width - 200, height, tile_size=32, theme='industrial')  # Leave space for UI panel
            self.minimap_renderer = MinimapRenderer(180, 180)
            
            # UI state
            self.selected_room = None
            self.current_theme = 'industrial'
            self.camera_speed = 5
            self.running = True
            self.fps_clock = pygame.time.Clock()
            self.fps = 60
            
            # Debug flags
            self.show_debug = False
            self.show_grid = True
            
            # Generate initial map with smaller dimensions
            self.regenerate_map()
            
            logger.info("Initialization complete")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            pygame.quit()
            raise

    def regenerate_map(self):
        """Generate a new map with error handling."""
        try:
            # Start with a smaller map size for better performance
            self.tilemap = self.generator.generate_sector(30, 24, self.current_theme)
            if not self.tilemap:
                logger.error("Failed to generate tilemap")
                return
                
            # Verify tilemap has rooms
            if not self.tilemap.rooms:
                logger.error("Generated tilemap has no rooms")
                return
                
            # Debug info
            logger.info(f"Generated map with {len(self.tilemap.rooms)} rooms")
            for room in self.tilemap.rooms.values():
                logger.debug(f"Room: {room.type} at ({room.x}, {room.y}) size {room.width}x{room.height}")
            
            self.selected_room = None
            self.map_renderer.camera_x = 0
            self.map_renderer.camera_y = 0
            self.map_renderer.set_theme(self.current_theme)
            logger.info("Map generation complete")
        except Exception as e:
            logger.error(f"Error generating map: {e}")
            self.tilemap = None

    def handle_input(self):
        """Handle user input with proper event cleanup."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                elif event.key == pygame.K_SPACE:
                    self.regenerate_map()
                elif event.key == pygame.K_F3:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    themes = ['residential', 'industrial', 'research']
                    theme_idx = event.key - pygame.K_1
                    if theme_idx < len(themes):
                        self.current_theme = themes[theme_idx]
                        self.regenerate_map()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self._handle_click(event.pos)
        
        # Handle continuous keyboard input with delta time
        keys = pygame.key.get_pressed()
        dt = self.fps_clock.get_time() / 1000.0  # Convert to seconds
        
        if keys[pygame.K_LEFT]:
            self.map_renderer.camera_x -= int(self.camera_speed * dt * 60)
        if keys[pygame.K_RIGHT]:
            self.map_renderer.camera_x += int(self.camera_speed * dt * 60)
        if keys[pygame.K_UP]:
            self.map_renderer.camera_y -= int(self.camera_speed * dt * 60)
        if keys[pygame.K_DOWN]:
            self.map_renderer.camera_y += int(self.camera_speed * dt * 60)

    def _handle_click(self, pos):
        """Handle mouse clicks with bounds checking."""
        if not self.tilemap or pos[0] >= self.width - 200:
            return
            
        tile_x = (pos[0] + self.map_renderer.camera_x) // self.map_renderer.tile_size
        tile_y = (pos[1] + self.map_renderer.camera_y) // self.map_renderer.tile_size
        
        clicked_room = None
        for room in self.tilemap.rooms.values():
            if (room.x <= tile_x < room.x + room.width and
                room.y <= tile_y < room.y + room.height):
                clicked_room = room
                break
        
        self.selected_room = clicked_room
        if clicked_room:
            logger.debug(f"Selected room: {clicked_room.type} at ({clicked_room.x}, {clicked_room.y})")

    def _render_ui_panel(self):
        """Render the UI panel with performance optimizations."""
        # Create UI panel surface
        panel_surface = pygame.Surface((200, self.height))
        panel_surface.fill(BLACK)
        
        # Draw minimap
        if self.tilemap:
            self.minimap_renderer.render(self.tilemap)
            panel_surface.blit(self.minimap_renderer.surface, (10, 10))
        
        # Draw theme info
        theme_text = self.title_font.render(f"Theme: {self.current_theme.title()}", True, WHITE)
        panel_surface.blit(theme_text, (10, 200))
        
        # Draw controls
        controls = [
            "Controls:",
            "SPACE - New Map",
            "1-3 - Change Theme",
            "Arrows - Move Camera",
            "G - Toggle Grid",
            "F3 - Debug Info",
            "Click - Select Room",
            "ESC - Exit"
        ]
        
        y = 250
        for text in controls:
            text_surface = self.font.render(text, True, WHITE)
            panel_surface.blit(text_surface, (10, y))
            y += 25
        
        # Draw selected room info
        if self.selected_room:
            y = 450
            room_info = [
                f"Room Info:",
                f"Type: {self.selected_room.type}",
                f"Size: {self.selected_room.width}x{self.selected_room.height}",
                f"Pos: ({self.selected_room.x}, {self.selected_room.y})",
                f"Connections: {len(self.selected_room.connections)}"
            ]
            
            for text in room_info:
                text_surface = self.font.render(text, True, NEON_GREEN)
                panel_surface.blit(text_surface, (10, y))
                y += 25
        
        # Draw debug info
        if self.show_debug:
            fps = self.fps_clock.get_fps()
            debug_text = self.font.render(f"FPS: {fps:.1f}", True, WHITE)
            panel_surface.blit(debug_text, (10, self.height - 30))
        
        # Draw panel border
        pygame.draw.line(panel_surface, THEME_COLORS[self.current_theme]['accent'],
                        (0, 0), (0, self.height))
        
        # Blit panel to screen
        self.screen.blit(panel_surface, (self.width - 200, 0))

    def run(self):
        """Main loop with proper error handling and cleanup."""
        try:
            while self.running:
                # Handle input
                self.handle_input()
                
                # Clear screen with background color
                self.screen.fill((10, 12, 15))  # Dark background
                
                # Render map if available
                if self.tilemap and hasattr(self.tilemap, 'tiles') and self.tilemap.tiles is not None:
                    try:
                        self.map_renderer.render(self.tilemap, show_grid=self.show_grid)
                        self.screen.blit(self.map_renderer.surface, (0, 0))
                    except Exception as e:
                        logger.error(f"Error rendering map: {e}")
                        error_text = self.font.render(f"Error rendering map: {str(e)}", True, WHITE)
                        self.screen.blit(error_text, (10, 10))
                else:
                    # Draw error message
                    error_text = self.font.render("No map available - Press SPACE to generate", True, WHITE)
                    self.screen.blit(error_text, (10, 10))
                
                # Render UI
                self._render_ui_panel()
                
                # Update display with vsync
                pygame.display.flip()
                
                # Control frame rate
                self.fps_clock.tick(self.fps)
                
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
        finally:
            pygame.quit()

if __name__ == "__main__":
    try:
        visualizer = GenerationVisualizer()
        visualizer.run()
    except Exception as e:
        logger.error(f"Failed to start visualizer: {e}")
        sys.exit(1)
