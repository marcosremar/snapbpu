"""
Dependency Injection Container
Implements Dependency Inversion Principle (DIP)
"""
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from functools import lru_cache

T = TypeVar('T')


class DependencyContainer:
    """
    Simple DI container for managing service dependencies.
    Supports singleton and factory patterns.
    """

    def __init__(self):
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._transient: Dict[str, Callable] = {}

    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance"""
        self._singletons[name] = instance

    def register_factory(self, name: str, factory: Callable) -> None:
        """Register a factory function (creates new instance each time)"""
        self._factories[name] = factory

    def register_transient(self, name: str, factory: Callable) -> None:
        """Register a transient service (new instance per request)"""
        self._transient[name] = factory

    def resolve(self, name: str) -> Any:
        """Resolve a dependency by name"""
        # Check singletons first
        if name in self._singletons:
            return self._singletons[name]

        # Check factories
        if name in self._factories:
            instance = self._factories[name]()
            self._singletons[name] = instance  # Cache as singleton
            return instance

        # Check transient
        if name in self._transient:
            return self._transient[name]()

        raise KeyError(f"Dependency '{name}' not registered")

    def reset(self) -> None:
        """Clear all registrations (useful for testing)"""
        self._singletons.clear()
        self._factories.clear()
        self._transient.clear()


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get or create the global DI container"""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def reset_container() -> None:
    """Reset the container (useful for testing)"""
    global _container
    if _container:
        _container.reset()


# Convenience functions
def register_singleton(name: str, instance: Any) -> None:
    """Register a singleton instance"""
    get_container().register_singleton(name, instance)


def register_factory(name: str, factory: Callable) -> None:
    """Register a factory function"""
    get_container().register_factory(name, factory)


def register_transient(name: str, factory: Callable) -> None:
    """Register a transient service"""
    get_container().register_transient(name, factory)


def resolve(name: str) -> Any:
    """Resolve a dependency"""
    return get_container().resolve(name)
