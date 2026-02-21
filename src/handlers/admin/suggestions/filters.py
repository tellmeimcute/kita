

from aiogram.utils.i18n import gettext as _

from helpers.enums import ViewerAdminAction
from helpers.filters import I18nTextFilter

VIEWER_ACTION_MAP = {
    "viewer_accept": (ViewerAdminAction.ACCEPT, True),
    "viewer_accept_no_caption": (ViewerAdminAction.ACCEPT_NO_CAPTION, True),
    "viewer_decline": (ViewerAdminAction.DECLINE, False),
}

def viewer_action(key: str) -> I18nTextFilter:
    if key not in VIEWER_ACTION_MAP:
        raise ValueError(f"Unknown key {key}")
    
    action, verdict = VIEWER_ACTION_MAP[key]
    return I18nTextFilter(
        i18n_key=key,
        viewer_action=action,
        verdict=verdict
    )