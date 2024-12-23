"""Combat abilities and skills system."""
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from .combat_system import CombatAction, StatusEffectType

class AbilityType(Enum):
    """Types of abilities."""
    MELEE = auto()
    RANGED = auto()
    TECH = auto()
    SUPPORT = auto()
    ULTIMATE = auto()

class DamageType(Enum):
    """Types of damage."""
    PHYSICAL = auto()
    ENERGY = auto()
    TECH = auto()
    PLASMA = auto()
    VOID = auto()

@dataclass
class AbilityRequirement:
    """Requirements for using an ability."""
    level: int = 1
    energy: int = 0
    tech_points: int = 0
    cooldown: int = 0
    weapon_type: Optional[str] = None

@dataclass
class AbilityUpgrade:
    """Upgrade data for an ability."""
    level: int
    damage_increase: float = 0.0
    accuracy_increase: float = 0.0
    cooldown_reduction: int = 0
    range_increase: float = 0.0
    additional_effects: List[Tuple[StatusEffectType, float, int]] = field(default_factory=list)

@dataclass
class Ability:
    """An ability that can be learned and upgraded."""
    name: str
    description: str
    ability_type: AbilityType
    damage_type: DamageType
    base_action: CombatAction
    requirements: AbilityRequirement
    upgrades: Dict[int, AbilityUpgrade] = field(default_factory=dict)
    current_level: int = 1
    
    def get_current_action(self) -> CombatAction:
        """Get the current version of the combat action."""
        action = CombatAction(
            name=self.base_action.name,
            damage=self.base_action.damage,
            accuracy=self.base_action.accuracy,
            critical_chance=self.base_action.critical_chance,
            critical_multiplier=self.base_action.critical_multiplier,
            range=self.base_action.range,
            cooldown=self.base_action.cooldown,
            status_effects=self.base_action.status_effects.copy(),
            area_of_effect=self.base_action.area_of_effect
        )
        
        # Apply upgrades
        for level in range(2, self.current_level + 1):
            if level in self.upgrades:
                upgrade = self.upgrades[level]
                action.damage += upgrade.damage_increase
                action.accuracy += upgrade.accuracy_increase
                action.cooldown = max(0, action.cooldown - upgrade.cooldown_reduction)
                action.range += upgrade.range_increase
                action.status_effects.extend(upgrade.additional_effects)
                
        return action
        
    def can_upgrade(self, player_level: int, available_points: int) -> bool:
        """Check if the ability can be upgraded."""
        next_level = self.current_level + 1
        if next_level not in self.upgrades:
            return False
            
        upgrade = self.upgrades[next_level]
        return (player_level >= upgrade.level and
                available_points >= next_level)
                
    def upgrade(self) -> bool:
        """Upgrade the ability if possible."""
        next_level = self.current_level + 1
        if next_level in self.upgrades:
            self.current_level = next_level
            return True
        return False

