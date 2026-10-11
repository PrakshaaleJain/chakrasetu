from sqlalchemy import select, func
from . import models as m
from .common import get, fail, expired, audit
from .auth import has_role
from .permissions import OPERATION_ROLES

CONFIRMATION = "Your request has been submitted successfully. The ChakraSetu team will review the information and contact your organisation within 48 hours with the next steps. Your existing approved capabilities will remain unchanged while this request is under review."


def manage(user, org_id):
    if user.organisation_id != org_id or not has_role(
        user,
        "ORG_ADMIN",
        "ORIGINATOR",
        "TRANSPORTER",
        "TECHNICIAN",
        "BUYER",
        "HUB",
        "REVIEWER",
    ):
        fail(
            "FORBIDDEN",
            "You can manage only your organisation profile and declarations.",
            status=403,
        )


def public_profile(db, org):
    profile = org.data.get("profile", {})
    facilities = db.scalars(
        select(m.Facility).where(m.Facility.organisation_id == org.id)
    ).all()
    operations = (
        db.scalars(
            select(m.OperationCapability).where(
                m.OperationCapability.facility_id.in_([f.id for f in facilities])
            )
        ).all()
        if facilities
        else []
    )
    pathways = (
        db.scalars(
            select(m.FacilityCapability).where(
                m.FacilityCapability.facility_id.in_([f.id for f in facilities])
            )
        ).all()
        if facilities
        else []
    )
    transport = db.scalars(
        select(m.TransporterProfile).where(
            m.TransporterProfile.organisation_id == org.id
        )
    ).all()
    members = db.scalars(
        select(m.Membership).where(
            m.Membership.organisation_id == org.id, m.Membership.active == True
        )
    ).all()
    roles = sorted(
        {r for x in members for r in x.roles if r not in {"ORG_ADMIN", "REVIEWER"}}
    )
    if not roles and org.role not in {"PLATFORM", "REVIEWER"}:
        roles = [org.role]

    def capability(kind, obj):
        verified = (
            obj.verified if kind == "OPERATION" else obj.verification == "VERIFIED"
        )
        # Demo approvals are distinct from independently reviewed operating approvals.
        demo = bool(
            org.synthetic
            and not obj.data.get("reviews")
            and not obj.data.get("verification_reviews")
        )
        status = (
            "EXAMPLE_SCOPE"
            if verified and demo
            else (
                "APPROVED" if verified and not expired(obj.valid_until) else "DECLARED"
            )
        )
        if obj.data.get("request_status") in {"SUSPENDED", "REMOVED"}:
            status = obj.data["request_status"]
        return {
            "id": obj.id,
            "kind": kind,
            "facility_id": getattr(obj, "facility_id", None),
            "name": getattr(
                obj,
                "operation",
                getattr(obj, "pathway", obj.name if kind == "TRANSPORT" else ""),
            ),
            "status": status,
            "scope": {
                "chemistries": getattr(
                    obj,
                    "chemistries",
                    obj.data.get(
                        "verified_chemistries", obj.data.get("chemistries", [])
                    ),
                ),
                "formats": getattr(obj, "formats", obj.data.get("forms", [])),
                "conditions": obj.data.get("conditions", []),
                "center": obj.data.get("center"),
                "radius_km": obj.data.get("radius_km"),
                "material_categories": getattr(obj, "material_categories", []),
                "handling_scope": obj.data.get("handling_scope"),
                "capacity_kg": getattr(obj, "capacity_kg", None),
                "declared_safety": obj.data.get("declared_safety_scope"),
                "verified_safety": obj.data.get("verified_safety_scope"),
            },
            "valid_until": obj.valid_until,
            "updated_at": obj.data.get("updated_at", obj.created_at),
        }

    declared = []
    for request in db.scalars(
        select(m.CapabilityRequest).where(
            m.CapabilityRequest.organisation_id == org.id,
            m.CapabilityRequest.status.in_(["PENDING", "INFORMATION_REQUESTED"]),
            m.CapabilityRequest.target_id == None,
        )
    ):
        if request.kind not in {"OPERATION", "PATHWAY", "TRANSPORT"}:
            continue
        scope = request.requested_scope
        declared.append(
            {
                "id": "request:" + request.id,
                "kind": request.kind,
                "facility_id": request.facility_id,
                "name": scope.get("operation") or scope.get("pathway") or "Transport",
                "status": request.status,
                "scope": {
                    k: scope.get(
                        k,
                        (
                            []
                            if k
                            in {
                                "chemistries",
                                "formats",
                                "material_categories",
                                "conditions",
                            }
                            else None
                        ),
                    )
                    for k in {
                        "chemistries",
                        "formats",
                        "material_categories",
                        "conditions",
                        "capacity_kg",
                        "handling_scope",
                        "center",
                        "radius_km",
                    }
                },
                "valid_until": None,
                "updated_at": request.updated_at,
            }
        )
    return {
        "id": org.id,
        "name": org.name,
        "display_name": profile.get("display_name") or org.name,
        "description": profile.get("description", ""),
        "organisation_type": profile.get("organisation_type") or org.role,
        "website": profile.get("website", ""),
        "regions": profile.get("regions", []),
        "roles": roles,
        "verification": (
            "EXAMPLE_SCOPE"
            if org.synthetic
            and org.verification == "VERIFIED"
            and not org.data.get("verification_reviews")
            else org.verification
        ),
        "logo_url": (
            f"/api/organisation-profiles/{org.id}/logo?v={org.data.get('logo_updated_at', org.created_at)}"
            if org.data.get("logo_file")
            else None
        ),
        "contact_visibility": profile.get("contact_visibility", "PRIVATE"),
        "facilities": [
            {
                "id": f.id,
                "name": f.name,
                "kind": f.kind,
                "lat": f.lat,
                "lng": f.lng,
                "registration": (
                    "EXAMPLE_SCOPE"
                    if org.synthetic
                    and f.registration == "VERIFIED"
                    and not f.data.get("verification_reviews")
                    else f.registration
                ),
                "description": f.data.get("description", ""),
            }
            for f in facilities
        ],
        "capabilities": [capability("OPERATION", c) for c in operations]
        + [capability("PATHWAY", c) for c in pathways]
        + [capability("TRANSPORT", c) for c in transport]
        + declared,
    }


