import json
import midi_gui as gui


current_slot=-1
class Recorder:
    """ records and archives played notes when necessary, to be replayed later """
    recorders=[]
    groups=[]
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
        all_data={'records':recs,'groups':Recorder.groups}
        with open(file_name,'w') as f:
            json.dump(all_data,f)
        gui.message({"event":"saved",
                             "text":
                             gui.Color.BLUE+"All data saved to file"+gui.Color.CLOSE
                })

    @classmethod
    def from_json(cls,file_name,seq):
        with open(file_name,'r') as f:
            j=json.load(f)
            for rec in j['records']:
                new_rec=Recorder(seq)
                for note in rec['notes']:
                    new_rec.recorded.append(note)
                    #print (new_rec.recorded[-1])
                #new_rec.playing=rec['meta']['playing']
                #new_rec.volume=rec['meta']['volume']
                #new_rec.offset=rec['meta']['offset']
                #new_rec.bars=rec['meta']['bars']
                for key in rec['meta']:
                    print("FROM JSON "+str(key)+" "+str(rec['meta'][key]))
                    new_rec.__dict__[key]=rec['meta'][key]
                new_rec.empty=False
            
                gui.message({"event":"new_record","subevent":"json","info":new_rec.all_data(),
                             "index":new_rec.index,
                             "text":
                             gui.Color.BLUE+"New record from json  "+str(new_rec.index)+gui.Color.CLOSE
                })
            Recorder.groups=j['groups']
            gui.message({"event":"groups","subevent":"json","info":Recorder.groups,
                         
                         "text":
                         gui.Color.YELLOW+"groups loaded"+gui.Color.CLOSE
            })

    def __init__(self,seq):
        self.recorded=[]
        self.seq=seq
        self.recording=False
        self.playing=False
        Recorder.recorders.append(self)
        self.index=len(Recorder.recorders)-1
        self.empty=True
        self.bars=1
        self.offset=0
        self.volume=1.0
        self.keep_offset=False
        
    def clear(self):
        self.recorded=[]
        self.playing=False
        self.empty=True
        gui.message({"event":"record_cleared",
                             "index":self.index,
                             "text":
                     gui.Color.RED+"Record "+str(self.index)+" cleared!"+gui.Color.CLOSE})
    def record(self):
        self.clear()
        self.empty=False
        self.recording=True
        self.playing=False
        gui.message({"event":"recording",
                             "index":self.index,'status':True,
                             "text":
                     gui.Color.RED+"Record "+str(self.index)+" recording"+gui.Color.CLOSE})
    def stop(self):
        """stops recording and cleans what is recorded: quantize,decide how many bars,etc"""
        self.recording=False;
        gui.message({"event":"recording",
                             "index":self.index,'status':False,
                             "text":
                     gui.Color.RED+"Record "+str(self.index)+" recording"+gui.Color.CLOSE})
        if (len(self.recorded)==0):
                    gui.message({"event":"no_rec",
                             "text":
                             gui.Color.RED+"Nothing recorded!"+gui.Color.CLOSE
                })
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
        gui.message({"event":"recorded","info":self.all_data(),
                             "index":self.index,
                             "text":
                     gui.Color.BLUE+"Slot "+str(self.index)+" recorded,number of bars: "+str(self.bars)+gui.Color.CLOSE})
        #print('number of bars:',self.bars)
    def all_data(self):
        me={}
        me['meta']={'bars':self.bars,'offset':self.offset,'volume':self.volume,
                    'playing':self.playing,'empty':self.empty}
        if ('channel' in self.__dict__):
            me['meta']['channel']=self.channel;
        if ('pitch' in self.__dict__):
            me['meta']['pitch']=self.pitch;
        if ('keep_offset' in self.__dict__):
            me['meta']['keep_offset']=self.keep_offset;
            
        me['notes']=self.recorded
        return me
    def clone(ind):
        orig=Recorder.recorders[ind]
        r=Recorder(orig.seq)
        for note in orig.recorded:
            r.recorded.append(note)
        
        r.bars=orig.bars
        r.offset=orig.offset
        r.volume=orig.volume
        
        if ('channel' in orig.__dict__):
            r.channel=orig.channel;
        if ('pitch' in orig.__dict__):
            r.pitch=orig.pitch;
        if ('keep_offset' in orig.__dict__):
            r.keep_offset=orig.keep_offset;
        r.empty=False;
        gui.message({"event":"recorded","info":r.all_data(),
                             "index":r.index,
                             "text":
                     gui.Color.BLUE+"Slot "+str(ind)+" cloned "+gui.Color.CLOSE})
        def tog_list(self):
            dest_stat=not Recorder.recorders[current_slot].playing
            
            gr=[]
            for g in Recorder.groups:
                if (current_slot in g['members']):
                    gr.append(g)

            

            


                                   
            
            
                               
                        
                    
                    

                    
            
            
        

            
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
    gui.message({"event":"slot_change","subevent":"minus",
                             "number":current_slot,
                             "text":
                 gui.Color.YELLOW+"Active slot changed to "+str(current_slot)+gui.Color.CLOSE})
            
    #print('New slot',current_slot)
    

def slot_plus():
    global current_slot
    current_slot+=1
    if (current_slot>=len(Recorder.recorders)):
        current_slot-=len(Recorder.recorders)
        if (current_slot>=len(Recorder.recorders)):
            current_slot=0
    gui.message({"event":"slot_change","subevent":"plus","number":current_slot,
                  "text":
                 gui.Color.YELLOW+"Active slot changed to "+str(current_slot)+gui.Color.CLOSE})       
    #print('New slot',current_slot)

def get_current_slot():
    global current_slot
    return current_slot

def set_current_slot(i):
    global current_slot
    current_slot=i

