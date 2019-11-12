import threading as th
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



class Seq:
    
    seqs=[]
    attr={}
    class MyThread(th.Thread):
        
        def __init__(self,*args,**kwargs):
            super().__init__()
            self.seq=args[0]
            
        def run(self):
            while True:
                time.sleep(.02)
                #print(self.seq.calculate_beat(),self.seq.processed_beat)
                #print(self.seq.condition())
                if self.seq.condition() :
                    self.seq.generate()
                
    
            
    def __init__(self,sampling=44100,tempo=90,name='untitled',bar=4,comp=2):
        self.sampling=sampling
        self.tempo=tempo
        self.offset_frame=-1
        self.offset_beat=0
        self.lock=th.Lock()
        self.queue=[]
        self.active=False
        self.name=name
        self.last_frame=-1
        self.processed_beat=0
        Seq.seqs.append(self)
        self.thread=Seq.MyThread(self)
        self.bar=bar
        self.comp=2
        
    def activate(self):
        self.active=True
        self.thread.start()
    def calculate_beat_o(self,frame):
        return (frame-self.offset_frame)/self.sampling*self.tempo/60+self.offset_beat

    def calculate_beat(self):
        return (self.last_frame-self.offset_frame)/self.sampling*self.tempo/60+self.offset_beat
    def calculate_frame(self,beat):
        return int(self.offset_frame+(beat-self.offset_beat)*self.sampling/self.tempo*60)
    def condition(self):
        return (-self.calculate_beat()+self.processed_beat<0.25)
    def set_generator(self,generator):
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
    recorders=[]
    @classmethod
    def new_note(cls,note):
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
        
    def clear(self):
        self.recorded=[]
        self.playing=False
    def record(self):
        self.clear()
        self.empty=False
        self.recording=True
        self.playing=False
    def stop(self):
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
    for outport in outports:
        outport.clear_buffer()
    for seq in Seq.seqs:
        if (seq.offset_frame < 0 ):
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

            seq.note(last,0x2a,0x70,1,0)
            seq.note(last+1,0x2a,0x40,1,0)
            seq.note(last+2,0x2a,0x40,1,0)
            seq.note(last+3,0x2a,0x40,1,0)

            #seq.note(last,C,0x70,4)
            #seq.note(last+1,C+10,0x40,1)
            #seq.note(last+2,C+4,0x40,1)
            #seq.note(last+3,C+10,0x40,1)
            for rec1 in Recorder.recorders:
                if ((rec1.playing) and ((s.processed_beat//4))%rec1.bars==rec1.offset) :
                    print('playin processed beat',(s.processed_beat//4))
                    
                    for note in rec1.recorded:
                        seq.queue.append((s.calculate_frame(last+note[0]),
                                      (note[1][0],note[1][1],note[1][2]),
                                      note[2]))
            

            s.queue.sort()

                
            s.processed_beat+=4
            print ("Beat difference:",s.processed_beat - s.calculate_beat())

    ctrl=Controller('knob',0x02,[seq],'knob2')
    @ctrl.set_handler
    def handler(c,info):
        c.seqs[0].change_tempo((40+info))
        
   

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
        if (info>0):
            rec=Recorder(seq)
            rec.record()
        else:
            Recorder.recorders[-1].stop()

    slot_play=Controller('knob',0x17,[seq],'portm')
    @slot_play.set_handler
    def handler(c,info):
        if ((info>0)):
            Recorder.recorders[-1].offset=((Recorder.recorders[-1].seq.processed_beat)//4)%Recorder.recorders[-1].bars
            Recorder.recorders[-1].playing=not Recorder.recorders[-1].playing
            print('handler rec1 playing',(Recorder.recorders[-1].seq.processed_beat)//4)
            
            
     
    
    
    seq.activate()
    
    input()
