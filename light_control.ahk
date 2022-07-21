F20::Light_Control("off", "Living room")
F21::Light_Control("read", "Living room")
F22::Light_Control("relax", "Living room")
F23::Light_Control("nightlight", "Living room")

^F20::Light_Control("off", "Bedroom")
^F21::Light_Control("read", "Bedroom")
^F22::Light_Control("relax", "Bedroom")
^F23::Light_Control("nightlight", "Bedroom")


Light_Control(setting, room) {
  Run "C:\Users\David\Documents\Personal Projects\PhilipsHueControl\light_control_v2.py" %setting% "%room%",, Hide
  return
}