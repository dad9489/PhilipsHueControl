import json
import requests
import sys
import pathlib
import time

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PATH = str(pathlib.Path(__file__).parent.absolute())
DEFAULT_ROOM = 'davids room'
SSL_CERT = PATH + '/huebridge_cacert.pem'


class HueCommunicator:
    def __init__(self):
        with open(PATH + '/user.json') as f:
            user = json.load(f)
        self.user = user['username']

        res = requests.get('https://discovery.meethue.com/')
        res = json.loads(res.content)
        ip = res[0]['internalipaddress']
        self.base_url = f"https://{ip}/clip/v2"

    def _get_rooms(self):
        """
        Creates a mapping of room names to the api id for that room.
        """
        rooms = json.loads(requests.get(self.base_url + "/resource/room", verify=False,
                                        headers={'hue-application-key': self.user}).content)
        rooms = {x['metadata']['name'].lower(): x['id'] for x in rooms['data']}
        return rooms

    def _get_room_grouped_light(self, room_name):
        """
        Gets the grouped light that corresponds to this room. This can be used to control all the lights in the room
        at once.
        :param room_name: The string name of the room
        :return: The id of the grouped light for this room
        """
        rooms = json.loads(requests.get(self.base_url + "/resource/room", verify=False,
                                        headers={'hue-application-key': self.user}).content)
        if room_name not in [x['metadata']['name'].lower() for x in rooms['data']]:
            raise Exception(f"There was an invalid room name given: {room_name}")

        return [x for x in [x['services'] for x in rooms['data'] if x['metadata']['name'].lower() == room_name][0] if
                x['rtype'] == 'grouped_light'][0]['rid']

    def apply_scene_to_room(self, room_name, scene_name):
        """
        Given a room name and a scene name, applies that scene to that room if possible. Throws an error if the room
        doesn't exist, if the scene doesn't exist in that room, or if something else goes wrong.
        :param room_name: The string name of the room
        :param scene_name: The string name of the scene
        """
        rooms = self._get_rooms()
        if room_name not in rooms:
            raise Exception(f"There was an invalid room name given: {room_name}")

        # Get all scenes, and then filter down to only scenes in this room. Create a map of scene names to ids.
        all_scenes = json.loads(requests.get(self.base_url + "/resource/scene", verify=False,
                                             headers={'hue-application-key': self.user}).content)
        scenes_for_room = {x['metadata']['name'].lower(): x['id'] for x in all_scenes['data'] if
                           x['group']['rid'] == rooms[room_name]}
        if scene_name not in scenes_for_room.keys():  # Validate that the given scene exists in this room
            raise Exception(f"The scene '{scene_name}' does not exist in the room '{room_name}'")

        # Apply the scene to the room
        result = requests.put(self.base_url + f"/resource/scene/{scenes_for_room[scene_name]}",
                              data=json.dumps({"recall": {"status": "active"}}), verify=False,
                              headers={'hue-application-key': self.user})

        if result.status_code != 200:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")

    def turn_off_room(self, room_name):
        start = time.time()
        grouped_light = self._get_room_grouped_light(room_name)
        result = requests.put(self.base_url + f"/resource/grouped_light/{grouped_light}",
                              data=json.dumps({"on": {"on": False}}), verify=False,
                              headers={'hue-application-key': self.user})
        if result.status_code != 200:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")


def main():
    action_str = sys.argv[1].lower()
    if len(sys.argv) > 2:
        room = sys.argv[2].lower()
    else:
        room = DEFAULT_ROOM

    hue = HueCommunicator()

    if action_str == 'off':
        hue.turn_off_room(room)
    else:
        hue.apply_scene_to_room(room, action_str)


if __name__ == '__main__':
    main()
