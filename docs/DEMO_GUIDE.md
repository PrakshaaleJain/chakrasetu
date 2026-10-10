# Interactive demonstration

Start with a fresh `python -m app.seed --reset`, then launch `python dev.py`. All actions below use the persistent backend. The top-right actor selector is a synthetic demo login, not a commercial approval override.

1. **Asha · Fleet originator** → Battery registry. Inspect `CS-BLR-002`: chemistry UNKNOWN and mass unknown are retained. `CS-BLR-001` has reviewed mock authority evidence and no flag reported. Register/edit a draft to show inline field validation. New transfer-authority evidence remains submitted until Priya reviews it.
2. **Kabir · Service originator** → Battery registry. `CS-SVC-003` is held because swelling is reported. Ordinary listing is blocked. **Priya · Network reviewer** can append a qualification-backed scoped report in Exception queue, using `CONTROLLED_HANDLING`, keeping original flags. Only the synthetic specialist and scoped carrier can then qualify; no blanket safety claim is made.
3. **Asha** → Listings & offers. Publish `CS-BLR-001`. Select the listing and inspect excluded receivers: wrong chemistry/pathway/capability/scope is explained.
4. **Meera · Refurbisher** → Listings & offers. Select the eligible listing, submit conditional offer ₹20,000, buyer pays logistics up to ₹3,000, and enter inspection criteria.
5. **Asha** → select that offer. Transactions → confirm v1. **Meera** → confirm the same v1. Neither party's single confirmation is sufficient.
6. **Asha or Meera** → Routes & quotes → generate alternatives. Inspect direct and one-hub legs, synthetic rate sources, ranking and rejection explanations. Select the direct route.
7. **Ravi · Transporter** → Routes & quotes → submit all-inclusive synthetic quote ₹4,200. **Meera** → attempt acceptance. A ₹1,200 overrun blocks acceptance and creates an exception. Either propose ₹4,500 in Transactions and obtain both parties' v2 confirmation, regenerate routes/requote; or **Ravi** submits another ₹2,500 quote on v1 and **Meera** accepts it. Existing overrun exception remains until reviewed with evidence.
8. **Meera** → hold selected route capacity, then commit/book shipment. A route plan/accepted quote alone is not a booking. The holder remains originator.
9. **Asha** → Shipments & custody → record Pickup scheduled. Record Picked up with physical checkbox/evidence. It stays pending the counterpart. **Ravi** → record the same physical pickup with his evidence. Only then does custody move to the carrier. Record In transit.
10. **Ravi** → emit a synthetic route-deviation value 8 (> demo 5 km threshold). Inspect SIMULATED labels and reviewer queue. Record Arrived pending receipt. Arrival does not transfer custody to buyer.
11. **Meera** → record physical receipt with the condition-match checkbox cleared. Receipt becomes disputed; no automatic settlement/closure. **Priya** resolves the discrepancy with evidence and authorises resume. **Meera** records reconciled complete receipt.
12. **Meera** → Receiving & completion → accept inspection as agreed. Report synthetic payment reference. **Asha** separately confirms that record as payee. No money is transferred.
13. **Meera** → record `REFURBISHMENT_COMPLETED` with synthetic report. **Priya** reviews any remaining linked alerts/overrun exception. Shipments shows closure gates. **Meera** can close only after all gates pass.

## Alternative failure paths

- Routes & quotes → close quote round with no acceptance: sale remains agreed, logistics `NO_ACCEPTANCE`, no shipment exists. Reopen a round, propose a new pickup window (both parties reconfirm new terms), seek another eligible quote, or each party confirms cancellation under terms.
- One-hub route: **Neel · Hub operator** explicitly approves the selected route before quote acceptance. At transit, both Neel and Ravi confirm `HUB_RECEIVED` and then `HUB_DISPATCHED`; destination arrival is blocked until the outbound handover is complete.
- Consolidation: independently agree/quote/book two compatible one-hub asset shipments. In Shipments, select both and propose a manifest. Each affected originator/buyer/hub/carrier approves before pickup. Custody events remain per shipment/asset; savings stay incomplete unless a comparable committed baseline exists.
- Receiving `REVISE_PRICE` requires evidence and a proposed amount. It creates v2; both parties reconfirm in Transactions. Old accepted price remains in history, and settlement cannot progress before inspection acceptance and confirmations.
- Recycler pathway: `SENT_FOR_RECYCLING` remains pending. Only an evidenced `RECYCLING_COMPLETED` record can satisfy the final recycling gate.

Resetting is an explicit destructive demo operation. Do not reset during a live demonstration if you intend to keep its records.
