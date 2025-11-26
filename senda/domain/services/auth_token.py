import abc

from senda.domain.dtos.auth_token import TokenPayloadDTO
from senda.domain.dtos.user import UserDTO


class IAuthTokenService(abc.ABC):
    @abc.abstractmethod
    def generate_jwt_token(self, user: UserDTO) -> str: ...

    @abc.abstractmethod
    def parse_jwt_token(self, token: str) -> TokenPayloadDTO: ...
