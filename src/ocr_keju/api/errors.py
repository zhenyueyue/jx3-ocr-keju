class JX3BoxApiError(RuntimeError):
    """Network or HTTP-level failure while talking to JX3BOX."""


class JX3BoxProtocolError(JX3BoxApiError):
    """JX3BOX returned a response that does not match the expected schema."""
