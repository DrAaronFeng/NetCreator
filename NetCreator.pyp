"""
NetCreator V1.3.0

Copyright: Lewis Orton, https://www.behance.net/gallery/38292207/NetCreator-v11-Cinema-4D-plugin
Author:    Lewis Orton
License:   GPL-3.0 License

Name-US: NetCreator
Description-US: Cinema 4D plugin for creating linking-splines effect.

Description:

    - NetCreator is an open-source Cinema 4D plugin, working as a Generator Object inside C4D. it can generate splines based on different kinds of objects. 
    - NetCreator's user interface should be very self-explanatory, all parameters would be available only when they're allowed to. 

Features:

    1. Two modes. You can choose to generate splines on one object or between two objects.
    2. Supports polygonal object, Thinking Particles, MoGraph objects (including Cloner Object, Matrix Object, Fracture Object, MoText Object). For MoGraph Object, NetCreator uses MoGraph Object's elements' positions to generate splines. And you can use effector to control Matrix points' visibility, which opens lots of posibilities.
    3. VertexMap support for polygonal object. NetCreator will only generating splines on points that have weights larger than 0.5 in assigned VertexMap.
    4. Distance and Visibility control. You can randomly remove points that are used to generate splines, or animating this process.
    5. Propagation for VertexMap. You can paint on part of VertexMap, and with this feature turned on, NetCreator will automatically create propagation effect for vertexmap, with fast algorithm. You can also use this feature alone to get an animating vertex map for other purposes in Cinema 4D.


Tutorial:

    V1.0-V1.2: https://www.behance.net/gallery/38292207/NetCreator-v11-Cinema-4D-plugin
    V1.3:      http://www.wise4d.com/netcreator-v1-3-plugin-is-now-compatible-with-cinema-4d-r23/

ChangeLog:

    Jan/1/2016 V1.0 (by Lewis Orton)
    - Release Version

    Nov/22/2016 V1.1.1 (by Lewis Orton)
    - Fixed issue where selection was scaled down

    Oct/21/2020 V1.3 (by Dr.Aaron Feng)
    - Fixed runtime issue in R19 R20 R21 R22: there is an error infomation when parameter "Propagation" be available: 
      AttributeError: type object 'c4d.plugins.NodeData' has no attribute 'GetDEnabling'Traceback (most recent call last).
    - Fixed Issue where parameter "Strength" and "Size" could not coordinate unavailable as parameter "Turblence" is unchecked.
    - Fixed Issues of the plugin can not work in R23: now NetCreator could perfectly compatibility with Cinema 4D R23.
    - Increase parameter "Factor" in order to accurate adjustment the speed of Propagation for VertexMap if the propagation process is too fast. 

Compatible:

    - Win / Mac
    - R13, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23

"""

import c4d
import timeit
from c4d.modules import mograph as mo
from c4d.bitmaps import BaseBitmap as bmp
import random
import math
import sys
import os

PLUGIN_ID = 1037040

NETCREATOR_MODE = 1000
NETCREATOR_MODE_A = 1001
NETCREATOR_MODE_B = 1002
NETCREATOR_OBJECTA = 1003
NETCREATOR_VERTEXMAPA = 1004
NETCREATOR_OBJECTB = 1005
NETCREATOR_VERTEXMAPB = 1006

ID_DISTANCE = 2000
NETCREATOR_SPACE = 2001
NETCREATOR_SPACE_LOCAL = 2002
NETCREATOR_SPACE_GLOBAL = 2003
NETCREATOR_MINDISTANCE = 2004
NETCREATOR_MAXDISTANCE = 2005
NETCREATOR_VISIBILITY = 2006
NETCREATOR_SEED = 2007

ID_PROPAGATION = 3000
NETCREATOR_PROPAGATION_ENABLE = 3001
NETCREATOR_PROPAGATION_SPEED = 3002
NETCREATOR_PROPAGATION_TURBULENCE = 3003
NETCREATOR_PROPAGATION_STRENGTH = 3004
NETCREATOR_PROPAGATION_SIZE = 3005
NETCREATOR_PROPAGATION_FACTOR = 3006

