"""Visualization tool for the procedural generation system."""
import pygame
import sys
import logging
import json
from typing import Optional, Tuple, Dict
import os
from datetime import datetime

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
    from engine.rendering.colors import UI_COLORS, THEME_COLORS, BLACK, WHITE, NEON_GREEN, RED
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
            self.screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF | pygame.HWSURFACE)
            pygame.display.set_caption("Megastructure Generator Visualizer")
            
            # Initialize fonts
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 32)
            
            # Initialize components
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            self.config = ConfigManager(data_dir)
            self.generator = MegastructureGenerator(self.config)
            
            # Initialize renderers
            self.tile_size = 32
            self.zoom_level = 1.0
            self.map_renderer = MapRenderer(width - 200, height, tile_size=self.tile_size, theme='industrial')
            self.minimap_renderer = MinimapRenderer(180, 180)
            
            # Cache UI elements
            self._init_ui_cache()
            
            # UI state
            self.selected_room = None
            self.current_theme = 'industrial'
            self.camera_speed = 5
            self.running = True
            self.fps_clock = pygame.time.Clock()
            self.fps = 60
            self.error_message = None
            self.error_timer = 0
            
            # Debug flags
            self.show_debug = False
            self.show_grid = True
            self.show_features = True
            self.show_spacing = False
            
            # Room spatial index
            self.room_grid = {}
            self.grid_cell_size = 10
            
            # Generation parameters
            self.gen_params = {
                'min_rooms': 10,
                'max_rooms': 20,
                'corridor_ratio': 0.4
            }
            
            # Theme features
            self.theme_features = {}
            
            # Generate initial map
            self.regenerate_map()
            
            logger.info("Initialization complete")
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            pygame.quit()
            raise

    def _init_ui_cache(self):
        """Initialize cached UI elements."""
        self.cached_controls = []
        controls = [
            "Controls:",
            "SPACE - New Map",
            "1-3 - Change Theme",
            "Arrows - Move Camera",
            "+/- - Zoom",
            "G - Toggle Grid",
            "F3 - Debug Info",
            "F - Toggle Features",
            "R - Toggle Spacing",
            "S - Save Layout",
            "Click - Select Room",
            "ESC - Exit"
        ]
        
        for text in controls:
            self.cached_controls.append(self.font.render(text, True, WHITE))

    def _update_room_spatial_index(self):
        """Update spatial index for room lookup."""
        self.room_grid.clear()
        if not self.tilemap or not self.tilemap.rooms:
            return
            
        for room in self.tilemap.rooms.values():
            grid_x1 = room.x // self.grid_cell_size
            grid_y1 = room.y // self.grid_cell_size
            grid_x2 = (room.x + room.width) // self.grid_cell_size
            grid_y2 = (room.y + room.height) // self.grid_cell_size
            
            for gx in range(grid_x1, grid_x2 + 1):
                for gy in range(grid_y1, grid_y2 + 1):
                    key = (gx, gy)
                    if key not in self.room_grid:
                        self.room_grid[key] = []
                    self.room_grid[key].append(room)

    def save_layout(self):
        """Save current layout to file."""
        if not self.tilemap:
            self.show_error("No layout to save")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"layout_{self.current_theme}_{timestamp}.json"
        
        try:
            layout_data = {
                'theme': self.current_theme,
                'rooms': [
                    {
                        'id': room_id,
                        'type': room.type,
                        'x': room.x,
                        'y': room.y,
                        'width': room.width,
                        'height': room.height,
                        'connections': list(room.connections)
                    }
                    for room_id, room in self.tilemap.rooms.items()
                ]
            }
            
            with open(filename, 'w') as f:
                json.dump(layout_data, f, indent=2)
            
            self.show_error(f"Layout saved to {filename}", color=NEON_GREEN)
        except Exception as e:
            logger.error(f"Error saving layout: {e}")
            self.show_error("Failed to save layout")

    def show_error(self, message: str, duration: int = 3000, color: Tuple[int, int, int] = RED):
        """Show error message for specified duration."""
        self.error_message = self.font.render(message, True, color)
        self.error_timer = duration

    def regenerate_map(self):
        """Generate a new map with error handling."""
        try:
            # Update generation parameters based on current state
            min_rooms = self.gen_params.get('min_rooms', 10)
            max_rooms = self.gen_params.get('max_rooms', 20)
            corridor_ratio = self.gen_params.get('corridor_ratio', 0.4)
            
            logger.debug(f"Generating map with params: min_rooms={min_rooms}, max_rooms={max_rooms}, corridor_ratio={corridor_ratio}")
            
            self.tilemap = self.generator.generate_sector(
                width=30,
                height=24,
                theme=self.current_theme,
                min_rooms=min_rooms,
                max_rooms=max_rooms,
                corridor_ratio=corridor_ratio
            )
            
            if not self.tilemap:
                self.show_error("Failed to generate tilemap")
                return
                
            if not self.tilemap.rooms:
                self.show_error("Generated tilemap has no rooms")
                return
            
            self._update_room_spatial_index()
            self.selected_room = None
            self.map_renderer.camera_x = 0
            self.map_renderer.camera_y = 0
            self.map_renderer.set_theme(self.current_theme)
            
            logger.info(f"Generated map with {len(self.tilemap.rooms)} rooms")
        except Exception as e:
            logger.error(f"Error generating map: {e}")
            self.show_error(str(e))

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
                elif event.key == pygame.K_f:
                    self.show_features = not self.show_features
                elif event.key == pygame.K_r:
                    self.show_spacing = not self.show_spacing
                elif event.key == pygame.K_s:
                    self.save_layout()
                elif event.key == pygame.K_PLUS or event.key == pygame.K_KP_PLUS:
                    self.zoom_level = min(2.0, self.zoom_level + 0.1)
                    self.map_renderer.tile_size = int(self.tile_size * self.zoom_level)
                elif event.key == pygame.K_MINUS or event.key == pygame.K_KP_MINUS:
                    self.zoom_level = max(0.5, self.zoom_level - 0.1)
                    self.map_renderer.tile_size = int(self.tile_size * self.zoom_level)
                elif event.key in [pygame.K_1, pygame.K_2, pygame.K_3]:
                    themes = ['residential', 'industrial', 'research']
                    theme_idx = event.key - pygame.K_1
                    if theme_idx < len(themes):
                        self.current_theme = themes[theme_idx]
                        self.theme_features = self.config.rules.get('themes', {}).get(self.current_theme, {})
                        self.regenerate_map()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self._handle_click(event.pos)
                elif event.button == 4:  # Mouse wheel up
                    self.zoom_level = min(2.0, self.zoom_level + 0.1)
                    self.map_renderer.tile_size = int(self.tile_size * self.zoom_level)
                elif event.button == 5:  # Mouse wheel down
                    self.zoom_level = max(0.5, self.zoom_level - 0.1)
                    self.map_renderer.tile_size = int(self.tile_size * self.zoom_level)
        
        # Handle continuous keyboard input
        keys = pygame.key.get_pressed()
        dt = self.fps_clock.get_time() / 1000.0
        
        speed = self.camera_speed * (2.0 if keys[pygame.K_LSHIFT] else 1.0)
        
        if keys[pygame.K_LEFT]:
            self.map_renderer.camera_x -= int(speed * dt * 60)
        if keys[pygame.K_RIGHT]:
            self.map_renderer.camera_x += int(speed * dt * 60)
        if keys[pygame.K_UP]:
            self.map_renderer.camera_y -= int(speed * dt * 60)
        if keys[pygame.K_DOWN]:
            self.map_renderer.camera_y += int(speed * dt * 60)

    def _handle_click(self, pos):
        """Handle mouse clicks with spatial indexing."""
        if not self.tilemap or pos[0] >= self.width - 200:
            return
            
        tile_x = (pos[0] + self.map_renderer.camera_x) // self.map_renderer.tile_size
        tile_y = (pos[1] + self.map_renderer.camera_y) // self.map_renderer.tile_size
        
        # Get grid cell
        grid_x = tile_x // self.grid_cell_size
        grid_y = tile_y // self.grid_cell_size
        
        # Check rooms in this and adjacent cells
        checked_rooms = set()
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                key = (grid_x + dx, grid_y + dy)
                if key in self.room_grid:
                    for room in self.room_grid[key]:
                        if room not in checked_rooms:
                            checked_rooms.add(room)
                            if (room.x <= tile_x < room.x + room.width and
                                room.y <= tile_y < room.y + room.height):
                                self.selected_room = room
                                logger.debug(f"Selected room: {room.type} at ({room.x}, {room.y})")
                                return
        
        self.selected_room = None

    def _render_ui_panel(self):
        """Render the UI panel with caching."""
        # Draw panel background
        panel_rect = pygame.Rect(self.width - 200, 0, 200, self.height)
        pygame.draw.rect(self.screen, BLACK, panel_rect)
        pygame.draw.line(self.screen, WHITE, (self.width - 200, 0), (self.width - 200, self.height))
        
        # Draw title
        title = self.title_font.render("Megastructure", True, WHITE)
        self.screen.blit(title, (self.width - 190, 10))
        
        # Draw theme and features
        theme_text = self.font.render(f"Theme: {self.current_theme}", True, WHITE)
        self.screen.blit(theme_text, (self.width - 190, 50))
        
        # Draw theme features
        y = 80
        if self.theme_features:
            features = self.theme_features.get('features', {})
            for key, value in features.items():
                feature_text = self.font.render(f"{key}: {value}", True, WHITE)
                self.screen.blit(feature_text, (self.width - 190, y))
                y += 20
        
        # Draw generation parameters
        y = max(y + 20, 140)
        params_text = [
            f"Min Rooms: {self.gen_params['min_rooms']}",
            f"Max Rooms: {self.gen_params['max_rooms']}",
            f"Corridor Ratio: {self.gen_params['corridor_ratio']:.1f}"
        ]
        for text in params_text:
            text_surface = self.font.render(text, True, WHITE)
            self.screen.blit(text_surface, (self.width - 190, y))
            y += 25
        
        # Draw controls
        y = max(y + 20, 250)
        for control in self.cached_controls:
            self.screen.blit(control, (self.width - 190, y))
            y += 25
        
        # Draw selected room info
        if self.selected_room:
            y = max(y + 20, 450)
            room_info = [
                f"Room ID: {self.selected_room.id}",
                f"Type: {self.selected_room.type}",
                f"Size: {self.selected_room.width}x{self.selected_room.height}",
                f"Pos: ({self.selected_room.x}, {self.selected_room.y})",
                f"Connections: {len(self.selected_room.connections)}"
            ]
            
            # Add feature counts
            if self.tilemap:
                feature_counts = self._count_room_features(self.selected_room)
                if feature_counts:
                    room_info.extend([
                        f"Pillars: {feature_counts.get('pillars', 0)}",
                        f"Machines: {feature_counts.get('machines', 0)}",
                        f"Containers: {feature_counts.get('containers', 0)}"
                    ])
            
            for info in room_info:
                text = self.font.render(info, True, WHITE)
                self.screen.blit(text, (self.width - 190, y))
                y += 25
        
        # Draw minimap
        if self.tilemap:
            minimap_surface = self.minimap_renderer.render(self.tilemap)
            self.screen.blit(minimap_surface, (self.width - 190, self.height - 190))

    def _count_room_features(self, room: Room) -> Dict[str, int]:
        """Count features in a room."""
        if not self.tilemap:
            return {}
            
        counts = {'pillars': 0, 'machines': 0, 'containers': 0}
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                tile = self.tilemap.get_tile(x, y)
                if tile == TileType.PILLAR:
                    counts['pillars'] += 1
                elif tile == TileType.MACHINE:
                    counts['machines'] += 1
                elif tile == TileType.CONTAINER:
                    counts['containers'] += 1
        return counts

    def run(self):
        """Main loop with proper error handling and cleanup."""
        try:
            while self.running:
                # Handle input
                self.handle_input()
                
                # Clear screen
                self.screen.fill((10, 12, 15))
                
                # Render map if available
                if self.tilemap and hasattr(self.tilemap, 'tiles') and self.tilemap.tiles is not None:
                    try:
                        self.map_renderer.render(self.tilemap, show_grid=self.show_grid, show_features=self.show_features, show_spacing=self.show_spacing)
                        self.screen.blit(self.map_renderer.surface, (0, 0))
                    except Exception as e:
                        logger.error(f"Error rendering map: {e}")
                        self.show_error(f"Render error: {str(e)}")
                else:
                    # Draw error message
                    error_text = self.font.render("No map available - Press SPACE to generate", True, WHITE)
                    self.screen.blit(error_text, (10, 10))
                
                # Render UI
                self._render_ui_panel()
                
                # Update display
                pygame.display.flip()
                self.fps_clock.tick(self.fps)
                
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}")
            self.show_error(f"Fatal error: {str(e)}")
        finally:
            pygame.quit()

if __name__ == "__main__":
    try:
        visualizer = GenerationVisualizer()
        visualizer.run()
    except Exception as e:
        logger.error(f"Failed to start visualizer: {e}")
        sys.exit(1)
