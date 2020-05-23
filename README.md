# FallingLetters
Heavily commented code (drawing on PyGame, PyMunk, and Tkinter) showing a way to add
arbitrary shapes to a pixel-perfect pygame 2D-animation in progress.  Letters or numbers entered from the keyboard are used as arbitrary shapes. The characters are stored in a fifo queue monitored from a worker thread. The leading element in the queue is sent to a workspace where an exterior profile of its glyph is derived as a sequence of segments. This 'shape', together with an appropriate 'body', is then added to the animation.

The demo uses a pymunk space (with the default collision handler) containing some static and dynamic objects, into which the glyph sprites are added sequentially from the queue.  Pixel-perfect or Bounding-box conditions can be selected and mixed, and various details can be chosen to display.

Requires: Python 3.7. or later.           Qualified: MacOS10, Windows10, Ubuntu20
