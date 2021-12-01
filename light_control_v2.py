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

# These functions are used as helpers to for consistency in constructing data
extract_name_func = lambda x: x['metadata']['name'].lower()
scene_name_func = lambda x, y: x + DELIMITER + y


class HueCommunicator:
    """
    This class is used to execute functions with the Hue API. It can apply a given scene to a given room and turn off
    the lights in a given room.
    """
    def __init__(self):
        with open(PATH + '/user.json') as f:
            user = json.load(f)
        self.user = user['username']

        if os.path.exists(PATH + '/cache.json'):
            with open(PATH + '/cache.json') as f:
                self.cache = json.load(f)
        else:
            self.cache = {}

        if 'base_url' in self.cache:
            self.base_url = self.cache['base_url']
        else:
            self._find_base_url()

    def _find_base_url(self):
        """
        Used to find the base url of the Hue bridge. Saves the value to the cache when complete
        :return: None
        """
        res = requests.get('https://discovery.meethue.com/')
        res = json.loads(res.content)
        ip = res[0]['internalipaddress']
        self.base_url = f"https://{ip}/clip/v2"
        self.cache['base_url'] = self.base_url

    def _get_room(self, expected_room, retried=False):
        """
        Gets the API id of the room with the given name. The cache is first checked for a room with the given name. If
        there is a cache, but no room with this name, we pull the data anyway because the cache might be out of date. If
        we timeout talking to the API, we refresh the base url in the cache. If we query the API for room ids, we save
        that to the cache.
        :param expected_room: The string name of the room we want the id of
        :param retried: flag to prevent infinite recursion (if we need to retry more than once, stop and throw an error)
        :return: The API id of the room
        """
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
        """
        Gets the API id of the scene with the given name that is within the given room. It needs to be based on the room
        as well because multiple rooms can have scenes with the same name. The cache is first checked for a scene with
        the given name. If there is a cache, but no scene with this name in this room, we pull the data anyway because
        the cache might be out of date. If the room id is not found to belong to any scene, we refresh the rooms because
        the cache may be wrong. If we timeout talking to the API, we refresh the base url in the cache. If we query the
        API for scene ids, we save that to the cache.
        :param expected_scene: The string name of the scene we want the id of
        :param room_name: The string name of the room that this scene is for
        :param room_id: The API id of the room
        :param retried: flag to prevent infinite recursion (if we need to retry more than once, stop and throw an error)
        :return: The API id of the scene
        """
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
                resource_res = {scene_name_func(extract_name_func(x), x['group']['rid']): x['id'] for x in
                                resource_res['data']}
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
        """
        Gets the API id of the grouped lights within the room with the given name. The cache is first checked for a
        grouped light in a room with the given name. If there is a cache, but no grouped light in a room with this name,
        we pull the data anyway because the cache might be out of date. If we timeout talking to the API, we refresh the
        base url in the cache. If we query the API for grouped light ids, we save that to the cache.
        :param expected_room: The string name of the room we want the id of
        :param retried: flag to prevent infinite recursion (if we need to retry more than once, stop and throw an error)
        :return: The API id of the grouped light for the room
        """
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
        Given a room name and a scene name, applies that scene to that room. Data is cached to make this process faster.
        Any cached data is used first, but if errors occur the cache is refreshed and that data is queried from the API.
        Any new data is then saved to the cache. If we timeout talking to the API, we refresh the base url in the cache.
        :param room_name: The string name of the room containing the scene
        :param scene_name: The string name of the scene to apply
        :param retried_ip: flag to prevent infinite recursion when finding the Hue Bridge IP (if we need to retry more
        than once, stop and throw an error)
        :param retried_data: flag to prevent infinite recursion when refreshing data (if we need to retry more than
        once, stop and throw an error)
        :return: None
        """
        if 'room' in self.cache and room_name in self.cache['room']:
            room_id = self.cache['room'][room_name]
        else:
            room_id = self._get_room(room_name)

        unique_scene_name = scene_name_func(scene_name, room_id)
        if 'scene' in self.cache and unique_scene_name in self.cache['scene']:
            scene_id = self.cache['scene'][unique_scene_name]
        else:
            scene_id = self._get_scene(scene_name, room_name, room_id)

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

        if result.status_code != 200:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")

    def turn_off_room(self, room_name, retried_ip=False, retried_data=False):
        """
        Given a room, turns off the lights in that room. This is done by getting the grouped light id for that room and
        turning off all the lights at once. Data is cached to make this process faster. Any cached data is used first,
        but if errors occur the cache is refreshed and that data is queried from the API.
        :param room_name: The string name of the room where the lights should be turned off
        ::param retried_ip: flag to prevent infinite recursion when finding the Hue Bridge IP (if we need to retry more
        than once, stop and throw an error)
        :param retried_data: flag to prevent infinite recursion when refreshing data (if we need to retry more than
        once, stop and throw an error)
        :return: None
        """
        grouped_light = self._get_room_grouped_light(room_name)

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

        if result.status_code != 200 and result.status_code != 207:
            raise Exception(f"Something went wrong applying the scene: {result.status_code}: {result.reason}")

    def save_cache(self):
        with open(PATH + '/cache.json', 'w+') as f:
            f.write(json.dumps(self.cache))


def main():
    scene_name = sys.argv[1].lower()
    if len(sys.argv) > 2:
        room = sys.argv[2].lower()
    else:
        room = DEFAULT_ROOM

    hue = HueCommunicator()

    total_start = time.time()

    def do_operation(retry=False):
        try:
            if scene_name == 'off':
                hue.turn_off_room(room)
            else:
                hue.apply_scene_to_room(room, scene_name)
        except Exception as e:
            # As a one time last resort, if we get an exception, clear the cache and try again
            if not retry:
                hue.cache = {}
                do_operation(retry=True)
            else:
                print('ERROR: ' + str(e))

    do_operation()

    print(f"Finished whole operation in {time.time() - total_start}s")

    hue.save_cache()


if __name__ == '__main__':
    main()
