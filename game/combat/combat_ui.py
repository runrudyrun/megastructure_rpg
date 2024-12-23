"""Combat user interface and visualization."""
from typing import List, Optional, Tuple
import curses
from ...engine.ecs.entity import Entity
from ...engine.ecs.component import Health, Stats, Position
from .combat_system import CombatSystem, CombatAction, StatusEffect, DamageInstance
from .abilities import Ability, AbilityManager

class CombatUI:
    """Handles combat visualization and user interaction."""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.combat_log: List[str] = []
        self.max_log_lines = 5
        self.selected_action_index = 0
        self.selected_target_index = 0
        self.show_ability_details = False
        
    def render_combat(self, stdscr, combat_system: CombatSystem,
                     ability_manager: AbilityManager) -> None:
        """Render the combat scene."""
        stdscr.clear()
        
        # Render combat area (2/3 of screen)
        combat_height = int(self.screen_height * 2/3)
        self._render_combat_area(stdscr, combat_system, combat_height)
        
        # Render UI area (1/3 of screen)
        ui_start = combat_height
        self._render_ui_area(stdscr, combat_system, ability_manager, ui_start)
        
        # Render combat log
        self._render_combat_log(stdscr)
        
        stdscr.refresh()
        
    def _render_combat_area(self, stdscr, combat_system: CombatSystem,
                           combat_height: int) -> None:
        """Render the main combat area."""
        # Draw border
        for y in range(combat_height):
            stdscr.addch(y, 0, '|')
            stdscr.addch(y, self.screen_width-1, '|')
        for x in range(self.screen_width):
            stdscr.addch(0, x, '-')
            stdscr.addch(combat_height-1, x, '-')
            
        # Render entities
        for entity in combat_system.turn_order:
            pos = entity.get_component(Position)
            if not pos:
                continue
                
            x = int(pos.x)
            y = int(pos.y)
            
            if 0 <= x < self.screen_width and 0 <= y < combat_height:
                # Determine symbol and color
                symbol = '@' if entity == combat_system.turn_order[0] else 'E'
                color = (curses.color_pair(2) if entity == combat_system.turn_order[0]
                        else curses.color_pair(4))
                
                # Add health bar
                health = entity.get_component(Health)
                if health:
                    health_percent = health.current / health.max
                    bar_width = 10
                    filled = int(health_percent * bar_width)
                    health_bar = f"[{'=' * filled}{' ' * (bar_width - filled)}]"
                    stdscr.addstr(y-1, x-len(health_bar)//2, health_bar,
                                curses.color_pair(1))
                    
                # Add status effects
                if entity.id in combat_system.status_effects:
                    effects = combat_system.status_effects[entity.id]
                    effect_str = ' '.join(e.type.name[0] for e in effects)
                    stdscr.addstr(y+1, x-len(effect_str)//2, effect_str,
                                curses.color_pair(3))
                    
                # Draw entity
                stdscr.addch(y, x, symbol, color)
                
    def _render_ui_area(self, stdscr, combat_system: CombatSystem,
                       ability_manager: AbilityManager, start_y: int) -> None:
        """Render the UI area with actions and status."""
        current_entity = combat_system.turn_order[combat_system.current_turn_index]
        
        # Show current turn
        turn_text = f"Current Turn: {'Player' if combat_system.current_turn_index == 0 else 'Enemy'}"
        stdscr.addstr(start_y + 1, 2, turn_text, curses.color_pair(6))
        
        # Show available actions
        actions = combat_system.get_available_actions(current_entity)
        if current_entity == combat_system.turn_order[0]:  # Player's turn
            stdscr.addstr(start_y + 3, 2, "Available Actions:", curses.color_pair(3))
            for i, action in enumerate(actions):
                color = curses.color_pair(2 if i == self.selected_action_index else 1)
                stdscr.addstr(start_y + 4 + i, 4, f"{i+1}. {action.name}", color)
                
            # Show ability details if requested
            if self.show_ability_details and 0 <= self.selected_action_index < len(actions):
                action = actions[self.selected_action_index]
                details = [
                    f"Damage: {action.damage:.1f}",
                    f"Accuracy: {action.accuracy*100:.0f}%",
                    f"Range: {action.range:.1f}",
                    f"Cooldown: {action.cooldown}"
                ]
                if action.status_effects:
                    effects = ", ".join(f"{effect[0].name}" for effect in action.status_effects)
                    details.append(f"Effects: {effects}")
                    
                for i, detail in enumerate(details):
                    stdscr.addstr(start_y + 4 + i, 40, detail, curses.color_pair(5))
                    
            # Show valid targets if an action is selected
            if 0 <= self.selected_action_index < len(actions):
                action = actions[self.selected_action_index]
                targets = combat_system.get_valid_targets(current_entity, action)
                if targets:
                    stdscr.addstr(start_y + 3, 40, "Valid Targets:", curses.color_pair(3))
                    for i, target in enumerate(targets):
                        color = curses.color_pair(2 if i == self.selected_target_index else 1)
                        health = target.get_component(Health)
                        health_str = f"({health.current}/{health.max})" if health else ""
                        stdscr.addstr(start_y + 4 + i, 42,
                                    f"{i+1}. Enemy {target.id} {health_str}", color)
                        
    def _render_combat_log(self, stdscr) -> None:
        """Render the combat log."""
        log_y = self.screen_height - self.max_log_lines - 1
        stdscr.addstr(log_y, 2, "Combat Log:", curses.color_pair(3))
        
        for i, message in enumerate(self.combat_log[-self.max_log_lines:]):
            stdscr.addstr(log_y + i + 1, 4, message, curses.color_pair(1))
            
    def add_combat_log(self, message: str) -> None:
        """Add a message to the combat log."""
        self.combat_log.append(message)
        if len(self.combat_log) > self.max_log_lines * 2:
            self.combat_log = self.combat_log[-self.max_log_lines:]
            
    def handle_input(self, key: int, combat_system: CombatSystem) -> Optional[Tuple[CombatAction, Entity]]:
        """Handle combat input and return selected action and target."""
        current_entity = combat_system.turn_order[combat_system.current_turn_index]
        
        if current_entity != combat_system.turn_order[0]:
            return None  # Not player's turn
            
        actions = combat_system.get_available_actions(current_entity)
        if not actions:
            return None
            
        if key == ord('j'):  # Down
            self.selected_action_index = (self.selected_action_index + 1) % len(actions)
            self.selected_target_index = 0
        elif key == ord('k'):  # Up
            self.selected_action_index = (self.selected_action_index - 1) % len(actions)
            self.selected_target_index = 0
        elif key == ord('h'):  # Previous target
            targets = combat_system.get_valid_targets(
                current_entity,
                actions[self.selected_action_index]
            )
            if targets:
                self.selected_target_index = (self.selected_target_index - 1) % len(targets)
        elif key == ord('l'):  # Next target
            targets = combat_system.get_valid_targets(
                current_entity,
                actions[self.selected_action_index]
            )
            if targets:
                self.selected_target_index = (self.selected_target_index + 1) % len(targets)
        elif key == ord('i'):  # Toggle ability details
            self.show_ability_details = not self.show_ability_details
        elif key == ord('\n'):  # Enter/Return
            action = actions[self.selected_action_index]
            targets = combat_system.get_valid_targets(current_entity, action)
            if targets and self.selected_target_index < len(targets):
                return action, targets[self.selected_target_index]
                
        return None
        
    def format_damage_message(self, damage: DamageInstance) -> str:
        """Format a damage message for the combat log."""
        source_name = "Player" if damage.source == damage.source == damage.source.id else f"Enemy {damage.source.id}"
        target_name = "Player" if damage.target == damage.target == damage.target.id else f"Enemy {damage.target.id}"
        
        crit_str = " (Critical!)" if damage.is_critical else ""
        return f"{source_name} hits {target_name} for {damage.amount:.1f} damage{crit_str}!"
        
    def format_status_message(self, target: Entity, effect: StatusEffect) -> str:
        """Format a status effect message for the combat log."""
        target_name = "Player" if target.id == 0 else f"Enemy {target.id}"
        return f"{target_name} is affected by {effect.type.name} for {effect.duration} turns!"