NETCREATOR_DEBUG_FLAG = 0

#def var_name(var,all_var=locals()):
    #return [var_name for var_name in all_var if all_var[var_name] is var][0]


def debug(output):
    if NETCREATOR_DEBUG_FLAG:
        print(output)


debug('\n')
debug('NetCreator v1.3.0')



# verify if a vmap belong to a obj
def verifyVertexMap(obj, vmap):
    if not vmap or vmap.GetObject() != obj:
        return False
    return True

# convert local pos to global pos for p_list
def localSpaceToGlobalSpace(obj, p_list):
    # get the transformation matrix
    trans_matrix = obj.GetMg()
    shift_list = []
    
    # transfer matrix for p_list
    for p in p_list:
        shift_list.append(trans_matrix * p)
        
    return shift_list

# get p_list from polygon object
def getPolyList(obj, vmap):
    d_obj = obj.GetDeformCache()
    if not d_obj:
        p_list = obj.GetAllPoints()
    else:
        p_list = d_obj.GetAllPoints()
        
    # filter p_list if there is legal vertex map
    if verifyVertexMap(obj, vmap):
        v_list = vmap.GetAllHighlevelData()
        p_list = listFilter(p_list, v_list)
        
    return p_list

# get p_list from thinking particles
def getTPList(tp_group):
    tp_list = []
    
    doc = tp_group.GetDocument()
    TP = doc.GetParticleSystem()
    
    for i in tp_group.GetParticles():
        tp_list.append(TP.Position(i))
    
    return tp_list

# get p_list from MoGraph object
def getMDList(MoObj):
    modata = mo.GeGetMoData(MoObj)
    mo_matrix = modata.GetArray(c4d.MODATA_MATRIX)
    mo_flags = modata.GetArray(c4d.MODATA_FLAGS)
    p_count = len(mo_matrix)
    
    # invisible filter list
    mo_visible = []
    for i in range(p_count):
        mo_visible.append(mo_flags[i] & c4d.MOGENFLAG_CLONE_ON)
    
    # filter invisible elements 
    mo_matrix = listFilter(mo_matrix, mo_visible)
    
    p_list = []
    for i in mo_matrix:
        p_list.append(i.off)
    
    return p_list

# check if obj type is legal
def checkObj(obj):
    if (obj.GetType() == c4d.Opolygon or
        obj.GetType() == 1001381 or
        obj.GetType() == 1018544 or
        obj.GetType() == 1018545 or
        obj.GetType() == 1018791 or
        obj.GetType() == 1019268):
        
        return True
    return False

# get p_list accroding to different obj types
def getPList(obj, vmap):    
    if obj.GetType() == c4d.Opolygon:
        p_list = getPolyList(obj, vmap)
    elif obj.GetType() == 1001381: # thinking particle type
        p_list = getTPList(obj)
    # MoGraph objects
    elif (obj.GetType() == 1018544 or    #Cloner
        obj.GetType() == 1018545 or    #Matrix
        obj.GetType() == 1018791 or    #Fracture
        obj.GetType() == 1019268):    #MoText
        
        p_list = getMDList(obj)
        pass
    else:
        print("Wrong object A.")
        return None
    return p_list

# remove all list elements with value < 0.5 in filter_list
def listFilter(p_list, filter_list):
    p_count = len(p_list)
    for i in range(p_count - 1,-1,-1):
        if filter_list[i] <0.5:
            del(p_list[i])
    return p_list

def pointVisibleFilter(p_list, index, seed):
    # no need to filter if visibility = 100%
    if index == 100:
        return p_list
    
    # count processing time
    start_time = timeit.default_timer()
    
    # initialize random
    rand = random.Random(seed)
    
    # create 0,1 choice base list
    choice_list = [1] * index + [0] * (100-index)
    
    p_count = len(p_list)
    filter_list = []
    
    # create filter list with 0,1 for later filtering use
    for i in range(p_count):
        filter_list += [rand.choice(choice_list)]
        
    p_list = listFilter(p_list, filter_list)
    
    elapsed = timeit.default_timer() - start_time
    print('Visibility Processing Time: %f' % elapsed)
    
    return p_list
        
