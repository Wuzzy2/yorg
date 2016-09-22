import sys
from direct.gui.DirectFrame import DirectFrame
sys.path.append('./ya2/thirdparty')

from datetime import datetime
from direct.directnotify.DirectNotify import DirectNotify
from direct.filter.CommonFilters import CommonFilters
from direct.particles.ParticleEffect import ParticleEffect
from direct.showbase.ShowBase import ShowBase
from gettext import install, translation
from os import environ, system
from panda3d.bullet import BulletWorld, BulletDebugNode
from panda3d.core import getModelPath, WindowProperties, LightRampAttrib, \
    PandaNode, NodePath, AntialiasAttrib, loadPrcFileData, \
    QueuedConnectionManager, QueuedConnectionListener, QueuedConnectionReader, \
    ConnectionWriter, PointerToConnection, NetAddress, NetDatagram
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.PyDatagramIterator import PyDatagramIterator
from webbrowser import open_new_tab
from pause import pause, resume, isPaused, get_isPaused
import __builtin__
import yaml
import platform
import sys


class OnFrame:
    pass


class OnCollision:

    def __init__(self, obj_name):
        self.obj_name = obj_name


class LogMgr:

    def __init__(self):
        self.__notify = DirectNotify().newCategory('ya2')

    @staticmethod
    def configure():
        loadPrcFileData('', 'notify-level-ya2 info')

    def log(self, msg):
        self.__notify.info(datetime.now().strftime("%H:%M:%S") + ' ' + str(msg))

    def log_conf(self):
        self.log('version: '+eng.version)
        self.log('operative system: '+platform.system()+' '+platform.release())
        gsg = eng.win.get_gsg()
        self.log(gsg.getDriverVendor())
        self.log(gsg.getDriverRenderer())
        self.log('shader: %s.%s' % (gsg.getDriverShaderVersionMajor(), gsg.getDriverShaderVersionMinor()))
        self.log(gsg.getDriverVersion())
        self.log('driver version: %s.%s' % (gsg.getDriverVersionMajor(), gsg.getDriverVersionMinor()))
        if eng.win:
            prop = eng.win.get_properties()
            self.log('fullscreen: '+str(prop.get_fullscreen()))
            resolution = (prop.get_x_size(), prop.get_y_size())
            self.log('resolution: %sx%s' % resolution)


class LangMgr(object):

    lang_list = ['en', 'it']
    languages = ['English', 'Italiano']

    def __init__(self, domain, path, lang_index):
        self.__domain = domain
        self.__path = path
        install(domain, path, unicode=1)
        self.set_lang(self.lang_list[lang_index])

    def set_lang(self, lang):
        self.curr_lang = lang
        try:
            lang = translation(self.__domain, self.__path, languages=[lang])
            lang.install(unicode=1)
        except IOError:
            install(self.__domain, self.__path, unicode=1)


class OptionMgr:

    @staticmethod
    def get_options():
        try:
            with open('options.yml') as opt_file:
                conf = yaml.load(opt_file)
        except IOError:
            conf = {
            'lang': 0,
            'volume': 1,
            'fullscreen': 0,
            'resolution': '1280 720',
            'aa': 0,
            'multithreaded_render': 0,
            'open_browser_at_exit': 1,
            'ai': 0,
            'submodels': 1,
            'split_world': 1}
        return conf

    @staticmethod
    def set_options(conf):
        with open('options.yml', 'w') as opt_file:
            yaml.dump(conf, opt_file, default_flow_style=False)


class FontMgr:

    def __init__(self, eng):
        self.__fonts = {}
        self.__eng = eng

    def load_font(self, path):
        if path not in self.__fonts:
            self.__fonts[path] = self.__eng.loader.loadFont(path)
            self.__fonts[path].setPixelsPerUnit(60)
            self.__fonts[path].setOutline((0, 0, 0, 1), .8, .2)
        return self.__fonts[path]


