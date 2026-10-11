import secrets
from fastapi import APIRouter, Depends, Request, Response
from pydantic import Field, field_validator
from sqlalchemy import select, func, text
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from . import models as m
from .db import get_db
from .auth import current_user, digest, COOKIE, has_role
from .common import fail, get, future, expired, audit
from .schemas import Schema
from .permissions import ROLES, BUSINESS_ROLES
from .config import APP_ENV

router = APIRouter(prefix="/auth", tags=["accounts"])
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))


class EmailIn(Schema):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if (
            value.count("@") != 1
            or "." not in value.split("@")[1]
            or any(c.isspace() for c in value)
        ):
            raise ValueError("Enter a valid email address")
        return value


class LoginIn(EmailIn):
    password: str = Field(min_length=1, max_length=256)


class RegisterIn(LoginIn):
    name: str = Field(min_length=2, max_length=120)
    organisation_name: str = Field(min_length=2, max_length=200)

    @field_validator("name", "organisation_name")
    @classmethod
    def meaningful_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Enter a name with at least two characters")
        return v

    @field_validator("password")
    @classmethod
    def strong(cls, v):
        if len(v) < 12:
            raise ValueError("Use at least 12 characters")
        return v


class PasswordIn(Schema):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class ResetIn(Schema):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=12, max_length=256)


class SwitchIn(Schema):
    membership_id: str
    role: str


class MemberIn(Schema):
    user_id: str
    roles: list[str] = Field(min_length=1, max_length=14)
    active: bool = True


class ActiveIn(Schema):
    active: bool


def limit(db, request, email=""):
    # Persistent single-instance limits. Proxy headers are deliberately not trusted.
    host = request.client.host if request.client else "local"
    for bucket, maximum in [
        (digest(host + ":all"), 60),
        (digest(host + ":" + email), 10),
    ]:
        count = db.scalar(
            select(func.count())
            .select_from(m.AuthAttempt)
            .where(m.AuthAttempt.bucket == bucket, m.AuthAttempt.expires_at > m.now())
        )
        if count >= maximum:
            fail(
                "AUTH_RATE_LIMIT",
                "Too many attempts. Try again in 15 minutes.",
                status=429,
            )
        db.add(m.AuthAttempt(bucket=bucket, expires_at=future(minutes=15)))
    db.commit()  # failures must count even if the request rolls back


def verify(account, password):
    try:
        ok = password_hasher.verify(
            account.password_hash if account else DUMMY_HASH, password
        )
        return bool(account and ok)
    except (VerificationError, InvalidHashError):
        return False


def revoke(db, user_id):
    for s in db.scalars(select(m.AuthSession).where(m.AuthSession.user_id == user_id)):
        s.revoked = True


def profile(db, user):
    account = db.scalar(select(m.Account).where(m.Account.user_id == user.id))
    memberships = db.scalars(
        select(m.Membership).where(
            m.Membership.user_id == user.id, m.Membership.active == True
        )
    ).all()
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "selected_role": getattr(user, "selected_role", user.role),
        "roles": getattr(user, "roles", [user.role]),
        "organisation_id": user.organisation_id,
        "email": account.email if account else None,
        "platform_admin": bool(account and account.platform_admin),
        "synthetic": user.data.get("synthetic", False),
        "memberships": [
            {
                "id": x.id,
                "organisation_id": x.organisation_id,
                "organisation_name": get(db, m.Organisation, x.organisation_id).name,
                "roles": x.roles,
            }
            for x in memberships
        ],
    }


def issue(db, user, member, response):
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    session = m.AuthSession(
        user_id=user.id,
        membership_id=member.id,
        selected_role=member.roles[0],
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        expires_at=future(minutes=480),
    )
    db.add(session)
    db.flush()
    secure = APP_ENV == "production"
    response.set_cookie(
        COOKIE,
        token,
        max_age=28800,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "chakra_csrf",
        csrf,
        max_age=28800,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )
    return {"signed_in": True}


