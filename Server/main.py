# set async_mode to 'threading', 'eventlet', 'gevent' or 'gevent_uwsgi' to
# force a mode else, the best mode is selected automatically from what's
# installed
async_mode = None

import time
from flask import Flask, render_template, send_from_directory
import socketio

sio = socketio.Server(logger=True, async_mode=async_mode)
app = Flask(__name__)
app.wsgi_app = socketio.Middleware(sio, app.wsgi_app)
app.config['SECRET_KEY'] = 'secret!'
thread = None


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        sio.sleep(10)
        count += 1
        sio.emit('my response', {'data': 'Server generated event'},
                 namespace='/')


@app.route('/', methods=['GET', 'POST'])
def index():
    global thread
    if thread is None:
        thread = sio.start_background_task(background_thread)
    return render_template('index.html')


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route('/css/<path:path>')
def send_css(path):
    return send_from_directory('css', path)


@sio.on('my event', namespace='/')
def test_message(sid, message):
    sio.emit('my response', {'data': message['data']}, room=sid,
             namespace='/')


@sio.on('my broadcast event', namespace='/')
def test_broadcast_message(sid, message):
    sio.emit('my response', {'data': message['data']}, namespace='/')


@sio.on('join', namespace='/')
def join(sid, message):
    sio.enter_room(sid, message['room'], namespace='/')
    sio.emit('my response', {'data': 'Entered room: ' + message['room']},
             room=sid, namespace='/')


@sio.on('leave', namespace='/')
def leave(sid, message):
    sio.leave_room(sid, message['room'], namespace='/')
    sio.emit('my response', {'data': 'Left room: ' + message['room']},
             room=sid, namespace='/')


@sio.on('close room', namespace='/')
def close(sid, message):
    sio.emit('my response',
             {'data': 'Room ' + message['room'] + ' is closing.'},
             room=message['room'], namespace='/')
    sio.close_room(message['room'], namespace='/')


@sio.on('my room event', namespace='/')
def send_room_message(sid, message):
    sio.emit('my response', {'data': message['data']}, room=message['room'],
             namespace='/')


@sio.on('disconnect request', namespace='/')
def disconnect_request(sid):
    sio.disconnect(sid, namespace='/')


@sio.on('connect', namespace='/')
def test_connect(sid, environ):
    sio.emit('my response', {'data': 'Connected', 'count': 0}, room=sid,
             namespace='/')


@sio.on('disconnect', namespace='/')
def test_disconnect(sid):
    print('Client disconnected')


if __name__ == '__main__':
    if sio.async_mode == 'threading':
        # deploy with Werkzeug
        app.run(threaded=True)
    elif sio.async_mode == 'eventlet':
        # deploy with eventlet
        import eventlet
        import eventlet.wsgi
        eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
    elif sio.async_mode == 'gevent':
        # deploy with gevent
        from gevent import pywsgi
        try:
            from geventwebsocket.handler import WebSocketHandler
            websocket = True
        except ImportError:
            websocket = False
        if websocket:
            pywsgi.WSGIServer(('', 5000), app,
                              handler_class=WebSocketHandler).serve_forever()
        else:
            pywsgi.WSGIServer(('', 5000), app).serve_forever()
    elif sio.async_mode == 'gevent_uwsgi':
        print('Start the application through the uwsgi server. Example:')
        print('uwsgi --http :5000 --gevent 1000 --http-websockets --master '
              '--wsgi-file app.py --callable app')
    else:
        print('Unknown async_mode: ' + sio.async_mode)