# return a list with splines(represented with two vectors) for self-connection mode
def buildSegList_One(p_list, min_distance, max_distance):
    p_count = len(p_list)
    seg_list = []
    
    start_time = timeit.default_timer() #timecount
    
    for i in range(p_count):
        for j in range(i + 1, p_count):
            temp_spline = p_list[i] - p_list[j]
            distance = temp_spline.GetLength()
            
            # append a spline into spline list when distance is legal
            if min_distance <= distance and distance <= max_distance:
                seg_list.extend([p_list[i], p_list[j]])  
            
    """elapsed = timeit.default_timer() - start_time    #timeend
    print('%f' % elapsed + ' in finding proper splines')"""
    return seg_list

# return a list with splines(represented with two vectors)  for A/B connection mode
def buildSegList_Two(p_list_A, p_list_B, min_distance, max_distance):
    
    seg_list = []
    
    for vec_a in p_list_A:
        for vec_b in p_list_B:
            vec_dis = vec_a - vec_b
            distance = vec_dis.GetLength()
            
            if min_distance <= distance and distance <= max_distance:
                seg_list.extend([vec_a, vec_b])   
    
    return seg_list
    pass
    

def verifyObj(obj):
    
    if obj.GetType() != c4d.Opolygon or obj.GetType != c4d.Oparticle:
        return False

def findTag(name, obj):
    tags = obj.GetTags()
    for tag in tags:
        if tag.GetName() == name:
            return tag
    return False 

# find the mean weight around certain point
def meanNeighborWeight(pindex, graph, vlist):
    nbwset = []
    for i in graph[pindex]:
        nbwset.append(vlist[i])
    mean_weight = sum(nbwset)/len(nbwset)
    return mean_weight

# create adjacent graph for object
def adjGraph(obj):
    polylist = obj.GetAllPolygons()
    pcnt = obj.GetPointCount()
    graph = []
    
    # build graph structure 
    for i in range(pcnt):
        graph.append(set())
    
    # fill chain data
    for poly in polylist:
        if poly.IsTriangle():
            for i in range(3):
                edge = poly.EdgePoints(i)
                graph[edge[0]].add(edge[1])
                graph[edge[1]].add(edge[0])
        else:
            for i in range(4):
                edge = poly.EdgePoints(i)
                graph[edge[0]].add(edge[1])
                graph[edge[1]].add(edge[0])
                
    #calc mem size
    size = 0
    for i in graph:
        size += sys.getsizeof(i)
    
    size += sys.getsizeof(graph)
    size /= 1048576
    print("size is %d" % size + "mb")
    
    return graph
  
def vertexmapGrow(self, tag, speed, turbulence, strength, size, factor):
    debug("func vertexmapGrow")
    obj = tag.GetObject()
    old_data = tag.GetAllHighlevelData()
    pcnt = obj.GetPointCount()
    p_list = obj.GetAllPoints()
    new_data = [0.0] * pcnt
    graph = adjGraph(obj)
    iters = math.ceil(float(speed))
    k = float(speed)/iters
    #fineTuning
    
    for iter in range(int(iters)):
        for i in range(obj.GetPointCount()):
            mean_weight = meanNeighborWeight(i, graph, old_data)
            if turbulence:
                new_weight = (old_data[i] + mean_weight * c4d.utils.noise.Turbulence(p_list[i]* size, strength, True)) * k * factor
            else:
                new_weight = (old_data[i] + mean_weight) * k * 0.5 * factor
            # += min(new_weight,1)
            new_data[i] += (new_weight, 1.0)[new_weight > 1]
            # = max(new_data[i], old_data[i])
            new_data[i] = (new_data[i], old_data[i])[new_data[i] < old_data[i]]
            # = min(new_data[i],1)
            new_data[i] = (new_data[i], 1.0)[new_weight > 1]
        old_data = new_data
    tag.SetAllHighlevelData(old_data)
    propagationFinishDetect(self, old_data)
        
def propagationFinishDetect(self,vlist):
    for i in vlist:
        if i < 0.5:
            self.propagation_finished = False
            return None
            
    self.propagation_finished = True
    return None
        
        
