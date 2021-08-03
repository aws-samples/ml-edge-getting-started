# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
from ray.rllib.policy.policy import Policy
import random
import numpy as np
from tictactoe import TicTacToeEnv

class SemiSmartTicTacToeHeuristicsPolicy(Policy):
    """Starts with random movements but tries to avoid defeat"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exploration = self._create_exploration()
        seed = args[2]['seed']
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
    
    def __attack_or_defend__(self, board, agent_id):
        board_play=board==agent_id # agent id
        board_mask=board==0 # empty cells
        h = np.sum(board_play, axis=1)# horizontal
        v = np.sum(board_play, axis=0) # vertical
        # diagonals
        diagA,diagAMask = np.diagonal(board_play),np.diagonal(board_mask)     
        diagB,diagBMask = np.fliplr(board_play).diagonal(),np.fliplr(board_mask).diagonal()    
        for idx,row in enumerate(h): # scan rows
            if row==2 and np.sum(board_mask[idx])>0:             
                return (idx,np.argmax(board_mask[idx]))
        for idx,col in enumerate(v): # scan cols
            if col==2 and np.sum(board_mask[:,idx])>0: 
                return (np.argmax(board_mask[:,idx]),idx)
        if np.sum(diagA)==2 and np.sum(diagAMask)>0: # scan diagonal A
            idx = np.argmax(diagAMask); return (idx,idx)
        if np.sum(diagB)==2 and np.sum(diagBMask)>0: # scan diagonal B
            idx = np.argmax(diagBMask); return (idx,2-idx)
        return None, None
        
    def compute_actions(self,
                        obs_batch,
                        state_batches=None,
                        prev_action_batch=None,
                        prev_reward_batch=None,
                        info_batch=None,
                        episodes=None,
                        **kwargs):
        
        def determine_action(obs):
            # Wait if it's not player's turn.
            if obs[9] == TicTacToeEnv.PLAYER_X: return 9
            
            board = obs[:-1].reshape((3,3))
            if random.randint(0,3) == 0: # 33% hard - 66% potentially dumb
                row,col = self.__attack_or_defend__(board, TicTacToeEnv.PLAYER_O) # attack
                if row is not None: return (row*3)+col
                row,col = self.__attack_or_defend__(board, TicTacToeEnv.PLAYER_X) # defend
                if row is not None: return (row*3)+col
                    
            # Make a move on the first empty field heuristic can find.
            empty_cells = []
            for i, symbol in enumerate(obs):
                if symbol == 0: empty_cells.append(i)
            if len(empty_cells) > 0: return empty_cells[random.randint(0,len(empty_cells)-1)]
            raise Exception('Heuristic did not find empty.')

        return [determine_action(obs) for obs in obs_batch], [], {}

    def get_weights(self):
        return None

    def set_weights(self, weights):
        return None
