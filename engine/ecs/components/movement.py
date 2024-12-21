"""Movement-related components for the ECS."""
from dataclasses import dataclass
from typing import Tuple, Optional

from ...physics.movement import MovementStats, MovementState


@dataclass
class TransformComponent:
    """Component for entity position and rotation."""
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0


@dataclass
class MovementComponent:
    """Component for entity movement capabilities."""
    stats: MovementStats = MovementStats()
    state: MovementState = MovementState.IDLE
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    target_rotation: Optional[float] = None