class AbsNetwork:

    def __init__(self, reader_cb):
        self.c_mgr = QueuedConnectionManager()
        self.c_reader = QueuedConnectionReader(self.c_mgr, 0)
        self.c_writer = ConnectionWriter(self.c_mgr, 0)
        self.reader_tsk = taskMgr.add(self.tsk_reader, 'connection reader', -40)
        self.reader_cb = reader_cb

    def _format(self, data_lst):
        dct_types = {bool: 'B', int: 'I', float: 'F', str: 'S'}
        return ''.join(dct_types[type(part)] for part in data_lst)

    def send(self, data_lst, receiver=None):
        datagram = PyDatagram()
        datagram.addString(self._format(data_lst))
        dct_meths = {bool: datagram.addBool, int: datagram.addInt64,
                     float: datagram.addFloat64, str: datagram.addString}
        for part in data_lst:
            dct_meths[type(part)](part)
        self._actual_send(datagram, receiver)

    def tsk_reader(self, task):
        if self.c_reader.dataAvailable():
            datagram = NetDatagram()
            if self.c_reader.getData(datagram):
                iterator = PyDatagramIterator(datagram)
                format = iterator.getString()
                dct_meths = {'B': iterator.getBool, 'I': iterator.getInt64,
                             'F': iterator.getFloat64, 'S': iterator.getString}
                msg_lst = [dct_meths[c]() for c in format]
                self.reader_cb(msg_lst, datagram.getConnection())
        return task.cont

    @property
    def is_active(self):
        return self.reader_tsk.is_alive()

    def register_cb(self, cb):
        self.reader_cb = cb

    def destroy(self):
        taskMgr.remove(self.reader_tsk)


class Server(AbsNetwork):

    def __init__(self, reader_cb, connection_cb):
        AbsNetwork.__init__(self, reader_cb)
        self.connection_cb = connection_cb
        self.c_listener = QueuedConnectionListener(self.c_mgr, 0)
        self.connections = []
        self.tcp_socket = self.c_mgr.openTCPServerRendezvous(9099, 1000)
        self.c_listener.addConnection(self.tcp_socket)
        self.listener_tsk = taskMgr.add(self.tsk_listener, 'connection listener', -39)
        eng.log_mgr.log('the server is up')

    def tsk_listener(self, task):
        if self.c_listener.newConnectionAvailable():
            rendezvous = PointerToConnection()
            net_address = NetAddress()
            new_connection = PointerToConnection()
            if self.c_listener.getNewConnection(rendezvous, net_address, new_connection):
                new_connection = new_connection.p()
                self.connections.append(new_connection)
                self.c_reader.addConnection(new_connection)
                self.connection_cb(net_address.getIpString())
                eng.log_mgr.log('received a connection from ' + net_address.getIpString())
        return task.cont

    def _actual_send(self, datagram, receiver):
        if receiver is not None:
            for client in self.connections:
                if client == receiver:
                    self.c_writer.send(datagram, client)
        else:
            for client in self.connections:
                self.c_writer.send(datagram, client)

    def destroy(self):
        AbsNetwork.destroy(self)
        for client in self.connections:
            self.c_reader.removeConnection(client)
        self.c_mgr.closeConnection(self.tcp_socket)
        taskMgr.remove(self.listener_tsk)
        eng.log_mgr.log('the server has been destroyed')


class ClientError(Exception):

    pass


class Client(AbsNetwork):

    def __init__(self, reader_cb, server_address):
        AbsNetwork.__init__(self, reader_cb)
        self.conn = self.c_mgr.openTCPClientConnection(server_address, 9099, 3000)
        if self.conn:
            self.c_reader.addConnection(self.conn)
        else:
            raise ClientError
        eng.log_mgr.log('the client is up')

    def _actual_send(self, datagram, receiver):
        self.c_writer.send(datagram, self.conn)

    def destroy(self):
        AbsNetwork.destroy(self)
        self.c_mgr.closeConnection(self.conn)
        eng.log_mgr.log('the client has been destroyed')


