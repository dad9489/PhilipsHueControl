F20::Light_Control("off", "Davids Room")
F21::Light_Control("read", "Davids Room")
F22::Light_Control("relax", "Davids Room")
F23::Light_Control("dimmed", "Davids Room")

^F20::Light_Control("off", "Living Room")
^F21::Light_Control("read", "Living Room")
^F22::Light_Control("relax", "Living Room")
^F23::Light_Control("dimmed", "Living Room")


Light_Control(setting, room) {
  Run "C:\Users\David\Documents\Personal Projects\PhilipsHueControl\light_control.py" %setting% "%room%"
  return
}