@router.post("/register")
def register(body: RegisterIn, request: Request, db=Depends(get_db, scope="function")):
    limit(db, request, body.email)
    if db.scalar(select(m.Account).where(m.Account.email == body.email)):
        fail(
            "REGISTRATION_UNAVAILABLE",
            "Account could not be registered. Use account recovery or contact an administrator.",
            status=409,
        )
    db.execute(text("BEGIN IMMEDIATE"))
    if db.scalar(
        select(m.Organisation).where(
            func.lower(func.trim(m.Organisation.name))
            == body.organisation_name.strip().lower()
        )
    ):
        fail(
            "ORGANISATION_EXISTS",
            "An organisation with this name is already registered. Contact ChakraSetu to recover its account.",
            status=409,
        )
    org = m.Organisation(
        name=body.organisation_name.strip(),
        role="ORIGINATOR",
        data={"status": "PENDING_REVIEW"},
    )
    db.add(org)
    db.flush()
    user = m.User(
        name=body.name,
        organisation_id=org.id,
        role="ORG_ADMIN",
        token_hash="disabled-" + secrets.token_hex(32),
        active=False,
        data={"provenance": "USER_REGISTERED"},
    )
    db.add(user)
    db.flush()
    account = m.Account(
        user_id=user.id,
        email=body.email,
        password_hash=password_hasher.hash(body.password),
    )
    db.add(account)
    db.flush()
    db.add(
        m.OrganisationAccount(
            organisation_id=org.id,
            account_id=account.id,
            data={"binding_source": "REGISTRATION"},
        )
    )
    db.add(
        m.Membership(
            user_id=user.id, organisation_id=org.id, roles=["ORG_ADMIN", "ORIGINATOR"]
        )
    )
    audit(db, user, "user", user, "REGISTER_PENDING_ACTIVATION")
    return {
        "status": "PENDING_ACTIVATION",
        "message": "Registration recorded. A platform administrator must activate the account after review; no email delivery is configured.",
    }


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db=Depends(get_db, scope="function"),
):
    limit(db, request, body.email)
    a = db.scalar(select(m.Account).where(m.Account.email == body.email))
    if not verify(a, body.password):
        fail(
            "LOGIN_FAILED",
            "Email or password is incorrect, or account is inactive.",
            status=401,
        )
    user = get(db, m.User, a.user_id)
    member = next(
        (
            x
            for x in db.scalars(
                select(m.Membership).where(
                    m.Membership.user_id == user.id, m.Membership.active == True
                )
            )
            if get(db, m.Organisation, x.organisation_id).active
            and (
                APP_ENV != "production"
                or not get(db, m.Organisation, x.organisation_id).synthetic
            )
        ),
        None,
    )
    if (
        not user.active
        or not member
        or (APP_ENV == "production" and user.data.get("synthetic"))
    ):
        fail(
            "LOGIN_FAILED",
            "Email or password is incorrect, or account is inactive.",
            status=401,
        )
    if password_hasher.check_needs_rehash(a.password_hash):
        a.password_hash = password_hasher.hash(body.password)
    audit(db, user, "user", user, "LOGIN")
    return issue(db, user, member, response)


