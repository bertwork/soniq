import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import SoniqApp

if __name__ == "__main__":
    SoniqApp().mainloop()
