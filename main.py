"""Audio Folder Unifier: make a whole folder of audio sound consistent."""

import sys


def main():
    if sys.platform == "win32" and not getattr(sys, "frozen", False):
        # Running as a script: show our icon in the taskbar instead of python.exe's
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Reactorcore.AudioFolderUnifier")

    from gui.app import App
    App().run()


if __name__ == "__main__":
    main()
