import midi_gui as gui
outports=[]
inports=[]
live_port=0
def create_channels(client,number=7):

    global inport
    inports.append(client.midi_inports.register("input"))

    outports.append(client.midi_outports.register("metronom"))

    for i in range(number):
        outports.append(client.midi_outports.register("output"+str(i)))
    gui.message({"event":"new_channels","number":i+1,
                 "text":gui.Color.BLUE+str(i+1)+" midi channels created"+gui.Color.CLOSE})

def port_plus():
    global live_port
    live_port+=1
    if (live_port>=len(outports)):
        live_port-=len(outports)
    gui.message({"event":"channel_change","subevent":"plus","number":live_port,
                 "text":gui.Color.GREEN+"New midi port is "+str(live_port)+gui.Color.CLOSE})

def port_minus():
    global live_port
    live_port-=1
    if (live_port<0):
        live_port+=len(outports)
    gui.message({"event":"channel_change","subevent":"minus","number":live_port,
                 "text":gui.Color.GREEN+"New midi port is "+str(live_port)+gui.Color.CLOSE})

def get_live_port():
    global live_port
    return live_port

