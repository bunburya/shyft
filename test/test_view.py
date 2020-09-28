import flask
from pyft.view import view_activity

server = flask.Flask(__name__)

app = view_activity.