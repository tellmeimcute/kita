

from aiogram_dialog import Window, Dialog, StartMode, LaunchMode
from aiogram_dialog.widgets.kbd import SwitchTo, Row, Start

from ui.widgets.i18n_text import I18nText
from ui.state_groups import AdminMenuSG, UserMenuSG, BannerMenuSG, BroadcastMenuSG, ModerationMenuSG

from .getters import get_app_stats

main_window = Window(
    I18nText("admin_menu_text"),
    Start(I18nText("broadcast_btn"), id="broadcast", state=BroadcastMenuSG.wait_broadcast_content),
    Start(I18nText("user_moderation_btn"), id="user_select", state=ModerationMenuSG.user_select),
    Row(
        SwitchTo(I18nText("app_stats_btn"), id="app_stats", state=AdminMenuSG.app_stats),
        Start(I18nText("post_banner_btn"), id="post_banner", state=BannerMenuSG.prepare_banner),
    ),
    Start(
        I18nText("menu_btn"),
        id="main_menu",
        mode=StartMode.RESET_STACK,
        state=UserMenuSG.main,
    ),
    state=AdminMenuSG.main,
)

bot_stats_window = Window(
    I18nText("global_stats"),
    SwitchTo(I18nText("back_admin_menu_btn"), id="admin_menu", state=AdminMenuSG.main),
    state=AdminMenuSG.app_stats,
    getter=get_app_stats,
)

dialog = Dialog(
    main_window,
    bot_stats_window,
    launch_mode=LaunchMode.ROOT,
)
