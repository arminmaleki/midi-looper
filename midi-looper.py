import json
import threading as th
#Jack interface library,needs to be installed
import jack
import binascii
import struct
import time
import random

###########local imports#############

import midi_channels
from midi_channels import outports,inports,get_live_port
from midi_sequencer import Seq
import midi_recorder
from midi_recorder import Recorder,current_rec,get_current_slot,set_current_slot



client = jack.Client("midi-looper")
midi_channels.create_channels(client)

class Controller:
    """ each controller is assigned with some midi control on keyboard. there are two types of them:
    those associated with knobs and those associated with pads (or normal midi notes).this class
    keeps a list of what is available later to be called by jack's loop"""
    pads={}
    knobs={}
    def __init__(self,ctype,ccode,seqs,name='untitled'):
        if (ctype=='knob'):
            Controller.knobs[ccode]=self;
        if (ctype=='pad'):
            Controller.pads[ccode]=self;
        self.name=name
        self.seqs=seqs
        
    def set_handler(self,handler):
        self.handle=handler
    def handler(self,info):
        self.handle(self,info)
        
        
###########Jack binding##################             
@client.set_process_callback
def process(frames):
    """main jack loop.connects jack midi engine to our controllers and multiplexer"""
    for outport in outports:
        outport.clear_buffer()
    for seq in Seq.seqs:
        if ((seq.active) and (seq.offset_frame < 0) ):
            seq.offset_frame=client.last_frame_time
            print(seq.name)
        seq.last_frame=client.last_frame_time
        with seq.lock:
            if (len(seq.queue)>0):
                while (client.last_frame_time>seq.queue[0][0]):
                    command=seq.queue.pop(0)
                    #print (command[1])
                    if (len(command)==2):
                        outport=outports[0]
                    else:
                        outport=outports[command[2]]
                        
                    outport.write_midi_event(0,command[1])
                    if (len(seq.queue)==0):
                        break
            
    for offset, data in inports[0].incoming_midi_events():
        #print("{0}: {1} 0x{2}".format(client.last_frame_time,offset,binascii.hexlify(data).decode()))
        status, pitch, vel = struct.unpack('3B', data)
        if (status==0xb0):
            if (pitch in Controller.knobs):
                Controller.knobs[pitch].handler(vel)
      
        if (pitch in Controller.pads):
            Controller.pads[pitch].handler((status,vel))

        if ((status==0x80) or (status==0x90)):
            outports[get_live_port()].write_midi_event(offset,(status,pitch,vel))
            Recorder.new_note((offset+client.last_frame_time,(status,pitch,vel),get_live_port()))

##########################################################################            
###### defines the sequencer, how it interacts with recorders and metronom
seq=Seq(tempo=120,bar=2,comp=3)

@seq.set_generator
def generator(s):
    """this function puts notes in the queue to be played. s is the associated sequencer"""
    last=s.processed_beat
    
    with s.lock:
        # Metronom (to be played on a drum set0:
        s.metronom(last,0x2a)

        for rec1 in Recorder.recorders:
            # to put the recorded lick 'just in time'
            if ((rec1.playing) and ((s.processed_beat//s.bar))%rec1.bars==rec1.offset
                and (rec1.seq==s)) :
                #print('playin processed beat',(s.processed_beat//4))
                    
                for note in rec1.recorded:
                    s.queue.append((s.calculate_frame(last+note[0]),
                                    (note[1][0],note[1][1],
                                       min(127,round(note[1][2]*rec1.volume))

                                      ),
                                      note[2]))

        s.queue.sort()
        s.processed_beat+=s.bar 

################Controller setup################################

def define_controllers():
    """this function defines the binding between program functions and the midi keyboard"""
    ctrl=Controller('knob',0x02,[seq],'knob2')
    @ctrl.set_handler
    def handler(c,info):
        c.seqs[0].change_tempo((40+info))
        
    slot_vol=Controller('knob',0x03,[seq],'knob23')
    @slot_vol.set_handler
    def handler(c,info):
        if (len(Recorder.recorders)==0):
            return
        new_vol=info/127.0*2
        if (round(new_vol*100)%10==0):
            print ('current slot',get_current_slot(),'new vol:',new_vol)
        current_rec().volume=new_vol

    port_plus=Controller('knob',0x15,[seq],'portp')
    @port_plus.set_handler
    def handler(c,info):
        if (info>0):
            midi_channels.port_plus()
        print('new port @',get_live_port())
          

    port_minus=Controller('knob',0x16,[seq],'portm')
    @port_minus.set_handler
    def handler(c,info):
        if (info>0):
            midi_channels.port_minus()
  

    new_slot_rec=Controller('knob',0x12,[seq],'portm')
    @new_slot_rec.set_handler
    def handler(c,info):
        if (info>0):
            Recorder(seq).record()
            set_current_slot(len(Recorder.recorders)-1)
            print('current slot',get_current_slot())
        else:
            Recorder.recorders[-1].stop()

    slot_play=Controller('knob',0x17,[seq],'portm')
    @slot_play.set_handler
    def handler(c,info):
        if ((info>0)):
            print ('current slot:',get_current_slot(),'volume:',current_rec().volume)
            current_rec().offset=((current_rec().seq.processed_beat)//4)%current_rec().bars
            current_rec().playing=not current_rec().playing

    slot_plus=Controller('knob',0x13,[seq],'portp')
    @slot_plus.set_handler
    def handler(c,info):
        if (info>0):
            midi_recorder.slot_plus()

    slot_minus=Controller('knob',0x14,[seq],'portm')
    @slot_minus.set_handler
    def handler(c,info):
         if (info>0):
            midi_recorder.slot_minus()

    old_slot_rec=Controller('knob',0x11,[seq],'portm')
    @old_slot_rec.set_handler
    def handler(c,info):
         if (info>0):
            if (get_current_slot()<0):
                new_slot_rec.handler(c,info)
                
            current_rec().record()
         else:
            current_rec().stop()

define_controllers()

##################midi-loopers main loop####################

with client:
    print("#" * 80)
    print("press Return to quit")
    print("#" * 80)
    
    
    seq.activate()
#    Recorder.from_json('test.json',seq)
  
    s=input()
    seq.stop()
    Recorder.to_json('test2.json')
    input()
    

    
