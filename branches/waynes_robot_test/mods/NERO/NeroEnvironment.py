import time
from math import *
from OpenNero import *
from NERO.module import *
from copy import copy

MAX_SPEED = 10
MAX_SD = 100
OBSTACLE = 1#b0001
AGENT = 2#b0010

class AgentState:
    """
    State that we keep for each agent
    """
    def __init__(self):
        self.id = -1
        # current x, y, heading pose
        self.pose = (0, 0, 0)
        # previous x, y, heading pose
        self.prev_pose = (0, 0, 0)
        # starting position
        self.initial_position = Vector3f(0, 0, 0)
        # starting orientation
        self.initial_rotation = Vector3f(0, 0, 0)        
        self.time = time.time()
        self.start_time = self.time
        self.total_damage = 0
        self.curr_damage = 0
        self.curr_fitness = 0
        self.prev_fitness = 0
        self.team = 0
        self.sg = 0
        self.st = 0
        self.ae = 0
        self.af = 0
        self.ht = 0
        self.vf = 0
        self.final_fitness = 0
        self.animation = 'stand'

class NeroEnvironment(Environment):
    """
    Environment for the Nero
    """
    def __init__(self, XDIM, YDIM):
        from NERO.module import getMod
        """
        Create the environment
        """

        print "CREATING NERO ENVIRONMENT: " + str(dir(module))
        Environment.__init__(self) 
        
        self.curr_id = 0
        self.step_size = 0.1 # time between steps in seconds
        self.max_steps = 20
        self.time = time.time()
        self.XDIM = XDIM
        self.YDIM = YDIM
        self.MAX_DIST = pow((pow(XDIM, 2) + pow(YDIM, 2)), .5)
        self.states = {}
        self.teams = {}
        self.flag_loc = getMod().flag_loc
        
        self.pop_state_1 = {}
        self.pop_state_2 = {}

        abound = FeatureVectorInfo() # actions
        sbound = FeatureVectorInfo() # sensors
        rbound = FeatureVectorInfo() # rewards
        
        # actions
        abound.add_continuous(-pi / 2, pi / 2) # direction of motion
        abound.add_continuous(0, 1) # how fast to move
        abound.add_continuous(-pi / 2, pi / 2) # Firing direction
        abound.add_continuous(0, 1)
        abound.add_continuous(0, 1) 

        #sensors
        sbound.add_continuous(0, 1) # -60 deg        
        sbound.add_continuous(0, 1) # -45 deg
        sbound.add_continuous(0, 1) # -30 deg
        sbound.add_continuous(0, 1) # -15 deg
        sbound.add_continuous(0, 1) # straight ahead
        sbound.add_continuous(0, 1) # 15 deg
        sbound.add_continuous(0, 1) # 30 deg
        sbound.add_continuous(0, 1) # 45 deg
        sbound.add_continuous(0, 1) # 60 deg
        
        sbound.add_continuous(0, self.MAX_DIST) # Flag Sensors - Dist
        sbound.add_continuous(-1 * pi * 2, pi * 2) # Flag Sensors - Heading
        
        sbound.add_continuous(0, self.MAX_DIST) # Ally Sensors - Dist
        sbound.add_continuous(-1 * pi * 2, pi * 2) # Ally Sensors - Heading
        
        sbound.add_continuous(0, self.MAX_DIST) # Enemy Sensors - Dist
        sbound.add_continuous(-1 * pi * 2, pi * 2) # Enemy Sensors - Heading
        
        #rewards
