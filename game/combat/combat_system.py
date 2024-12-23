"""Combat system for tactical turn-based battles."""
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import random
import math
from ...engine.ecs.entity import Entity
from ...engine.ecs.component import Health, Stats, Position, Collider
from ...engine.physics.spatial_grid import PhysicsGrid

class CombatantType(Enum):
    """Types of combatants."""
    PLAYER = auto()
    ALLY = auto()
    ENEMY = auto()
    NEUTRAL = auto()

class StatusEffectType(Enum):
    """Types of status effects."""
    POISON = auto()
    BURN = auto()
    STUN = auto()
    BLEED = auto()
    WEAK = auto()
    VULNERABLE = auto()
    STRENGTHEN = auto()
    SHIELD = auto()
    REGENERATION = auto()
    HASTE = auto()

@dataclass
class StatusEffect:
    """A status effect that can be applied to combatants."""
    type: StatusEffectType
    duration: int
    magnitude: float
    tick_effect: Optional[float] = None
    
    def tick(self, entity: Entity) -> None:
        """Apply the effect's per-turn effects."""
        if not self.tick_effect:
            return
            
        health = entity.get_component(Health)
        if health:
            if self.type in {StatusEffectType.POISON, StatusEffectType.BURN, StatusEffectType.BLEED}:
                health.current -= self.tick_effect
            elif self.type == StatusEffectType.REGENERATION:
                health.current = min(health.current + self.tick_effect, health.max)

@dataclass
class DamageInstance:
    """A single instance of damage."""
    amount: float
    source: Entity
    target: Entity
    is_critical: bool = False
    penetration: float = 0.0  # Percentage of defense ignored

@dataclass
class CombatAction:
    """An action that can be taken in combat."""
    name: str
    damage: float
    accuracy: float
    critical_chance: float = 0.1
    critical_multiplier: float = 1.5
    range: float = 1.0
    cooldown: int = 0
    current_cooldown: int = 0
    status_effects: List[Tuple[StatusEffectType, float, int]] = field(default_factory=list)
    area_of_effect: float = 0.0
    
    def is_in_range(self, source_pos: Position, target_pos: Position) -> bool:
        """Check if target is in range of this action."""
        dx = target_pos.x - source_pos.x
        dy = target_pos.y - source_pos.y
        distance = math.sqrt(dx * dx + dy * dy)
        return distance <= self.range
        
    def can_use(self) -> bool:
        """Check if the action can be used."""
        return self.current_cooldown == 0

