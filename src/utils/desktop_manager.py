import ctypes
import logging

from .typing_engine import HumanTypist

# Windows API Constants
GENERIC_ALL = 0x10000000
DESKTOP_SWITCHDESKTOP = 0x0100
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_READOBJECTS = 0x0001
DESKTOP_CREATEMENU = 0x0004
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_ENUMERATE = 0x0040
DESKTOP_HOOKCONTROL = 0x0008
DESKTOP_JOURNALPLAYBACK = 0x0020
DESKTOP_JOURNALRECORD = 0x0010
DESKTOP_READCONTROL = 0x00020000
DESKTOP_WRITEDAC = 0x00040000

# Strict access mask for what we essentially need
ACCESS_FLAGS = (
    DESKTOP_READOBJECTS
    | DESKTOP_WRITEOBJECTS
    | DESKTOP_CREATEWINDOW
    | DESKTOP_CREATEMENU
    | DESKTOP_HOOKCONTROL
    | DESKTOP_JOURNALRECORD
    | DESKTOP_JOURNALPLAYBACK
    | DESKTOP_ENUMERATE
    | DESKTOP_SWITCHDESKTOP
    | 0x02000000  # MAXIMUM_ALLOWED
)

logger = logging.getLogger("DesktopMgr")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def get_current_desktop_name():
    try:
        h_desktop = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
        length = ctypes.c_ulong()
        user32.GetUserObjectInformationW(
            h_desktop, 2, None, 0, ctypes.byref(length)
        )  # UOI_NAME = 2
        buff = ctypes.create_unicode_buffer(length.value)
        user32.GetUserObjectInformationW(
            h_desktop, 2, buff, length, ctypes.byref(length)
        )
        return buff.value
    except Exception:
        return "Unknown"


def switch_to_input_desktop():
    """
    Attempts to switch the current thread to the active Input Desktop.
    Useful when an application (like SEB or UAC) switches to a secure desktop.
    Returns:
        True if currently attached to the input desktop (switched or already there).
        False if failed to open/switch.
    """
    try:
        current_name = get_current_desktop_name()

        # Open the currently active input desktop
        # First try maximal access
        h_input_desktop = user32.OpenInputDesktop(0, False, GENERIC_ALL)

        if not h_input_desktop:
            # Retry with specific rights needed for screenshots/input
            h_input_desktop = user32.OpenInputDesktop(0, False, ACCESS_FLAGS)

        if not h_input_desktop:
            # Even if we can't open it (e.g., access denied), we might be on it?
            # But usually we can open our own desktop.
            # If we can't open it, we can't switch to it anyway.
            # Just log and return False
            err = ctypes.get_last_error()
            # 5 = Access Denied. Likely need to run as SYSTEM for UAC secure desktops.
            # But for SEB running as user, it might work if same user.
            if err != 0:
                logger.debug(f"OpenInputDesktop failed. Error: {err}")
            return False

        # Get name of input desktop
        length = ctypes.c_ulong()
        user32.GetUserObjectInformationW(
            h_input_desktop, 2, None, 0, ctypes.byref(length)
        )
        buff = ctypes.create_unicode_buffer(length.value)
        user32.GetUserObjectInformationW(
            h_input_desktop, 2, buff, length, ctypes.byref(length)
        )
        input_name = buff.value

        if current_name != input_name:
            logger.info(
                f"Desktop Switch Detected! Current: '{current_name}' -> Input: '{input_name}'"
            )
            # Switch thread to this desktop
            success = user32.SetThreadDesktop(h_input_desktop)
            if not success:
                err = ctypes.get_last_error()
                logger.error(
                    f"Failed to switch thread desktop to '{input_name}'. Error: {err}"
                )
                user32.CloseDesktop(h_input_desktop)
                return False
            else:
                logger.info(f"Successfully attached to desktop: '{input_name}'")
                # We need to keep the handle open if we want to stay attached?
                # Actually, SetThreadDesktop keeps it?
                # "The SetThreadDesktop function replaces the desktop for the specified thread...
                # The system closes the handle to the old desktop automatically,
                # unless we want to be explicit, but CloseDesktop behavior is tricky if it's the current one.
                # But h_input_desktop is a new handle we just opened.
                # We should NOT close it immediately if it's the current desktop now?
                # Actually it's fine to close the handle *if* SetThreadDesktop incremented the ref on the object.
                # Windows docs are vague. But typically we can close this specific handle if thread is attached.
                user32.CloseDesktop(h_input_desktop)
                return True
        else:
            # We are already on the correct desktop
            user32.CloseDesktop(h_input_desktop)
            return True

    except Exception as e:
        logger.error(f"Desktop switch exception: {e}")
        return False


# =============================================================================
# KEYBOARD SIMULATION
# =============================================================================

# Ctypes structures for SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_ushort),
        ("wParamH", ctypes.c_ushort),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", INPUT_I)]


# Constants
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
VK_RETURN = 0x0D


def _send_vk(vk_code):
    """
    Sends a virtual key code (non-unicode)
    """
    # Key Down
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down.ii.ki.wVk = vk_code
    inp_down.ii.ki.wScan = 0
    inp_down.ii.ki.dwFlags = 0
    inp_down.ii.ki.time = 0
    inp_down.ii.ki.dwExtraInfo = None

    # Key Up
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up.ii.ki.wVk = vk_code
    inp_up.ii.ki.wScan = 0
    inp_up.ii.ki.dwFlags = KEYEVENTF_KEYUP
    inp_up.ii.ki.time = 0
    inp_up.ii.ki.dwExtraInfo = None

    # Send
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))


def _send_char(char):
    """
    Sends a single unicode character using SendInput.
    This works for most keyboard layouts and isolated desktops.
    """
    # Create inputs for KeyDown and KeyUp
    # We use UNICODE mode to support all characters easily

    # Key Down
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down.ii.ki.wVk = 0
    inp_down.ii.ki.wScan = ord(char)
    inp_down.ii.ki.dwFlags = KEYEVENTF_UNICODE
    inp_down.ii.ki.time = 0
    inp_down.ii.ki.dwExtraInfo = None

    # Key Up
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up.ii.ki.wVk = 0
    inp_up.ii.ki.wScan = ord(char)
    inp_up.ii.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inp_up.ii.ki.time = 0
    inp_up.ii.ki.dwExtraInfo = None

    # Send
    user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))
    user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))


# =============================================================================
# HUMAN-LIKE TYPING ENGINE
# =============================================================================


def type_text_human_like(text, min_wpm=30, max_wpm=70, error_rate=0.03):
    """
    Types text with hyper-realistic human characteristics using HumanTypist engine.

    Args:
        text (str): The text to type.
        min_wpm (int): Minimum words per minute.
        max_wpm (int): Maximum words per minute.
        error_rate (float): Probability of errors.
    """
    typist = HumanTypist(min_wpm=min_wpm, max_wpm=max_wpm, error_rate=error_rate)
    typist.type_text(text)
