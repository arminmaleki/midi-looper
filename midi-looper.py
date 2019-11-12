import pdb
import threading as th
#Jack interface library,needs to be installed
import jack
import binascii
import struct
import time
import random


client = jack.Client("Seq")
port = client.midi_inports.register("input")
outports=[]
outports.append(client.midi_outports.register("metronom"))
outports.append(client.midi_outports.register("output1"))
outports.append(client.midi_outports.register("output2"))
outports.append(client.midi_outports.register("output3"))
outports.append(client.midi_outports.register("output4"))
outports.append(client.midi_outports.register("output5"))
outports.append(client.midi_outports.register("output6"))
outports.append(client.midi_outports.register("output7"))

live_port=0
current_slot=-1



class Seq:
    """Main sequencer class."""    
    seqs=[] #list of all sequencers
    attr={} 
    class SequencerThread(th.Thread):
        """ Sequencer's main Thread, checks when it is necessary to generate new notes"""
        def __init__(self,*args,**kwargs):
            super().__init__()
            self.seq=args[0]
            
        def run(self):
            while self.seq.active:
                time.sleep(.02)
                if self.seq.condition() :
                    self.seq.generate()
                
    
            
    def __init__(self,sampling=44100,tempo=90,name='untitled',bar=4,comp=2):
        self.sampling=sampling #rate
        self.tempo=tempo
        self.offset_frame=-1 #frame and beat off set, specially for changetempo
        self.offset_beat=0
        self.lock=th.Lock() #sequencers thread lock
        self.queue=[] #all notes to be played later
        self.active=False 
        self.name=name
        self.last_frame=-1
        self.processed_beat=0 #up to which beat every note is generated
        Seq.seqs.append(self)
      
        self.bar=bar #TODO number of beats in each bar
        self.comp=2  #TODO simple of complex bar
        
    def activate(self):
        self.active=True
        self.thread=Seq.SequencerThread(self)
        self.thread.start()

    def stop(self):
        self.active=False
        self.queue=[]
        self.processed_beat=0
        self.offset_frame=-1
        
    def calculate_beat_o(self,frame):
        """calculates corresponding beat for a given frame"""
        return (frame-self.offset_frame)/self.sampling*self.tempo/60+self.offset_beat

    def calculate_beat(self):
        """for current frame"""
        return (self.last_frame-self.offset_frame)/self.sampling*self.tempo/60+self.offset_beat
    
    def calculate_frame(self,beat):
        return int(self.offset_frame+(beat-self.offset_beat)*self.sampling/self.tempo*60)
    
    def condition(self):
        """condition calling the generator, that is notes left to be played"""
        return (-self.calculate_beat()+self.processed_beat<0.25)
    
    def set_generator(self,generator):
        """ used with python decorators"""
        self.generator=generator
        
    def generate(self):
        self.generator(self)
        
    def change_tempo(self,new_tempo):
        new_offset_frame=self.last_frame
        new_offset_beat=self.calculate_beat()
        self.offset_beat=new_offset_beat
        self.offset_frame=new_offset_frame
        self.tempo=new_tempo
        
    def note_on (self,time,pitch,vel,outport=0):
        #important: needs to be run with self.lock !
        self.queue.append((self.calculate_frame(time),  (0x90,pitch,vel),outport))
    def note_off(self,time,pitch,outport=0):
        self.queue.append((self.calculate_frame(time)-5,  (0x80,pitch,0x40),outport))
    def note(self,time,pitch,vel,length,outport=0):
        self.note_on (time,pitch,vel,outport)
        self.note_off(time+length,pitch,outport)
    
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
        
class Recorder:
    """ records and archives played notes when necessary, to be replayed later """
    recorders=[]
    @classmethod
    def new_note(cls,note):
        """this function is called in jack loop. informs Recorder class that something new is available"""
        for recorder in Recorder.recorders:
            if recorder.recording:
                recorder.recorded.append((
                    recorder.seq.calculate_beat_o(note[0]),(note[1][0],note[1][1],note[1][2]),note[2]))
    def __init__(self,seq):
        self.recorded=[]
        self.seq=seq
        self.recording=False
        self.playing=False
        Recorder.recorders.append(self)
        self.empty=True
        self.bars=1
        self.offset=0
        self.volume=1.0
        
    def clear(self):
        self.recorded=[]
        self.playing=False
    def record(self):
        self.clear()
        self.empty=False
        self.recording=True
        self.playing=False
    def stop(self):
        """stops recording and cleans what is recorded: quantize,decide how many bars,etc"""
        self.recording=False;
        if (len(self.recorded)==0):
            print('nothing recorded')
            return
        r=[]
        for note in self.recorded:
            r.append((round(note[0]*4)/4,note[1],note[2]))
        self.recorded=r
        offset=self.recorded[0][0]
        offset=-(round(offset*4) % 16)/4+offset
        r=[]
        for note in self.recorded:
            r.append((note[0]-offset,note[1],note[2]))
        self.recorded=r
        self.bars=int(self.recorded[-1][0]-self.recorded[0][0])//4+1
        buff=self.bars
        if (self.bars>2):
            buff=4
        if (self.bars>4):
            buff=8
        if (self.bars>8):
            buff=16
        self.bars=buff
        
        for note in self.recorded:
            print(note)
        print('number of bars:',self.bars)
            

        
        
    