# entry function for vertexmap propagation        
def initPropagation(self, grow_enabled, tag, speed, turbulence, strength, size, factor):
    debug("initPropagation funcc")
    # exit if no animated tag
    if not tag:
        return None
    tag_tail = tag.GetName()[-8:]
    if tag_tail != "_Animate":
        debug("animate tag NOT deteted") 
        return None
    
    debug("animate tag deteted")
    doc = tag.GetDocument()
    frame = doc.GetTime().GetFrame(doc.GetFps())
    
    if frame == 0:
        #self.propagation_started = False
        self.propagation_finished = False
        
        # reset tag data on the beginning
        tag_name = tag.GetName()
        old_tag_name = tag_name[:-8]
        obj = tag.GetObject()
        origin_tag = findTag(old_tag_name, obj)
        origin_data = origin_tag.GetAllHighlevelData()
        tag.SetAllHighlevelData(origin_data)
        
        self.propagation_resetflag = True
        #self.propagation_started = True

  
    if grow_enabled and frame > self.lastFrame:
        # real propagation process
        vertexmapGrow(self, tag, speed, turbulence, strength, size, factor)
        self.propagation_resetflag = False
    
    self.lastFrame = frame


# find or build animate vertexmap
def getGrowTag(tag):
    tag_name = tag.GetName()
    if tag_name[-8:] == "_Animate":
        return tag
       
    # find existing animate tag 
    obj = tag.GetObject()
    target_name = tag.GetName() + "_Animate"
    target_tag = findTag(target_name, obj)
    
    # make a new vertexmap tag if target tag does not exist
    if not target_tag:
        pcnt = obj.GetPointCount()
        target_tag = c4d.VariableTag(c4d.Tvertexmap, pcnt)
        target_tag.SetName(target_name)
        obj.InsertTag(target_tag, tag)
        
    # copy vertexmap data from original tag
        transfer_data = tag.GetAllHighlevelData()
        target_tag.SetAllHighlevelData(transfer_data)
    return target_tag

# entry func to build spline
def buildSpline(self, op):
    debug('--------------buildSpline---------------')
    
    mode = op[NETCREATOR_MODE]
    obj_A = op[NETCREATOR_OBJECTA]
    vmap_A = op[NETCREATOR_VERTEXMAPA]
    obj_B = op[NETCREATOR_OBJECTB]
    vmap_B = op[NETCREATOR_VERTEXMAPB]
    min_distance = op[NETCREATOR_MINDISTANCE]
    max_distance = op[NETCREATOR_MAXDISTANCE]
    working_space = op[NETCREATOR_SPACE]
    visible_index = op[NETCREATOR_VISIBILITY]
    seed = op[NETCREATOR_SEED]
    propagation_enable = op[NETCREATOR_PROPAGATION_ENABLE]
    propagation_speed = op[NETCREATOR_PROPAGATION_SPEED]
    propagation_turbulence = op[NETCREATOR_PROPAGATION_TURBULENCE]
    propagation_strength = op[NETCREATOR_PROPAGATION_STRENGTH]
    propagation_size = op[NETCREATOR_PROPAGATION_SIZE]
    propagation_factor = op[NETCREATOR_PROPAGATION_FACTOR]
    
    
    if vmap_A and mode == NETCREATOR_MODE_A:
        initPropagation(self, propagation_enable, vmap_A, propagation_speed, propagation_turbulence, propagation_strength, propagation_size/10, propagation_factor)
        
    if vmap_A and mode == NETCREATOR_MODE_A and propagation_enable:
        #find existing animate tag or generate a new animate Tag
        vmap_A = getGrowTag(vmap_A)
        op[NETCREATOR_VERTEXMAPA] = vmap_A
    
    debug("-> vmap_A is: "+ str(vmap_A.GetName()) if vmap_A else "-> vmap_A is: None")

    # ---generate p_list A ---
    p_list_A = getPList(obj_A, vmap_A)
    if not p_list_A:
        return None
    
    # filter invisible points
    p_list_A = pointVisibleFilter(p_list_A, int(visible_index * 100), seed)
    # ---generate p_list_B ---
    if mode == NETCREATOR_MODE_B:
        p_list_B = getPList(obj_B, vmap_B)
        if not p_list_B:
            return None
        # filter invisible points
        p_list_B = pointVisibleFilter(p_list_B, int(visible_index * 100), seed)
    # ---creating splines---
    
    # self connection mode
    if mode == NETCREATOR_MODE_A:
        if working_space == NETCREATOR_SPACE_GLOBAL:
            p_list_A = localSpaceToGlobalSpace(obj_A, p_list_A)
            
        seg_list = buildSegList_One(p_list_A, min_distance, max_distance)

    # A/B Connection mode
    else:
        p_list_A = localSpaceToGlobalSpace(obj_A, p_list_A)
        p_list_B = localSpaceToGlobalSpace(obj_B, p_list_B)
        seg_list = buildSegList_Two(p_list_A, p_list_B, min_distance, max_distance)
    
    if not seg_list:
        print( 'No spline was created')
        debug('----------buildSplineFinished------------')
        debug('\n')        
        return None
    
    seg_count = int(len(seg_list)/2)
    
    # Initiate all segments
    splineObj = c4d.SplineObject(0,0)
    splineObj.ResizeObject(len(seg_list), seg_count)

    for i in range(seg_count):
        splineObj.SetSegment(i,2,False)
        

    #start_time = timeit.default_timer()
    
    #print(str(p_count) + " points in obj")
    print(str(seg_count) + " segments")
    # Set all segments
    splineObj.SetAllPoints(seg_list)
    
    debug('----------buildSplineFinished------------')
    debug('\n')

    return splineObj
    
