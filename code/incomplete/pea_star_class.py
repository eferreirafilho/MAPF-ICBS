import time as timer
import heapq
from itertools import product
import numpy as np
import copy

def move(loc, dir):
    directions = [(0, 0), (0, -1), (1, 0), (0, 1), (-1, 0)]
    return loc[0] + directions[dir][0], loc[1] + directions[dir][1]


def get_sum_of_cost(paths):
    rst = 0
    for path in paths:
        # print(path)
        rst += len(path) - 1
        # if(len(path)>1):
        #     assert path[-1] != path[-2]
    return rst


def compute_heuristics(my_map, goal):
    # Use Dijkstra to build a shortest-path tree rooted at the goal location
    open_list = []
    closed_list = dict()
    root = {'loc': goal, 'cost': 0}
    heapq.heappush(open_list, (root['cost'], goal, root))
    closed_list[goal] = root
    while len(open_list) > 0:
        (cost, loc, curr) = heapq.heappop(open_list)
        for dir in range(1,5):
            child_loc = move(loc, dir)
            child_cost = cost + 1
            if child_loc[0] < 0 or child_loc[0] >= len(my_map) \
               or child_loc[1] < 0 or child_loc[1] >= len(my_map[0]):
               continue
            if my_map[child_loc[0]][child_loc[1]]:
                continue
            child = {'loc': child_loc, 'cost': child_cost}
            if child_loc in closed_list:
                existing_node = closed_list[child_loc]
                if existing_node['cost'] > child_cost:
                    closed_list[child_loc] = child
                    # open_list.delete((existing_node['cost'], existing_node['loc'], existing_node))
                    heapq.heappush(open_list, (child_cost, child_loc, child))
            else:
                closed_list[child_loc] = child
                heapq.heappush(open_list, (child_cost, child_loc, child))

    # build the heuristics table
    h_values = dict()
    for loc, node in closed_list.items():
        h_values[loc] = node['cost']
    return h_values

def get_location(path, time):
    if time < 0:
        return path[0]
    elif time < len(path):
        return path[time]
    else:
        return path[-1]  # wait at the goal location


def get_path(goal_node,meta_agent):

    # print('\n')

    path = []
    for i in range(len(meta_agent)):
        path.append([])
    curr = goal_node
    while curr is not None:
        for i in range(len(meta_agent)):
            path[i].append(curr['loc'][i])
        curr = curr['parent']
    for i in range(len(meta_agent)):
        path[i].reverse()
        assert path[i] is not None

        # print(path[i])

        if len(path[i]) > 1: 
            # remove trailing duplicates
            while path[i][-1] == path[i][-2]:
                # path[i].remove(path[i][-1])
                path[i].pop()
                print(path[i])
                if len(path[i]) <= 1:
                    break
            # assert path[i][-1] != path[i][-2] # no repeats at the end!!

    # print('\n')

    assert path is not None
    return path


def get_path_test(node,meta_agent):

    # print('\n')

    path = []
    for i in range(len(meta_agent)):
        path.append([])
    curr = node
    while curr is not None:
        for i in range(len(meta_agent)):
            path[i].append(curr['loc'][i])
        curr = curr['parent']
    for i in range(len(meta_agent)):
        path[i].reverse()
        assert path[i] is not None

        # print(path[i])

        if node['reached_goal'][i]:
            # print(meta_agent[i], "HAS REACH GOAL")
            if len(path[i]) > 1: 
                # remove trailing duplicates
                while path[i][-1] == path[i][-2]:
                    # path[i].remove(path[i][-1])
                    path[i].pop()
                    # print(path[i])
                    if len(path[i]) <= 1:
                        break
                # assert path[i][-1] != path[i][-2] # no repeats at the end!!

    # print('\n')

    assert path is not None
    return path

