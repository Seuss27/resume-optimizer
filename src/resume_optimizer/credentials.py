"""The one reader of provider API keys (plan §3.8): the OS keyring, under one service name.

No other module reads a provider API key or touches the keyring. There is no
environment-variable fallback, and no function here puts a secret value into a log record, an
exception message or a `repr`.
"""

import keyring
import keyring.errors

SERVICE_NAME: str = "resume-optimizer"

# Credential name -> keyring username. The ledger token is not here: the ledger writer owns it.
_USERNAMES: dict[str, str] = {
    "gemini": "gemini-api-key",
    "anthropic": "anthropic-api-key",
    "perplexity": "perplexity-api-key",
}


class MissingCredentialError(RuntimeError):
    """A credential is absent from the keyring, or the keyring cannot be used."""


def get_credential(name: str) -> str:
    """Reads one provider API key from the OS keyring.

    Args:
        name: One of "gemini", "anthropic" or "perplexity".

    Returns:
        The stored value, exactly as stored.

    Raises:
        ValueError: `name` is not a known credential.
        MissingCredentialError: The entry is missing, empty or malformed (surrounding
            whitespace or a control character), or the keyring is unusable.
    """
    if name not in _USERNAMES:
        raise ValueError(f"Unknown credential name: {name!r}")
    username: str = _USERNAMES[name]
    hint: str = f"python -m keyring set {SERVICE_NAME} {username}"
    backend = keyring.get_keyring()
    backend_name: str = type(backend).__name__
    try:
        value: str | None = backend.get_password(SERVICE_NAME, username)
    except keyring.errors.KeyringError as exc:
        raise MissingCredentialError(
            f"The keyring backend {backend_name} could not read {SERVICE_NAME}/{username}. "
            f"Store the entry with: {hint}"
        ) from exc
    if not value:
        raise MissingCredentialError(
            f"No credential stored for {SERVICE_NAME}/{username} (backend {backend_name}). "
            f"Store it with: {hint}"
        )
    # A key with surrounding whitespace, a control character or any non-ASCII character is
    # rejected, never stripped: the HTTP layer would refuse it with an error that can quote the
    # whole value.
    if value != value.strip() or not (value.isascii() and value.isprintable()):
        raise MissingCredentialError(
            f"The stored credential {SERVICE_NAME}/{username} is malformed (surrounding "
            f"whitespace or a control character). Store it again with: {hint}"
        )
    return value
