class AX206Error(Exception):
    """Base exception for pyax206."""

class AX206NotFoundError(AX206Error):
    """Device not found or not accessible."""

class AX206USBError(AX206Error):
    """Low-level USB error."""

class AX206ProtocolError(AX206Error):
    """Protocol or device status error."""
