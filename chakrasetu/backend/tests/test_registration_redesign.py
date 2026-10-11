from io import BytesIO
from uuid import uuid4
import zipfile
from types import SimpleNamespace
import pytest
from PIL import Image
from pypdf import PdfWriter
from app.common import future
from app.services.registration import acceptance_reasons
from test_intake_commercial import auth


def intake(**changes):
    return {
        "internal_id": "PBS-" + uuid4().hex[:10],
        "registration_title": "Workshop battery registration",
        "form": "PACK",
        "application_type": "TWO_WHEELER",
        "quantity": 1,
        "address": "Bengaluru workshop",
        "lat": 12.97,
        "lng": 77.59,
        "removal_reason": "unknown",
        "condition": "UNKNOWN",
        "pbs": "L3",
        "collection_availability": "YES",
        **changes,
    }


def create(client, **changes):
    body = intake(**changes)
    r = client.post("/batteries", headers=auth("originator"), json=body)
    assert r.status_code == 200, r.text
    return r.json(), body


def review(client, id, decision="APPROVED", **changes):
    return client.post(
        f"/batteries/{id}/registration-review",
        headers=auth("reviewer"),
        json={
            "decision": decision,
            "reason": "Information and preliminary observations reviewed",
            **changes,
        },
    )


def upload(
    client, id, name="note.txt", raw=b"Available owner information", actor="originator"
):
    return client.post(
        f"/batteries/{id}/evidence", headers=auth(actor), files={"file": (name, raw)}
    )


def scope(max_pbs="L3", **changes):
    return {
        "max_pbs": max_pbs,
        "application_types": ["TWO_WHEELER", "UNKNOWN"],
        "specialist_assessment": True,
        "damaged_handling": True,
        "critical_hazard_handling": False,
        "dangerous_goods": True,
        "service_areas": [],
        "restrictions": "",
        **changes,
    }


def verify_scope(client, kind="PATHWAY", max_pbs="L3", **changes):
    target = "fac-refurb-REPAIR_REFURBISHMENT" if kind == "PATHWAY" else "trans-1"
    s = {
        "capacity_kg": 500,
        "chemistries": ["LFP"],
        "formats": ["PACK"],
        "conditions": ["WORKING", "DEGRADED", "NON_FUNCTIONAL", "UNKNOWN"],
        "handling_scope": "ORDINARY",
        "safety": scope(max_pbs, **changes),
    }
    if kind == "PATHWAY":
        s["pathway"] = "REPAIR_REFURBISHMENT"
    else:
        s.update(center=[12.97, 77.59], radius_km=1500)
    r = client.post(
        "/capability-requests",
        headers=auth("buyer" if kind == "PATHWAY" else "transporter"),
        json={
            "kind": kind,
            "action": "MODIFY",
            "target_id": target,
            "facility_id": "fac-refurb" if kind == "PATHWAY" else None,
            "requested_scope": s,
        },
    )
    assert r.status_code == 200, r.text
    r = client.post(
        "/capability-requests/" + r.json()["request"]["id"] + "/review",
        headers=auth("reviewer"),
        json={
            "decision": "APPROVED",
            "reason": "Activity-specific fictional qualification reviewed",
            "evidence": "Synthetic scope evidence",
            "valid_until": future(days=60),
        },
    )
    assert r.status_code == 200, r.text
    return target


def test_required_only_persists_missing_as_unknown_or_null(client):
    a, _ = create(client, additional_information="Repair history unavailable")
    detail = client.get("/batteries/" + a["id"], headers=auth("originator")).json()
    assert detail["data"]["registration"]["status"] == "PENDING_REVIEW"
    assert detail["evidence"] == [] and detail["mass_kg"] is None
    assert detail["data"]["inspection"] is None
    assert detail["data"]["nominal_voltage"] is None
    assert detail["data"]["additional_information"] == "Repair history unavailable"
    assert detail["data"]["pbs"] == "L3" and not detail["authority_confirmed"]
    r = client.post(
        "/listings",
        headers=auth("originator"),
        json={"asset_id": a["id"], "expires_at": future(days=1)},
    )
    assert (
        r.status_code == 409
        and r.json()["detail"]["code"] == "REGISTRATION_NOT_APPROVED"
    )


