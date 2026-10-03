from dataclasses import dataclass
import importlib
import logging
from .demo import DemoAI, DemoFile, DemoLearning
from ..errors import ApiError

log = logging.getLogger(__name__)

def load_provider(spec, methods):
    if not spec:
        return None
    module, sep, name = spec.partition(':')
    if not sep:
        raise ValueError('Provider must use module.path:ClassName')
    provider = getattr(importlib.import_module(module), name)()
    if not all(callable(getattr(provider, method, None)) for method in methods):
        raise ValueError('Provider does not implement its contract')
    return provider

@dataclass
class Providers:
    ai: object = None
    file: object = None
    learning: object = None
    mode: str = 'production'

    @classmethod
    def from_settings(cls, settings):
        if settings.mode == 'demo':
            return cls(DemoAI(), DemoFile(), DemoLearning(), 'demo')
        return cls(load_provider(settings.ai_provider, ('summarize','chat')),
                   load_provider(settings.file_provider, ('process',)),
                   load_provider(settings.learning_provider, ('flashcards','quiz','grade')), 'production')

    def call(self, kind, method, *args):
        provider = getattr(self, kind)
        if provider is None:
            raise ApiError(503, 'PROVIDER_UNAVAILABLE', f'Module {kind} chưa được kết nối.')
        try:
            return getattr(provider, method)(*args)
        except ApiError:
            raise
        except Exception:
            log.exception('Provider %s.%s failed', kind, method)
            raise ApiError(502, 'PROVIDER_FAILED', f'Module {kind} xử lý không thành công.') from None

    def status(self):
        return {kind: 'demo' if self.mode == 'demo' else ('connected' if getattr(self,kind) else 'not_connected') for kind in ('ai','file','learning')}
