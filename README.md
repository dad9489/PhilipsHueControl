# PhilipsHueControl

This is a script for controlling the Philips Hue light bulbs in my house. I have it hooked up to macros on my keyboard
to control my lights with the touch of a button.

In order to run this script, you must create a json file titled user.json that contains the following information:
```
{
    "username": PHILIPS_HUE_USERNAME
}
```
`PHILIPS_HUE_USERNAME` is the id of the user on your Philips Hue bridge. For more information about creating this
user visit, https://developers.meethue.com/develop/get-started-2/.

This program accepts two command line arguments: the light setting and the room. If no room is supplied, it will use the
defined `DEFAULT_ROOM`.

An example of running this program would look like:
```
python light_control_v2.py read "Living Room"
```

## Hue API V2

V2 of the Philips Hue API is now released. `light_control_v2.py` makes use of this new version of the API. Instead of
relying on hard coding what each scene means, this v2 script can directly use the scenes configured in the Philips Hue
app. It also works more reliably. An issue would sometimes occur with v1 where the lights would be dimmed, but the color
would not change or vice versa. Working directly with the scenes in v2 prevents this.

### Caching
V2 of the API requires more API calls since the id of the scene needs to be queried as well as the id of the room.
This means executing the v2 script could take longer than v1. To counteract this, a caching system was implemented for
`light_control_v2.py`. It will cache data pulled from the API so subsequent calls are faster. If anything changes in
the API such as the IP address of the Hue Bridge, the internal id of a room, etc., the cache is updated with the new
data. The script call that caused the update will be slower, but all others after it will remain fast.