@pytest.mark.parametrize("pbs", ["L1", "L2", "L3", "L4", "L5"])
def test_all_pbs_preserved_and_independent_of_diagnostics(client, pbs):
    a, _ = create(
        client,
        pbs=pbs,
        inspection={
            "conducted": "YES",
            "source": "BMS_REPORTED",
            "soh_percent": 72,
            "soc_percent": 30,
        },
    )
    assert a["data"]["pbs"] == pbs
    assert a["data"]["inspection"]["soh_percent"] == 72
    assert a["data"]["inspection"]["voltage_v"] is None
    assert not a["data"].get("final_pathway")
    policy = client.get("/registration-policy", headers=auth("originator")).json()
    assert len(policy["levels"]) == 5 and all(
        x["description"] for x in policy["levels"]
    )


def test_missing_location_and_invalid_measurements(client):
    for changes in [
        {"lat": None},
        {"quantity": 0},
        {"mass_kg": 0},
        {"inspection": {"conducted": "YES", "soh_percent": 101}},
        {"inspection": {"conducted": "NO", "voltage_v": 50}},
    ]:
        r = client.post(
            "/batteries", headers=auth("originator"), json=intake(**changes)
        )
        assert r.status_code == 422, r.text


def test_critical_contradiction_escalates_and_cannot_clear(client):
    a, _ = create(
        client,
        pbs="L1",
        condition="WORKING",
        pbs_comments="The battery is emitting smoke",
    )
    assert a["state"] == "HOLD" and a["data"]["pbs"] == "L1"
    assert review(client, a["id"]).status_code == 409
    assert review(client, a["id"], "SPECIALIST_ASSESSMENT").status_code == 200
    case = next(
        c
        for c in client.get("/exceptions", headers=auth("reviewer")).json()
        if c["object_id"] == a["id"]
    )
    r = client.post(
        "/exceptions/" + case["id"] + "/qualified-review",
        headers=auth("reviewer"),
        json={
            "decision": "SCOPED_CLEARANCE",
            "qualification_evidence": "Mock qualification",
            "report": "Mock report",
            "handling_scope": "CONTROLLED_HANDLING",
            "valid_until": future(days=3),
            "conditions": "Controlled handling",
        },
    )
    assert (
        r.status_code == 409
        and r.json()["detail"]["code"] == "CRITICAL_HAZARD_REPORTED"
    )


def test_l4_operator_approval_is_not_specialist_clearance(client):
    a, _ = create(client, pbs="L4", condition="DAMAGED_REPORTED")
    approved = review(client, a["id"]).json()
    assert (
        approved["data"]["registration"]["status"] == "APPROVED"
        and approved["state"] == "HOLD"
    )
    result = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    assert result["hold"] and not any(c["eligible"] for c in result["candidates"])
    assert "SPECIALIST_REVIEW_REQUIRED" in [
        r["code"] for r in result["registration_reasons"]
    ]