def create_basic_abilities() -> List[Ability]:
    """Create a set of basic abilities."""
    abilities = []
    
    # Melee Abilities
    power_strike = Ability(
        name="Power Strike",
        description="A powerful melee strike that can weaken enemies.",
        ability_type=AbilityType.MELEE,
        damage_type=DamageType.PHYSICAL,
        base_action=CombatAction(
            name="Power Strike",
            damage=20.0,
            accuracy=0.8,
            critical_chance=0.2,
            critical_multiplier=2.0,
            range=1.0,
            cooldown=3,
            status_effects=[(StatusEffectType.WEAK, 0.8, 2)]
        ),
        requirements=AbilityRequirement(level=1)
    )
    power_strike.upgrades = {
        2: AbilityUpgrade(level=3, damage_increase=5.0),
        3: AbilityUpgrade(level=5, cooldown_reduction=1),
        4: AbilityUpgrade(
            level=7,
            damage_increase=10.0,
            additional_effects=[(StatusEffectType.VULNERABLE, 0.3, 2)]
        )
    }
    abilities.append(power_strike)
    
    # Ranged Abilities
    plasma_shot = Ability(
        name="Plasma Shot",
        description="A ranged plasma attack that can burn enemies.",
        ability_type=AbilityType.RANGED,
        damage_type=DamageType.PLASMA,
        base_action=CombatAction(
            name="Plasma Shot",
            damage=15.0,
            accuracy=0.85,
            critical_chance=0.15,
            range=5.0,
            cooldown=2,
            status_effects=[(StatusEffectType.BURN, 0.5, 3)]
        ),
        requirements=AbilityRequirement(level=2, energy=10)
    )
    plasma_shot.upgrades = {
        2: AbilityUpgrade(level=4, accuracy_increase=0.05),
        3: AbilityUpgrade(level=6, damage_increase=8.0),
        4: AbilityUpgrade(
            level=8,
            range_increase=2.0,
            additional_effects=[(StatusEffectType.BURN, 0.3, 2)]
        )
    }
    abilities.append(plasma_shot)
    
    # Tech Abilities
    nano_swarm = Ability(
        name="Nano Swarm",
        description="Release a swarm of nanobots that damage and weaken enemies.",
        ability_type=AbilityType.TECH,
        damage_type=DamageType.TECH,
        base_action=CombatAction(
            name="Nano Swarm",
            damage=12.0,
            accuracy=0.9,
            range=3.0,
            cooldown=4,
            area_of_effect=2.0,
            status_effects=[
                (StatusEffectType.WEAK, 0.4, 3),
                (StatusEffectType.VULNERABLE, 0.3, 2)
            ]
        ),
        requirements=AbilityRequirement(level=3, tech_points=2)
    )
    nano_swarm.upgrades = {
        2: AbilityUpgrade(
            level=5,
            damage_increase=5.0,
            area_of_effect=0.5
        ),
        3: AbilityUpgrade(
            level=7,
            cooldown_reduction=1,
            additional_effects=[(StatusEffectType.POISON, 0.3, 3)]
        ),
        4: AbilityUpgrade(
            level=9,
            damage_increase=8.0,
            area_of_effect=0.5
        )
    }
    abilities.append(nano_swarm)
    
    # Support Abilities
    repair_field = Ability(
        name="Repair Field",
        description="Create a field that repairs and strengthens allies.",
        ability_type=AbilityType.SUPPORT,
        damage_type=DamageType.TECH,
        base_action=CombatAction(
            name="Repair Field",
            damage=0.0,
            accuracy=1.0,
            range=3.0,
            cooldown=5,
            area_of_effect=2.0,
            status_effects=[
                (StatusEffectType.REGENERATION, 0.5, 3),
                (StatusEffectType.SHIELD, 0.3, 2)
            ]
        ),
        requirements=AbilityRequirement(level=4, tech_points=3)
    )
    repair_field.upgrades = {
        2: AbilityUpgrade(
            level=6,
            area_of_effect=0.5,
            additional_effects=[(StatusEffectType.REGENERATION, 0.2, 1)]
        ),
        3: AbilityUpgrade(
            level=8,
            cooldown_reduction=1,
            additional_effects=[(StatusEffectType.SHIELD, 0.2, 1)]
        ),
        4: AbilityUpgrade(
            level=10,
            area_of_effect=0.5,
            additional_effects=[
                (StatusEffectType.REGENERATION, 0.3, 1),
                (StatusEffectType.HASTE, 0.3, 2)
            ]
        )
    }
    abilities.append(repair_field)
    
    # Ultimate Ability
    void_burst = Ability(
        name="Void Burst",
        description="Channel the power of the void to devastate enemies.",
        ability_type=AbilityType.ULTIMATE,
        damage_type=DamageType.VOID,
        base_action=CombatAction(
            name="Void Burst",
            damage=50.0,
            accuracy=0.7,
            critical_chance=0.25,
            critical_multiplier=2.5,
            range=4.0,
            cooldown=8,
            area_of_effect=3.0,
            status_effects=[
                (StatusEffectType.WEAK, 0.6, 3),
                (StatusEffectType.VULNERABLE, 0.5, 3)
            ]
        ),
        requirements=AbilityRequirement(level=10, energy=30, tech_points=5)
    )
    void_burst.upgrades = {
        2: AbilityUpgrade(
            level=12,
            damage_increase=20.0,
            accuracy_increase=0.1
        ),
        3: AbilityUpgrade(
            level=14,
            cooldown_reduction=2,
            area_of_effect=1.0
        ),
        4: AbilityUpgrade(
            level=16,
            damage_increase=30.0,
            additional_effects=[
                (StatusEffectType.STUN, 1.0, 1),
                (StatusEffectType.VULNERABLE, 0.3, 3)
            ]
        )
    }
    abilities.append(void_burst)
    
    return abilities

class AbilityManager:
    """Manages abilities for entities."""
    
    def __init__(self):
        self.entity_abilities: Dict[int, List[Ability]] = {}
        
    def add_ability(self, entity_id: int, ability: Ability) -> None:
        """Add an ability to an entity."""
        if entity_id not in self.entity_abilities:
            self.entity_abilities[entity_id] = []
        self.entity_abilities[entity_id].append(ability)
        
    def remove_ability(self, entity_id: int, ability_name: str) -> None:
        """Remove an ability from an entity."""
        if entity_id in self.entity_abilities:
            self.entity_abilities[entity_id] = [
                ability for ability in self.entity_abilities[entity_id]
                if ability.name != ability_name
            ]
            
    def get_abilities(self, entity_id: int) -> List[Ability]:
        """Get all abilities for an entity."""
        return self.entity_abilities.get(entity_id, [])