def validate_request(db, user, body):
    if body.facility_id:
        if (
            get(db, m.Facility, body.facility_id).organisation_id
            != user.organisation_id
        ):
            fail("FORBIDDEN", "Choose one of your organisation facilities.", status=403)
    kind = body.kind
    scope = body.requested_scope
    if kind == "ROLE" and not scope.role:
        fail("SCOPE_REQUIRED", "Choose an operational role.")
    if kind in {"OPERATION", "PATHWAY", "FACILITY"} and not body.facility_id:
        fail("FACILITY_REQUIRED", "Choose the facility to which the request applies.")
    if kind == "OPERATION" and not scope.operation:
        fail("SCOPE_REQUIRED", "Choose an operation.")
    if kind == "PATHWAY" and not scope.pathway:
        fail("SCOPE_REQUIRED", "Choose a battery pathway.")
    if kind == "TRANSPORT" and (
        scope.capacity_kg is None or scope.center is None or scope.radius_km is None
    ):
        fail(
            "SCOPE_REQUIRED",
            "Enter transport capacity, centre coordinates and coverage radius.",
        )
    if kind == "PATHWAY" and scope.capacity_kg is None:
        fail("SCOPE_REQUIRED", "Enter the requested facility capacity.")
    if body.target_id:
        model = {
            "OPERATION": m.OperationCapability,
            "PATHWAY": m.FacilityCapability,
            "TRANSPORT": m.TransporterProfile,
            "FACILITY": m.Facility,
            "IDENTITY": m.Organisation,
        }.get(kind)
        if not model:
            fail(
                "SCOPE_INVALID",
                "Role requests use the selected role, not a resource identifier.",
            )
        obj = get(db, model, body.target_id)
        org_id = (
            get(db, m.Facility, obj.facility_id).organisation_id
            if kind in {"OPERATION", "PATHWAY"}
            else (obj.id if kind == "IDENTITY" else obj.organisation_id)
        )
        if org_id != user.organisation_id:
            fail(
                "FORBIDDEN",
                "The requested capability belongs to another organisation.",
                status=403,
            )
        if kind in {"OPERATION", "PATHWAY"} and obj.facility_id != body.facility_id:
            fail("SCOPE_INVALID", "The capability cannot be moved to another facility.")
        if kind == "OPERATION" and obj.operation != scope.operation:
            fail(
                "SCOPE_INVALID", "Request a separate capability for another operation."
            )
        if kind == "PATHWAY" and obj.pathway != scope.pathway:
            fail("SCOPE_INVALID", "Request a separate capability for another pathway.")
    elif body.action != "ADD" and kind not in {"ROLE", "IDENTITY", "FACILITY"}:
        fail("TARGET_REQUIRED", "Choose an existing capability to change or remove.")


