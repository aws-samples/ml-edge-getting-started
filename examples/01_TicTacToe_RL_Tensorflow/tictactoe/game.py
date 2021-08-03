# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
import random
import numpy as np
import dlr
import time
from IPython import display
from ipywidgets import Button, GridspecLayout, Layout, Label, VBox
from dlr.counter.phone_home import PhoneHome                             

class TicTacToeGame(object):
    """IPython widgets based board game"""
    def __init__(self):
        self.turn = 1 if random.random() > 0.5 else 2
        self.observations = ([0] * 9) + [self.turn]
        self.buttons = {}
        self.buttons_rev = []
        self.label = Label(value="X - Human vs Bot - O")
        self.status = 0
        # Load the model
        PhoneHome.disable_feature()
        self.model = dlr.DLRModel('model_neo', 'cpu')

        ## Initialize grid
        grid = GridspecLayout(3, 3, height='300px', width='300px')
        for i in range(3):
            for j in range(3):
                btn = Button(description=" ", layout=Layout(height='95px', width='95px'))
                self.buttons[btn] = j + (i*3)
                self.buttons_rev.append(btn)
                grid[i, j] = btn
                grid[i, j].on_click(self.__button_click__)
                grid[i, j].style.button_color = '#ffccbc'
                grid[i, j].style.font_weight="bold"
        self.board = VBox([self.label, grid])

    def __next_bot_action__(self):
        x = np.array(self.observations, dtype=np.float32)
        return np.argmax(self.model.run(x)[0])
    
    def __reset_game__(self):        
        self.label.value = "X - Human vs Bot - O"
        for b in self.buttons: b.description=" "
        self.turn=1 if random.random() > 0.5 else 2
        self.observations = ([0] * 9) + [self.turn]
        self.status = 0
        if self.turn==1:
            bot_action = random.randint(0,8)
            self.__button_click__(self.buttons_rev[bot_action])
        display.display(board)

    def __check_winner__(self):
        board = np.array(self.observations[:-1]).reshape((3,3))
        tests = [np.diagonal(board), np.fliplr(board).diagonal()]
        for i in range(3): tests += [board[i],board[:,i]]
        # check board status
        if   (np.array(tests)==2).all(axis=1).any(): self.status = 2 # human wins
        elif (np.array(tests)==1).all(axis=1).any(): self.status = 1 # bot wins
        elif not (np.array(tests)==0).any(): self.status = -1 # draw
        else: self.status = 0 # match didn't finish

    def __button_click__(self, btn):
        self.__check_winner__()
        if self.status == 0 and btn.description==' ':
            btn.description="O" if self.turn == 1 else "X" # mark the cell
            self.observations[self.buttons[btn]]=self.turn # change the observation status
            self.turn = 2 if self.turn == 1 else 1 # change the turn
            self.observations[9] = self.turn
            self.__check_winner__()
            if self.status == 0 and self.turn == 1: # run next action for the bot
                bot_action = self.__next_bot_action__()
                assert(bot_action != 9)
                self.__button_click__(self.buttons_rev[bot_action])
        
        if self.status == -1: self.label.value = "Draw!"
        elif self.status == 2: self.label.value = "Human won!"
        elif self.status == 1: self.label.value = "Bot won!"
        if self.status != 0:
            time.sleep(3)
            self.__reset_game__()

    def run(self):
        display.display(self.board)
        display.display(display.HTML("""
        <style> 
        .jupyter-button { --jp-widgets-font-size: 50pt; } 
        .widget-label { 
            --jp-widgets-font-size: 20pt; 
            text-align: center;
            width: 300px;
        } 
        </style>
        """))