class Configuration:

    def __init__(self, fps=False, win_size='1280 720', win_title='Ya2',
                 fullscreen=False, cursor_hidden=False, sync_video=True,
                 antialiasing=False, profiling=False, mt_render=False):
        self.fps = fps
        self.win_size = win_size
        self.win_title = win_title
        self.fullscreen = fullscreen
        self.cursor_hidden = cursor_hidden
        self.sync_video = sync_video
        self.antialiasing = antialiasing
        self.multithreaded_render = mt_render
        self.profiling = profiling
        self.configure()

    @staticmethod
    def __set(key, value):
        loadPrcFileData('', key+' '+str(value))

    def configure(self):
        self.__set('show-frame-rate-meter', int(self.fps))
        if self.win_size:
            self.__set('win-size', self.win_size)
        self.__set('window-title', self.win_title)
        self.__set('cursor-hidden', int(self.cursor_hidden))
        self.__set('sync-video', int(self.sync_video))
        if self.antialiasing:
            self.__set('framebuffer-multisample', 1)
            self.__set('multisamples', 2)
        if self.multithreaded_render:
            self.__set('threading-model', '/Draw')
        if self.profiling:
            self.__set('want-pstats', 1)
            self.__set('task-timer-verbose', 1),
            self.__set('pstats-tasks', 1),
            self.__set('gl-finish', 1),
            self.__set('pstats-host', '127.0.0.1')
        LogMgr.configure()


