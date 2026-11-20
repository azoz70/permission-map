"""Canonical data models (Pydantic) for PERMISSION MAP.

These models define the unified shape every importer must produce, regardless of
the source system. Importers map source columns onto these fields first, then
Pydantic validates types and required values.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class User(BaseModel):
    external_id: str
    name: str | None = None
    email: str | None = None
    department: str | None = None
    job_title: str | None = None
    status: str = "active"
    is_privileged: bool = False
    source: str | None = None


class Group(BaseModel):
    external_id: str
    name: str | None = None
    description: str | None = None
    source: str | None = None


class Role(BaseModel):
    external_id: str
    name: str | None = None
    description: str | None = None
    is_admin: bool = False
    role_type: str | None = None
    source: str | None = None


class Resource(BaseModel):
    external_id: str
    name: str | None = None
    resource_type: str | None = None
    source: str | None = None


class Permission(BaseModel):
    external_id: str
    resource_id: str = Field(..., description="External id of the target resource")
    name: str | None = None
    action: str | None = None
    source: str | None = None


class Membership(BaseModel):
    user_id: str
    group_id: str
    source: str | None = None


# Canonical entities importable from CSV in the current phase.
ENTITY_MODELS: dict[str, type[BaseModel]] = {
    "users": User,
    "groups": Group,
    "roles": Role,
    "resources": Resource,
    "permissions": Permission,
    "memberships": Membership,
}
