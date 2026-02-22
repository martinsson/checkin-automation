## ADDED Requirements

### Requirement: Draft list is accessible via browser
The system SHALL expose a web page at `GET /` that lists all pending drafts, accessible from any device with a browser. Each entry SHALL show: draft ID, intent, step, guest name, reservation ID, and a truncated preview of the draft body.

#### Scenario: Owner views pending drafts on mobile
- **WHEN** an authenticated user navigates to `/`
- **THEN** the system returns an HTML page listing all pending drafts with their intent, guest name, and preview text

#### Scenario: No pending drafts
- **WHEN** an authenticated user navigates to `/` and no pending drafts exist
- **THEN** the system returns an HTML page with a message indicating no pending drafts

### Requirement: Draft detail view with approve and reject actions
The system SHALL expose a web page at `GET /drafts/{id}` showing the full draft body, the original guest message, and two action buttons: Approve and Reject.

#### Scenario: Owner views a specific draft
- **WHEN** an authenticated user navigates to `/drafts/{id}` for a valid pending draft
- **THEN** the system returns an HTML page showing the draft body, guest message, intent, step, and reservation ID

#### Scenario: Draft not found
- **WHEN** an authenticated user navigates to `/drafts/{id}` for a non-existent draft ID
- **THEN** the system returns a 404 response

### Requirement: Owner can approve a draft
The system SHALL accept `POST /drafts/{id}/approve` and record the verdict as `ok` in the request memory.

#### Scenario: Successful approval
- **WHEN** an authenticated user submits the approve form for a pending draft
- **THEN** the draft verdict is set to `ok`, the reviewed_at timestamp is recorded, and the user is redirected to `/`

#### Scenario: Approving an already-reviewed draft
- **WHEN** an authenticated user submits the approve form for a draft that is not pending
- **THEN** the system responds with an appropriate error message and does not modify the draft

### Requirement: Owner can reject a draft with optional context
The system SHALL accept `POST /drafts/{id}/reject` with optional form fields `actual_message_sent` and `owner_comment`, and record the verdict as `nok`.

#### Scenario: Rejection with actual message and comment
- **WHEN** an authenticated user submits the reject form with `actual_message_sent` and `owner_comment`
- **THEN** the draft verdict is set to `nok`, both fields are persisted, and the user is redirected to `/`

#### Scenario: Rejection without optional fields
- **WHEN** an authenticated user submits the reject form with empty optional fields
- **THEN** the draft verdict is set to `nok` with null optional fields, and the user is redirected to `/`

### Requirement: All routes require authentication
The system SHALL require a valid session token for all routes except `GET /login` and `POST /login`. Unauthenticated requests SHALL be redirected to `GET /login`.

#### Scenario: Unauthenticated access is redirected
- **WHEN** a user without a valid session cookie navigates to any protected route
- **THEN** the system redirects them to `/login`

#### Scenario: Login with correct token sets session cookie
- **WHEN** a user submits `POST /login` with a token matching the `REVIEW_TOKEN` environment variable
- **THEN** the system sets an httponly `session` cookie and redirects to `/`

#### Scenario: Login with incorrect token is rejected
- **WHEN** a user submits `POST /login` with a token that does not match `REVIEW_TOKEN`
- **THEN** the system re-renders the login page with an error message and does not set a session cookie

### Requirement: Web UI is mobile-friendly
The system SHALL render all pages with responsive layout suitable for use on a mobile browser. Draft body text SHALL be fully readable without horizontal scrolling.

#### Scenario: Draft body renders legibly on small screens
- **WHEN** an authenticated user views a draft on a viewport width of 375px or less
- **THEN** the draft body text wraps and remains fully readable without horizontal overflow

### Requirement: REVIEW_TOKEN must be set to start the web service
The system SHALL refuse to start the web service if the `REVIEW_TOKEN` environment variable is not set or is empty.

#### Scenario: Missing token prevents startup
- **WHEN** the web service starts without `REVIEW_TOKEN` set
- **THEN** the process exits with a non-zero exit code and logs a clear error message
