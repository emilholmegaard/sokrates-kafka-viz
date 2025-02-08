"""
Service collection model.
"""

from typing import Dict, Iterator, Optional

from .service import Service


class ServiceCollection:
    """Collection of microservices."""

    def __init__(self) -> None:
        """Initialize an empty service collection."""
        self.services: Dict[str, Service] = {}

    def add_service(self, service: Service) -> None:
        """Add a service to the collection.

        Args:
            service: Service to add
        """
        self.services[service.name] = service

    def get_service(self, name: str) -> Optional[Service]:
        """Get a service by name.

        Args:
            name: Name of the service to get

        Returns:
            Service if found, None otherwise
        """
        return self.services.get(name)

    def get_all_services(self) -> Dict[str, Service]:
        """Get all services.

        Returns:
            Dict of service name to Service objects
        """
        return self.services

    def remove_service(self, name: str) -> None:
        """Remove a service from the collection.

        Args:
            name: Name of the service to remove
        """
        if name in self.services:
            del self.services[name]

    def __len__(self) -> int:
        """Get number of services in collection."""
        return len(self.services)

    def __contains__(self, name: str) -> bool:
        """Check if service exists in collection."""
        return name in self.services

    def __iter__(self) -> Iterator[Service]:
        """Iterate over services."""
        return iter(self.services.values())

    def __str__(self) -> str:
        return f"ServiceCollection({len(self)} services)"

    def __repr__(self) -> str:
        """Get detailed string representation."""
        return str(self)