#        rbound.add_continuous(-100,100) # range for reward
        
        self.agent_info = AgentInitInfo(sbound, abound, rbound)
    
    def out_of_bounds(self, pos):
        return pos.x < 0 or pos.y < 0 or pos.x > self.XDIM or pos.y > self.YDIM
    
    def reset(self, agent):
        """
        reset the environment to its initial state
        """
        state = self.get_state(agent)
        agent.state.position = copy(state.initial_position)
        agent.state.rotation = copy(state.initial_rotation)
        state.pose = (state.initial_position.x, state.initial_position.y, state.initial_rotation.z)
        state.prev_pose = state.pose
        state.total_damage = 0
        state.curr_damage = 0
        state.prev_fitness = state.curr_fitness
        state.curr_fitness = 0
        state.team = agent.getTeam()
        #update client fitness
        from client import set_stat
        ff = self.getFriendFoe(agent)
        avg = 0
        for x in ff[0]:
            avg += x.prev_fitness
        avg /= len(ff[0])
        set_stat(avg, state.team)
        print "Episode %d complete" % agent.episode 
        return True
    
    def get_agent_info(self, agent):
        """
        return a blueprint for a new agent
        """
        return self.agent_info
   
    def get_state(self, agent):
        if agent in self.states:
            return self.states[agent]
        else:
            self.states[agent] = AgentState()
            self.states[agent].id = agent.state.id
            myTeam = agent.getTeam()
            self.states[agent].team = myTeam
            if myTeam in self.teams:
                self.teams[myTeam].append(self.states[agent])
            else:
                self.teams[myTeam] = []
            return self.states[agent]

    def getStateId(self, id):
        for state in self.states:
            if id == self.states[state].id:
                return self.states[state]
        else:
            return - 1
            
    def getFriendFoe(self, agent):
        friend = []
        foe = []
        astate = self.get_state(agent)
        myTeam = astate.team
        friend = self.teams[myTeam]
        for r in self.teams:
            if r != myTeam:
                foe = self.teams[r] #TODO MAKE THIS VIABLE OVER 3+ TEAMS
        return (friend, foe)

    def step(self, agent, action):
        """
        A step for an agent
        """
        from NERO.module import getMod
        # check if the action is valid
        assert(self.agent_info.actions.validate(action))
        state = self.get_state(agent)
        if agent.step == 0:
            print 'FIRST STEP!', state.id, agent.state.position
            p = agent.state.position
            r = agent.state.rotation
            state.initial_position = p
            state.initial_rotation = r
            state.pose = (p.x, p.y, r.z)
            state.prev_pose = (p.x, p.y, r.z)
            if agent.get_team() == 1: 
             self.pop_state_1[agent.org.id] = state 
            else:
             self.pop_state_2[agent.org.id] = state 
        
        # Update Damage totals
        state.total_damage += state.curr_damage
        damage = state.curr_damage
        state.curr_damage = 0
        
        #Add current unit to pop_state
        if agent.get_team() == 1: 
             self.pop_state_1[agent.org.id] = state 
        else:
             self.pop_state_2[agent.org.id] = state 
        
        #Fitness Function Parameters
        stand_ground = getMod().sg
        stick_together = getMod().st
        approach_enemy = getMod().ae
        approach_flag = getMod().af
        hit_target = getMod().ht
        avoid_fire = getMod().vf
        distance_st = getMod().dta
        distance_ae = getMod().dtb
        distance_af = getMod().dtc
        friendly_fire = getMod().ff
        # the position and the rotation of the agent on-screen
        position = agent.state.position
        rotation = agent.state.rotation
        # get the current pose of the agent
        (x, y, heading) = state.pose
        # get the actions of the agent
        turn_by = degrees(action[0])
        move_by = action[1]
        fire_by = action[2]
        #print 'move by: %f, turn by: %f, fire by %f' % (move_by, turn_by, fire_by)
        # figure out the new heading
        new_heading = wrap_degrees(heading, turn_by)        
        # figure out the new x,y location
        new_x = x + MAX_SPEED * cos(radians(new_heading)) * move_by
        new_y = y + MAX_SPEED * sin(radians(new_heading)) * move_by
        # figure out the firing location
        fire_x = x + self.MAX_DIST * cos(radians(new_heading))
        fire_y = y + self.MAX_DIST * sin(radians(new_heading))
        # see if we can move forward
        new_position = copy(position)
        new_position.x, new_position.y = new_x, new_y
        distance_ahead = self.raySense(agent, turn_by, MAX_SPEED * move_by, OBSTACLE)
        safe = (distance_ahead >= 1)
        if not safe:
            # keep the position the same if we cannot move
            #print "not safe to move!"
            new_position = agent.state.position
        # draw the line of fire
        fire_pos = copy(position)
        fire_pos.x, fire_pos.y = fire_x, fire_y
        data = getSimContext().findInRay(position, fire_pos, AGENT + OBSTACLE, True)
        # calculate if we hit anyone
        string = agent.state.label + str(len(data)) + ": "
        hit = 0
        if len(data) > 0:
            sim = data[0]
            string += str(sim.label) + "," + str(sim.id) + ";"
            target = self.getStateId(sim.id)
            if target != -1:
                if target.team == state.team:
                    target.curr_damage += 1 * friendly_fire
                else:
                    target.curr_damage += 1
                    hit = 1
        # calculate friend/foe
        ffr = self.getFriendFoe(agent)
        if ffr[0] == []:
            return 0 #Corner Case
        ff = []
        ff.append(self.nearest(state.pose, state.id, ffr[0]))
        ff.append(self.nearest(state.pose, state.id, ffr[1]))
        
        st = 0
        ae = 0
        #calculate f
        sg = -action[0]
        if ff[0] != 1:
         st = self.distance(ff[0].pose,state.pose)
        if ff[1] != 1:
         ae = self.distance(ff[1].pose,state.pose)
        af = (distance_af/self.flag_distance(agent))
        ht = hit
        vf = -damage        
        
        #update current state data with f's
        state.sg += sg
        state.st += st
        state.ae += ae
        state.af += af
        state.ht += ht
        state.vf += vf
        
        #Update Fitness Function with 
        stand_ground *= -action[0]
        if not safe:
            stand_ground = 0
        if ff[0] == 1:
            stick_together = 0
        else:
            stemp = self.distance(ff[0].pose, state.pose)
            if stemp > 0:
                stick_together *= min(distance_st / stemp, 1)
            else:
                stick_together = 0
        if ff[1] == 1:
            approach_enemy = 0
        else:
            atemp = self.distance(ff[1].pose, state.pose)
            if atemp > 0:
                approach_enemy *= min(distance_ae / atemp, 1)
            else:
                approach_enemy = 0
        approach_flag *= (distance_af / self.flag_distance(agent))
        hit_target *= hit
        avoid_fire *= -damage        
        
        state.curr_fitness += stand_ground + stick_together + approach_enemy + approach_flag + hit_target + avoid_fire

        # make the calculated motion
        position.x, position.y = state.pose[0], state.pose[1]
        agent.state.position = position
        rotation.z = new_heading
        agent.state.rotation = rotation
        state.prev_pose = state.pose
        state.pose = (new_position.x, new_position.y, rotation.z)
        state.time = time.time()
        
        if agent.step >= self.max_steps - 1:
            rtneat = agent.get_rtneat()
            pop = rtneat.get_population_ids()
            if len(pop) == 0:
                return 0
            avg,sig = self.generate_averages(agent)
            sum = 0
            sum += ((state.sg - avg['sg'])/sig['sg']) * getMod().sg
            sum += ((state.st - avg['st'])/sig['st']) * getMod().st
            sum += ((state.ae - avg['ae'])/sig['ae']) * getMod().ae
            sum += ((state.af - avg['af'])/sig['af']) * getMod().af
            sum += ((state.ht - avg['ht'])/sig['ht']) * getMod().ht
            sum += ((state.vf - avg['vf'])/sig['vf']) * getMod().vf
        
            #Add current unit to pop_state
            if agent.get_team() == 1: 
             self.pop_state_1[agent.org.id] = state 
            else:
             self.pop_state_2[agent.org.id] = state 

            state.final_fitness = sum
            
            return sum
           # print "FINAL REWARD (if Z):", sum

        return 0
        #return stand_ground + stick_together + approach_enemy + approach_flag + hit_target + avoid_fire
    
    def raySense (self, agent, heading_mod, dist, types=0, draw=False):
        state = self.get_state(agent)
        firing = agent.state.position
        rotation = agent.state.rotation
        heading = radians(rotation.z + heading_mod)
        firing.x += dist * cos(heading)
        firing.y += dist * sin(heading)
        p0 = agent.state.position
        p1 = firing
        result = getSimContext().findInRay(p0, p1, types, draw)
        if len(result) > 0:
            (sim, hit) = result
            ray = p1 - p0
            len_ray = ray.getLength()
            data = hit - p0
            len_data = data.getLength()
            if len_ray != 0:
                return len_data / len_ray
        return 1

    def sense(self, agent):
        """ figure out what the agent should sense """
        v = self.agent_info.sensors.get_instance()
        vx = []
        vx.append(self.raySense(agent, -60, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, -45, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, -30, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, -15, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, 0, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, 15, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, 30, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, 45, MAX_SD, OBSTACLE))
        vx.append(self.raySense(agent, 60, MAX_SD, OBSTACLE))
        for iter in range(len(vx)):
            v[iter] = vx[iter]
        state = self.get_state(agent)
        v[9] = self.flag_distance(agent)
        v[10] = sin((state.pose[1] - self.flag_loc.y) / v[9])
        ffr = self.getFriendFoe(agent)
        if (ffr[0] == []):
            return v
        ff = []
        ff.append(self.nearest(state.pose, state.id, ffr[0]))
        ff.append(self.nearest(state.pose, state.id, ffr[1]))
        if ff[0] == 1:
            return v
        v[11] = self.distance(ff[0].pose, state.pose)
        v[12] = self.angle(state.pose, ff[0].pose)
        v[13] = self.distance(state.pose, ff[1].pose)
        v[14] = self.angle(state.pose, ff[1].pose)
        return v
    
    def flag_distance(self, agent):
        pos = self.get_state(agent).pose
        return pow(pow(float(pos[0]) - self.flag_loc.x, 2) + pow(float(pos[1]) - self.flag_loc.y, 2), .5)

    def distance(self, agloc, tgloc):
        return pow(pow(float(agloc[0] - tgloc[0]), 2) + pow(float(agloc[1] - tgloc[1]), 2), .5)

    def angle(self, agloc, tgloc):
        if(agloc[1] == tgloc[1]):
            return 0
        (x, y, heading) = agloc
        (xt, yt, ignore) = tgloc
        # angle to target
        theading = atan2(yt - y, xt - x)
        rel_angle_to_target = theading - radians(heading)
        return rel_angle_to_target

    def nearest(self, cloc, id, array):
        # TODO: this needs to only be computed once per tick, not per agent
        nearest = 1
        value = self.MAX_DIST * 5
        for other in array:
            if id == other.id:
                continue
            if self.distance(cloc, other.pose) < value:
                nearest = other
                value - self.distance(cloc, other.pose)
        return nearest

    def set_animation(self, agent, state, animation):
        if state.animation != animation:
            agent.state.setAnimation(animation)
            state.animation = animation

    def is_active(self, agent):
        """ return true when the agent should act """
        state = self.get_state(agent)
        # interpolate between prev_pose and pose
        (x1, y1, h1) = state.prev_pose
        (x2, y2, h2) = state.pose
        if x1 != x2 or y1 != y2:
            fraction = 1.0
            if self.step_size:
                fraction = min(1.0, float(time.time() - state.time) / self.step_size)
            pos = agent.state.position
            pos.x = x1 * (1 - fraction) + x2 * fraction
            pos.y = y1 * (1 - fraction) + y2 * fraction
            agent.state.position = pos
            self.set_animation(agent, state, 'run')
        else:
            self.set_animation(agent, state, 'stand')
        if time.time() - state.time > self.step_size:
            state.time = time.time()
            return True
        else:
            return False
    
    def is_episode_over(self, agent):
        """
        is the current episode over for the agent?
        """
        from NERO.module import getMod
        self.max_steps = getMod().lt
        state = self.get_state(agent)
        if self.max_steps != 0 and agent.step >= self.max_steps:
            return True
        if getMod().hp != 0 and state.total_damage >= getMod().hp:
            return True
        else:
            return False
    
    def cleanup(self):
        """
        cleanup the world
        """
        return True

    def generate_averages(self,agent):
        rtneat = agent.get_rtneat()
        pop = rtneat.get_population_ids()
        average = {'sg':0,'st':0,'ae':0,'af':0,'ht':0,'vf':0}
        sigma   = {'sg':1,'st':1,'ae':1,'af':1,'ht':1,'vf':1}
        if len(pop) == 0:
            return average,sigma
        
        #Add current unit to pop_state
        if agent.get_team() == 1: 
             pop_state = self.pop_state_1
        else:
             pop_state = self.pop_state_2
        
        curr_dict = {}
        for x in pop:
            curr_dict[x] = pop_state[x]
        curr_dict[agent.org.id] = pop_state[agent.org.id]
        pop_state = curr_dict
        
        #Add current unit to pop_state
        #if agent.get_team() == 1: 
        #     self.pop_state_1 = pop_state
        #else:
        #     self.pop_state_2 = pop_state

        for x in pop_state:
            x = pop_state[x]
            average['sg'] += x.sg
            average['st'] += x.st
            average['ae'] += x.ae
            average['af'] += x.af
            average['ht'] += x.ht
            average['vf'] += x.vf
        for x in average:
            average[x] /= len(pop_state)
         
        for x in pop_state:
            x = pop_state[x]
            sigma['sg'] += pow(average['sg'] - x.sg,2)
            sigma['st'] += pow(average['st'] - x.st,2)
            sigma['ae'] += pow(average['ae'] - x.ae,2)
            sigma['af'] += pow(average['af'] - x.af,2)
            sigma['ht'] += pow(average['ht'] - x.ht,2)
            sigma['vf'] += pow(average['vf'] - x.vf,2)

        for x in sigma:
            sigma[x] /= len(pop_state)
            sigma[x] = pow(sigma[x],.5)

        return average,sigma

def wrap_degrees(a, da):
    a2 = a + da
    if a2 > 180:
        a2 = -180 + (a2 % 180)
    elif a2 < -180:
        a2 = 180 - (abs(a2) % 180)
    return a2