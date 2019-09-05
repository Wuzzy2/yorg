# ================================= BUGS ======================================


# ============================== TODO LIST ====================================


# =============================== WAITING =====================================

# flatpak on the vps: issues #28

# ============================ MAYBE/SOMEDAY ==================================

# remove camera's render_all workaround
# refactor the server (async.io) or
#     def update(): ... threading.Timer(.5, update).start()
# refactoring: do event/observer for joystick buttons
# remove dependencies: bson (struct), pyyaml (configparser+json),
#   feedparser (write my function which retrieve posts' titles)
# use python's logging in place of eng.log
# lib/p3d/gui.py, lib/p3d/gfx.py: __init__ method from a non direct base class
#   'Facade' is called
# remove eng.server
# gui: do a single page for configuring the race (less testing)
# class Player (has-a car, has-a driver)
# where proper (i.e. where observers aren't tied to the observable) replace
#   observer with publisher-subscriber
# attach/attach_obs, detach/detach_obs - the client attach-es it to the
#   observed, then it attach-es it to the component
# notify's sender (see page.py)
# object's creation: isolate the parallel creation and construct object in the
#   standard way (fields) and use the parallel creation only when it is useful
# (waiting for refactored objects' creation): facade, pass a single list (meth
#   for callables, prop for others)
# racing should be another package in another submodule (i.e. yorg contains
#   yyagl/ and racing/)
# yyagl's scons
# unit tests
# https://discourse.panda3d.org/t/sample-using-directional-lights-shadows-effectively/24424
# improve rear camera
# load the car and the track from a single file
# reconfigure gamepad buttons (as for keyboard ones)
# force feedback on crash and weapon
# improve online multiplayer's end of race (print realtime ranking, show
#   bigger minimap)
# fix ai
# appimage packages
# add inertia to the camera (more info on freegamer)
# joypad's commands in the loading menu