class Engine(ShowBase, object):

    def __init__(self, configuration=None, domain=''):
        configuration = configuration or Configuration()
        ShowBase.__init__(self)
        __builtin__.eng = self
        self.disableMouse()
        getModelPath().appendDirectory('assets/models')
        self.enableParticles()
        #base.cam.node().getLens().setNearFar(10.0, 1000.0)

        self.render.setShaderAuto()
        self.render.setTwoSided(True)
        if configuration.antialiasing:
            self.render.setAntialias(AntialiasAttrib.MAuto)
        #self.__set_toon()

        self.font_mgr = FontMgr(self)
        self.log_mgr = LogMgr()
        self.log_mgr.log_conf()

        self.lang_mgr = LangMgr(domain, './assets/locale',
                                OptionMgr.get_options()['lang'])

        if self.win:
            try:
                self.set_resolution('x'.join(configuration.win_size.split()))
            except AttributeError:
                pass  # configuration file doesn't exist
            if OptionMgr.get_options()['fullscreen']:
                self.toggle_fullscreen()

            self.win.setCloseRequestEvent('window-closed')
            self.accept('window-closed', self.__on_close)

    def __set_toon(self):
        tempnode = NodePath(PandaNode("temp node"))
        tempnode.setAttrib(LightRampAttrib.makeSingleThreshold(0.5, 0.4))
        tempnode.setShaderAuto()
        base.cam.node().setInitialState(tempnode.getState())
        CommonFilters(base.win, base.cam).setCartoonInk(separation=1)

    def __on_close(self):
        if OptionMgr.get_options()['open_browser_at_exit']:
            eng.open_browser('http://www.ya2.it')
        self.closeWindow(self.win)
        sys.exit()

    def toggle_pause(self):
        if not get_isPaused():
            self.pauseFrame = DirectFrame(
                frameColor=(.3, .3, .3, .7), frameSize=(-1.8, 1.8, -1, 1))
        else:
            self.pauseFrame.destroy()
        (resume if get_isPaused() else pause)()

    def init(self):
        self.collision_objs = []
        self.__coll_dct = {}
        self.world_np = render.attachNewNode('world')
        self.world_phys = BulletWorld()
        self.world_phys.setGravity((0, 0, -9.81))
        debug_node = BulletDebugNode('Debug')
        debug_node.showBoundingBoxes(True)
        self.__debug_np = self.render.attachNewNode(debug_node)
        self.world_phys.setDebugNode(self.__debug_np.node())

    def start(self):
        self.taskMgr.add(self.__update, 'Engine::update')

    def stop(self):
        eng.world_phys = None
        eng.world_np.removeNode()
        self.__debug_np.removeNode()

    def __update(self, task):
        if self.world_phys:
            dt = globalClock.getDt()
            self.world_phys.doPhysics(dt, 10, 1/180.0)
            self.__do_collisions()
            self.messenger.send('on_frame')
            return task.cont

    def __do_collisions(self):
        to_clear = self.collision_objs[:]
        for obj in self.collision_objs:
            if not obj in self.__coll_dct:
                self.__coll_dct[obj] = []
            result = self.world_phys.contactTest(obj)
            for contact in result.getContacts():
                def process_contact(node):
                    if node != obj:
                        if obj in to_clear:
                            to_clear.remove(obj)
                        if not node in [coll_pair[0] for coll_pair in self.__coll_dct[obj]]:
                            self.__coll_dct[obj] += [(node, globalClock.getFrameTime())]
                            self.messenger.send('on_collision', [obj, node.getName()])
                process_contact(contact.getNode0())
                process_contact(contact.getNode1())
        for obj in to_clear:
            for coll_pair in self.__coll_dct[obj]:
                if globalClock.getFrameTime() - coll_pair[1] > .25:
                    self.__coll_dct[obj].remove(coll_pair)

    @property
    def resolutions(self):
        di = self.pipe.getDisplayInformation()
        res_values = [
            (di.getDisplayModeWidth(idx), di.getDisplayModeHeight(idx))
            for idx in range(di.getTotalDisplayModes())]
        return ['%dx%d' % (s[0], s[1]) for s in sorted(list(set(res_values)))]

    @property
    def resolution(self):
        win_prop = self.win.get_properties()
        res_x, res_y = win_prop.get_x_size(), win_prop.get_y_size()
        return '%dx%d' % (res_x, res_y)

    @property
    def closest_res(self):
        def split_res(res):
            return [int(v) for v in res.split('x')]

        def distance(res):
            curr_res, res = split_res(eng.resolution), split_res(res)
            return abs(res[0] - curr_res[0]) + abs(res[1] - curr_res[1])

        dist_lst = map(distance, eng.resolutions)
        try:
            idx_min = dist_lst.index(min(dist_lst))
            return eng.resolutions[idx_min]
        except ValueError:  # sometimes we have empty resolutions
            return eng.resolution

    def set_resolution(self, res, check=True):
        self.log_mgr.log('setting resolution ' + str(res))
        props = WindowProperties()
        props.set_size(*[int(resol) for resol in res.split('x')])
        self.win.request_properties(props)
        if check:
            taskMgr.doMethodLater(
                3.0, self.set_resolution_check, 'resolution check', [res])

    def set_resolution_check(self, res):
        self.log_mgr.log('resolutions: %s %s' % (self.resolution, res))
        if self.resolution != res:
            self.log_mgr.log('second attempt: %s %s' % (self.resolution, res))
            self.set_resolution(res, False)

    def open_browser(self, url):
        if sys.platform.startswith('linux'):
            environ['LD_LIBRARY_PATH'] = ''
            system('xdg-open '+url)
        else:
            open_new_tab(url)

    @property
    def version(self):
        version = 'version: source'
        if self.appRunner:
            package = self.appRunner.p3dInfo.FirstChildElement('package')
            version = 'version: ' + package.Attribute('version')
        return version

    def print_stats(self):
        print '\n\n#####\nrender2d.analyze()'
        self.render2d.analyze()
        print '\n\n#####\nrender.analyze()'
        self.render.analyze()
        print '\n\n#####\nrender2d.ls()'
        self.render2d.ls()
        print '\n\n#####\nrender.ls()'
        self.render.ls()

    def particle(self, path, parent, renderParent, pos, timeout):
        p = ParticleEffect()
        p.loadConfig(path)
        p.start(parent=parent, renderParent=renderParent)
        p.setPos(pos)
        taskMgr.doMethodLater(timeout, lambda p: p.cleanup(), 'clear', [p])

    def toggle_debug(self):
        is_hidden = self.__debug_np.isHidden()
        (self.__debug_np.show if is_hidden else self.__debug_np.hide)()

    def toggle_fullscreen(self, state=None):
        self.set_resolution(self.closest_res)
        props = WindowProperties()
        props.set_fullscreen(not self.win.is_fullscreen())
        base.win.requestProperties(props)
