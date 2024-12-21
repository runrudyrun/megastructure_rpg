from typing import Dict, Any, Optional, Type
import yaml
import os
from pathlib import Path
from ..ecs.component import Component
from ..ecs.entity import Entity
from ..ecs.world import World

class ConfigManager:
    """Manages loading and accessing game configuration data."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.entity_templates: Dict[str, Dict] = {}
        self.behavior_configs: Dict[str, Dict] = {}
        self.generation_rules: Dict[str, Dict] = {}
        self._load_configurations()
    
    def _load_configurations(self) -> None:
        """Load all configuration files."""
        # Load entity templates
        entity_path = self.data_dir / 'entities'
        if entity_path.exists():
            for file in entity_path.glob('*.yaml'):
                with open(file, 'r') as f:
                    templates = yaml.safe_load(f)
                    self.entity_templates.update(templates)
        
        # Load behavior configurations
        behavior_path = self.data_dir / 'behaviors'
        if behavior_path.exists():
            for file in behavior_path.glob('*.yaml'):
                with open(file, 'r') as f:
                    behaviors = yaml.safe_load(f)
                    self.behavior_configs.update(behaviors)

        # Load generation rules
        generation_path = self.data_dir / 'generation'
        if generation_path.exists():
            for file in generation_path.glob('*.yaml'):
                with open(file, 'r') as f:
                    rules = yaml.safe_load(f)
                    self.generation_rules.update(rules)
    
    def get_entity_template(self, template_name: str) -> Optional[Dict]:
        """Get an entity template by name, including inherited properties."""
        template = self.entity_templates.get(template_name)
        if not template:
            return None
            
        # Handle template inheritance
        if 'inherit' in template:
            parent = self.get_entity_template(template['inherit'])
            if parent:
                # Deep merge parent and child templates
                merged = self._deep_merge(parent.copy(), template)
                return merged
                
        return template
    
    def create_entity_from_template(self, world: World, template_name: str,
                                  position: Optional[Dict[str, float]] = None) -> Optional[Entity]:
        """Create an entity instance from a template."""
        template = self.get_entity_template(template_name)
        if not template:
            return None
            
        entity = world.create_entity()
        
        # Create components from template
        components = template.get('components', {})
        for component_name, component_data in components.items():
            # Import the component class dynamically
            component_class = getattr(__import__('engine.ecs.component', fromlist=[component_name]),
                                   component_name)
            
            # Override position if provided
            if component_name == 'Position' and position:
                component_data.update(position)
            
            # Create and add the component
            component = component_class(**component_data)
            world.add_component(entity.id, component)
            
        return entity
    
    def get_behavior_config(self, behavior_type: str) -> Optional[Dict]:
        """Get behavior configuration by type."""
        return self.behavior_configs.get(behavior_type)
    
    def get_generation_rules(self) -> Dict[str, Dict]:
        """Get all generation rules."""
        return self.generation_rules
    
    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
