"""
Dependency Injection контейнер.
Управляет зависимостями в приложении.
"""


class Container:
    """Простой DI-контейнер для управления зависимостями"""

    def __init__(self):
        self.instances = {}   # Singleton экземпляры
        self.registry = {}    # Фабрики

    def register(self, name, f):
        """Регистрация Transient зависимости"""
        self.registry[name] = {"f": f, "singleton": False}

    def singleton(self, name, f):
        """Регистрация Singleton зависимости"""
        self.registry[name] = {"f": f, "singleton": True}

    def get(self, name):
        """Получить экземпляр зависимости"""
        if name not in self.registry:
            raise KeyError(f"Dependency '{name}' not registered")

        entry = self.registry[name]

        if entry["singleton"]:
            if name not in self.instances:
                self.instances[name] = entry["f"](self)
            return self.instances[name]
        else:
            return entry["f"](self)

    def has(self, name):
        """Проверка наличия зависимости"""
        return name in self.registry