import json
import threading as th
#Jack interface library,needs to be installed
import jack
import binascii
import struct
import time
import random
import flask
###########local imports#############

import midi_channels
from midi_channels import outports,inports,get_live_port
from midi_sequencer import Seq
import midi_recorder
from midi_recorder import Recorder,current_rec,get_current_slot,set_current_slot
import midi_gui as gui


client = jack.Client("midi-looper")

gui.gui_type=gui.GUI.SERVER

midi_channels.create_channels(client)



class Controller:
    """ each controller is assigned with some midi control on keyboard. there are two types of them:
    those associated with knobs and those associated with pads (or normal midi notes).this class
    keeps a list of what is available later to be called by jack's loop"""
    pads={}
    knobs={}
    by_name={}
    last_midi=-1
    def __init__(self,ctype,ccode,seqs,name='untitled'):
        if (ctype=='knob'):
            Controller.knobs[ccode]=self;
        if (ctype=='pad'):
            Controller.pads[ccode]=self;
        self.name=name
        Controller.by_name[name]=self;
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
        Controller.last=pitch
        if (status==0xb0):
            if (pitch in Controller.knobs):
                Controller.knobs[pitch].handler(vel)
      
        if (pitch in Controller.pads):
            Controller.pads[pitch].handler((status,vel))

        elif ((status==0x80) or (status==0x90)):
            outports[get_live_port()].write_midi_event(offset,(status,pitch,vel))
            Recorder.new_note((offset+client.last_frame_time,(status,pitch,vel),get_live_port()))
##########################################################################
def gr_recur(gr,actual,slot,depth):
    print('depth '+str(depth)+' slot '+str(slot)+' value '+str(actual[slot]))
    print(actual)
    pre_map={}
    err=False
    
        
    touched_list={}

    gr_slot=[]
    dest_stat=not actual[slot]
    
    for g in gr:
        if (g['enabled']):
            if (slot in g['elements']):
                gr_slot.append(g)
    print (gr_slot)

    for g in gr_slot:
        if (g['type']=='c'):
            for s in g['elements']:
                if (s!=slot):
                    pre_map[s]=dest_stat
                    touched_list[s]=dest_stat
        if (g['type']=='x' and dest_stat==True):
            for s in g['elements']:
                if (s!=slot):
                    pre_map[s]=False
                    if (s in touched_list):
                        print('conflict in flip list!')
                        err=True
                        return [],err
                    touched_list[s]=False
    for g in gr:
        if (len(g['elements'])>0):
            if (g['elements'][0]==slot and g['type']=='ms'):
                pre_map[g['elements'][1]]=not dest_stat
                if (g['elements'][1] in touched_list):
                    if not (touched_list[g['elements'][1]] == (not dest_stat)):
                        err=True
                        return [],err
                touched_list[g['elements'][1]]=not dest_stat
                

    
    print(pre_map)
    res=[]
    for s in actual:
        res.append(s)
    for m in pre_map:
        res[m]=pre_map[m]
    print("depth: "+str(depth)+"res: "+str(res))

    flip_list=[]

    for i in range(len(actual)):
        if (not((res[i] and actual[i])or(not res[i] and not actual[i]))):
            flip_list.append(i)
    print("depth: "+str(depth)+" flip_list: "+str(flip_list))

    actual[slot]=not actual[slot]
    depth-=1
    if (depth<0 or len(flip_list)==0):
        return flip_list,err

    flip_list_new=[]

    #for fl in flip_list:
    #    flip_list_new.append(fl)
        

    for flip in flip_list:
        if flip in flip_list_new:
            continue
        flip_list_new.append(flip)
        fl_new,err_new =gr_recur(gr,actual,flip,depth)
        if err_new:
            err=True
            break
        for fl in fl_new:
            if fl in flip_list_new:
                err=True
                break
            flip_list_new.append(fl)
            
    return flip_list_new,err

