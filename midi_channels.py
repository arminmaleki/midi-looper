outports=[]
inports=[]
live_port=0
def create_channels(client,number=7):

    global inport
    inports.append(client.midi_inports.register("input"))

    outports.append(client.midi_outports.register("metronom"))

    for i in range(number):
        outports.append(client.midi_outports.register("output"+str(i)))

def port_plus():
    global live_port
    live_port+=1
    if (live_port>=len(outports)):
        live_port-=len(outports)
    print('New outport',live_port)

def port_minus():
    global live_port
    live_port-=1
    if (live_port<0):
        live_port+=len(outports)
    print('New outport',live_port)

def get_live_port():
    global live_port
    return live_port

