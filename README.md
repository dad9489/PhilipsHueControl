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
python light_control.py read "Living Room"
```