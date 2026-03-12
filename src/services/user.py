from logging import getLogger

from aiogram.types import User as UserTelegram
from sqlalchemy.ext.asyncio import AsyncSession

from database.dao import UserAlchemyDAO
from database.dto import UserDTO
from database.roles import UserRole
from database.models import UserAlchemy

from helpers.schemas import ChangeRoleData
from helpers.message_payload import MessagePayload
from handlers.keyboards import get_main_kb_by_role

from config import Config

logger = getLogger("user_service")

class UserService:
    dao = UserAlchemyDAO

    def __init__(self, session: AsyncSession, config: Config):
        self.session = session
        self.config = config

    async def create(self, user_tg: UserTelegram):
        role = UserRole.ADMIN if user_tg.id == self.config.ADMIN_ID else UserRole.USER

        prep_user_dto = UserDTO(
            user_id=user_tg.id,
            username=user_tg.username,
            name=user_tg.full_name,
            role=role,
            is_bot_blocked=False
        )

        prep_user_alchemy = UserAlchemy(**prep_user_dto.model_dump())

        async with self.session.begin():
            user_alchemy = await self.dao.create(self.session, prep_user_alchemy)

        logger.info("Created new user %s", user_tg.id)
        return UserDTO.model_validate(user_alchemy)
    
    async def get(self, user_id: int) -> UserDTO | None:
        async with self.session.begin():
            user_alchemy = await self.dao.get_one_or_none_by_id(self.session, user_id)

        if not user_alchemy:
            return None
        
        return UserDTO.model_validate(user_alchemy)

    async def get_active(self):
        async with self.session.begin():
            active = await self.dao.get_active(self.session)
        return UserDTO.from_model_list(active)

    async def set_role(self, user_dto: UserDTO, role: UserRole):
        user_dto.role = role

        async with self.session.begin():
            result = await self.dao.update_by_id(
                self.session, user_dto.user_id, user_dto.prepare_changed_data()
            )
        
        return result

    async def change_role(self, data: ChangeRoleData, notify_user: bool = True, return_kb = None):
        notifier = data.notifier
        caller_dto = data.caller_dto

        if data.target_id == self.config.ADMIN_ID or data.target_id == data.caller_dto.user_id:
            payload = MessagePayload(i18n_key="error_user_immune", reply_markup=return_kb)
            await notifier.notify_user(caller_dto, payload)
            return
    
        try:
            target_dto = await self.get(data.target_id)
            if not target_dto:
                raise KeyError("User not found")
            target_dto.role = data.target_role
            async with self.session.begin():
                await self.dao.update_by_id(self.session, data.target_id, target_dto.prepare_changed_data())
                if data.target_role == UserRole.BANNED:
                    await self.dao.decline_all_suggestions(self.session, data.target_id)
        except KeyError:
            i18n_kwargs = {"user_id": data.target_id}
            payload = MessagePayload(i18n_key="user_not_found", i18n_kwargs=i18n_kwargs, reply_markup=return_kb)
            await notifier.notify_user(caller_dto, payload)
            return
        except Exception as e:
            logger.error(e)
            return

        # NOTIFY CALLER
        i18n_kwargs = {
            "username": target_dto.username,
            "user_id": target_dto.user_id,
            "role": target_dto.role,
        }
        payload = MessagePayload(i18n_key="answer_admin_role_changed", i18n_kwargs=i18n_kwargs, reply_markup=return_kb)
        await notifier.notify_user(caller_dto, payload)

        # NOTIFY USER
        if notify_user:
            kb = get_main_kb_by_role(data.target_role)
            i18n_kwargs = {"role": data.target_role}
            payload = MessagePayload(
                i18n_key="notify_user_role_changed", i18n_kwargs=i18n_kwargs, reply_markup=kb
            )
            await notifier.notify_user(target_dto, payload)

        logger.info(
            "%s (%s) change user role %s (%s) to %s",
            caller_dto.username,
            caller_dto.user_id,
            target_dto.username,
            target_dto.user_id,
            target_dto.role,
        )

        return target_dto