# check if scene has changed
# used to decide if rebuild is needed
def sceneChange(self, op):
    debug("run sceneChange ...")
    debug("-> propagation_finished is:"+str(self.propagation_finished))
    debug("-> propagation_resetflag is:"+str(self.propagation_resetflag))
    obj_A = op[NETCREATOR_OBJECTA]
    vmap_A = op[NETCREATOR_VERTEXMAPA]
    
    obj_B = op[NETCREATOR_OBJECTB]
    vmap_B = op[NETCREATOR_VERTEXMAPB]
    
    dirty_now = 0
    
    dirty_now += op.GetDirty(c4d.DIRTY_DATA)
    
    if obj_A:
        dirty_now += obj_A.GetDirty(c4d.DIRTY_DATA)
        dirty_now += obj_A.GetDirty(c4d.DIRTY_CACHE)
        if obj_A.GetType() == 1001381:
            doc = op.GetDocument()
            TP = doc.GetParticleSystem()
            dirty_now += TP.GetDirty()
        
    if vmap_A:
        dirty_now += vmap_A.GetDirty(c4d.DIRTY_DATA)
    
    if op[NETCREATOR_MODE] == NETCREATOR_MODE_B:
        if obj_B:
            dirty_now += obj_B.GetDirty(c4d.DIRTY_DATA)
            
            if (obj_B.GetType() == 1018544 or    #Cloner
                obj_B.GetType() == 1018545 or    #Matrix
                obj_B.GetType() == 1018791 or    #Fracture
                obj_B.GetType() == 1019268):     #MoText
                dirty_now += obj_B.GetDirty(c4d.DIRTYFLAGS_CACHE)
        if vmap_B:
            dirty_now += vmap_B.GetDirty(c4d.DIRTY_DATA)
    
    if op[NETCREATOR_SPACE] == NETCREATOR_SPACE_GLOBAL:
        if obj_A:   dirty_now += obj_A.GetDirty(c4d.DIRTY_MATRIX)
        if obj_B:   dirty_now += obj_B.GetDirty(c4d.DIRTY_MATRIX)
        
    if self.DIRTY_COUNT != dirty_now:
        self.DIRTY_COUNT = dirty_now
        debug("-> DIRTY_COUNT changing")
        return True
        
    
    # Detect animated vertexmap
    if op[NETCREATOR_MODE] != NETCREATOR_MODE_A:
        return False
    doc = op.GetDocument()
    frame = doc.GetTime().GetFrame(doc.GetFps())

    
    tag = op[NETCREATOR_VERTEXMAPA]
    if not tag:
        return False
    tag_tail = tag.GetName()[-8:]
    if tag_tail == "_Animate":
        debug("-> tag detected")
        if frame is 0 and not self.propagation_resetflag:
            # reset tag data
            debug("-> frame = 0")
            return True
        if op[NETCREATOR_PROPAGATION_ENABLE] and frame > self.lastFrame and not self.propagation_finished:
            debug("-> frame > 0")
            # propagate vertexmap
            return True

    return False
    