def test_operator_permissions_information_resubmission_and_material_reassessment(
    client,
):
    a, body = create(client, pbs="L1", condition="DEGRADED")
    assert (
        client.post(
            "/batteries/" + a["id"] + "/registration-review",
            headers=auth("originator"),
            json={"decision": "APPROVED", "reason": "I approve myself"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/batteries/" + a["id"] + "/registration-review",
            headers=auth("reviewer"),
            json={"decision": "REJECTED", "reason": ""},
        ).status_code
        == 422
    )
    r = review(
        client,
        a["id"],
        "INFORMATION_REQUESTED",
        reason="Please clarify location access",
    )
    assert (
        r.json()["data"]["registration"]["last_reason"]
        == "Please clarify location access"
    )
    body["additional_information"] = "Workshop gate access available"
    r = client.patch("/batteries/" + a["id"], headers=auth("originator"), json=body)
    assert (
        r.json()["id"] == a["id"]
        and r.json()["data"]["registration"]["status"] == "PENDING_REVIEW"
    )
    assert review(client, a["id"]).status_code == 200
    body["pbs"] = "L4"
    revised = client.patch(
        "/batteries/" + a["id"], headers=auth("originator"), json=body
    ).json()
    assert (
        revised["data"]["registration"]["status"] == "PENDING_REVIEW"
        and revised["state"] == "HOLD"
    )
    assert len(revised["data"]["registration"]["history"]) >= 5


def test_rejected_and_no_match_remain_unavailable(client):
    a, _ = create(client)
    assert review(client, a["id"], "REJECTED").status_code == 200
    assert (
        client.post(
            "/listings",
            headers=auth("originator"),
            json={"asset_id": a["id"], "expires_at": future(days=1)},
        ).status_code
        == 409
    )
    other, _ = create(client)
    assert review(client, other["id"]).status_code == 200
    result = client.get(
        "/batteries/" + other["id"] + "/eligible-participants",
        headers=auth("originator"),
    ).json()
    assert result["hold"] and not any(c["eligible"] for c in result["candidates"])


def test_batch_measurements_cannot_be_applied_to_every_asset(client):
    r = client.post(
        "/batteries",
        headers=auth("originator"),
        json=intake(
            quantity=3,
            inspection={"conducted": "YES", "scope": "INDIVIDUAL", "voltage_v": 40},
        ),
    )
    assert r.status_code == 422
    a, _ = create(
        client,
        quantity=3,
        mixed_batch=True,
        inspection={"conducted": "YES", "scope": "SAMPLE_ONLY", "voltage_v": 40},
    )
    assert review(client, a["id"]).status_code == 200
    matches = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    assert matches["hold"] and "BATCH_REASSESSMENT_REQUIRED" in [
        x["code"] for x in matches["registration_reasons"]
    ]


def test_registration_retry_and_four_files_fifth_rejected(client):
    a, body = create(client)
    retry = client.post("/batteries", headers=auth("originator"), json=body)
    assert retry.json()["id"] == a["id"]
    for n in range(4):
        assert (
            upload(
                client, a["id"], f"{n}.txt", f"Owner document {n}".encode()
            ).status_code
            == 200
        )
    assert (
        upload(client, a["id"], "fifth.txt", b"fifth").json()["detail"]["code"]
        == "UPLOAD_COUNT_EXCEEDED"
    )
    one = upload(client, a["id"], "retry.txt", b"Owner document 0")
    assert one.status_code == 200
    assert (
        len(
            client.get("/batteries/" + a["id"], headers=auth("originator")).json()[
                "evidence"
            ]
        )
        == 4
    )


def test_attachment_size_total_and_private_access(client):
    a, _ = create(client)
    assert (
        upload(client, a["id"], raw=b"a" * (10 * 1024 * 1024 + 1)).json()["detail"][
            "code"
        ]
        == "UPLOAD_SIZE_EXCEEDED"
    )
    for b in [b"a", b"b"]:
        assert upload(client, a["id"], raw=b * (9 * 1024 * 1024)).status_code == 200
    assert (
        upload(client, a["id"], raw=b"c" * (9 * 1024 * 1024)).json()["detail"]["code"]
        == "UPLOAD_TOTAL_EXCEEDED"
    )
    doc = upload(client, a["id"], raw=b"Small private doc").json()
    assert (
        client.get(
            "/evidence/" + doc["id"] + "/download", headers=auth("originator2")
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/evidence/" + doc["id"] + "/download", headers=auth("originator")
        ).status_code
        == 200
    )


def test_allowed_documents_and_active_content_rejection(client):
    a, _ = create(client)
    img = BytesIO()
    Image.new("RGB", (2, 2)).save(img, format="PNG")
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(pdf)
    files = [("image.png", img.getvalue()), ("doc.pdf", pdf.getvalue())]
    for suffix, required in [
        ("docx", "word/document.xml"),
        ("xlsx", "xl/workbook.xml"),
    ]:
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr(required, "<root/>")
        files.append(("doc." + suffix, buf.getvalue()))
    for name, raw in files:
        assert upload(client, a["id"], name, raw).status_code == 200
    other, _ = create(client)
    for name, raw in [
        ("code.exe", b"MZ executable"),
        ("fake.png", b"not an image"),
        ("active.pdf", b"%PDF-1.4 /JavaScript\n%%EOF"),
        ("bad.docx", b"not a zip"),
    ]:
        assert upload(client, other["id"], name, raw).status_code == 422


def test_attachment_removal_is_audited_and_revokes_approval(client):
    a, _ = create(client, pbs="L1", condition="DEGRADED")
    doc = upload(client, a["id"]).json()
    review(client, a["id"])
    r = client.post(
        f"/batteries/{a['id']}/evidence/{doc['id']}/remove", headers=auth("originator")
    )
    assert r.status_code == 200
    detail = client.get("/batteries/" + a["id"], headers=auth("originator")).json()
    assert (
        detail["data"]["registration"]["status"] == "PENDING_REVIEW"
        and detail["evidence"] == []
    )
    assert (
        client.get(
            "/evidence/" + doc["id"] + "/download", headers=auth("originator")
        ).status_code
        == 404
    )
    history = client.get("/audit/battery/" + a["id"], headers=auth("originator")).json()
    assert any(x["action"] == "REMOVE_ATTACHMENT" for x in history)


def test_reviewed_role_specific_capability_matching_and_unknown_condition(client):
    verify_scope(client, max_pbs="L2")
    a, _ = create(client, pbs="L1", condition="DEGRADED", chemistry="LFP", mass_kg=42)
    review(client, a["id"])
    result = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    assert next(
        c
        for c in result["candidates"]
        if c["facility"]["id"] == "fac-refurb"
        and c["pathway"] == "REPAIR_REFURBISHMENT"
    )["eligible"]
    unknown, _ = create(client, pbs="L1", chemistry="LFP", mass_kg=42)
    review(client, unknown["id"])
    result = client.get(
        "/batteries/" + unknown["id"] + "/eligible-participants",
        headers=auth("originator"),
    ).json()
    candidate = next(
        c
        for c in result["candidates"]
        if c["facility"]["id"] == "fac-refurb"
        and c["pathway"] == "REPAIR_REFURBISHMENT"
    )
    assert not candidate["eligible"] and "PBS_SCOPE_EXCEEDED" in [
        r["code"] for r in candidate["reasons"]
    ]
    assert (
        client.post(
            "/batteries/" + a["id"] + "/confirm-transfer-authority",
            headers=auth("originator"),
        ).status_code
        == 409
    )


def test_declared_scope_cannot_expand_permission_and_other_org_cannot_edit(client):
    cap = verify_scope(client, max_pbs="L2")
    url = "/organisation-profiles/org-refurb/capabilities/" + cap + "/declaration"
    assert (
        client.patch(
            url,
            headers=auth("originator"),
            json={"kind": "PATHWAY", "scope": scope("L5")},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            url, headers=auth("buyer"), json={"kind": "PATHWAY", "scope": scope("L5")}
        ).status_code
        == 200
    )
    a, _ = create(client, pbs="L3", condition="DEGRADED", chemistry="LFP", mass_kg=42)
    review(client, a["id"])
    result = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    c = next(
        c
        for c in result["candidates"]
        if c["facility"]["id"] == "fac-refurb"
        and c["pathway"] == "REPAIR_REFURBISHMENT"
    )
    assert not c["eligible"] and "PBS_SCOPE_EXCEEDED" in [
        r["code"] for r in c["reasons"]
    ]


def test_activity_scope_never_grants_universal_permission():
    a = SimpleNamespace(
        data={
            "pbs": "L3",
            "application_type": "TWO_WHEELER",
            "collection_availability": "YES",
            "registration": {"status": "APPROVED"},
        },
        condition="DEGRADED",
        chemistry="LFP",
        form="PACK",
    )
    cap = SimpleNamespace(
        data={"verified_safety_scope": scope("L3", dangerous_goods=False)}
    )
    assert acceptance_reasons(a, cap, "REPAIR_REFURBISHMENT") == []
    assert "DANGEROUS_GOODS_SCOPE_REQUIRED" in [
        r["code"] for r in acceptance_reasons(a, cap, "TRANSPORT")
    ]


def test_new_pbs_registration_books_and_tracks_custody_without_questionnaire(client):
    verify_scope(client, max_pbs="L2")
    verify_scope(client, kind="TRANSPORT", max_pbs="L2")
    a, _ = create(
        client,
        pbs="L1",
        condition="DEGRADED",
        chemistry="LFP",
        mass_kg=42,
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, a["id"]).status_code == 200
    listing = client.post(
        "/listings",
        headers=auth("originator"),
        json={"asset_id": a["id"], "expires_at": future(days=4)},
    ).json()
    offer = {
        "facility_id": "fac-refurb",
        "pathway": "REPAIR_REFURBISHMENT",
        "price_paise": 2000000,
        "payer_org_id": "org-refurb",
        "budget_paise": 300000,
        "expires_at": future(days=3),
        "acceptance_criteria": "Identity, condition and evidence checked",
    }
    assert (
        client.post(
            "/listings/" + listing["id"] + "/offers", headers=auth("buyer"), json=offer
        ).status_code
        == 409
    )
    # Upload during a listing would affect accepted snapshots. Use a fresh registration to obtain authorization before allocation.
    b, _ = create(
        client,
        pbs="L1",
        condition="DEGRADED",
        chemistry="LFP",
        mass_kg=42,
        window_start=future(days=1),
        window_end=future(days=3),
    )
    e = upload(client, b["id"], raw=b"Synthetic transfer mandate").json()
    assert (
        client.post(
            "/evidence/" + e["id"] + "/review",
            headers=auth("reviewer"),
            json={
                "kind": "TRANSFER_AUTHORITY",
                "status": "VERIFIED",
                "reason": "Mock mandate reviewed",
                "evidence": "Synthetic source",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/batteries/" + b["id"] + "/confirm-transfer-authority",
            headers=auth("originator"),
        ).status_code
        == 200
    )
    assert review(client, b["id"]).status_code == 200
    listing = client.post(
        "/listings",
        headers=auth("originator"),
        json={"asset_id": b["id"], "expires_at": future(days=4)},
    ).json()
    o = client.post(
        "/listings/" + listing["id"] + "/offers", headers=auth("buyer"), json=offer
    )
    assert o.status_code == 200, o.text
    tx = client.post(
        "/offers/" + o.json()["id"] + "/accept", headers=auth("originator")
    ).json()
    for actor in ["originator", "buyer"]:
        assert (
            client.post(
                "/transactions/" + tx["id"] + "/confirm",
                headers=auth(actor),
                json={"version": 1},
            ).status_code
            == 200
        )
    from test_logistics import quoted
    from test_shipment import advance

    planned = client.post(
        "/transactions/" + tx["id"] + "/route-plans", headers=auth("originator")
    )
    assert planned.status_code == 200, planned.text
    plan = next(p for p in planned.json()["candidates"] if p["hub_id"] is None)
    q = quoted(client, tx, plan, 250000)
    assert (
        client.post("/quotes/" + q["id"] + "/accept", headers=auth("buyer")).status_code
        == 200
    )
    assert (
        client.post(
            "/transactions/" + tx["id"] + "/reserve-capacity",
            headers=auth("buyer"),
            json={"route_id": plan["id"]},
        ).status_code
        == 200
    )
    r = client.post("/transactions/" + tx["id"] + "/shipments", headers=auth("buyer"))
    assert r.status_code == 200, r.text
    s = r.json()
    advance(client, s, "PICKUP_SCHEDULED", "originator")
    advance(
        client,
        s,
        "PICKED_UP",
        "originator",
        physical=True,
        evidence="Owner handover recorded",
    )
    assert (
        client.get("/batteries/" + b["id"], headers=auth("originator")).json()[
            "current_holder_org_id"
        ]
        == "org-fleet"
    )
    advance(
        client,
        s,
        "PICKED_UP",
        "transporter",
        physical=True,
        evidence="Carrier handover recorded",
    )
    assert (
        client.get("/batteries/" + b["id"], headers=auth("originator")).json()[
            "current_holder_org_id"
        ]
        == "org-trans"
    )


def test_suspended_scope_and_declared_narrowing_exclude_new_matches(client):
    cap = verify_scope(client, max_pbs="L2")
    a, _ = create(client, pbs="L1", condition="DEGRADED", chemistry="LFP", mass_kg=42)
    review(client, a["id"])
    url = "/organisation-profiles/org-refurb/capabilities/" + cap + "/declaration"
    assert (
        client.patch(
            url,
            headers=auth("buyer"),
            json={
                "kind": "PATHWAY",
                "scope": scope("L1", application_types=["THREE_WHEELER"]),
            },
        ).status_code
        == 200
    )
    result = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    c = next(
        c
        for c in result["candidates"]
        if c["facility"]["id"] == "fac-refurb"
        and c["pathway"] == "REPAIR_REFURBISHMENT"
    )
    assert "APPLICATION_NOT_ACCEPTED" in [r["code"] for r in c["reasons"]]
    r = client.post(
        "/network/capability/" + cap + "/review",
        headers=auth("reviewer"),
        json={
            "verification": "SUSPENDED",
            "valid_until": future(days=10),
            "reason": "Qualification unavailable",
            "evidence": "Synthetic scope suspension",
        },
    )
    assert r.status_code == 200, r.text
    result = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    c = next(
        c
        for c in result["candidates"]
        if c["facility"]["id"] == "fac-refurb"
        and c["pathway"] == "REPAIR_REFURBISHMENT"
    )
    assert "REGISTRATION_INVALID_OR_EXPIRED" in [r["code"] for r in c["reasons"]]


@pytest.mark.real_auth
def test_real_auth_guards_registration_and_documents(client):
    from test_security import setup, login

    setup(client)
    assert client.get("/registration-policy").status_code == 401
    h = login(client, "originator")
    a = client.post("/batteries", headers=h, json=intake()).json()
    e = client.post(
        "/batteries/" + a["id"] + "/evidence",
        headers=h,
        files={"file": ("note.txt", b"private workshop information")},
    ).json()
    h = login(client, "originator2")
    assert client.get("/batteries/" + a["id"]).status_code == 403
    assert client.get("/evidence/" + e["id"] + "/download").status_code == 403
    assert (
        client.patch("/batteries/" + a["id"], headers=h, json=intake()).status_code
        == 403
    )
    h = login(client, "transporter")
    assert (
        client.post(
            "/batteries/" + a["id"] + "/registration-review",
            headers=h,
            json={"decision": "APPROVED", "reason": "Unauthorized attempted approval"},
        ).status_code
        == 403
    )
    h = login(client, "reviewer")
    assert (
        client.post(
            "/batteries/" + a["id"] + "/registration-review",
            headers=h,
            json={
                "decision": "INFORMATION_REQUESTED",
                "reason": "Request complete location instructions",
            },
        ).status_code
        == 200
    )


def test_critical_report_cannot_be_erased_by_originator_edit(client):
    a, body = create(client, pbs="L1", pbs_comments="Battery on fire")
    body["pbs_comments"] = "Looks fine now"
    body["pbs"] = "L1"
    revised = client.patch(
        "/batteries/" + a["id"], headers=auth("originator"), json=body
    )
    assert revised.status_code == 200 and revised.json()["state"] == "HOLD"
    assert revised.json()["data"]["critical_report_unresolved"]
    assert review(client, a["id"]).status_code == 409


def test_draft_can_be_saved_incomplete_then_submitted_without_duplicate(client):
    body = {"internal_id": "draft-" + uuid4().hex[:8]}
    draft = client.post("/batteries?draft=true", headers=auth("originator"), json=body)
    assert draft.status_code == 200, draft.text
    a = draft.json()
    assert a["state"] == "DRAFT" and a["data"]["registration"]["status"] == "DRAFT"
    assert (
        client.post(
            "/listings",
            headers=auth("originator"),
            json={"asset_id": a["id"], "expires_at": future(days=2)},
        ).status_code
        == 409
    )
    submitted = client.patch(
        "/batteries/" + a["id"],
        headers=auth("originator"),
        json=intake(internal_id=body["internal_id"]),
    )
    assert submitted.status_code == 200 and submitted.json()["id"] == a["id"]
    assert submitted.json()["data"]["registration"]["status"] == "PENDING_REVIEW"


def test_submission_requires_explicit_pbs_and_location(client):
    for key in ["pbs", "registration_title", "address", "lat", "lng"]:
        body = intake()
        body.pop(key)
        r = client.post("/batteries", headers=auth("originator"), json=body)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "FIELD_REQUIRED"


@pytest.mark.parametrize("reported", ["L1", "L4"])
def test_l4_scoped_specialist_path_keeps_pbs_and_transfer_gate(client, reported):
    a, _ = create(
        client,
        pbs=reported,
        condition="DAMAGED_REPORTED",
        chemistry="LFP",
        mass_kg=36,
        window_start=future(days=1),
        window_end=future(days=3),
    )
    assert review(client, a["id"]).status_code == 200
    case = next(
        c
        for c in client.get("/exceptions", headers=auth("reviewer")).json()
        if c["object_id"] == a["id"]
    )
    r = client.post(
        "/exceptions/" + case["id"] + "/qualified-review",
        headers=auth("reviewer"),
        json={
            "decision": "SCOPED_CLEARANCE",
            "qualification_evidence": "Synthetic qualified specialist reference",
            "report": "Synthetic report permitting only controlled assessment transport",
            "handling_scope": "CONTROLLED_HANDLING",
            "valid_until": future(days=7),
            "conditions": "Only scoped qualified carrier and specialist; no safety certification",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CLOSED", r.text
    detail = client.get("/batteries/" + a["id"], headers=auth("originator")).json()
    assert detail["data"]["pbs"] == reported and not detail["authority_confirmed"]
    matches = client.get(
        "/batteries/" + a["id"] + "/eligible-participants", headers=auth("originator")
    ).json()
    eligible = [c for c in matches["candidates"] if c["eligible"]]
    assert eligible and all(
        c["facility"]["id"] == "fac-review" and c["pathway"] == "QUALIFIED_REVIEW"
        for c in eligible
    )


def test_policy_configuration_cannot_weaken_high_concern_gates(tmp_path, monkeypatch):
    import json
    from app.services.registration import load_policy, PBS_CONFIGURATION

    p = tmp_path / "policy.json"
    policy = json.loads(json.dumps(PBS_CONFIGURATION))
    policy["minimum_handling_concern"]["L4"] = "L1"
    p.write_text(json.dumps(policy))
    monkeypatch.setenv("PBS_POLICY_PATH", str(p))
    with pytest.raises(RuntimeError):
        load_policy()


@pytest.mark.real_auth
def test_database_cleanup_failure_is_returned_before_success_response(client):
    from app.main import app
    from app.db import get_db
    from app.common import fail
    from test_security import setup, login

    setup(client)
    h = login(client, "originator")
    original = app.dependency_overrides[get_db]
    body = intake(internal_id="commit-failure-check")

    def rejected_commit():
        gen = original()
        db = next(gen)
        try:
            yield db
            db.rollback()
            fail(
                "DATABASE_WRITE_FAILED",
                "Simulated persistence failure; no success response is permitted.",
                status=503,
            )
        finally:
            gen.close()

    app.dependency_overrides[get_db] = rejected_commit
    try:
        r = client.post("/batteries", headers=h, json=body)
        assert r.status_code == 503, r.text
    finally:
        app.dependency_overrides[get_db] = original
    assert not any(
        a["internal_id"] == body["internal_id"] for a in client.get("/batteries").json()
    )