##########################################################################            
###### defines the sequencer, how it interacts with recorders and metronom
seq=Seq(tempo=120,bar=4,comp=2)

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
                    pitch=note[1][1]
                    if ('pitch' in rec1.__dict__):
                        pitch+=rec1.pitch
                    channel=note[2]
                    if ('channel' in rec1.__dict__):
                        channel=rec1.channel
                        
                        
                        
                    s.queue.append((s.calculate_frame(last+note[0]),
                                    (note[1][0],pitch,
                                       min(127,round(note[1][2]*rec1.volume))

                                      ),
                                      channel))

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
        #print('new port @',get_live_port())
          

    port_minus=Controller('knob',0x16,[seq],'portm')
    @port_minus.set_handler
    def handler(c,info):
        if (info>0):
            midi_channels.port_minus()
  

    new_slot_rec=Controller('knob',0x12,[seq],'portm')
    @new_slot_rec.set_handler
    def handler(c,info):
        if (info>0):
            if (get_current_slot()>=0):
                if (not current_rec().recording):
                    Recorder(seq).record()
                    set_current_slot(len(Recorder.recorders)-1)
                else:
                    Recorder.recorders[-1].stop()
            else:
                Recorder(seq).record()
                set_current_slot(len(Recorder.recorders)-1)
                

    slot_play=Controller('knob',0x17,[seq],'slot_play')
    @slot_play.set_handler
    def handler(c,info):
        if ((info>0)):
            print ('current slot:',get_current_slot(),'volume:',current_rec().volume)
            #tog_list=Recorder.tog_list()
            #print('tog_list: '+tog_list)
            actual=[]
            for rec in Recorder.recorders:
                actual.append(rec.playing)
            flip_list,err=gr_recur(Recorder.groups,actual,get_current_slot(),4)
            if err :
                print ('slot_play ERROR. canceled')
                return
            print ("FLIP_LIST "+str(flip_list))
            
            flip_list.append(get_current_slot())
            
            for slot_number in flip_list:
                current_r=Recorder.recorders[slot_number]
                
                if (not current_r.keep_offset):
                    current_r.offset=((current_r.seq.processed_beat)//4)%current_r.bars
                    
                current_r.playing=not current_r.playing
            
                gui.message({"event":"toggle_play",
                             "index":current_r.index,
                             "offset":current_r.offset,
                             "status":current_r.playing,
                             "text":gui.Color.YELLOW+str(slot_number)+"playing "+
                             str(current_r.playing)+" volume "+str(current_r.volume)+gui.Color.CLOSE
                })

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
         if (get_current_slot()<0):
                new_slot_rec.handler(c,info)
                return
         if (info>0):
             if (not current_rec().recording):
                 current_rec().record()
             else:
                 current_rec().stop()

define_controllers()

def full_report():
    res=[]
    res.append({"event":"new_channels","number":len(midi_channels.outports),
                "text":gui.Color.BLUE+str(len(midi_channels.outports))+
                " midi channels created"+gui.Color.CLOSE})
    res.append({"event":"channel_change","subevent":"request","number":midi_channels.live_port,
                "text":gui.Color.GREEN+"New midi port is "+str(midi_channels.live_port)
                +gui.Color.CLOSE})
               
    for new_rec in Recorder.recorders:
         res.append({"event":"new_record","subevent":"request","info":new_rec.all_data(),
                     "index":new_rec.index,
                     "text":
                     gui.Color.BLUE+"New record from json  "+str(new_rec.index)+gui.Color.CLOSE})
    if (get_current_slot()>0):
        res.append({"event":"slot_change","subevent":"request",
                    "number":get_current_slot(),
                    "text":
                    gui.Color.YELLOW+"Active slot changed to "+str(get_current_slot())+gui.Color.CLOSE})
    res.append({"event":"groups","subevent":"json","info":Recorder.groups,
                "text":
                gui.Color.YELLOW+"groups loaded"+gui.Color.CLOSE
            })
        
    print(res)

    return res
    
##################midi-loopers main loop####################

with client:
    #print(gui.Color.RED+"#" * 80+gui.Color.CLOSE)
    #print(gui.Color.YELLOW+"press Return to quit"+gui.Color.CLOSE)
    #print(gui.Color.RED+"#" * 80+gui.Color.CLOSE)
    
    
    seq.activate()
    #Recorder.from_json('test.json',seq)
    if (gui.gui_type==gui.GUI.SERVER):
        first_req=True
        buffer_all={}
        app=flask.Flask(__name__)

        app=flask.Flask(__name__)
        @app.route('/',methods=['GET'])
        def get():
            with open('client.html','r') as f:
                return f.read()
        @app.route('/static/<string:filename>',methods=['GET'])
        def get_static(filename):
            with open('./static/'+filename,'rb') as f:
                return f.read()
        @app.route('/get_info',methods=['GET'])
        def get_info():
            global buffer_all
            global first_req
            rep={"reply":[]}
            for item in gui.gui_buffer:
                rep["reply"].append(item)
            gui.gui_buffer=[]
            print (rep)
            if (first_req):
                buffer_all=rep
                first_req=False
            return json.dumps(rep)
        
        @app.route('/all_info',methods=['GET'])
        def all_info():
            global buffer_all
            global first_req
            if (not first_req):
                gui.gui_buffer=[]
                #print(buffer_all
                return json.dumps({'reply':full_report()})
            
            rep={"reply":[]}
            for item in gui.gui_buffer:
                rep["reply"].append(item)
            gui.gui_buffer=[]
            print (rep)
            if (first_req):
                buffer_all=rep
                firs_req=False
            return json.dumps(rep)
        
        @app.route('/command/toggle_play/<int:index>',methods=['GET'])
        def command_toggle_play(index):
            print('toggle play'+str(index))
            #time.sleep(1.0);
            s=get_current_slot()
            set_current_slot(index)
            Controller.by_name['slot_play'].handler(1)
            set_current_slot(s)
            return "success"
        
        @app.route('/command/save/<string:filename>',methods=['GET'])
        def command_save(filename):
            print("save "+filename)
            Recorder.to_json(filename)
            return "success"
        
        @app.route('/command/load/<string:filename>',methods=['GET'])
        def command_load(filename):
            print("load "+filename)
            
            Recorder.from_json(filename,seq)
            #print(flask.request.form)
            #input()
            return "success"
        @app.route('/command/prop_update/<int:ind>/<string:jstring>',methods=['GET'])
        def command_update(ind,jstring):
            print('update '+str(ind)+' '+jstring);
            js=json.loads(jstring)
            rec=Recorder.recorders[ind]
            for key in js:
                rec.__dict__[key]=js[key]
            #print(
            #rec.playing=js['playing']
            #rec.volume=js['volume']
            #rec.offset=js['offset']
            #rec.bars=js['bars']
            return "success"
        @app.route('/command/clone/<int:index>',methods=['GET'])
        def command_clone(index):
            print("cloning "+str(index))
            Recorder.clone(index);
            
            #print(flask.request.form)
            #input()
            return "success"
        @app.route('/command/select/<int:index>',methods=['GET'])
        def command_select(index):
            set_current_slot(index)
            print('slot changed to '+str(get_current_slot()))
            return "success"
        @app.route('/command/groups_update/<string:jstring>',methods=['GET'])
        def command_groups_update(jstring):
            print('groups:')
            Recorder.groups=json.loads(jstring)
            for g in Recorder.groups:
                for i in range(len(g['elements'])):
                    g['elements'][i]=int(g['elements'][i])
            print(Recorder.groups)
            return 'succes'
        
        @app.route('/command/set_pad/<int:index>',methods=['GET'])
        def command_set_pad(index):
            #print('toggle play'+str(index))
            #time.sleep(1.0);
            midi_local=Controller.last_midi
            slot_midi=Controller('pad',Controller.last_midi,[seq],'portp')
            @slot_midi.set_handler
            def handler(c,info):
                s=get_current_slot()
                set_current_slot(index)
                Controller.by_name['slot_play'].handler(1)
                set_current_slot(s)
                print('midi pad control' + str(midi_local))
                
            

            
                  
        app.run(host='0.0.0.0',port=8080)
        
        print(gui.Color.RED+"\n Server terminated! \n"+gui.Color.CLOSE)
        
    if (gui.gui_type==gui.GUI.PRINT):
        input()

    seq.stop()
    Recorder.to_json('test2.json')
    input()
    

    