# validate if plugin parameters are legal
def paramsValid(op):
    debug("run paramsValid ...")
    mode = op[NETCREATOR_MODE]
    obj_A = op[NETCREATOR_OBJECTA]
    vmap_A = op[NETCREATOR_VERTEXMAPA]
    obj_B = op[NETCREATOR_OBJECTB]
    vmap_B = op[NETCREATOR_VERTEXMAPB]
    min_distance = op[NETCREATOR_MINDISTANCE]
    max_distance = op[NETCREATOR_MAXDISTANCE]
    
    # verify all objects
    if not obj_A:
        print("Source object A does not exist.")
        return False
    if not checkObj(obj_A):
        print("Source object A is illegal.")
        return False        
    if vmap_A:
        if vmap_A.GetType() != c4d.Tvertexmap or vmap_A.GetObject() != obj_A():
            print("Illegal Vertex Map A.")
            op[NETCREATOR_VERTEXMAPA] = None
            return False
        
    # verify when mode = 2 objs
    if mode == NETCREATOR_MODE_B:
        if not obj_B:
            print("Source object B does not exist.")
            return False
        if not checkObj(obj_B):
            print("Source object B is illegal.")
            return False     
        if vmap_B:
            if vmap_B.GetType() != c4d.Tvertexmap or vmap_B.GetObject() != obj_B():
                print("Illegal Vertex Map B")
                op[NETCREATOR_VERTEXMAPB] = None
                return False 
            

    if min_distance >= max_distance:
        print('Wrong distance, no spline is created.')
        return False
    
    return True


