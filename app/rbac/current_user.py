# Standard library
import uuid
from dataclasses import dataclass, field

# Internal
from app.constants.roles import MemberRole


@dataclass
class CurrentUser:
    """
    Represents the authenticated user attached to every request.
    Loaded from the JWT payload — no DB query on every request.

    Attributes:
        id          — clinic_members.id (not users.id)
        user_id     — users.id
        clinic_id   — the clinic this user belongs to
        full_name   — display name
        role        — MemberRole enum value
        permissions — list of permission strings loaded at login
        is_active   — account active flag
    """

    id: uuid.UUID
    user_id: uuid.UUID
    clinic_id: uuid.UUID
    full_name: str
    role: str                              # MemberRole value
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True

    @property
    def is_owner(self) -> bool:
        return self.role == MemberRole.CLINIC_OWNER.value

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def has_all_permissions(self, permissions: list[str]) -> bool:
        return all(p in self.permissions for p in permissions)