@client.set_process_callback
def process(frames):
    """main jack loop"""
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
                
    
            
  
    for offset, data in port.incoming_midi_events():
        #print("{0}: {1} 0x{2}".format(client.last_frame_time,offset,binascii.hexlify(data).decode()))
        status, pitch, vel = struct.unpack('3B', data)
        if (status==0xb0):
            if (pitch in Controller.knobs):
                Controller.knobs[pitch].handler(vel)
      
        if (pitch in Controller.pads):
            Controller.pads[pitch].handler((status,vel))

        if ((status==0x80) or (status==0x90)):
            outports[live_port].write_midi_event(offset,(status,pitch,vel))
            Recorder.new_note((offset+client.last_frame_time,(status,pitch,vel),live_port))
    

with client:
    print("#" * 80)
    print("press Return to quit")
    print("#" * 80)
    seq=Seq(tempo=120)
    #rec1=Recorder(seq)
    b=0
    @seq.set_generator
    def generator(s):
        last=s.processed_beat
    
        C=0x3c-12
        rnd=int(random.random()*4)
        C+=rnd
        if ('shift' in s.attr):
            C+=s.attr['shift']
        with s.lock:
            # Metronom (to be played on a drum set0:

            seq.note(last,0x2a,0x70,1,0)
            seq.note(last+1,0x2a,0x05,1,0)
            seq.note(last+2,0x2a,0x05,1,0)
            seq.note(last+3,0x2a,0x05,1,0)

            #seq.note(last,C,0x70,4)
            #seq.note(last+1,C+10,0x40,1)
            #seq.note(last+2,C+4,0x40,1)
            #seq.note(last+3,C+10,0x40,1)
            
            for rec1 in Recorder.recorders:
                # to put the recorded lick 'just in time'
                if ((rec1.playing) and ((s.processed_beat//4))%rec1.bars==rec1.offset) :
                    #print('playin processed beat',(s.processed_beat//4))
                    
                    for note in rec1.recorded:
                        seq.queue.append((s.calculate_frame(last+note[0]),
                                      (note[1][0],note[1][1],
                                       min(127,round(note[1][2]*rec1.volume))

                                      ),
                                      note[2]))
            

            s.queue.sort()
            #pdb.set_trace()

                
            s.processed_beat+=4
            #print ("Beat difference:",s.processed_beat - s.calculate_beat())

    ctrl=Controller('knob',0x02,[seq],'knob2')
    @ctrl.set_handler
    def handler(c,info):
        c.seqs[0].change_tempo((40+info))
    slot_vol=Controller('knob',0x03,[seq],'knob23')
    @slot_vol.set_handler
    def handler(c,info):
        if (len(Recorder.recorders)==0):
            return
        global current_slot
        new_vol=info/127.0*2
        if (round(new_vol*100)%10==0):
            print ('current slot',current_slot,'new vol:',new_vol)
        Recorder.recorders[current_slot].volume=new_vol
        

        

    port_plus=Controller('knob',0x15,[seq],'portp')
    @port_plus.set_handler
    def handler(c,info):
        global live_port
        if (info>0):
            live_port+=1
            if (live_port>=len(outports)):
                live_port-=len(outports)
            print('New outport',live_port)

    port_minus=Controller('knob',0x16,[seq],'portm')
    @port_minus.set_handler
    def handler(c,info):
        global live_port
        if (info>0):
            live_port-=1
            if (live_port<0):
                live_port+=len(outports)
            print('New outport',live_port)
  

    new_slot_rec=Controller('knob',0x12,[seq],'portm')
    @new_slot_rec.set_handler
    def handler(c,info):
        global current_slot
        if (info>0):
            rec=Recorder(seq)
            rec.record()
            current_slot=len(Recorder.recorders)-1
            print('current slot',current_slot)
        else:
            Recorder.recorders[-1].stop()

    slot_play=Controller('knob',0x17,[seq],'portm')
    @slot_play.set_handler
    def handler(c,info):
        global current_slot
        if ((info>0)):
            print ('current slot:',current_slot,'volume:',Recorder.recorders[current_slot].volume)
            Recorder.recorders[current_slot].offset=((Recorder.recorders[current_slot].seq.processed_beat)//4)%Recorder.recorders[current_slot].bars
            Recorder.recorders[current_slot].playing=not Recorder.recorders[current_slot].playing
            #print('handler rec1 playing',(Recorder.recorders[current_slot].seq.processed_beat)//4)

    slot_plus=Controller('knob',0x13,[seq],'portp')
    @slot_plus.set_handler
    def handler(c,info):
        global current_slot
        if (info>0):
            current_slot+=1
            if (current_slot>=len(Recorder.recorders)):
                current_slot-=len(Recorder.recorders)
                if (current_slot>=len(Recorder.recorders)):
                    current_slot=0
            print('New slot',current_slot)

    slot_minus=Controller('knob',0x14,[seq],'portm')
    @slot_minus.set_handler
    def handler(c,info):
        global current_slot
        if (info>0):
            current_slot-=1
            if (current_slot<0):
                current_slot+=len(Recorder.recorders)
                #this only happens if no slot is alread recorded!
                if (current_slot<0):
                    current_slot=0
            print('New slot',current_slot)
    old_slot_rec=Controller('knob',0x11,[seq],'portm')
    @old_slot_rec.set_handler
    def handler(c,info):
        global current_slot
        if (info>0):
            if (current_slot<0):
                new_slot_rec.handler(c,info)
                
            rec=Recorder.recorders[current_slot]
            rec.record()
        else:
            Recorder.recorders[current_slot].stop()
            
            
     
    
    
    seq.activate()
    
    input()
    seq.stop()

    