def apply_decision(db, reviewer, request, body):
    kind = request.kind
    s = request.requested_scope
    accepted = body.decision == "APPROVED"
    disabling = body.decision in {"SUSPENDED", "REMOVED"}
    if not accepted and not disabling:
        return
    if request.action == "REMOVE" and accepted:
        fail("DECISION_INVALID", "Approve a removal using the Removed decision.")
    if body.decision == "REMOVED" and request.action != "REMOVE":
        fail("DECISION_INVALID", "Removal must be explicitly requested.")
    if (
        accepted
        and kind != "ROLE"
        and (not body.evidence or not body.valid_until or expired(body.valid_until))
    ):
        fail(
            "REVIEW_EVIDENCE_REQUIRED",
            "Approval requires a current review reference and expiry date.",
        )
    if kind == "ROLE":
        desired = s["role"]
        members = db.scalars(
            select(m.Membership).where(
                m.Membership.organisation_id == request.organisation_id,
                m.Membership.active == True,
            )
        ).all()
        binding = db.scalar(
            select(m.OrganisationAccount).where(
                m.OrganisationAccount.organisation_id == request.organisation_id
            )
        )
        account = get(db, m.Account, binding.account_id) if binding else None
        member = next(
            (
                x
                for x in members
                if x.user_id == (account.user_id if account else request.submitted_by)
            ),
            None,
        )
        if not member:
            fail(
                "ACCOUNT_REQUIRED",
                "The organisation account must be active before roles are approved.",
            )
        before = member.roles
        assigned = sorted(
            (set(member.roles) | {desired})
            if accepted
            else (set(member.roles) - {desired})
        )
        if not assigned:
            fail(
                "ACCOUNT_ROLE_REQUIRED",
                "A platform administrator must assign organisation administration before the final account role can be removed.",
            )
        member.roles = assigned
        audit(
            db,
            reviewer,
            "membership",
            member,
            "REVIEWED_ROLE_CHANGE",
            request_id=request.id,
            before=before,
            after=assigned,
        )
        return
    if kind == "IDENTITY":
        obj = get(db, m.Organisation, request.organisation_id)
    elif kind == "FACILITY":
        obj = get(db, m.Facility, request.facility_id)
    elif request.target_id:
        obj = get(
            db,
            {
                "OPERATION": m.OperationCapability,
                "PATHWAY": m.FacilityCapability,
                "TRANSPORT": m.TransporterProfile,
            }[kind],
            request.target_id,
        )
    elif accepted:
        if kind == "OPERATION":
            obj = db.scalar(
                select(m.OperationCapability).where(
                    m.OperationCapability.facility_id == request.facility_id,
                    m.OperationCapability.operation == s["operation"],
                )
            )
            if obj and obj.verified:
                fail(
                    "TARGET_REQUIRED",
                    "Use a modification request for this existing approved operation.",
                )
            if not obj:
                obj = m.OperationCapability(
                    facility_id=request.facility_id,
                    operation=s["operation"],
                    chemistries=[],
                    formats=[],
                    material_categories=[],
                    data={},
                )
                db.add(obj)
        elif kind == "PATHWAY":
            existing = db.scalar(
                select(m.FacilityCapability).where(
                    m.FacilityCapability.facility_id == request.facility_id,
                    m.FacilityCapability.pathway == s["pathway"],
                )
            )
            if existing:
                fail(
                    "TARGET_REQUIRED",
                    "Use a modification request to review the existing pathway scope.",
                )
            obj = m.FacilityCapability(
                facility_id=request.facility_id,
                pathway=s["pathway"],
                capacity_kg=s["capacity_kg"],
                available_kg=s["capacity_kg"],
                valid_until=body.valid_until,
                data={},
            )
            db.add(obj)
        else:
            obj = m.TransporterProfile(
                organisation_id=request.organisation_id,
                name=get(db, m.Organisation, request.organisation_id).name,
                capacity_kg=s["capacity_kg"],
                valid_until=body.valid_until,
                data={},
            )
            db.add(obj)
        db.flush()
        request.target_id = obj.id
    else:
        fail("TARGET_REQUIRED", "There is no approved scope to suspend or remove.")
    if accepted:
        if kind == "IDENTITY" and s.get("official_name"):
            name = s["official_name"].strip()
            if db.scalar(
                select(m.Organisation).where(
                    m.Organisation.id != obj.id,
                    func.lower(func.trim(m.Organisation.name)) == name.lower(),
                )
            ):
                fail(
                    "ORGANISATION_EXISTS",
                    "This official organisation name is already registered.",
                )
            obj.name = name
        if kind == "OPERATION":
            obj.verified = True
            obj.capacity_kg = s["capacity_kg"]
            obj.chemistries = s["chemistries"]
            obj.formats = s["formats"]
            obj.material_categories = s["material_categories"]
        elif kind == "FACILITY":
            obj.registration = "VERIFIED"
        else:
            obj.verification = "VERIFIED"
        if kind not in {"IDENTITY"}:
            obj.valid_until = body.valid_until
        if kind in {"PATHWAY", "TRANSPORT"}:
            if s["capacity_kg"] is None:
                fail("SCOPE_REQUIRED", "A known approved capacity is required.")
            obj.capacity_kg = s["capacity_kg"]
            if kind == "PATHWAY":
                obj.available_kg = min(obj.available_kg, s["capacity_kg"])
            obj.data = {
                **obj.data,
                "verified_chemistries": s["chemistries"],
                "chemistries": s["chemistries"],
                "forms": s["formats"],
                "conditions": s["conditions"],
                "handling_scope": s["handling_scope"],
            }
            if kind == "TRANSPORT":
                obj.data = {
                    **obj.data,
                    "center": s["center"],
                    "radius_km": s["radius_km"],
                }
    else:
        if kind == "OPERATION":
            obj.verified = False
        elif kind == "FACILITY":
            obj.registration = "SUSPENDED"
        else:
            obj.verification = "SUSPENDED"
    if accepted and kind in {"OPERATION", "TRANSPORT"}:
        required = (
            OPERATION_ROLES.get(s.get("operation"), set())
            if kind == "OPERATION"
            else {"TRANSPORTER"}
        )
        binding = db.scalar(
            select(m.OrganisationAccount).where(
                m.OrganisationAccount.organisation_id == request.organisation_id
            )
        )
        if binding:
            account = get(db, m.Account, binding.account_id)
            member = db.scalar(
                select(m.Membership).where(
                    m.Membership.user_id == account.user_id,
                    m.Membership.organisation_id == request.organisation_id,
                    m.Membership.active == True,
                )
            )
            if member and required and not required.intersection(member.roles):
                before = member.roles
                member.roles = sorted(set(member.roles) | {sorted(required)[0]})
                audit(
                    db,
                    reviewer,
                    "membership",
                    member,
                    "CAPABILITY_ROLE_APPROVED",
                    request_id=request.id,
                    before=before,
                    after=member.roles,
                )
    if accepted and kind == "OPERATION":
        obj.data = {**obj.data, "conditions": s["conditions"]}
    if (
        accepted
        and kind in {"OPERATION", "PATHWAY", "TRANSPORT"}
        and s.get("safety") is not None
    ):
        obj.data = {
            **obj.data,
            "verified_safety_scope": s["safety"],
            "declared_safety_scope": s["safety"],
        }
    from .services.registration import invalidate_pending

    if kind in {"OPERATION", "PATHWAY", "TRANSPORT", "FACILITY", "IDENTITY"}:
        invalidate_pending(db, request.organisation_id, reviewer)
    review = {
        "request_id": request.id,
        "reviewer_id": reviewer.id,
        "decision": body.decision,
        "reason": body.reason,
        "evidence": body.evidence,
        "valid_until": body.valid_until,
        "scope": s,
        "timestamp": m.now(),
    }
    obj.data = {
        **obj.data,
        "request_status": body.decision,
        "updated_at": m.now(),
        "reviews": [*obj.data.get("reviews", []), review],
        "verification_reviews": [*obj.data.get("verification_reviews", []), review],
    }
