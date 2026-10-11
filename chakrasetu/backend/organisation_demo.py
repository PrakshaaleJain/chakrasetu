"""Real HTTP organisation-profile and verification rehearsal; uses explicit demo credentials."""

import json, os, urllib.request, urllib.error, http.cookiejar


def run(base="http://127.0.0.1:8000"):
    sessions = {}

    def call(actor, path, body=None, method=None, expected=200):
        if actor not in sessions:
            jar = http.cookiejar.CookieJar()
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(jar)
            )
            request = urllib.request.Request(
                base + "/auth/login",
                data=json.dumps(
                    {
                        "email": actor + "@demo.chakrasetu.local",
                        "password": os.environ["CHAKRA_DEMO_PASSWORD"],
                    }
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            with opener.open(request):
                pass
            sessions[actor] = (
                opener,
                next(c.value for c in jar if c.name == "chakra_csrf"),
            )
        opener, csrf = sessions[actor]
        request = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        )
        try:
            with opener.open(request) as result:
                status = result.status
                data = json.load(result)
        except urllib.error.HTTPError as error:
            status = error.code
            data = json.load(error)
        assert status == expected, (path, status, data)
        return data

    profile = call("originator", "/auth/profile")
    org = profile["organisation_id"]
    call(
        "originator",
        "/organisation-profiles/" + org,
        {
            "display_name": "Setu Fleet",
            "description": "Local rehearsal of circular battery collection",
            "business_email": "fleet@example.invalid",
            "contact_visibility": "PRIVATE",
        },
        "PATCH",
    )
    assert (
        call("originator", "/organisation-profiles/" + org)["description"]
        == "Local rehearsal of circular battery collection"
    )
    call("originator2", f"/organisation-profiles/{org}/contacts", expected=403)
    assert "fleet@example.invalid" not in json.dumps(call("originator2", "/network"))
    req = call(
        "originator",
        "/capability-requests",
        {"kind": "ROLE", "requested_scope": {"role": "TRANSPORTER"}},
    )["request"]
    assert (
        req["status"] == "PENDING"
        and "TRANSPORTER" not in call("originator", "/auth/profile")["roles"]
    )
    call(
        "reviewer",
        f"/capability-requests/{req['id']}/review",
        {
            "decision": "INFORMATION_REQUESTED",
            "reason": "Provide the transport operating scope",
        },
    )
    call(
        "originator",
        f"/capability-requests/{req['id']}/respond",
        {"message": "Ordinary transport only; separate carrier qualification required"},
    )
    call(
        "reviewer",
        f"/capability-requests/{req['id']}/review",
        {
            "decision": "APPROVED",
            "reason": "Reviewed operating role; carrier scope is a separate gate",
        },
    )
    assert "TRANSPORTER" in call("originator", "/auth/profile")["roles"]
    rows = call("originator", "/organisation-profiles")
    assert len(rows) == len({x["id"] for x in rows})
    print(
        "PASS real HTTP profile persistence, private contact isolation, one-card directory and pending → information → approval with combined roles",
        flush=True,
    )


if __name__ == "__main__":
    run()
