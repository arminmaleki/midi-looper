import threading as th
import time
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
        self.comp=comp  #TODO simple of complex bar
        
    def activate(self):
        self.active=True
        self.thread=Seq.SequencerThread(self)
        self.thread.start()

    def stop(self):
        self.active=False
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
    def metronom(self,last,code):
        self.note(last,code,0x70,1,0)
        for i in range(self.bar-1):
            self.note(last+i+1,code,0x05,1,0)
        
