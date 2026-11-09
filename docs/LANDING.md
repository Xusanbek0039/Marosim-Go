# MarosimGo landing

The public page is served from `backend/landing/` by the existing Django panel router. No frontend build, remote font service, or external CDN is required at runtime.

## Files

- `index.html`: Uzbek product content, semantic sections, cabinet examples, FAQ, partner form and login dialog.
- `landing.css`: responsive dark/light design, focus styles, reduced motion and print styles.
- `landing.js`: navigation, keyboard-accessible tabs, synthetic calendar and sharing examples, cabinet links, theme and reveal behavior.
- `mercury-hero.js`: the user-selected Mercury nucleus, rendered with Three.js. The geometry and material match concept 01 of `liquid-lab.js`.
- `partner-form.js`: existing partner endpoint integration and HTTP-LAN-compatible SHA-256 proof of work, validation, one-time challenge retry, rate-limit feedback and receipt confirmation.
- `vendor/`: pinned Three.js 0.180.0 and its room environment. License is in `THREE-LICENSE.txt`.
- `motion-tanlov.html` / `liquid-lab.js`: separate exploration gallery, not loaded by the landing page.

## Behavior

The 3D hero is decorative and independent from navigation and the form. A CSS Mercury illustration remains visible when WebGL or module loading fails. Reduced-motion visitors start with animation paused; the visitor can opt in. Rendering pauses off screen and when the document is hidden, runs at up to 30 frames per second and caps pixel density.

Cabinet links use production subdomains by default. On localhost or IPv4 LAN addresses they use the current hostname and the existing user/studio/venue ports 3002/8002/3003. Product paths are `/toyxonalar` and `/obuna` in the user application.

Calendar and sharing demonstrations are labeled synthetic. They never submit bookings or invitations. Real actions belong to authenticated cabinets.

## Product accuracy

Copy was checked against `CEREMONY_OWNERSHIP.md`, `VENUE_AVAILABILITY.md`, the recent progress notes and current subscription models. The subscription code is newer than some early documentation: downloading originals requires an active owner subscription. Without one the standard viewer limit is five; subscribed owners use their plan's limit. Viewers never have download permission. A month of viewer access is 30 days and starts at invitation acceptance.

No user counts, endorsements, current prices, automatic payments or lifetime storage promises are invented. Current prices are read in the authenticated cabinet. A booking request does not reserve a session until venue confirmation and does not automatically create a ceremony archive.

## Verification

Chrome browser checks cover the live WebGL hero; 1440/768/390/320 px layouts without horizontal overflow; tab and keyboard navigation; sample calendar and sharing/reset; login dialog and Escape; theme and motion controls; and reduced motion.

Partner form browser checks intercept its own API requests: invalid input, duplicate submission suppression, a failed challenge and one retry, field errors, HTTP 429 and a valid 201 receipt. The generated proof is checked independently with Node SHA-256. No real partner application is sent by these checks. This verifies the UI/API contract, not a running production backend.

A static local preview cannot accept real applications. The existing Django application must be running for `/api/v1/public/partner-applications/` and its challenge endpoint to respond.
