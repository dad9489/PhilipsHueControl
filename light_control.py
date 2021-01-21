import json
import requests
import sys
import pathlib

READ = {"on": True, "bri": 254, "hue": 8593, "sat": 121, "xy": [0.4452, 0.4068], "ct": 343, "colormode": "xy"}
RELAX = {"on": True, "bri": 144, "hue": 8593, "sat": 121, "xy": [0.5018, 0.4152], "ct": 447, "colormode": "xy"}
DIMMED = {"on": True, "bri": 84, "hue": 7676, "sat": 199, "xy": [0.561, 0.4042], "ct": 443, "colormode": "xy"}
OFF = {"on": False}

DEFAULT_ROOM = 'Davids Room'


def get_base_url():
    path = str(pathlib.Path(__file__).parent.absolute())
    with open(path+'/user.json') as f:
        user = json.load(f)
    user = user['username']
    try:
        res = requests.get('https://discovery.meethue.com/')
        res = json.loads(res.content)
        ip = res[0]['internalipaddress']
        return f"http://{ip}/api/{user}"
    except Exception as e:
        raise Exception(f"There was a problem reaching the Philips Hue bridge: {e}")


def main():
    base_url = get_base_url()
    groups = json.loads(requests.get(base_url+"/groups").content)
    action_str = sys.argv[1]
    if len(sys.argv) > 2:
        room = sys.argv[2]
    else:
        room = DEFAULT_ROOM
    room_id = [x['name'] for x in groups.values()].index(room) + 1

    if action_str == "read":
        action = READ
    elif action_str == "relax":
        action = RELAX
    elif action_str == "dimmed":
        action = DIMMED
    elif action_str == "off":
        action = OFF
    else:
        raise TypeError(f"Invalid command argument '{action_str}'")
    requests.put(base_url+f"/groups/{room_id}/action", data=json.dumps(action))
    x = 1


if __name__ == '__main__':
    main()
