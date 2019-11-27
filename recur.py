print('Here!')

def gr_recur(gr,actual,slot,depth):
    print('depth '+str(depth)+' slot '+str(slot)+' value '+str(actual[slot]))
    print(actual)
    pre_map={}
    err=False
    
        
    touched_list={}

    gr_slot=[]
    dest_stat=not actual[slot]
    
    for g in gr:
        if (slot in g['members']):
            gr_slot.append(g)
    print (gr_slot)

    for g in gr_slot:
        if (g['type']=='c'):
            for s in g['members']:
                if (s!=slot):
                    pre_map[s]=dest_stat
                    touched_list[s]=dest_stat
        if (g['type']=='x' and dest_stat==True):
            for s in g['members']:
                if (s!=slot):
                    pre_map[s]=False
                    if (s in touched_list):
                        print('conflict in flip list!')
                        err=True
                        return [],err
                    touched_list[s]=False
    for g in gr:
        if (g['members'][0]==slot and g['type']=='ms'):
            pre_map[g['members'][1]]=not dest_stat
            if (g['members'][1] in touched_list):
                if not (touched_list[g['members'][1]] == (not dest_stat)):
                    err=True
                    return [],err
            touched_list[g['members'][1]]=not dest_stat
                

    
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


def test1():
    gr=[]
    gg={'type':'c','members':[0,1]}
    gr.append(gg)

    gg={'type':'c','members':[2,3]}
    gr.append(gg)

    gg={'type':'c','members':[2,4]}
    gr.append(gg)

    gg={'type':'x','members':[1,2,4]}
    gr.append(gg)

    actual=[False,False,True,True,True]
    dest_stat=True
    slot=0

    flip_list,err=gr_recur(gr,actual,slot,4)
    print (flip_list,err)
    print(actual)
    if (actual==[True,True,False,False,False] and not err):
        print ("test1 is fine")
        return True
    else:
        print ('test1 failed')
        return False

def test2():
    gr=[]
    gg={'type':'c','members':[0,1]}
    gr.append(gg)

    gg={'type':'c','members':[2,3]}
    gr.append(gg)

    gg={'type':'c','members':[1,2,3]}
    gr.append(gg)

 
    actual=[False,False,False,False]
    
    slot=0

    flip_list,err=gr_recur(gr,actual,slot,4)
    print (flip_list,err)
    print(actual)
    if (actual==[True,True,True,True] and not err):
        print ("test2 is fine")
        return True
    else:
        print ('test2 failed')
        return False
#test2()

def test3():
    gr=[]
    gg={'type':'c','members':[0,1]}
    gr.append(gg)

    gg={'type':'c','members':[2,3]}
    gr.append(gg)

    gg={'type':'c','members':[0,3]}
    gr.append(gg)

    gg={'type':'x','members':[2,3]}
    gr.append(gg)

 
    actual=[False,False,False,False]
    
    slot=0

    flip_list,err=gr_recur(gr,actual,slot,4)
    print (flip_list,err)
    print(actual)
    if (err):
        print ("test3 is fine")
        return True
    else:
        print ('test3 failed')
        return False

def test4():
    gr=[]
    gg={'type':'ms','members':[0,1]}
    gr.append(gg)

    actual=[False,True]

    slot=0

    flip_list,err=gr_recur(gr,actual,slot,4)

    print (flip_list,err)
    print(actual)

    if (not err and actual==[True,False]):
        print ("test4 is fine")
        return True
    else:
        print ('test4 failed')
        return False

def test5():
    print('test5')
    gr=[]
    gg={'type':'ms','members':[0,1]}
    gr.append(gg)
    gg={'type':'c','members':[1,2,3]}
    gr.append(gg)
    gg={'type':'x','members':[3,0,4]}
    gr.append(gg)

    actual=[True,False,False,False,True]
    print(actual)

    slot=0

    flip_list,err=gr_recur(gr,actual,slot,4)

    print (flip_list,err)
    print(actual)

    if (not err and actual==[False,True,True,True,False]):
        print ("test5 is fine")
        return True
    else:
        print ('test5 failed')
        return False
        
    
    
    
test5()

 
