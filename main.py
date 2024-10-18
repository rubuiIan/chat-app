from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join")
        create = request.form.get("create")

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        # Check if creating a room
        if create == "create":
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
            session["room"] = room
            session["name"] = name
            # Ensure full URL is used (with http://)
            shareable_link = request.host_url + url_for("room", code=room)
            return render_template("home.html", code=room, name=name, shareable_link=shareable_link)
        
        # Check if joining a room
        if join == "join":
            if not code or code not in rooms:
                return render_template("home.html", error="Room does not exist.", code=code, name=name)
            session["room"] = code
            session["name"] = name
            return redirect(url_for("room", code=code))

    return render_template("home.html")

@app.route("/room/<code>")
def room(code):
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    # Log message to terminal
    print(f"{session.get('name')} said: {data['data']} in room {room}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    # Notify others in the room that a new user has joined
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    # Log to terminal
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
