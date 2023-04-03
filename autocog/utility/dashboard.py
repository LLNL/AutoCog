import os, time, copy, json
import flask
from flask_socketio import SocketIO
from threading import Thread
from IPython.display import IFrame, display

from autocog.architecture import PromptPipe

class Prompt2DashBoard(PromptPipe):
    def __init__(self, dashboard, **kwargs):
        self.dashboard = dashboard
        self.kwargs = copy.deepcopy(kwargs)

    def set(self, **kwargs):
        self.kwargs.update(kwargs)
        self.dashboard.update(stream='stream1', text=json.dumps(kwargs) + '\n')
        return self

    def write(self, text):
        self.dashboard.update(stream='stream2', text=text)

class LiveDashboard:
    def _index(self):
        return flask.render_template(self.template_board)

    def _handle_connect(self):
        print('connected')

    def _handle_stop(self, data):
        print('stop')

    def _start_dashboard_thread(self):
        self.sio.run(self.app, allow_unsafe_werkzeug=True)

    def __init__(self, template_folder=os.path.realpath('share'), width="100%", height="500px", template_board='dashboard.html'):
        self.template_board = template_board

        self.app = flask.Flask(__name__, template_folder=template_folder)
        self.app.add_url_rule('/', view_func=self._index)

        self.sio = SocketIO(self.app)
        self.sio.on_event('connect', self._handle_connect)
        self.sio.on_event('stop', self._handle_stop)

        self.width = width
        self.height = height

        self.server = Thread(target=self._start_dashboard_thread)
        self.server.start()

        time.sleep(.1)
        display(IFrame(src="http://localhost:5000", width=self.width, height=self.height))

    def update(self, **data):
        self.sio.emit('update', data)

    def get_prompt_output(self):
        return Prompt2DashBoard(dashboard=self)