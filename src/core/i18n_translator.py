
from aiogram.utils.i18n import gettext as _

class Translator:
    def translate(self, i18n_key: str) -> str:
        return _(i18n_key)

    def format(self, text: str, i18n_kwargs: dict[str, str]) -> str:
        return text.format(**i18n_kwargs)

    def i18n_text(self, i18n_key, i18n_kwargs) -> str:
        translated = self.translate(i18n_key)
        return self.format(translated, i18n_kwargs)