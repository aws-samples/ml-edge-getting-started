# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import gym
import numpy as np
import random
import ray.rllib as rllib

class TicTacToeEnv(rllib.env.MultiAgentEnv, gym.Env):
    """OpenAI Gym for Tic Tac Toe"""
    PLAYER_X=1
    PLAYER_O=2
    WAIT=9
    marker = ['-', 'X', 'O']
    def __init__(self):
        self.action_space = gym.spaces.Discrete(9 + 1) # 9 valid + wait
        self.observation_space = gym.spaces.Box(0,2, [9+1]) # values between 0 and 2
        self.reset()

    def __defense_detection__(self, board, enemy_id):
        """Checks if there is an opportunity to defend itself from an attack"""
        board_play=board==enemy_id # agent id
        board_mask=board==0 # empty cells
        h = np.sum(board_play, axis=1)# horizontal
        v = np.sum(board_play, axis=0) # vertical
        # diagonals
        diagA,diagAMask = np.diagonal(board_play),np.diagonal(board_mask)     
        diagB,diagBMask = np.fliplr(board_play).diagonal(),np.fliplr(board_mask).diagonal()
        defense_options = []
        for idx,row in enumerate(h): # scan rows
            if row==2 and np.sum(board_mask[idx])>0:
                defense_options.append((idx,np.argmax(board_mask[idx])))
        for idx,col in enumerate(v): # scan cols
            if col==2 and np.sum(board_mask[:,idx])>0:
                defense_options.append((np.argmax(board_mask[:,idx]),idx))
        if np.sum(diagA)==2 and np.sum(diagAMask)>0: # scan diagonal A
            idx = np.argmax(diagAMask); defense_options.append((idx,idx))
        if np.sum(diagB)==2 and np.sum(diagBMask)>0: # scan diagonal B
            idx = np.argmax(diagBMask); defense_options.append((idx,2-idx))
        return defense_options
        
    def step(self, action_dict):
        """One step in the simulation"""
        done=False
        reward=[0,0,0]
        action_x = action_dict['agent_x']
        action_o = action_dict['agent_o']
        
        if self.turn==self.PLAYER_X:
            player_id,enemy_id = (self.PLAYER_X,self.PLAYER_O)
            action_player,action_enemy = (action_x,action_o)
        else:
            player_id,enemy_id = (self.PLAYER_O,self.PLAYER_X)        
            action_player,action_enemy = (action_o,action_x)
        
        # check movement current player        
        if action_player == self.WAIT or self.board[action_player//3, action_player%3] != 0:
            # invalid movement
            reward[player_id] = -7
        else:
            # next time the enemy will play
            self.turn = enemy_id
            # valid movement
            row,col=action_player//3,action_player%3
            self.board[row, col] = player_id
            # is it a critical situation that requires defense?
            defense_options = self.__defense_detection__(self.board, enemy_id)            
            if len(defense_options) > 0:
                reward[player_id] = -10 # probably will lose if this is not a defense, lets see
                for i in defense_options:
                    if i[0]==row and i[1]==col: ## woohoo! defended
                        reward[player_id] = 8
                        break
            else:
                reward[player_id] = 1
        
        # Enemy should be waiting
        if action_enemy != self.WAIT: reward[enemy_id] = -7
        
        tests = [np.diagonal(self.board), np.fliplr(self.board).diagonal()]
        for i in range(3): tests += [self.board[i],self.board[:,i]]
        # check board status
        if   (np.array(tests)==player_id).all(axis=1).any(): done,reward[player_id] = True,15 # win
        elif (np.array(tests)==enemy_id).all(axis=1).any(): done,reward[player_id] = True,-15 # defeat
        elif not (np.array(tests)==0).any(): done,reward[player_id],reward[enemy_id] = True,2,2 # draw
        elif self.trials < 1: done,reward[player_id],reward[enemy_id] = True,-5,-5
        
        self.trials -= 1        
        
        if done: self.render()

        obs = {
            'agent_x': np.concatenate([self.board.flatten(),[self.turn]], axis=0),
            'agent_o': np.concatenate([self.board.flatten(),[self.turn]], axis=0)
        }
        reward = {'agent_x': reward[1], 'agent_o': reward[2]}
        done = {'agent_x': done, 'agent_o': done, '__all__': done}
        
        return obs, reward, done, {}
    
    def reset(self):        
        self.trials = 20
        self.turn = np.random.randint(1,3)
        self.board = np.zeros((3,3), dtype=np.uint8)
        obs = {
            'agent_x': np.concatenate([self.board.flatten(),[self.turn]], axis=0),
            'agent_o': np.concatenate([self.board.flatten(),[self.turn]], axis=0)
        }
        return obs
 
    def render(self, mode='none', close=False):
        if mode=='none': return
        for i in range(9):
            print(self.marker[self.board[i//3,i%3]], end='\n' if i % 3 == 2 else ' ')
        print()
    
    def seed(self, seed):
        print(f"TicTacToeEnv - Seeding {seed}")
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
