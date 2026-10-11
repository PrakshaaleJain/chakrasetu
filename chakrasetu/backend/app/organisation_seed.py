"""Public demo descriptions. Fictional provenance stays internal; no invented contacts."""

from sqlalchemy import select
from . import models as m

NAMES = {
    "org-processor": "Setu Material Processing",
    "org-refiner": "ReLoop Refining",
    "org-manufacturer": "CycleWorks Manufacturing",
    "org-customer": "Setu Storage Operations",
}
DESCRIPTIONS = {
    "ORIGINATOR": "Registers retired micromobility batteries and coordinates their collection and downstream transfer.",
    "BUYER": "Receives eligible battery consignments within its declared facility scope.",
    "TRANSPORTER": "Coordinates collection and delivery within its documented coverage and handling scope.",
    "HUB": "Provides aggregation and documented intermediate custody for eligible consignments.",
    "REVIEWER": "Reviews operational evidence and coordinates qualified exception handling.",
    "PROCESSOR": "Processes documented material inputs into measured downstream material lots.",
    "REFINER": "Refines accepted intermediate materials against documented incoming specifications.",
    "MANUFACTURER": "Receives qualified material inputs for documented manufacturing operations.",
    "CUSTOMER": "Accepts second-life storage products and records deployment, service and retirement.",
}


def seed_profiles(db):
    for org in db.scalars(
        select(m.Organisation).where(m.Organisation.synthetic == True)
    ):
        if org.id in NAMES and org.name.startswith("Synthetic "):
            org.name = NAMES[org.id]
        if "profile" not in org.data:
            org.data = {
                **org.data,
                "profile": {
                    "display_name": org.name,
                    "description": DESCRIPTIONS.get(org.role, ""),
                    "organisation_type": org.role,
                    "regions": [],
                    "contact_visibility": "PRIVATE",
                },
                "profile_provenance": "SYNTHETIC",
            }
    for user in db.scalars(select(m.User)):
        if user.data.get("synthetic") and user.name.startswith("Synthetic "):
            user.name = (
                "RenewCell Diagnostics"
                if user.id == "technician"
                else NAMES.get(user.organisation_id, user.name)
            )
    for f in db.scalars(select(m.Facility)):
        if f.organisation_id in NAMES and f.name.startswith("Synthetic "):
            f.name = NAMES[f.organisation_id] + " Facility"