@router.get("/profile")
def me(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    return profile(db, user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    request.state.auth_session.revoked = True
    response.delete_cookie(COOKIE, path="/")
    response.delete_cookie("chakra_csrf", path="/")
    audit(db, user, "user", get(db, m.User, user.id), "LOGOUT")
    return {"signed_in": False}


@router.post("/switch")
def switch(
    body: SwitchIn,
    request: Request,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    member = get(db, m.Membership, body.membership_id)
    if (
        member.user_id != user.id
        or not member.active
        or body.role not in member.roles
        or not get(db, m.Organisation, member.organisation_id).active
    ):
        fail(
            "FORBIDDEN",
            "Select one of your active memberships and assigned roles.",
            status=403,
        )
    request.state.auth_session.membership_id = member.id
    request.state.auth_session.selected_role = body.role
    audit(db, user, "membership", member, "SWITCH_ROLE", role=body.role)
    return {"switched": True}


@router.post("/password")
def change(
    body: PasswordIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    a = db.scalar(select(m.Account).where(m.Account.user_id == user.id))
    if not verify(a, body.current_password):
        fail("LOGIN_FAILED", "Current password is incorrect.", status=401)
    a.password_hash = password_hasher.hash(body.new_password)
    revoke(db, user.id)
    audit(
        db, user, "user", get(db, m.User, user.id), "PASSWORD_CHANGED_SESSIONS_REVOKED"
    )
    return {"message": "Password changed. Sign in again on each device."}


@router.post("/reset-request")
def reset_request(
    body: EmailIn, request: Request, db=Depends(get_db, scope="function")
):
    limit(db, request, body.email)
    # No token returned or sent without a verified delivery channel.
    return {
        "message": "Contact the platform administrator for a securely delivered, one-use recovery token. This deployment has no email delivery service."
    }


@router.post("/reset")
def reset(body: ResetIn, request: Request, db=Depends(get_db, scope="function")):
    limit(db, request)
    db.execute(text("BEGIN IMMEDIATE"))
    row = db.scalar(
        select(m.RecoveryToken).where(m.RecoveryToken.token_hash == digest(body.token))
    )
    if not row or row.used or expired(row.expires_at):
        fail("RECOVERY_INVALID", "Recovery token is invalid or expired.", status=400)
    a = db.scalar(select(m.Account).where(m.Account.user_id == row.user_id))
    a.password_hash = password_hasher.hash(body.new_password)
    row.used = True
    revoke(db, row.user_id)
    audit(
        db,
        get(db, m.User, row.user_id),
        "user",
        get(db, m.User, row.user_id),
        "PASSWORD_RESET",
    )
    return {"message": "Password reset. Sign in again."}


def admin(user):
    if not user.platform_admin:
        fail("FORBIDDEN", "Platform administrator access required.", status=403)


@router.get("/accounts")
def accounts(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    admin(user)
    return [
        {
            "id": x.user_id,
            "email": x.email,
            "name": get(db, m.User, x.user_id).name,
            "active": get(db, m.User, x.user_id).active,
        }
        for x in db.scalars(select(m.Account))
    ]


@router.post("/accounts/{id}/active")
def activate(
    id: str,
    body: ActiveIn,
    db=Depends(get_db, scope="function"),
    user=Depends(current_user),
):
    admin(user)
    target = get(db, m.User, id)
    if id == user.id and not body.active:
        fail(
            "LAST_ADMIN_PROTECTION",
            "Use another administrator to deactivate this account.",
        )
    target.active = body.active
    revoke(db, id)
    audit(db, user, "user", target, "ACCOUNT_ACTIVATION", active=body.active)
    return {"active": target.active}


@router.post("/accounts/{id}/recovery")
def recovery(id: str, db=Depends(get_db, scope="function"), user=Depends(current_user)):
    admin(user)
    target = get(db, m.User, id)
    if not db.scalar(select(m.Account).where(m.Account.user_id == id)):
        fail("NOT_FOUND", "No account provisioned.", status=404)
    token = secrets.token_urlsafe(40)
    for old in db.scalars(select(m.RecoveryToken).where(m.RecoveryToken.user_id == id)):
        old.used = True
    db.add(
        m.RecoveryToken(
            user_id=id, token_hash=digest(token), expires_at=future(minutes=30)
        )
    )
    audit(db, user, "user", target, "RECOVERY_TOKEN_ISSUED")
    return {
        "token": token,
        "expires_in_minutes": 30,
        "instruction": "Deliver privately after verifying the account holder. Token is shown once; do not log it.",
    }


@router.get("/memberships")
def members(db=Depends(get_db, scope="function"), user=Depends(current_user)):
    if not has_role(user, "ORG_ADMIN") and not user.platform_admin:
        fail("FORBIDDEN", "Organisation administrator required.", status=403)
    return [
        {
            "id": x.id,
            "user_id": x.user_id,
            "name": get(db, m.User, x.user_id).name,
            "roles": x.roles,
            "active": x.active,
        }
        for x in db.scalars(
            select(m.Membership).where(
                m.Membership.organisation_id == user.organisation_id
            )
        )
    ]


@router.post("/memberships")
def membership(
    body: MemberIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    if not has_role(user, "ORG_ADMIN") and not user.platform_admin:
        fail("FORBIDDEN", "Organisation administrator required.", status=403)
    allowed = (
        ROLES
        if user.platform_admin
        else set(
            row.roles
            if (
                row := db.scalar(
                    select(m.Membership).where(
                        m.Membership.user_id == body.user_id,
                        m.Membership.organisation_id == user.organisation_id,
                    )
                )
            )
            else []
        )
    )
    # Operational role expansion goes through the capability review queue.
    if not set(body.roles) <= allowed:
        fail(
            "FORBIDDEN",
            "Platform roles cannot be assigned by an organisation.",
            status=403,
        )
    get(db, m.User, body.user_id)
    row = db.scalar(
        select(m.Membership).where(
            m.Membership.user_id == body.user_id,
            m.Membership.organisation_id == user.organisation_id,
        )
    )
    # Joining another organisation requires platform-mediated identity/consent review, not arbitrary IDs.
    if not row and not user.platform_admin:
        fail(
            "MEMBERSHIP_REVIEW_REQUIRED",
            "A platform administrator must approve initial membership after verifying consent.",
            status=403,
        )
    if not row:
        row = m.Membership(
            user_id=body.user_id, organisation_id=user.organisation_id, roles=body.roles
        )
        db.add(row)
        db.flush()
    row.roles = sorted(set(body.roles))
    row.active = body.active
    row.data = {
        **row.data,
        "review_scope": (
            "GLOBAL_OPERATIONS"
            if "REVIEWER" in body.roles and user.platform_admin
            else row.data.get("review_scope")
        ),
    }
    revoke(db, body.user_id)
    audit(
        db,
        user,
        "membership",
        row,
        "MEMBERSHIP_CHANGED",
        roles=row.roles,
        active=row.active,
    )
    return {"id": row.id, "roles": row.roles, "active": row.active}


class PlacementIn(Schema):
    user_id: str
    organisation_id: str
    roles: list[str] = Field(min_length=1, max_length=14)
    consent_evidence: str = Field(min_length=3, max_length=2000)


@router.post("/platform-memberships")
def assign_membership(
    body: PlacementIn, db=Depends(get_db, scope="function"), user=Depends(current_user)
):
    admin(user)
    if not set(body.roles) <= ROLES:
        fail(
            "ROLE_INVALID",
            "Only defined organization roles can be assigned.",
            status=422,
        )
    get(db, m.User, body.user_id)
    get(db, m.Organisation, body.organisation_id)
    row = db.scalar(
        select(m.Membership).where(
            m.Membership.user_id == body.user_id,
            m.Membership.organisation_id == body.organisation_id,
        )
    )
    if not row:
        row = m.Membership(
            user_id=body.user_id,
            organisation_id=body.organisation_id,
            roles=sorted(set(body.roles)),
        )
        db.add(row)
        db.flush()
    row.roles = sorted(set(body.roles))
    row.active = True
    row.data = {
        **row.data,
        "consent_evidence": body.consent_evidence,
        "review_scope": "GLOBAL_OPERATIONS" if "REVIEWER" in body.roles else None,
        "assigned_by": user.id,
        "timestamp": m.now(),
    }
    revoke(db, body.user_id)
    audit(
        db,
        user,
        "membership",
        row,
        "PLATFORM_MEMBERSHIP_ASSIGNED",
        roles=row.roles,
        consent_evidence=body.consent_evidence,
        organisation_id=body.organisation_id,
    )
    return {"id": row.id, "roles": row.roles, "organisation_id": row.organisation_id}
