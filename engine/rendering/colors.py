"""Color definitions for the rendering system with a cyberpunk aesthetic."""

# Basic colors with neon touches
BLACK = (0, 0, 0)
DARKER_GRAY = (15, 15, 20)
DARK_GRAY = (30, 30, 40)
GRAY = (60, 60, 80)
LIGHT_GRAY = (120, 120, 160)
WHITE = (200, 200, 255)  # Slightly blue-tinted

# Neon accent colors
NEON_CYAN = (0, 255, 255)
NEON_MAGENTA = (255, 0, 255)
NEON_YELLOW = (255, 255, 0)
NEON_GREEN = (0, 255, 150)
NEON_BLUE = (0, 150, 255)
NEON_RED = (255, 50, 50)

# Theme-specific colors with cyberpunk aesthetic
THEME_COLORS = {
    'residential': {
        'wall': (40, 45, 60),
        'floor': (25, 28, 35),
        'accent': (0, 150, 255),  # Neon blue
        'glow': (0, 100, 170),    # Subtle blue glow
    },
    'industrial': {
        'wall': (50, 40, 35),
        'floor': (30, 25, 22),
        'accent': (255, 100, 0),  # Industrial orange
        'glow': (170, 70, 0),     # Subtle orange glow
    },
    'research': {
        'wall': (35, 50, 50),
        'floor': (22, 30, 30),
        'accent': (0, 255, 150),  # Neon green
        'glow': (0, 170, 100),    # Subtle green glow
    }
}

# Feature colors with neon effects
FEATURE_COLORS = {
    'door': (120, 80, 40),
    'door_glow': (180, 120, 60, 100),  # Door glow effect
    'window': (40, 130, 180),
    'window_glow': (60, 150, 200, 100),  # Window glow
    'terminal': (0, 255, 150),  # Neon green
    'terminal_glow': (0, 170, 100, 100),  # Terminal glow
    'container': (180, 140, 40),
    'container_glow': (200, 160, 60, 100),  # Container glow
    'machine': (180, 50, 50),
    'machine_glow': (200, 70, 70, 100),  # Machine glow
    'pillar': (60, 65, 75),
    'pillar_glow': (80, 85, 95, 100),  # Subtle pillar glow
    'light': (255, 255, 200),
    'light_glow': (255, 255, 220, 150),  # Strong light glow
}

# UI colors
UI_COLORS = {
    'background': (10, 12, 15),
    'panel': (20, 24, 30),
    'border': (40, 45, 55),
    'text': (200, 200, 255),
    'text_highlight': (255, 255, 255),
    'text_dim': (100, 100, 140),
    'selection': (0, 150, 255, 100),
    'grid': (40, 45, 55, 80),
}