class NetCreator(c4d.plugins.ObjectData):
    # Initialize default parameters
    def Init(self, node):
        #Called when Cinema 4D Initialize the ObjectData (used to define, default values)
        
        debug("run NetCreator: Initialize default parameters ...")
        self.InitAttr(node, int, NETCREATOR_MODE)
        self.InitAttr(node, int, NETCREATOR_SPACE)
        self.InitAttr(node, float, NETCREATOR_MINDISTANCE)
        self.InitAttr(node, float, NETCREATOR_MAXDISTANCE)
        self.InitAttr(node, float, NETCREATOR_VISIBILITY)
        self.InitAttr(node, float, NETCREATOR_PROPAGATION_SPEED)
        self.InitAttr(node, float, NETCREATOR_PROPAGATION_FACTOR)
        self.InitAttr(node, int, NETCREATOR_PROPAGATION_STRENGTH)
        self.InitAttr(node, float, NETCREATOR_PROPAGATION_SIZE)
        
        node[NETCREATOR_MODE] = NETCREATOR_MODE_A
        node[NETCREATOR_SPACE] = NETCREATOR_SPACE_LOCAL
        node[NETCREATOR_MINDISTANCE] = 0
        node[NETCREATOR_MAXDISTANCE] = 100
        node[NETCREATOR_VISIBILITY] = 1
        node[NETCREATOR_PROPAGATION_SPEED] = 1.1
        node[NETCREATOR_PROPAGATION_FACTOR] = 1
        node[NETCREATOR_PROPAGATION_STRENGTH] = 5
        node[NETCREATOR_PROPAGATION_SIZE] = 0.2
        
        self.DIRTY_COUNT = 0
        self.propagation_started = False
        self.spline_cache = None
        self.lastFrame = 0
        self.propagation_finished = False
        self.propagation_resetflag = False   #flag is used to indicate if there is propagation in the middle
        
        return True
        
    # Main Entry
    def GetVirtualObjects(self, op, hh):
        #This method is called automatically when Cinema 4D ask for the cache of an object.
        
        debug("run GetVirtualObjects ...")
        # use cache if scene is not changed
        if not sceneChange(self, op):
            debug("GetVirtualObjects ... not sceneChange \n")
            return self.spline_cache
        # keeps cache if params are illegal
        if not paramsValid(op):
            debug("GetVirtualObjects ... not paramsValid \n")
            return self.spline_cache
        else:
            debug("GetVirtualObjects ... buildSpline")
            self.spline_cache = buildSpline(self, op)
            return self.spline_cache
    
    # params grey-out detection
    def GetDEnabling(self, node, id, t_data, flags, itemdesc):
        #Called by Cinema 4D to decide which parameters should be enabled or disabled (ghosted).
        
        #debug("run GetDEnabling ...")
        if id[0].id == NETCREATOR_VERTEXMAPA:
            if not node[NETCREATOR_OBJECTA]:
                return False
            if node[NETCREATOR_OBJECTA].GetType() != c4d.Opolygon:
                return False
        
        if id[0].id == NETCREATOR_OBJECTB :
            if node[NETCREATOR_MODE] != NETCREATOR_MODE_B:
                return False
                
        if id[0].id == NETCREATOR_VERTEXMAPB:
            if node[NETCREATOR_MODE] != NETCREATOR_MODE_B:
                return False
            if not node[NETCREATOR_OBJECTB]:
                return False
            if node[NETCREATOR_OBJECTB].GetType() != c4d.Opolygon:
                return False
            
        if id[0].id == NETCREATOR_PROPAGATION_ENABLE:
            if not node[NETCREATOR_VERTEXMAPA]:
                node[NETCREATOR_PROPAGATION_ENABLE] = False
                return False
            if node[NETCREATOR_MODE] == NETCREATOR_MODE_B:
                node[NETCREATOR_PROPAGATION_ENABLE] = False
                return False
                
        if id[0].id == NETCREATOR_SPACE:
            if node[NETCREATOR_MODE] == NETCREATOR_MODE_B:
                node[NETCREATOR_SPACE] = NETCREATOR_SPACE_GLOBAL
                return False
                
        if (id[0].id == NETCREATOR_PROPAGATION_SPEED or
            id[0].id == NETCREATOR_PROPAGATION_FACTOR or
            id[0].id == NETCREATOR_PROPAGATION_STRENGTH or
            id[0].id == NETCREATOR_PROPAGATION_SIZE ):
            if not node[NETCREATOR_PROPAGATION_ENABLE]:
                return False
                
        if id[0].id == NETCREATOR_PROPAGATION_TURBULENCE:
            if not node[NETCREATOR_PROPAGATION_ENABLE]:
                node[NETCREATOR_PROPAGATION_TURBULENCE] = False
                return False

        if (id[0].id == NETCREATOR_PROPAGATION_STRENGTH or
            id[0].id == NETCREATOR_PROPAGATION_SIZE ):
            if not node[NETCREATOR_PROPAGATION_TURBULENCE]:
                return False        
        
        #return c4d.plugins.NodeData.GetDEnabling(self, node, id, t_data, flags, itemdesc)
        return True


            
def main():
    debug("run NetCreator main fun() ...")
    # Retrieves the icon path
    directory, _ = os.path.split(__file__)
    fn = os.path.join(directory, "res", "icon.png")

    # Creates a BaseBitmap
    bmp = c4d.bitmaps.BaseBitmap()
    if bmp is None:
        raise MemoryError("Failed to create a BaseBitmap.")

    # Init the BaseBitmap with the icon
    if bmp.InitWith(fn)[0] != c4d.IMAGERESULT_OK:
        raise MemoryError("Failed to initialize the BaseBitmap.")

    # Registers the object plugin
    c4d.plugins.RegisterObjectPlugin(id=PLUGIN_ID,
                                     str="NetCreator",
                                     g=NetCreator,
                                     description="Onetcreator",
                                     icon=bmp,
                                     info=c4d.OBJECT_GENERATOR)    
    
    
    
    

if __name__ == '__main__':
    main()
