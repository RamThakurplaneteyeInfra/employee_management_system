# Clients APIs – Testing reference

Base prefix: `{{baseurl}}/clients/` (or whichever prefix you mount `Clients/urls.py` under).

Use this file to document all executable APIs in the `Clients` app (client profiles, stages, conversations).

---

## 1. Client stages

Endpoints to list or manage `Current_client_stage` entries.

> Add URLs, methods, and sample responses for stage listing and any admin operations.

---

## 2. Client profiles

Endpoints for `ClientProfile`:

- Create / update / delete client profiles.
- List and filter by `status`, `Product`, `created_by`, etc.

> Document base URLs, request bodies, and typical responses.

---

## 3. Client conversations

Endpoints for `ClientConversation`:

- Add conversation notes for a client.
- List conversations for a given client.

> Add detailed examples for creating and fetching conversations.

