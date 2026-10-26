from dishka import Provider, Scope, provide

from core.config import Config
from core.cryptographer import Cryptographer


class ConfigProvider(Provider):
    scope = Scope.APP

    cryptographer = provide(Cryptographer)

    @provide
    def config(self) -> Config:
        return Config.get()
