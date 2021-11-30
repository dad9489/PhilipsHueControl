import json
import requests
import sys
import pathlib
import time
import os

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

PATH = str(pathlib.Path(__file__).parent.absolute())
DEFAULT_ROOM = 'davids room'

DELIMITER = '#$#$#'

# If the resource is a room, we just get the name. If its a scene, multiple rooms can have scenes with
# the same name so we also add the room id to the key to ensure the keys are unique
extract_name_func = lambda x: x['metadata']['name'].lower()
scene_name_func = lambda x, y: x + DELIMITER + y


class HueCommunicator:
    def __init__(self):
        start = time.time()
        with open(PATH + '/user.json') as f:
            user = json.load(f)
        self.user = user['username']
        print(f"Loaded file in {time.time() - start}s")

        if os.path.exists(PATH + '/cache.json'):
            with open(PATH + '/cache.json') as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

        if 'base_url' in self.cache:
            self.base_url = self.cache['base_url']
            # Check base url
            # valid = True
            # try:
            #     # TODO should we do this validation check? Is it necessary?
            #     start_valid_check = time.time()
            #     status = requests.get('://'.join(urlsplit(self.base_url)[0:2]), verify=False,
            #                           headers={'hue-application-key': self.user}).status_code
            #     valid = (status == 200)
            # except requests.exceptions.ConnectionError:
            #     valid = False
            #
            # if not valid:
            #     self._find_base_url()
            # else:
            #     print(f"Verified cached base url in {time.time() - start_valid_check}s")
        else:
            self._find_base_url()
        print(f"Init in {time.time() - start}s")

    def _find_base_url(self):
        res = requests.get('https://discovery.meethue.com/')
        res = json.loads(res.content)
        ip = res[0]['internalipaddress']
        self.base_url = f"https://{ip}/clip/v2"
        self.cache['base_url'] = self.base_url

    def _get_room(self, expected_room, retried=False):
        try:
            if 'room' in self.cache and self.cache['room'] != {}:
                resource_res = self.cache['room']
            else:
                resource_res = json.loads(requests.get(self.base_url + f"/resource/room", verify=False,
                                                       headers={'hue-application-key': self.user}, timeout=1).content)

                # If the resource is a room, we just get the name. If its a scene, multiple rooms can have scenes with
                # the same name so we also add the room id to the key to ensure the keys are unique
                resource_res = {extract_name_func(x): x['id'] for x in resource_res['data']}
                self.cache['room'] = resource_res

            if expected_room not in resource_res:
                if retried:
                    raise Exception(f"Could not find room named {expected_room}")
                else:
                    self.cache['room'] = {}
                    return self._get_room(expected_room, retried=True)
        except requests.exceptions.ConnectionError:
            # There was an error when connecting the bridge. This either means there is truly an error, or it means
            # we cached the bridge url and it changed. In this case, we query for the bridge ip again.
            if retried:
                raise Exception("Could not connect to Hue Bridge")
            else:
                self.cache['room'] = {}
                self._find_base_url()
                return self._get_room(expected_room, retried=True)
        return resource_res[expected_room]

    def _get_scene(self, expected_scene, room_name, room_id, retried=False):
        try:
            if 'scene' in self.cache and self.cache['scene'] != {}:
                resource_res = self.cache['scene']
            else:
                resource_res = json.loads(requests.get(self.base_url + f"/resource/scene", verify=False,
                                                       headers={'hue-application-key': self.user}, timeout=1).content)
                rooms_with_scenes = {x['group']['rid'] for x in resource_res['data']}
                if room_id not in rooms_with_scenes:
                    self.cache['room'] = {}
                    room_id = self._get_room(room_name)
                resource_res = {scene_name_func(extract_name_func(x), x['group']['rid']): x['id'] for x in resource_res['data']}
                self.cache['scene'] = resource_res

            unique_scene = scene_name_func(expected_scene, room_id)
            if unique_scene not in resource_res:
                if retried:
                    raise Exception(f"Could not find scene named {expected_scene}")
                else:
                    self.cache['scene'] = {}
                    return self._get_scene(expected_scene, room_name, room_id, retried=True)
        except requests.exceptions.ConnectionError:
            # There was an error when connecting the bridge. This either means there is truly an error, or it means
            # we cached the bridge url and it changed. In this case, we query for the bridge ip again.
            if retried:
                raise Exception("Could not connect to Hue Bridge")
            else:
                self.cache['scene'] = {}
                self._find_base_url()
                return self._get_scene(expected_scene, room_name, room_id, retried=True)
        return resource_res[unique_scene]

    def _get_room_grouped_light(self, expected_room, retried=False):
        try:
            if 'grouped_light' in self.cache and self.cache['grouped_light'] != {}:
                resource_res = self.cache['grouped_light']
            else:
                resource_res = json.loads(requests.get(self.base_url + f"/resource/room", verify=False,
                                                       headers={'hue-application-key': self.user}, timeout=1).content)

                # If the resource is a room, we just get the name. If its a scene, multiple rooms can have scenes with
                # the same name so we also add the room id to the key to ensure the keys are unique
                resource_res = {extract_name_func(x): x['grouped_services'][0]['rid'] for x in resource_res['data']}
                self.cache['grouped_light'] = resource_res

            if expected_room not in resource_res:
                if retried:
                    raise Exception(f"Could not find room named {expected_room}")
                else:
                    self.cache['grouped_light'] = {}
                    return self._get_room_grouped_light(expected_room, retried=True)
        except requests.exceptions.ConnectionError:
            # There was an error when connecting the bridge. This either means there is truly an error, or it means
            # we cached the bridge url and it changed. In this case, we query for the bridge ip again.
            if retried:
                raise Exception("Could not connect to Hue Bridge")
            else:
                self.cache['grouped_light'] = {}
                self._find_base_url()
                return self._get_room_grouped_light(expected_room, retried=True)
        return resource_res[expected_room]

    def apply_scene_to_room(self, room_name, scene_name, retried_ip=False, retried_data=False):
        """
        Given a room name and a scene name, applies that scene to that room if possible. Throws an error if the room
        doesn't exist, if the scene doesn't exist in that room, or if something else goes wrong.
        :param room_name: The string name of the room
        :param scene_name: The string name of the scene
        """
        start = time.time()
        if 'room' in self.cache and room_name in self.cache['room']:
            room_id = self.cache['room'][room_name]
        else:
            room_id = self._get_room(room_name)
        print(f"Got room id in {time.time() - start}s")

        unique_scene_name = scene_name_func(scene_name, room_id)
        if 'scene' in self.cache and unique_scene_name in self.cache['scene']:
            scene_id = self.cache['scene'][unique_scene_name]
        else:
            scene_id = self._get_scene(scene_name, room_name, room_id)
        print(f"Got scenes in {time.time() - start}s")

        # Apply the scene to the room
        try:
            result = requests.put(self.base_url + f"/resource/scene/{scene_id}",
                                  data=json.dumps({"recall": {"status": "active"}}), verify=False,
                                  headers={'hue-application-key': self.user}, timeout=1)
            if result.status_code == 404:
                if retried_data:
                    raise Exception("Something went wrong, could not match scene with a valid id.")
                else:
                    self.cache['room'] = {}
                    self.cache['scene'] = {}
                    return self.apply_scene_to_room(room_name, scene_name, retried_ip=True)
        except requests.exceptions.ConnectionError:
            # There was an error when connecting the bridge. This either means there is truly an error, or it means
            # we cached the bridge url and it changed. In this case, we query for the bridge ip again.
            if retried_ip:
                raise Exception("Could not connect to Hue Bridge")
            else:
                self._find_base_url()
                return self.apply_scene_to_room(room_name, scene_name, retried_ip=True)

        print(f"Applied operation in {time.time() - start}s")
        if result.status_code != 200:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")

    def turn_off_room(self, room_name, retried_ip=False, retried_data=False):
        start = time.time()
        grouped_light = self._get_room_grouped_light(room_name)
        print(f"Got grouped light in {time.time() - start}s")

        try:
            result = requests.put(self.base_url + f"/resource/grouped_light/{grouped_light}",
                                  data=json.dumps({"on": {"on": False}}), verify=False,
                                  headers={'hue-application-key': self.user}, timeout=1)
            if result.status_code == 404:
                if retried_data:
                    raise Exception("Something went wrong, could not match scene with a valid id.")
                else:
                    self.cache['grouped_light'] = {}
                    return self.turn_off_room(room_name, retried_ip=True)
        except requests.exceptions.ConnectionError:
            # There was an error when connecting the bridge. This either means there is truly an error, or it means
            # we cached the bridge url and it changed. In this case, we query for the bridge ip again.
            if retried_ip:
                raise Exception("Could not connect to Hue Bridge")
            else:
                self._find_base_url()
                return self.turn_off_room(room_name, retried_ip=True)

        print(f"Applied result in {time.time() - start}s")
        if result.status_code != 200 and result.status_code != 207:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")

    def save_cache(self):
        with open(PATH + '/cache.json', 'w+') as f:
            f.write(json.dumps(self.cache))


def main():
    action_str = sys.argv[1].lower()
    if len(sys.argv) > 2:
        room = sys.argv[2].lower()
    else:
        room = DEFAULT_ROOM

    hue = HueCommunicator()

    total_start = time.time()
    if action_str == 'off':
        hue.turn_off_room(room)
    else:
        hue.apply_scene_to_room(room, action_str)
    print(f"Finished whole operation in {time.time() - total_start}s")

    hue.save_cache()


if __name__ == '__main__':
    main()