class CombatSystem:
    """Manages combat interactions between entities."""
    
    def __init__(self):
        self.combatants: Dict[int, CombatantType] = {}
        self.actions: Dict[int, List[CombatAction]] = {}
        self.status_effects: Dict[int, List[StatusEffect]] = {}
        self.turn_order: List[Entity] = []
        self.current_turn_index: int = 0
        self.in_combat: bool = False
        
    def start_combat(self, player: Entity, enemies: List[Entity]) -> None:
        """Start a combat encounter."""
        self.in_combat = True
        self.turn_order = [player] + enemies
        self.current_turn_index = 0
        
        # Register combatants
        self.combatants[player.id] = CombatantType.PLAYER
        for enemy in enemies:
            self.combatants[enemy.id] = CombatantType.ENEMY
            
        # Initialize default actions
        self._initialize_actions(player)
        for enemy in enemies:
            self._initialize_actions(enemy)
            
    def _initialize_actions(self, entity: Entity) -> None:
        """Initialize default actions for an entity."""
        actions = []
        
        # Basic attack
        basic_attack = CombatAction(
            name="Attack",
            damage=10.0,
            accuracy=0.9,
            range=1.0
        )
        actions.append(basic_attack)
        
        # Add more complex actions based on entity type
        if self.combatants[entity.id] == CombatantType.PLAYER:
            # Power Strike
            power_strike = CombatAction(
                name="Power Strike",
                damage=20.0,
                accuracy=0.8,
                critical_chance=0.2,
                critical_multiplier=2.0,
                cooldown=3,
                status_effects=[(StatusEffectType.WEAK, 0.8, 2)]
            )
            actions.append(power_strike)
            
            # Defensive Stance
            defensive_stance = CombatAction(
                name="Defensive Stance",
                damage=0.0,
                accuracy=1.0,
                cooldown=4,
                status_effects=[(StatusEffectType.SHIELD, 0.5, 2)]
            )
            actions.append(defensive_stance)
            
        self.actions[entity.id] = actions
        
    def apply_status_effect(self, target: Entity,
                          effect_type: StatusEffectType,
                          duration: int,
                          magnitude: float) -> None:
        """Apply a status effect to a target."""
        if target.id not in self.status_effects:
            self.status_effects[target.id] = []
            
        # Calculate tick effect for damage over time
        tick_effect = None
        if effect_type in {StatusEffectType.POISON, StatusEffectType.BURN}:
            tick_effect = magnitude * 5  # Base DoT damage
        elif effect_type == StatusEffectType.BLEED:
            tick_effect = magnitude * 3  # Bleed does less damage but ignores defense
        elif effect_type == StatusEffectType.REGENERATION:
            tick_effect = magnitude * 4  # Healing per turn
            
        effect = StatusEffect(effect_type, duration, magnitude, tick_effect)
        self.status_effects[target.id].append(effect)
        
    def calculate_damage(self, action: CombatAction,
                        source: Entity,
                        target: Entity) -> Optional[DamageInstance]:
        """Calculate damage for an action."""
        # Check accuracy
        if random.random() > action.accuracy:
            return None
            
        # Get stats
        source_stats = source.get_component(Stats)
        target_stats = target.get_component(Stats)
        
        if not source_stats or not target_stats:
            return None
            
        # Base damage calculation
        damage = action.damage * (source_stats.strength / 10.0)
        
        # Critical hit
        is_critical = random.random() < action.critical_chance
        if is_critical:
            damage *= action.critical_multiplier
            
        # Defense reduction
        if target_stats.defense > 0:
            defense_multiplier = 100 / (100 + target_stats.defense)
            damage *= defense_multiplier
            
        # Status effect modifications
        if target.id in self.status_effects:
            for effect in self.status_effects[target.id]:
                if effect.type == StatusEffectType.VULNERABLE:
                    damage *= (1 + effect.magnitude)
                elif effect.type == StatusEffectType.SHIELD:
                    damage *= (1 - effect.magnitude)
                    
        return DamageInstance(
            amount=max(1, damage),  # Minimum 1 damage
            source=source,
            target=target,
            is_critical=is_critical
        )
        
    def perform_action(self, source: Entity, target: Entity,
                      action: CombatAction) -> Optional[DamageInstance]:
        """Perform a combat action."""
        if not action.can_use():
            return None
            
        # Check range
        source_pos = source.get_component(Position)
        target_pos = target.get_component(Position)
        
        if not source_pos or not target_pos:
            return None
            
        if not action.is_in_range(source_pos, target_pos):
            return None
            
        # Calculate and apply damage
        damage_instance = self.calculate_damage(action, source, target)
        if damage_instance:
            target_health = target.get_component(Health)
            if target_health:
                target_health.current -= damage_instance.amount
                
            # Apply status effects
            for effect_type, magnitude, duration in action.status_effects:
                self.apply_status_effect(target, effect_type, duration, magnitude)
                
        # Set cooldown
        action.current_cooldown = action.cooldown
        
        return damage_instance
        
    def update_status_effects(self) -> None:
        """Update all status effects."""
        for entity_id, effects in list(self.status_effects.items()):
            # Apply effect ticks
            entity = None
            for effect in effects:
                if not entity:
                    # Find entity in turn order
                    entity = next((e for e in self.turn_order if e.id == entity_id), None)
                    if not entity:
                        continue
                        
                effect.tick(entity)
                
            # Update durations and remove expired effects
            self.status_effects[entity_id] = [
                effect for effect in effects
                if effect.duration > 0
            ]
            
            if not self.status_effects[entity_id]:
                del self.status_effects[entity_id]
                
    def update_cooldowns(self) -> None:
        """Update action cooldowns."""
        for actions in self.actions.values():
            for action in actions:
                if action.current_cooldown > 0:
                    action.current_cooldown -= 1
                    
    def get_available_actions(self, entity: Entity) -> List[CombatAction]:
        """Get all available actions for an entity."""
        return [
            action for action in self.actions.get(entity.id, [])
            if action.can_use()
        ]
        
    def get_valid_targets(self, source: Entity, action: CombatAction) -> List[Entity]:
        """Get all valid targets for an action."""
        source_type = self.combatants.get(source.id)
        if not source_type:
            return []
            
        source_pos = source.get_component(Position)
        if not source_pos:
            return []
            
        valid_targets = []
        for target in self.turn_order:
            if target == source:
                continue
                
            target_type = self.combatants.get(target.id)
            if not target_type:
                continue
                
            # Check if target is valid based on combatant types
            if source_type == CombatantType.PLAYER:
                if target_type != CombatantType.ENEMY:
                    continue
            elif source_type == CombatantType.ENEMY:
                if target_type == CombatantType.ENEMY:
                    continue
                    
            target_pos = target.get_component(Position)
            if not target_pos:
                continue
                
            # Check range
            if action.is_in_range(source_pos, target_pos):
                valid_targets.append(target)
                
        return valid_targets
        
    def next_turn(self) -> Entity:
        """Advance to the next turn and return the active entity."""
        self.update_status_effects()
        self.update_cooldowns()
        
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
        return self.turn_order[self.current_turn_index]
        
    def check_combat_end(self) -> Optional[CombatantType]:
        """Check if combat has ended and return the winning side."""
        players_alive = False
        enemies_alive = False
        
        for entity in self.turn_order:
            health = entity.get_component(Health)
            if not health or health.current <= 0:
                continue
                
            combatant_type = self.combatants.get(entity.id)
            if combatant_type == CombatantType.PLAYER:
                players_alive = True
            elif combatant_type == CombatantType.ENEMY:
                enemies_alive = True
                
        if not enemies_alive:
            return CombatantType.PLAYER
        elif not players_alive:
            return CombatantType.ENEMY
            
        return None
        
    def end_combat(self) -> None:
        """End the current combat encounter."""
        self.in_combat = False
        self.turn_order.clear()
        self.current_turn_index = 0
        self.status_effects.clear()
        
        # Reset cooldowns
        for actions in self.actions.values():
            for action in actions:
                action.current_cooldown = 0
