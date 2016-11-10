from mock import create_autospec
from os import chdir, getcwd
from panda3d.core import loadPrcFileData, NodePath
from unittest import TestCase

from racing.game.engine.engine import Engine
from racing.game.game import GameLogic, Game
from racing.game.gameobject import GameObjectMdt


class LogicTests(TestCase):

    def setUp(self):
        loadPrcFileData('', 'window-type none')

    def tearDown(self):
        self.eng.destroy()

    def test_init(self):
        self.eng = Engine()
        game_obj = GameObjectMdt()
        logic = GameLogic(game_obj)
        self.assertIsInstance(logic, GameLogic)


class GameTests(TestCase):

    def setUp(self):
        loadPrcFileData('', 'window-type none')

    def tearDown(self):
        self.eng.destroy()

    def test_init(self):
        self.eng = Engine()
        self.eng.camera = create_autospec(NodePath)
        game = Game()
        self.assertIsInstance(game, Game)
        game.destroy()
