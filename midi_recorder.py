import json

current_slot=-1
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
    @classmethod
    def to_json(cls,file_name):
       
        recs=[]
        for recorder in Recorder.recorders:
            if (not recorder.empty):
                recs.append(recorder.all_data())
        all_data={'records':recs}
        with open(file_name,'w') as f:
            json.dump(all_data,f)

    @classmethod
    def from_json(cls,file_name,seq):
        with open(file_name,'r') as f:
            j=json.load(f)
            for rec in j['records']:
                new_rec=Recorder(seq)
                for note in rec['notes']:
                    new_rec.recorded.append(note)
                    print (new_rec.recorded[-1])
                new_rec.playing=rec['meta']['playing']
                new_rec.volume=rec['meta']['volume']
                new_rec.offset=rec['meta']['offset']
                new_rec.bars=rec['meta']['bars']
                new_rec.empty=False

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
        quant=self.seq.comp
        if (quant<3):
            quant=quant*2
        print('quant is:',quant)
        for note in self.recorded:
            r.append((round(note[0]*quant)/quant,note[1],note[2]))
        self.recorded=r
        offset=self.recorded[0][0]
        offset=-(round(offset*quant) % (quant*self.seq.bar))/quant+offset
        r=[]
        for note in self.recorded:
            r.append((note[0]-offset,note[1],note[2]))
        self.recorded=r
        self.bars=int(self.recorded[-1][0]-self.recorded[0][0])//self.seq.bar+1
        buff=self.bars
        if (self.bars>2):
            buff=4
        if (self.bars>4):
            buff=8
        if (self.bars>8):
            buff=12
        if (self.bars>12):
            buff=16
        self.bars=buff
        
        for note in self.recorded:
            print(note)
        print('number of bars:',self.bars)
    def all_data(self):
        me={}
        me['meta']={'bars':self.bars,'offset':self.offset,'volume':self.volume,'playing':self.playing}
        me['notes']=self.recorded
        return me

            
def current_rec():
    return Recorder.recorders[current_slot]

def slot_minus():
    global current_slot
    current_slot-=1
    if (current_slot<0):
        current_slot+=len(Recorder.recorders)
        #this only happens if no slot is alread recorded!
        if (current_slot<0):
            current_slot=0
    print('New slot',current_slot)

def slot_plus():
    global current_slot
    current_slot+=1
    if (current_slot>=len(Recorder.recorders)):
        current_slot-=len(Recorder.recorders)
        if (current_slot>=len(Recorder.recorders)):
            current_slot=0
    print('New slot',current_slot)

def get_current_slot():
    global current_slot
    return current_slot

def set_current_slot(i):
    global current_slot
    current_slot=i

