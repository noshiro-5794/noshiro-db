# Transition affordances

Things the service does **because Django is still running**, not because they are
the design. Each row names the condition that removes it. None of them should
survive the cutover, and none of them should be presented as a feature.

| Affordance | Why it exists | Removed when |
|---|---|---|
| `pbkdf2_sha256` password verifier | that is the format Django wrote | every account has been re-hashed with argon2id and the column rewritten |
| `hash_password` claim | SimpleJWT writes the digest of the password hash under this name, and refresh cookies already in browsers carry it | the Django service stops issuing tokens; the claim becomes a random token version stored on the user |
| Accepting a token minted by Django | a session opened before the cutover must not be logged out | the cutover is complete and the old cookie has expired (30 days) |
| Minting a token Django accepts | during the parallel run the web client may send one token to either service | the same moment |
| `X-Forwarded-Proto` reading | Django refuses insecure requests; the new service must agree during the parallel run | the service is the only one behind the proxy |
| `about:blank` for plain 404s | Django's handler emits it for `NotFound` but a type URI for domain errors | the last Django response is gone |

## The token contract this service wants

Once nothing else has to read it:

```json
{"sub": "42", "type": "access", "ver": 3, "jti": "…", "iat": …, "exp": …}
```

- `sub` is the user id, `type` replaces `token_type`;
- `ver` is a per-user token version, bumped on password change — revocation by
  comparison instead of a digest of a hash nobody else needs;
- no digest of the password hash in the token: a stolen token already grants the
  session, and embedding the hash only makes rotation fragile.

That change needs a migration window (old tokens must keep working until they
expire), which is why it happens after the switch, not before.
