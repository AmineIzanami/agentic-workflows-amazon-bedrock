from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ResourceRegistry:
    resources: Dict[str, Any] = field(default_factory=dict)

    def add_resource(self, name: str, resource: Any):
        """Add a resource to the factory."""
        if name in self.resources:
            raise ValueError(f"Resource '{name}' already exists!")
        self.resources[name] = resource

    def get_resource(self, name: str) -> Any:
        """Retrieve a resource by name."""
        return self.resources.get(name, None)