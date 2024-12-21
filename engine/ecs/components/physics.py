"""Physics-related components for the ECS."""
from dataclasses import dataclass
from typing import Optional

from ...physics.collision import CollisionShape, ShapeType


@dataclass
class ColliderComponent:
    """Component for collision detection."""
    shape: CollisionShape
    is_trigger: bool = False  # If True, generates collision events but doesn't block movement
    layer: int = 0  # Collision layer for filtering


@dataclass
class RigidbodyComponent:
    """Component for physics simulation."""
    mass: float = 1.0
    drag: float = 0.1
    gravity_scale: float = 1.0
    is_kinematic: bool = False  # If True, not affected by forces/gravity
    fixed_rotation: bool = False  # If True, rotation is not affected by physics
