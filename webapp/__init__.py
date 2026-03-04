# Install custom exception handler before any imports that might fail
from core.util.traceback import install_custom_excepthook

install_custom_excepthook()
