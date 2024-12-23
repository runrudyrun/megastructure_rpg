"""Main game loop and initialization."""
import time
import curses
import logging
from typing import Optional, Tuple
from .game_state import GameStateManager, GameState
from .quest_system import QuestManager, create_main_quest_line
from ..engine.ecs.entity import Entity
from ..engine.ecs.component import Position, Input, Health
from ..engine.rendering.renderer import Renderer

logging.basicConfig(filename='game.log', level=logging.INFO)
logger = logging.getLogger(__name__)

class Game:
    """Main game class."""
    
    def __init__(self, screen_width: int = 80, screen_height: int = 24):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.running = False
        self.target_fps = 60
        self.frame_time = 1.0 / self.target_fps
        
        # Core systems
        self.state_manager = GameStateManager(
            world_width=1000.0,
            world_height=1000.0
        )
        self.quest_manager = QuestManager()
        self.renderer: Optional[Renderer] = None
        
        # Initialize main quest line
        for quest in create_main_quest_line():
            self.quest_manager.add_quest(quest)
            
    def initialize(self, stdscr) -> None:
        """Initialize game systems."""
        # Set up curses
        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(0)
        stdscr.nodelay(1)
        
        # Initialize renderer
        self.renderer = Renderer(stdscr, self.screen_width, self.screen_height)
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        curses.init_pair(5, curses.COLOR_CYAN, -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
        
    def handle_input(self, key: int) -> None:
        """Handle keyboard input."""
        if self.state_manager.current_state == GameState.MAIN_MENU:
            self._handle_menu_input(key)
        elif self.state_manager.current_state == GameState.PLAYING:
            self._handle_game_input(key)
        elif self.state_manager.current_state == GameState.INVENTORY:
            self._handle_inventory_input(key)
        elif self.state_manager.current_state == GameState.CHARACTER:
            self._handle_character_input(key)
            
    def _handle_menu_input(self, key: int) -> None:
        """Handle input in the main menu."""
        if key == ord('n'):  # New Game
            self.state_manager.initialize_new_game()
            self.quest_manager.start_quest("main_01_awakening")
        elif key == ord('l'):  # Load Game
            # TODO: Implement load game
            pass
        elif key == ord('q'):  # Quit
            self.running = False
            
    def _handle_game_input(self, key: int) -> None:
        """Handle input during gameplay."""
        if not self.state_manager.player:
            return
            
        player = self.state_manager.player.entity
        pos = player.get_component(Position)
        if not pos:
            return
            
        # Movement
        move_delta = {
            ord('h'): (-1, 0),  # Left
            ord('l'): (1, 0),   # Right
            ord('j'): (0, 1),   # Down
            ord('k'): (0, -1),  # Up
            ord('y'): (-1, -1), # Up-left
            ord('u'): (1, -1),  # Up-right
            ord('b'): (-1, 1),  # Down-left
            ord('n'): (1, 1)    # Down-right
        }.get(key, (0, 0))
        
        if move_delta != (0, 0):
            new_x = int(pos.x + move_delta[0])
            new_y = int(pos.y + move_delta[1])
            
            if self.state_manager.collision_system.move_entity(
                player, new_x, new_y
            ):
                pos.x = float(new_x)
                pos.y = float(new_y)
                
        # Other actions
        elif key == ord('i'):  # Inventory
            self.state_manager.change_state(GameState.INVENTORY)
        elif key == ord('c'):  # Character
            self.state_manager.change_state(GameState.CHARACTER)
        elif key == ord('q'):  # Quit to menu
            self.state_manager.change_state(GameState.MAIN_MENU)
            
    def _handle_inventory_input(self, key: int) -> None:
        """Handle input in the inventory screen."""
        if key == ord('i') or key == ord('escape'):
            self.state_manager.revert_state()
            
    def _handle_character_input(self, key: int) -> None:
        """Handle input in the character screen."""
        if key == ord('c') or key == ord('escape'):
            self.state_manager.revert_state()
            
    def render(self) -> None:
        """Render the current game state."""
        self.renderer.clear()
        
        if self.state_manager.current_state == GameState.MAIN_MENU:
            self._render_main_menu()
        elif self.state_manager.current_state == GameState.PLAYING:
            self._render_game()
        elif self.state_manager.current_state == GameState.INVENTORY:
            self._render_inventory()
        elif self.state_manager.current_state == GameState.CHARACTER:
            self._render_character()
            
        self.renderer.refresh()
        
    def _render_main_menu(self) -> None:
        """Render the main menu."""
        title = "MEGASTRUCTURE RPG"
        self.renderer.draw_text(
            self.screen_width // 2 - len(title) // 2,
            self.screen_height // 3,
            title,
            curses.color_pair(6)
        )
        
        options = [
            "(N) New Game",
            "(L) Load Game",
            "(Q) Quit"
        ]
        
        for i, option in enumerate(options):
            self.renderer.draw_text(
                self.screen_width // 2 - len(option) // 2,
                self.screen_height // 2 + i * 2,
                option,
                curses.color_pair(1)
            )
            
    def _render_game(self) -> None:
        """Render the game world."""
        if not self.state_manager.player:
            return
            
        # Render map
        current_sector = self.state_manager.world_generator.get_sector(
            *self.state_manager.current_sector
        )
        self.renderer.render_map(current_sector.tilemap)
        
        # Render entities
        player_pos = self.state_manager.player.entity.get_component(Position)
        if player_pos:
            self.renderer.draw_char(
                int(player_pos.x),
                int(player_pos.y),
                '@',
                curses.color_pair(2)
            )
            
        # Render UI
        self._render_hud()
        
    def _render_inventory(self) -> None:
        """Render the inventory screen."""
        if not self.state_manager.player:
            return
            
        inventory = self.state_manager.player.entity.get_component(Input)
        if not inventory:
            return
            
        self.renderer.draw_text(
            2, 1, "Inventory", curses.color_pair(3)
        )
        # TODO: Render inventory items
        
    def _render_character(self) -> None:
        """Render the character screen."""
        if not self.state_manager.player:
            return
            
        player = self.state_manager.player
        self.renderer.draw_text(
            2, 1, f"Character Level {player.level}", curses.color_pair(3)
        )
        
        health = player.entity.get_component(Health)
        if health:
            self.renderer.draw_text(
                2, 3, f"HP: {health.current}/{health.max}",
                curses.color_pair(1)
            )
            
        self.renderer.draw_text(
            2, 4, f"XP: {player.experience}",
            curses.color_pair(1)
        )
        self.renderer.draw_text(
            2, 5, f"Skill Points: {player.skill_points}",
            curses.color_pair(1)
        )
        
    def _render_hud(self) -> None:
        """Render the heads-up display."""
        if not self.state_manager.player:
            return
            
        player = self.state_manager.player
        health = player.entity.get_component(Health)
        
        # Status bar
        status_text = f"Level: {player.level} "
        if health:
            status_text += f"HP: {health.current}/{health.max} "
        status_text += f"XP: {player.experience}"
        
        self.renderer.draw_text(
            0, self.screen_height - 1, status_text,
            curses.color_pair(1)
        )
        
    def run(self, stdscr) -> None:
        """Main game loop."""
        self.initialize(stdscr)
        self.running = True
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            dt = current_time - last_time
            
            # Handle input
            key = stdscr.getch()
            if key != -1:
                self.handle_input(key)
                
            # Update game state
            self.state_manager.update(dt)
            
            # Render
            self.render()
            
            # Cap frame rate
            frame_end = time.time()
            frame_duration = frame_end - current_time
            if frame_duration < self.frame_time:
                time.sleep(self.frame_time - frame_duration)
                
            last_time = current_time

def main():
    """Entry point for the game."""
    try:
        curses.wrapper(Game().run)
    except Exception as e:
        logger.exception("Game crashed: %s", str(e))
        raise

if __name__ == "__main__":
    main()
