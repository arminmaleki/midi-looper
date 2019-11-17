from enum import Enum


class GUI(Enum):
    NONE=0
    PRINT=1
    SERVER=2
    CURSES=3
    QT=4
class Color:
    WHITE="\033[1;37m"
    RED="\033[1;31m"
    YELLOW="\033[1;33m"
    CLOSE="\033[0m"
    BLUE="\033[1;34m"
    GREEN="\033[1;32m"
    
gui_type=GUI.PRINT

gui_buffer=[]

def message(m):
    if (gui_type==GUI.NONE):
        return
    if (gui_type==GUI.PRINT):
        print(m['text'])
    if (gui_type==GUI.SERVER):
        gui_buffer.append(m)

