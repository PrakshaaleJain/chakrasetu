# Business roles are scoped to the selected active organisation membership.
ROLES = {
    "ORG_ADMIN",
    "ORIGINATOR",
    "TECHNICIAN",
    "REFURBISHER",
    "SECOND_LIFE",
    "RECYCLER",
    "PROCESSOR",
    "REFINER",
    "MANUFACTURER",
    "CUSTOMER",
    "TRANSPORTER",
    "BUYER",
    "HUB",
    "REVIEWER",
}
BUSINESS_ROLES = ROLES - {"REVIEWER"}
# Compatibility with established commercial/shipment role checks. Technician has no BUYER power.
LEGACY_ROLE = {
    "REFURBISHER": "BUYER",
    "SECOND_LIFE": "BUYER",
    "RECYCLER": "BUYER",
    "PROCESSOR": "BUYER",
    "REFINER": "BUYER",
    "MANUFACTURER": "BUYER",
    "CUSTOMER": "BUYER",
}
OPERATION_ROLES = {
    "ASSESSMENT": {"TECHNICIAN"},
    "REFURBISHMENT": {"REFURBISHER"},
    "REPURPOSING": {"SECOND_LIFE", "REFURBISHER"},
    "INTEGRATION": {"SECOND_LIFE"},
    "DISMANTLING": {"RECYCLER"},
    "RECYCLING": {"RECYCLER"},
    "PROCESSING": {"PROCESSOR"},
    "REFINING": {"REFINER"},
    "MANUFACTURING": {"MANUFACTURER"},
}