class PEA_Star(object):

    def __init__(self,my_map,starts,goals,heuristics,agents,contraints):
        """my_map   - list of lists specifying obstacle positions
        starts      - [(x1, y1), (x2, y2), ...] list of start locations for CBS
        goals       - [(x1, y1), (x2, y2), ...] list of goal locations for CBS
        agents      - the agent (CBS) or meta-agent of the agent (MA-CBS) involved in collision
        constraints - list of dict constraints generated by a CBS splitter; dict = {agent,loc,timestep,positive}
        """        

        self.my_map = my_map


        self.num_generated = 0
        self.num_expanded = 0
        self.CPU_time = 0

        self.open_list = []
        self.closed_list = dict()

        
        self.constraints = contraints # to be used to create c_table

        self.agents = agents

        # check if meta_agent is only a simple agent (from basic CBS)
        if not isinstance(agents, list):
            self.agents = [agents]
            # print(meta_agent)

            # add meta_agent keys to constraints
            for c in self.constraints:
                c['meta_agent'] = {c['agent']}

        # FILTER BY INDEX FOR STARTS AND GOALS AND HEURISTICS
        self.starts = [starts[a] for a in self.agents]
        self.heuristics = [heuristics[a] for a in self.agents]
        self.goals = [goals[a] for a in self.agents]

        self.c_table = [] # constraint table
        self.max_constraints = np.zeros((len(self.agents),), dtype=int)


    def push_node(self, node):

        f_value = node['g_val'] + node['h_val']
        # heapq.heappush(self.open_list, (node['F_val'], f_value, node['h_val'], node['loc'], node['timestep'], self.num_generated, node))
        heapq.heappush(self.open_list, (node['F_val'], node['h_val'], node['loc'], -node['timestep'], self.num_generated, node))
        # print("Generate node {}".format(self.num_of_generated))
        self.num_generated += 1

    def pop_node(self):
        _, _, _, _, id, curr = heapq.heappop(self.open_list)
        # print("> Expand node {} t=d={} with F_val {}".format(id, curr['timestep'], curr['F_val']))
        self.num_expanded += 1
        return curr

    # return a table that constains the list of constraints of a given agent for each time step. 
    def build_constraint_table(self, agent):
        constraint_table = dict()

        if not self.constraints:
            return constraint_table
        for constraint in self.constraints:

            # print(constraint)

            timestep = constraint['timestep']

            t_constraint = []
            if timestep in constraint_table:
                t_constraint = constraint_table[timestep]

            # positive constraint for agent
            if constraint['positive'] and constraint['agent'] == agent:
                
                # constraint_table[timestep].append(constraint)
                t_constraint.append(constraint)
                constraint_table[timestep] = t_constraint
            # and negative (external) constraint for agent
            elif not constraint['positive'] and constraint['agent'] == agent:
                # constraint_table[timestep].append(constraint)
                t_constraint.append(constraint)
                constraint_table[timestep] = t_constraint
            # enforce positive constraints from other agents (i.e. create neg constraint)
            elif constraint['positive']: 
                assert not (constraint['agent'] == agent)
                neg_constraint = copy.deepcopy(constraint)
                neg_constraint['agent'] = agent
                # neg_constraint['meta_agent'] = meta_agent
                # if edge collision
                if len(constraint['loc']) == 2:
                    # switch traversal direction
                    prev_loc = constraint['loc'][1]
                    curr_loc = constraint['loc'][0]
                    neg_constraint['loc'] = [prev_loc, curr_loc]
                neg_constraint['positive'] = False
                # constraint_table[timestep].append(neg_constraint)
                t_constraint.append(neg_constraint)
                constraint_table[timestep] = t_constraint
        
        return constraint_table


    # # returns if a move at timestep violates a "positive" or a "negative" constraint in c_table
    # def is_constrained(self, curr_loc, next_loc, timestep, c_table_agent, agent):

    #     # print("the move : {}, {}".format(curr_loc, next_loc))

    #     if timestep not in c_table_agent:
    #         return False
        
    #     for constraint in c_table_agent[timestep]:
    #         # negative constraint
    #         if agent == constraint['agent'] and constraint['positive'] == False:
    #             # vertex constraint
    #             if len(constraint['loc']) == 1:
    #                 if next_loc == constraint['loc'][0]:
    #                     print("the move : {}, {}  time {}".format(curr_loc, next_loc,timestep))
    #                     print("vertex constraint", constraint)
    #                     return True
    #             # edge constraint
    #             else:
    #                 if constraint['loc'] == [curr_loc, next_loc]:
    #                     print("the move : {}, {}  time {}".format(curr_loc, next_loc,timestep))
    #                     print("edge constraint", constraint)
    #                     return True
            
    #         elif agent == constraint['agent'] and constraint['positive']:
    #             # do stuff...


    #     return False


    # returns if a move at timestep violates a "positive" or a "negative" constraint in c_table
    def constraint_violated(self, curr_loc, next_loc, timestep, c_table_agent, agent):

        # print("the move : {}, {}".format(curr_loc, next_loc))


        if timestep not in c_table_agent:
            return None
        
        for constraint in c_table_agent[timestep]:
            
            if agent == constraint['agent']:
                # vertex constraint
                if len(constraint['loc']) == 1:
                    # positive constraint
                    if constraint['positive'] and next_loc != constraint['loc'][0]:
                        # print("time {} positive constraint : {}".format(timestep, constraint))
                        return constraint
                    # negative constraint
                    elif not constraint['positive'] and next_loc == constraint['loc'][0]:
                        # print("time {} negative constraint : {}".format(timestep, constraint))
                        return constraint
                # edge constraint
                else:
                    if constraint['positive'] and constraint['loc'] != [curr_loc, next_loc]:
                        # print("time {} positive constraint : {}".format(timestep, constraint))
                        return constraint
                    if not constraint['positive'] and constraint['loc'] == [curr_loc, next_loc]:
                        # print("time {} negative constraint : {}".format(timestep, constraint))
                        return constraint

        return None

    # returns whether an agent at goal node at current timestep will violate a constraint in next timesteps
    def future_constraint_violated(self, curr_loc, timestep, max_timestep, c_table_agent, agent):

        for t in range(timestep+1, max_timestep+1):
            if t not in c_table_agent:
                continue

            for constraint in c_table_agent[t]:
        
                if agent == constraint['agent']:
                    # vertex constraint
                    if len(constraint['loc']) == 1:
                        # positive constraint
                        if constraint['positive'] and curr_loc != constraint['loc'][0]:
                            # print("future time {} positive constraint : {}".format(t, constraint))
                            return True
                        # negative constraint
                        elif not constraint['positive'] and curr_loc == constraint['loc'][0]:
                            # print("time {} negative constraint : {}".format(timestep, constraint))
                            # print("future time {} negative constraint : {}".format(t, constraint))
                            return True


        return False
            
    def generate_child_nodes(self, curr):
        
        children = []
        # ma_dirs = product(list(range(5)), repeat=len(self.agents)) # directions for move() for each agent: 0, 1, 2, 3, 4
        
        dirs_product_lists = [] # contains lists with directions for move() for each agent: 1 (down), 2 (right), 3 (up), 4 (left), 0 (stay)
        for i, a in enumerate(self.agents):
            if curr['reached_goal'][i] == True:
                dirs_product_lists.append([0]) # stay in current location
            else:
                dirs_product_lists.append(list(range(5))) # try all 0-4 directions

        ma_dirs = product(*dirs_product_lists)

        for dirs in ma_dirs: 
            # print(dirs)
            invalid_move = False
            child_loc = []
            # move each agent for new timestep & check for (internal) conflicts with each other
            for i, a in enumerate(self.agents):           
                    aloc = move(curr['loc'][i], dirs[i])
                    # vertex collision; check for duplicates in child_loc
                    if aloc in child_loc:
                        invalid_move = True
                        # print("internal conflict")
                        break
                    child_loc.append(move(curr['loc'][i], dirs[i]))   


            if invalid_move:
                continue


            for i, a in enumerate(self.agents):   
                # edge collision: check for matching locs in curr_loc and child_loc between two agents
                for j, a in enumerate(self.agents):   
                    if i != j:
                        # print(ai, aj)
                        if child_loc[i] == curr['loc'][j] and child_loc[j] == curr['loc'][i]:
                            invalid_move = True             
            
            if invalid_move:
                continue

            # check map constraints and external constraints
            for i, a in enumerate(self.agents):  
                next_loc= child_loc[i]
                # agent out of map bounds
                if next_loc[0]<0 or next_loc[0]>=len(self.my_map) or next_loc[1]<0 or next_loc[1]>=len(self.my_map[0]):
                    invalid_move = True
                # agechild_locnt collison with map obstacle
                elif self.my_map[next_loc[0]][next_loc[1]]:
                    invalid_move = True
                # agent is constrained by a negative external constraint
                elif self.constraint_violated(curr['loc'][i],next_loc,curr['timestep']+1,self.c_table[i], self.agents[i]):
                    # print()
                    
                    invalid_move = True
                if invalid_move:
                    break

            if invalid_move:
                continue

            # find h_values for current moves
            # h_value = 0
            # for i in range(len(self.agents)):
            #         h_value += self.heuristics[i][child_loc[i]]

            h_value = sum([self.heuristics[i][child_loc[i]] for i in range(len(self.agents))])

            # assert h_value == h_test

            # g_value = curr['g_val']+ curr['reached_goal'].count(False)
            num_moves = curr['reached_goal'].count(False)
            # print("(edge) cost (curr -> child) in a* tree == ", num_moves)

            
            # 'reached_goal' not true if future constraints => not true cost b/c not reached_goal[i] != cost increase
            # agent may have reached goal without violating future constraints....


            g_value = curr['g_val'] + num_moves 

            reached_goal = [False for i in range(len(self.agents))]
            for i, a in enumerate(self.agents):
                # print(child_loc[i], goal_loc[i])
                # print(max_constraints[i], curr['timestep']+1)
                
                # if not reached_goal[i] and child_loc[i] == self.goals[i]:
                #     print("agent ", a, 'has reached goal at timestep ', curr['timestep'] + 1)

                # to-do: check if future constraints violated
                
                if not reached_goal[i] and child_loc[i] == self.goals[i]:


                    if curr['timestep']+1 <= self.max_constraints[i]:
                        if not self.future_constraint_violated(child_loc[i], curr['timestep']+1, self.max_constraints[i] ,self.c_table[i], self.agents[i]):
                    # print("agent ", a, 'has found solution at timestep ', curr['timestep'] + 1)
                    # print ('MAX CONSTRIANT:', self.max_constraints[i])
                            reached_goal[i] = True
                            # g_value -= 1 #
                    else:
                        reached_goal[i] = True



            child = {'loc': child_loc,
                    'F_val': g_value+h_value,
                    'g_val': None, # number of new locs (cost) added
                    'h_val': h_value,
                    'parent': curr,
                    'timestep': curr['timestep']+1,
                    'reached_goal': copy.deepcopy(reached_goal)
                    } 


            # # USE TO TEST g_val AND reached_goal
            # get_path_test(curr, self.agents)
            # g_test = get_sum_of_cost( get_path_test(child, self.agents) ) # inefficient, to-do: check if future constraints violated instread
            # print(g_test, g_value)
            # assert g_value == g_test

            child['g_val'] = g_value

            # print(child)

            children.append(child)

        return children

    def find_paths(self):

        self.start_time = timer.time()

        print("> build constraint table")

        for i, a in enumerate(self.agents):
            table_i = self.build_constraint_table(a)
            print(table_i)
            self.c_table.append(table_i)
            if table_i.keys():
                self.max_constraints[i] = max(table_i.keys())

       
        # print (self.c_table)

        # combined h value for agents

        # h_test = 0
        # # for a in self.agents:
        # #     # print(a)
        # #     h_test += self.heuristics[i][self.starts[i]]

        # for i in range(len(self.agents)):
        #     h_test += self.heuristics[i][self.starts[i]]

        h_value = sum([self.heuristics[i][self.starts[i]] for i in range(len(self.agents))])

        # assert h_value == h_test



        # for a in range(len(self.agents)):
        #     print('\nself.starts[i], i')
        #     print(self.starts[i], i)
        #     print('\nself.starts[a], a')
        #     print(self.starts[a], a)
        #     assert self.starts[i] == self.starts[a]



        root = {'loc': [self.starts[i] for i in range(len(self.agents))],
                'F_val' : h_value, # only consider children with f_val == F_val
                'g_val': 0, 
                'h_val': h_value, 
                'parent': None,
                'timestep': 0,
                'reached_goal': [False for i in range(len(self.agents))]
                }
        
        # check if any any agents are already at goal loc
        for i, a in enumerate(self.agents):
            if root['loc'][i] == self.goals[i]:

                if root['timestep'] <= self.max_constraints[i]:
                    if not self.future_constraint_violated(root['loc'][i], root['timestep'], self.max_constraints[i] ,self.c_table[i], self.agents[i]):
                        root['reached_goal'][i] = True

        self.push_node(root)

        while len(self.open_list) > 0:

            # if num_node_generated >= 30:
            #     return

            curr = self.pop_node()

            solution_found = all(curr['reached_goal'][i] for i in range(len(self.agents)))
            # print(curr['reached_goal'] )

            if solution_found:
                return get_path(curr,self.agents)


            ### TEST #######
            if(len(self.max_constraints) == 2):
                if curr['timestep'] > self.max_constraints[0] and curr['timestep'] > self.max_constraints[1]:
                    # print(curr['loc'][0] == goal_loc[self.agents[0]], curr['loc'][1] == goal_loc[self.agents[1]])
                    assert not(curr['loc'][0] == self.goals[0] and curr['loc'][1] == self.goals[1])

            ### END TEST ###

            children = self.generate_child_nodes(curr)

            next_best_f = False

            for child in children:


                # print("curr F: ", curr['F_val'])
                # print("child f: ", child['g_val'] + child['h_val'])
                # print(child['reached_goal'])
                # assert child_loc[i] != goal_loc[a]
                # assert child['reached_goal'] != [True]

                f_value = child['g_val'] + child['h_val']

                # add children if it's f_val is equal to curr's
                if f_value == curr['F_val']:
                    # print("curr F: ", curr['F_val'])
                    # print("child f: ", child['g_val'] + child['h_val'])
                    if (tuple(child['loc']),child['timestep']) not in self.closed_list:
                        # existing_node = self.closed_list[(tuple(child['loc']),child['timestep'])]
                        # if compare_nodes(child, existing_node):
                        self.closed_list[(tuple(child['loc']),child['timestep'])] = child
                        # print('bye child ',child['loc'])
                        self.push_node(child)
                    
                elif f_value > curr['F_val']:
                    # print("curr F: ", curr['F_val'])
                    # print("child f: ", child['g_val'] + child['h_val'])
                    next_best_f = f_value if not next_best_f else min(next_best_f, f_value)

            # push curr back into open list with best f_val > curr['f_val']
            if next_best_f:
                curr['F_val'] = next_best_f
                self.push_node(curr)
            # if curr has no unexpanded children, add to closed list 
            elif (tuple(curr['loc']),curr['timestep']) not in self.closed_list:
                # print('die parent', curr['loc'])
                self.closed_list[(tuple(curr['loc']),curr['timestep'])] = curr

        print('no solution')

        # print("\nEND OF A*\n") # comment out if needed
        return None        