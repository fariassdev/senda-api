from fastapi import APIRouter

from senda.api.schemas.requests.user import AdminUserCreationRequest, UserUpdateRequest
from senda.api.schemas.responses.user import (
    AdminUserCreationResponse,
    CurrentUserResponse,
    UpdatedUserResponse,
    UserPromotionResponse,
)
from senda.core.dependencies import (
    CurrentAdminUser,
    CurrentUser,
    DBSession,
    IUserService,
    JWTToken,
)

router = APIRouter()


@router.get("", response_model=CurrentUserResponse)
async def get_current_user(
    token: JWTToken, current_user: CurrentUser
) -> CurrentUserResponse:
    """
    Return current user.
    """
    return CurrentUserResponse.from_dto(dto=current_user, token=token)


@router.put("", response_model=UpdatedUserResponse)
async def update_current_user(
    payload: UserUpdateRequest,
    token: JWTToken,
    session: DBSession,
    current_user: CurrentUser,
    user_service: IUserService,
) -> UpdatedUserResponse:
    """
    Update current user.
    """
    updated_user_dto = await user_service.update_user(
        session=session, current_user=current_user, user_to_update=payload.to_dto()
    )
    return UpdatedUserResponse.from_dto(dto=updated_user_dto, token=token)


@router.post("/admin", response_model=AdminUserCreationResponse)
async def create_admin_user(
    payload: AdminUserCreationRequest,
    session: DBSession,
    current_user: CurrentAdminUser,
    user_service: IUserService,
) -> AdminUserCreationResponse:
    """
    Create a new admin user. Requires admin permissions.
    """
    admin_user_dto = await user_service.create_admin_user(
        session=session, user_to_create=payload.to_dto()
    )
    return AdminUserCreationResponse.from_dto(dto=admin_user_dto)


@router.put("/{user_id}/promote", response_model=UserPromotionResponse)
async def promote_user_to_admin(
    user_id: int,
    session: DBSession,
    current_user: CurrentAdminUser,
    user_service: IUserService,
) -> UserPromotionResponse:
    """
    Promote an existing user to admin role. Requires admin permissions.
    """
    promoted_user_dto = await user_service.promote_user_to_admin(
        session=session, user_id=user_id
    )
    return UserPromotionResponse.from_dto(dto=promoted_user_dto)
