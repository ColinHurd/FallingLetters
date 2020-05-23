#                                FALLING LETTERS
#                         With acknowledgement to R.\Marxer                                             #       http://www.ricardmarxer.com/fisica/examples/Letters/applet/Letters.pde
"""
Heavily commented code (drawing on PyGame, PyMunk, and Tkinter) showing a way to add
arbitrary shapes to a pixel-perfect pygame 2D-animation in progress.  Letters or numbers entered from the keyboard are used as arbitrary shapes. The characters are stored in a fifo queue monitored from a worker thread. The leading element in the queue is sent to a workspace where an exterior profile of its glyph is derived as a sequence of segements. This 'shape', together with an appropriate 'body', is then added to the animation.

The demo uses a pymunk space (with the default collision handler) containing some static and dynamic objects, into which the glyph sprites are added sequentially from the queue.  Pixel-perfect or Bounding-box conditions can be selected and mixed, and various details can be chosen to display.
     Requires: Python 3.7. or later.   Qualified: MacOS10, Windows10, Ubuntu20
"""
import sys, os
import threading
import queue as Queue
import time
import platform
import math, random
import pygame as pg
from pygame.locals import *
from pymunk import BB, Vec2d
import numpy as np
import pymunk as pm
import pymunk.pygame_util
import pymunk.autogeometry

# Unless prefixed by 'tk', a widget is its ttk version.
import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter.ttk import *

backgrnd = pg.Color('#dcdcdc')          # Hex colors: https://xkcd.com/color/rgb/
beige = pg.Color('#ffe4c4')
white = pg.Color('#ffffff')
black = pg.Color('#000000')
red = pg.Color('#ff0000')
green = pg.Color('#00ff00')
fontcolor = pg.Color('#0a888a')
linecolor = pg.Color('#5a7d9a')

clock = pg.time.Clock()
system = platform.system()
sprite_group = pg.sprite.Group()              # Sprite container

# --------------------------------------------------------------------------------------
class Globs:
    """ Arguments container. https://pythonconquerstheuniverse.wordpress.com/2010/10/23/
    """
    q_graphic = (917, 338, 25, 30)            # Details for 'queue' (pg units).
    w_graphic = (960, 390, 140, 160)          # Details for 'work area' (pg units).
    
    # Initial dashboard function-key settings: 
    flag_list = [1, 0, 0, 1, 0]                # flag_list = [F1_key, ....... F5_key]
# ---------------------------------------------------------------------------------------

class Layout(Frame):
    """ Create pg- and tk-windows with their objects and graphics """
    def __init__(self, root):
        self.root = root
        
    # Main screen dimensions      
        self.screen_w = root.winfo_screenwidth()          
        self.screen_h = root.winfo_screenheight()

    # Centre a pg-window 1180 x 600 on the main screen.
        if self.screen_w >= 1366:
            self.pg_w, self.pg_h = 1180, 600 
        else:
            print("Limitation: Screen width must be at least 1366 pixels")
            root.destroy()
            sys.exit()
        self.pg_posn =  (int((self.screen_w-self.pg_w)/2),
              int((self.screen_h-self.pg_h)/2) )
        os.environ['SDL_VIDEO_WINDOW_POS']="%d,%d" % (self.pg_posn[0], self.pg_posn[1])
        
    # Create two tk-frames as drop-down panels: the right_panel ('Set Collision Type') 
    # and the left_panel ('Code Summary') are root and child. 
    # Since 'many strange side-effects' can occur when pygame is an embedded display 
    # (https://www.pygame.org/docs/ref/display.html), use a canvas widget in each 
    # frame to create the illusion of integration. Set the opacity of each frame at
    # 80% and (except for Linux case) remove the titlebar.
    # (stackoverflow.com/questions/55868430.)
        tab_h = 30    # tab's exposure
        panel_w, panel_h = 560,280
        
        # Right's position
        right_x = int((self.pg_w+self.screen_w)/2-panel_w)
        right_y=  int((self.screen_h-self.pg_h)/2-tab_h)
        root.overrideredirect(True)
        
        # Right's geometry
        root.geometry("%dx%d+%d+%d" % (panel_w, panel_h, right_x, right_y))
        if system == "Windows":
            root.wm_attributes("-alpha", 0.8)
        elif system == "Darwin":
            root.wm_attributes("-topmost", "true")
            root.wm_attributes("-alpha", 0.8)
            root.wm_attributes("-topmost", "true")
            root.lift()
        elif system == "Linux":
            root.wait_visibility(root)
            root.wm_attributes("-alpha", 0.8)
        root.configure(background="#c5c9c7")
        
        # Left's geometry       
        left_panel=Toplevel(self.root)
        left_panel.overrideredirect(True)
        left_panel.geometry("%dx%d+%d+%d" % (560,280,self.pg_posn[0],
            self.pg_posn[1]-29,))
        if system == "Windows":
            left_panel.wm_attributes("-alpha", 0.8)
        elif system == "Darwin":
            left_panel.wm_attributes("-topmost", "true")
            left_panel.wm_attributes("-alpha", 0.8)
            left_panel.lift()
        elif system == "Linux":
            left_panel.geometry("%dx%d+%d+%d" % (560,250,self.pg_posn[0],
                self.pg_posn[1]-34,))
                
        # We need the title-manager control in the Linux case, so no override there.                 
            left_panel.overrideredirect(False)
            left_panel.wait_visibility(left_panel)
            left_panel.wm_attributes("-alpha", 0.8)
            left_panel.title(" Code Summary ")
        left_panel.configure(background="#c5c9c7")
# ---------------------------------------------

        # Define the pg-Display 'DS'.
        pg.init()
        self.DS=pg.display.set_mode((self.pg_w, self.pg_h),
             HWSURFACE|DOUBLEBUF|NOFRAME)
        self.DS.fill(backgrnd)
        pg.display.flip()
        
        # A serif font as the keyboard glyph shows better the pixel-perfect finesse.
        global letter_font
        try:
            letter_font = pg.font.SysFont('liberationserif', 125)
        except:
            letter_font = pg.font.Font(None,125)
            
        # Glyphs from keyboard are used as examples of arbitrary shapes.
        # We limit the choice to letters and numbers.  
        self.lett_list = range(pg.K_a, pg.K_z+1)
        self.numb_list = range(pg.K_0, pg.K_9+1)
        self.nono_list = [33,64,35,36,37,94,38,42,40,41,28,29]
        
        # Two-part glyphs that require special attention:
        self.dot_list = [pg.K_i, pg.K_j]
        
        # Certain function-keys are also used.
        self.funk_list = range(pg.K_F1, pg.K_F6)
                   
        # Set panels' graphics.
        my_widgets(root, left_panel)
        
        # Pymunk stuff
        self.space = pm.Space()
        pm.pygame_util.positive_y_is_up = False
        self.space.gravity = Vec2d(0.0, 900.0)
# ---------------------------------------------

        # Add static lines to pymunk space  (pg coords unless otherwise stated).
        self.static_lines = [                          
            pm.Segment(self.space.static_body, (560.0, 365.0), (1000.0, 200.0), 4.0),
            pm.Segment(self.space.static_body, (1000.0, 200.0), (1100.0, 90.0), 4.0),
            pm.Segment(self.space.static_body, (1100.0, 90.0), (1100.0, 20.0), 4.0),
            pm.Segment(self.space.static_body, (0.0, 345.0), (75.0, 365.0), 4.0),
            pm.Segment(self.space.static_body, (75.0, 365.0), (82.0, 360.0), 4.0)
            ]
        for index, line in enumerate(self.static_lines):
            line.elasticity = 0.1
            line.friction = 0.1
        self.space.add(self.static_lines)
# ---------------------------------------------

        # Add dynamic lines to pm-space as a pivoted, constrained seesaw. 
        rotation_center_body = pm.Body(body_type = pm.Body.STATIC)
        rotation_center_body.position = (350,460)
        
        # Constrain motion
        rotation_limit_body = pm.Body(body_type = pm.Body.STATIC)
        rotation_limit_body.position = (200,460)
        
        # Arbitrary mass and inertia are selected for a plausible animation.   
        body = pymunk.Body(5, 10000000)         
        body.position = (350,460)
            
        # In local coords
        self.dynamic_lines = [ pm.Segment(body, (-150, 0), (400.0, 0.0), 4.0),                        
                          pm.Segment(body, (-150.0, 0), (-160.0, -30.0), 4.0),
             ]
        for index, line in enumerate(self.dynamic_lines):
            line.elasticity = 0
            line.friction = 0.8
        rotation_center_joint = pymunk.PinJoint(body, rotation_center_body,
            (0,0), (0,0))
        joint_limit = 50  
        rotation_limit_joint = pymunk.SlideJoint(body, rotation_limit_body,
            (-150,0), (0,0), 0, joint_limit)
        self.space.add(self.dynamic_lines, rotation_center_joint, 
            rotation_limit_joint, body)
# ---------------------------------------------

        # Set a white workspace where 'march_soft' is applied to the rendered glyph.
        pg.draw.rect(self.DS, white, (Globs().w_graphic), 0)
        work_area_text(self.DS)
        
        # Define a FIFO queue of 20 places. Only the top 8 are shown.
        self.queue = Queue.Queue(20)
         
        # Start the worker thread.
        t = Worker(args=(self.queue, self.DS, self.space))
        t.start()
        self.game_loop()
# ---------------------------------------------

    def game_loop(self):
        """ A standard pg-loop. https://www.youtube.com/watch?v=VO8rTszcW4s """
        
        # 'ij_flag' signals when glyph is in 'dot_list'
        ij_flag = False                        
        while True:
            # Limit max frame rate
            dt = clock.tick(60)/1000 
            
            # Watch for pg-events                  
            handle_pg_event(self.DS, self.space, self.numb_list, self.lett_list,
             self.nono_list, self.dot_list, self.funk_list, ij_flag, self.queue)
             
            # Update the physics
            self.space.step(1/60)                      
            Render().framework(self.DS)
            
            # Update the sprites
            sprite_group.update(dt)
            
            # Update tk.Tk()                    
            root.update()                              
            draw(self.DS, self.space, self.static_lines, self.dynamic_lines)
            pg.display.flip()
# ---------------------------------------------------------------------------------------

class Assemble(pg.sprite.Sprite):
    """ Make a sprite (pm-shape + pm-body) from the segments of the glyph's
        profile. Add both shape and body to the pymunk space  """
    def __init__(self, segments, glyph_surf, pos, space, DS, bbox):
        super().__init__()                    

        # 'sprite.Group' use requires 'image' & 'rect' objects to be defined here.
        self.image = glyph_surf
        self.rect = self.image.get_rect(topleft = pos)

        self.bbox=bbox
        self.segs = segments
        self.space = space
        
        # Allow for two-part glyphs from 'dot_list'
        self.shape = [[] for i in range(2)]  
        width = self.rect.width
        height = self.rect.height
        
        # Keep an original copy of 'image' to use in transforms that are destructive.
        self.orig_image = self.image
        
        # Centroid of bounding box (bbox)
        cent = self.rect.center
        
        # Define a dynamic body for the glyph.
        self.body = pm.Body(body_type=pm.Body.DYNAMIC)
        
        # Shift the the glyph's image to a new position for animation.
        shift = (random.randint(1,900), 350)  
        self.body.position = (pos[0]-shift[0], pos[1]-shift[1])

        # Do same to the segments of the image's profile.
        for n in range(2):
        # segments[n] lists segments (p1---p2) that form the glyph's outer profile.
            for i, val in enumerate(segments[n]):  
                p1 = val.a                         
                p2 = val.b                         
                p1[0] = int(p1[0]-cent[0])         
                p2[0] = int(p2[0]-cent[0])
                p1[1] = int(p1[1]-cent[1])
                p2[1] = int(p2[1]-cent[1])

        # Create a pm-shape from the accumulated segments 'segs'. Do not use the
        # pm.Poly(body, end_points) method because of its implicit convex hull.
                self.shape[n].append(pm.Segment(self.body,(p1[0],p1[1]),
                     (p2[0],p2[1]),1))
                     
        # Add animation attributes to the shape.
            self.angle = 0       # OPTION: random.uniform(0, 2.0*math.pi)
            for s in self.shape[n]:
                s.mass = 1
                s.elasticity=0.01
                s.friction=0.1
                s.body.angle = self.angle
                
        # Add body and shape to the pm-Space.            
        self.space.add(self.body, tuple(self.shape[0]), tuple(self.shape[1]))
# ---------------------------------------------

    def update(self, dt):
        wx,wy = Globs().w_graphic[0], Globs().w_graphic[1]
        pos_now = (self.body.position)
        
        # Set a maximum velocity for sprites to minimise tunneling
        max_velocity = 1000
        vel_length = self.body.velocity.length
        if vel_length > max_velocity:
            scale = max_velocity/vel_length
            self.body.velocity = self.body.velocity * scale
        self.image = pg.transform.rotate(
            self.orig_image, math.degrees(-self.body.angle))
        self.rect = self.image.get_rect(center=np.int_(pos_now))
        
        # Remove sprites that have left the screen or would enter the workspace
        if pos_now[0]<5 or pos_now[1]>600 or (pos_now[0]>(wx-140) 
            and pos_now[1]>(wy-140)):
            self.space.remove(self.body, self.shape)
            self.kill()
            
        # 'spacebar' to remove all sprites from pm-space
    def clear_all(self):
        self.space.remove(self.body, self.shape)
        
        # 'alt/opt' to dislodge sprites trapped by tunneling.
    def disturb_event(self):
        self.body.angular_velocity = 10*[-1,1][random.randrange(2)] 
        
        # 'impulse' needs an arbitrary non-zero mass for the body.        
        self.body.mass = 1                            
        self.body.apply_impulse_at_local_point(Vec2d(0, 700))
# ---------------------------------------------------------------------------------------

class Worker(threading.Thread):
    """ Monitor the queue. Get its top item, turn it into a sprite and add it to
        sprite_group  """
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        super().__init__()
        self.queue = args[0]
        self.DS = args[1]
        self.space = args[2]
        
    def run(self):
        while True:
        
        # 'item' is a tuple: (unicode, ij_flag). 'None' is sentinel for shutdown.
            item = self.queue.get()       
            if item[0] is None:
                break 
                                  
        # Send 'item' to Render() for progressive profile segmentation and display.
            (size, position, segments, glyph_surf, bbox) = Render.pg_setup(self, self.DS,
             self.queue, item)
             
        # Make a sprite from the segments and add it to sprite_group.
            ans = Assemble(segments, glyph_surf, position, self.space, self.DS, bbox)
            sprite_group.add(ans)
            Render().when_done(self.DS, size, position, self.queue)
# ---------------------------------------------------------------------------------------

class Render:
    """Set up a pg-surface. Render the glyph onto it and get a segmented profile. """ 
    def __init__(self):
    
        # Status of the most recent (formerly enqueued) task.    
        done = []
                           
        # Dashboard graphics  
    def pg_setup(self, DS, queue, item):
        F1_key, F2_key, F3_key, F4_key, F5_key = Globs().flag_list
        wx,wy,ww,wh = Globs().w_graphic
        pg.display.flip()
        queue_clear(queue, DS)
        queue_display(queue, DS)
        
        # Render glyph onto 'glyph_surf'.
        glyph_surf = letter_font.render(item[0], True, fontcolor)
        size = pg.Surface.get_size(glyph_surf)
        
        # This is top-left corner of glyph-surf 
        position = (int(wx+ww/2-size[0]/2), int(wy+10))
        
        # Blit glyph_surf onto the white workspace in DS.
        self.DS.blit(glyph_surf, position)
        
        # Decide what is to be shown in the workspace.    
        # (1) In bounding-box case, show the glyph briefly before 'get_profile' is called.   
        if F1_key==0:   
            time.sleep(0.5)
                            
        # Otherwise get the segments and bbox of the glyph's profile. 
        segments, bbox  = get_profile(DS, glyph_surf, position, size, item[1])
        
        # (2) In pix-perfect case, show the bbox briefly after the segmentation is done.
        if F1_key==1 and F4_key==1:
            pg.draw.rect(DS, black, (bbox.x, bbox.y, bbox.w, bbox.h), 1)
            time.sleep(0.5)     

        # Decide what is to be included in the pm-animation space.        
        # (3) For the pix-perfect case, include bbox with the glyph's sprite.
        
        if  F2_key==1:
        # Match top-left corners of bbox and glyph_surf rectangles 
            pg.draw.rect(glyph_surf, red, (bbox.x-position[0], bbox.y-position[1],
              bbox.w, bbox.h), 1)
            pg.display.flip()
            
         # (4) For the bounding-box case, Repeat the above except treat the bbox (filled
         # with fontcolor) as the glyph. The segmented profile of this rectangle then
         # becomes the pm-shape used in Assemble(). In this case the sprites are shown
         # as white, and can be mixed in the animation with the pix-perfect type.
        if F1_key==0:
            pg.draw.rect(DS, fontcolor, (bbox.x, bbox.y, bbox.w, bbox.h), 0)
            pg.display.flip()
            segments, bbox  = get_profile(DS, glyph_surf, position, size, item[1])
            glyph_surf = letter_font.render(item[0], True, white)
            
         # Include bbox with the animated glyph
            if F5_key==1: 
                pg.draw.rect(glyph_surf, red, (bbox.x-position[0]+1, bbox.y-position[1],
                  bbox.w, bbox.h), 1)
                pg.display.flip()  
        return (size, position, segments, glyph_surf, bbox)
# ---------------------------------------------        

    def framework(self, DS):
        """ Graphics for the workspace """
        qx,qy,qh,xd = Globs().q_graphic
        wx,wy,ww,wh = Globs().w_graphic
        pg.draw.rect(DS, black, (wx-68, wy-90, 266, 275), 1)
        
        # For the dashed lines
        dashx=qx+170             
        for i in range(6):
            pg.draw.rect(DS, black, (qx + xd * i, qy, 30, 25), 1)
            if i < 4:
                dashx += 12
                p1 = dashx, qy
                p2 = dashx+6, qy
                pg.draw.line(DS, black, p1, p2,1)
                p1 = dashx, qy+qh-1
                p2 = dashx+6, qy+qh-1
                pg.draw.line(DS, black, p1, p2,1)
# ---------------------------------------------
                
    def when_done(self, DS, size, position, queue):
        """Notify when no tasks remain in the queue """
        # 'task_done' returns None when done     
        done = (queue.task_done())                     
        time.sleep(.5)
        pg.draw.rect(DS, white, (Globs().w_graphic), 0)
        pg.display.flip()
        queue_display(queue, DS)
# ---------------------------------------------------------------------------------------

def queue_clear(queue, DS):
    """ Erase queue entries """
    qx, qy, qh, xd = Globs().q_graphic
    for i in range(8):
        pg.draw.rect(DS, backgrnd, (qx+xd*i, qy, 30, 25), 0)
        Render().framework(DS)
        
def queue_display(queue, DS):
    """ Dynamic queue graphics """
    qx, qy, qh, xd = Globs().q_graphic
    
    # Recall that item is a tuple: (unicode, ij_flag)
    for index, item in enumerate(list(queue.queue)):  
        if index <= 7:
            pg.draw.rect(DS, beige , (qx + xd * index, qy, 30, 25), 0)
            pg.draw.rect(DS, black, (qx + xd * index, qy, 30, 25), 1)
            font = pg.font.Font(None, 28)
            letter = font.render(item[0], True, black)
            DS.blit(letter, (qx+7+xd*index, qy+3))
            pg.display.flip()
# ---------------------------------------------

def get_profile(DS, glyph_surf, pos, size, ij_flag):
    """  Apply 'march_soft' to 'glyph_surf' and get a segmented (outer) profile of its
         contents. Also, get the bounding box and, optionally, display the segments as 
         they are calculated.
    """
    F1_key, F4_key = Globs().flag_list[0], Globs().flag_list[3]
    x = pos[0]
    y = pos[1]
    width=size[0]
    height=size[1]
    
    # Lists of segments by parts.
    segments =[[] for i in range (2)]
    
    # Lists of x,y coords of the segments' end points.           
    pts_x=[]
    pts_y=[]                                     
    line_set = pm.autogeometry.PolylineSet()

    def segment_func(v0, v1):
        line_set.collect_segment(v0, v1)

    def sample_func(point):
    
    # Check that p is inside surface. 
    # Use the 'lightness' criterion to delineate the glyph.
        try:
            p = int(point.x), int(point.y)      
            color = DS.get_at(p)
            return color.hsla[2]                
        except:
            print('Exception in get_profile. Weak hsla criterion?')
            shutdown()
            
    # Range over an area slightly larger than glyph_surf to include the occasional 
    # pixel outlier from the glyph's extremities.
    pm.autogeometry.march_soft(BB(x-5, y-5, x+width+10, y+height+10),
         100, 100, 50, segment_func, sample_func)
    count = 0
    for polyline in line_set:
        line = pm.autogeometry.simplify_curves(polyline, 1.)
        
    # Create a dynamic body having zero mass and inertia. The mass is arbitrarily
    # defined when the sprite's shape is created in Assemble(). The moment of inertia  
    # is then available after the shape and body are added to the pm-space.      
        for i in range(len(line)-1):
            p1 = line[i]
            p2 = line[i+1]
            
    # Option: Show the progress of profiling.
            if F1_key == 1 and F4_key == 1:
    # Set the display rate.
                time.sleep(.1)                      
                pg.draw.line(DS, red, np.int_(p1), np.int_(p2), 2)
                pg.display.flip()
                
    # Build the lists of segments and end points.                
            seg = pm.Segment(None, (int(p1[0]),int(p1[1])),
                  (int(p2[0]),int(p2[1])), 1)
            pts_x.append((int(p1[0])))
            pts_y.append((int(p1[1])))
            segments[count].append(seg)
        count += 1
        if not ij_flag:
            break
                 
    # 'break' allows only one cycle of 'get_profile' and so prevents the profiling 
    # of closed interiors in glyphs like D, p, O, etc. The no-break alternative 
    # allows the two cycles needed to profile two-part glyphs like those of i and j.
     
    # Get the bounding box as a pg-rectangle
    bbox= pg.Rect(min(pts_x), min(pts_y), max(pts_x)-min(pts_x), max(pts_y)-min(pts_y))
    return segments, bbox
# ---------------------------------------------------------------------------------------

def my_widgets(root, child):
    """ Set details of the tk Frames and Canvas widgets"""
    global canv1, canv2
    
    # Set up the widgets. Use grid management for the benefit of its themes.
    frame = ttk.Frame(root)
    frame.grid()   
    s = Style()
    s.theme_use('classic')
    s.configure("B.TLabel", background="#c5c9c7")
    
    # Details of root/child frames
    lab1=Label(root, text="Set Collision Type:  toggle F1  ",
       style="B.TButton")
    lab1.grid(column=0, columnspan=1, row=0, padx=168)
    if system == "Windows" or system == "Darwin": 
        lab2=Label(child, text="  Code Summary  ", style="B.TButton")
        lab2.grid(column=0, columnspan=1, row=0, padx=214)
        
    # Create a canvas widget to cover each tk window except the 'tab' area.  
    canv1=Canvas(root, bg = "#ffffff", height = 253, width = 560, bd=0,
                highlightthickness=0)
    canv1.grid(column=0, columnspan=1, row=1)
    canv2=Canvas(child, bg = "#ffffff", height = 253, width = 560, bd=0,
                highlightthickness=0)
    canv2.grid(column=0, columnspan=1, row=1)
    
    # Set up the function-key events. In Windows and Linux we monitor the tk-loop
    # for these events. In Darwin we monitor the pg-loop via 'handle_pg_event()'. 
    # Function-key events from both sources are handled by 'func_key(event)'.  
    if system == "Windows":   
        canv1.bind("<FocusOut>", lose_focus)   
        canv1.bind("<Button-1>", func_key)
        canv1.bind("<FocusIn>", get_focus)
        list=("<F1>","<F2>","<F3>","<F4>","<F5>")     
        [canv1.bind(i, func_key) for i in list]
        canv1.focus_set()
    if system == "Linux":
        child.bind("<FocusOut>", get_focus)
        child.bind("<FocusIn>", luse_focus)
        child.bind("<Button-1>")
        
    # Display the opening versions of the panels.
    r_h_panel(0)
    l_h_panel()
# ---------------------------------------------

def get_focus(event):
    event.widget.configure(background="#ffffff")   
    canv1.create_rectangle(300,90,540,140, width=0, fill = "#c5c9c7")
    canv1.create_text(420,110, text = "To select:  toggle keyboard F-keys")
# ---------------------------------------------

def luse_focus(event):
    event.widget.configure(background="#ffffff")
    canv1.create_rectangle(300,90,540,140, width=0, fill = "#00ff00")
    canv1.create_text(420,110, text = "Click screen to use F-keys")
# ---------------------------------------------

def lose_focus(event):
    canv1.focus_set()
    event.widget.configure(background="#ffffff")
    canv1.create_rectangle(300,90,540,140, width=0, fill = "#00ff00")
    canv1.create_text(420,110, text = "Click here to use keyboard F-keys")
# ---------------------------------------------

def work_area_text(DS):
    """ Work area graphics """
    qx, qy, qh, xd = Globs().q_graphic 
    font0 = pg.font.Font(None, 28)
    text0 = font0.render("{0:>13}  queue".format(' '), True, black)
    DS.blit(text0, (qx+15, qy-28))
    
    # Arrows 
    pg.draw.polygon(DS, black, [[qx+38,321],[qx+50,316],[qx+50,324]],0)
    pg.draw.polygon(DS, black, [[qx+38,470],[qx+24,474],[qx+24,466]],0)
    pg.draw.line(DS, black, [qx+50,320], [qx+81,320], 3)
    pg.draw.line(DS, black, [qx+15,368], [qx+15,470], 3)
    pg.draw.line(DS, black, [qx+15,470], [qx+35,470], 3)
# ---------------------------------------------

def shutdown():
    """ All done """
    pg.quit()
    root.destroy()
    sys.exit()
# ----------------------------------------------

def r_h_panel(m):
    """ Right-hand panel"""
    if m == 0:
        canv1.create_rectangle(10,5,550,155, width=1, fill = "#c5c9c7")
        canv1.create_line(280,5,280,155, width=1)
        canv1.create_rectangle(20,15,260,40, width=1, fill = "#ffc0cb")
        canv1.create_rectangle(300,15,540,40, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(20,50,216,75, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(20,85,216,110, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(20,120,216,145, width=1, fill = "#ffc0cb")
        canv1.create_rectangle(220,50,260,75, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(220,85,260,110, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(220,120,260,145, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(300,50,496,75, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(500,50,540,75, width=1, fill = "#c5c9c7")
        canv1.create_text(140,28, text = "Pixel Perfect")
        canv1.create_text(420,28, text = "Bounding Box")
        canv1.create_text(121,63, text = "Include bbox with sprite")
        canv1.create_text(121,98, text = "Show profile only")
        canv1.create_text(121,133, text = "Show profile's construction")
        canv1.create_text(398,63, text = "Include bbox with sprite")
        canv1.create_text(280,173, text = "'esc' to QUIT.    (Effective \
only after queue is empty and tasks are done.)")
        canv1.create_text(280,193, text= "'alt/opt' to dislodge trapped sprites.\
    'spacebar' to clear existing sprites.")
        canv1.create_text(280,225, text= "Click main screen to input glyph from keyboard.")
        canv1.create_text(240,63, text = "F2")
        canv1.create_text(240,98, text = "F3")
        canv1.create_text(240,133, text = "F4")
        canv1.create_text(520,63, text = "F5") 
        if system == "Darwin" or system == 'Linux':
            canv1.create_text(420,110, text = "To select: toggle keyboard F-keys")
    elif m==1:
        canv1.create_rectangle(20,15,260,40, width=1, fill = "#ffc0cb")
        canv1.create_rectangle(300,15,540,40, width=1, fill = "#c5c9c7")
        canv1.create_text(140,28, text = "Pixel Perfect")
        canv1.create_text(420,28, text = "Bounding Box")
    elif m==2:
        canv1.create_rectangle(20,15,260,40, width=1, fill = "#c5c9c7")
        canv1.create_rectangle(300,15,540,40, width=1, fill = "#ffc0cb")    
        canv1.create_text(140,28, text = "Pixel Perfect")
        canv1.create_text(420,28, text = "Bounding Box")
    elif m==3:
        canv1.create_rectangle(20,50,216,75, width=1, fill = "#ffc0cb")
        canv1.create_text(121,63, text = "Include bbox with sprite")
    elif m==4:
        canv1.create_rectangle(20,50,216,75, width=1, fill = "#c5c9c7")
        canv1.create_text(121,63, text = "Include bbox with sprite")
    elif m==5:
        canv1.create_rectangle(20,85,216,110, width=1, fill = "#ffc0cb")
        canv1.create_text(121,98, text = "Show profile only")
    elif m==6:
        canv1.create_rectangle(20,85,216,110, width=1, fill = "#c5c9c7")
        canv1.create_text(121,98, text = "Show profile only")
    elif m==7:
        canv1.create_rectangle(20,120,216,145, width=1, fill = "#ffc0cb")
        canv1.create_text(121,133, text = "Show profile's construction")
    elif m==8:
        canv1.create_rectangle(20,120,216,145, width=1, fill = "#c5c9c7")
        canv1.create_text(121,133, text = "Show profile's construction")
    elif m==9:
        canv1.create_rectangle(300,50,496,75, width=1, fill = "#ffc0cb")
        canv1.create_text(398,63, text = "Include bbox with sprite")
    elif m==10:
        canv1.create_rectangle(300,50,496,75, width=1, fill = "#c5c9c7")
        canv1.create_text(398,63, text = "Include bbox with sprite") 
# ---------------------------------------------       
        
def l_h_panel():
    """ Left-hand panel"""
    fsize=10
    inset=50
    text_y =235
    if system == "Darwin":
        fsize=13
        inset=30
    canv2.create_rectangle(3,5,552,50, width=1, fill = "#ffc0cb")
    canv2.create_text(278,17, text = "REAL-TIME PROFILING OF ARBITRARY SHAPES\
 FOR PIXEL-PERFECT ANIMATION IN PYGAME", font=('TkDefaultFont',fsize-1))    
    canv2.create_text(280,37, text = "With acknowledgement to R.\
 Marxer   http://www.ricardmarxer.com/fisica/examples/Letters/applet/Letters.pde",\
  font=('TkDefaultFont',fsize-3))
    if system == "Linux":
       inset=10
       text_y=242
    canv2.create_text(inset,text_y,
     text=("We show how to add an arbitrary shape to a pixel-perfect pygame animation\n"
      "in progress.  We use the glyphs of letters or numbers as arbitrary shapes.\n"
      "Their characters, entered from the keyboard, are stored in a fifo queue that is\n"
      "monitored from a worker thread.  The leading element in the queue is sent to a\n"
      "workspace where an exterior profile of its glyph is derived as a sequence of\n"
      "segements.  This 'shape', together with an appropriate 'body', is then\
 added to the\n"
      "animation as a sprite.\n"
      "This demo shows a pymunk space (using the default collision handler) containing\n"
      "some simple static and dynamic objects, into which the glyph sprites are added.\n"
      "Pixel-perfect or Bounding-box conditions can be selected, and mixed, and various\n"
      "details can be chosen for display."),
      font=('TkDefaultFont',fsize), anchor=SW)
# ---------------------------------------------    
    
def func_key(event):
    """ Handle function-key event"""
    F1_key, F2_key, F3_key, F4_key, F5_key = Globs().flag_list
    
    # Allow for the different styles of the incoming event per platform.
    if isinstance(event, tk.Event):
        event = event.keysym
    if event == "f1" or event == "F1":
        F1_key = not F1_key
        if F1_key:
            r_h_panel(1)
        else:
            r_h_panel(2)
    if F1_key:
        r_h_panel(10)
        F5_key=0 
        if event == "f2" or event == "F2":
            F3_key=0
            r_h_panel(6)
            F2_key = not F2_key
            if F2_key:
                r_h_panel(3)
            else:
                r_h_panel(4)
        elif event == "f3" or event == "F3":
            F5_key, F2_key = 0,0 
            r_h_panel(4)
            F3_key = not F3_key
            if F3_key:
                r_h_panel(5)
            else:
                r_h_panel(6)
        elif event == "f4" or event == "F4":
            F4_key = not F4_key
            if F4_key:
                r_h_panel(7)
            else:
                r_h_panel(8)
    else:
        [r_h_panel(i) for i in (4,6,8)]
        F2_key, F3_key, F4_key = 0,0,0
        if event == "f5" or event == "F5":
            F5_key = not F5_key
            if F5_key:
                r_h_panel(9)
            else:
                r_h_panel(10)
                
    # Update the flag_list
    _=[F1_key, F2_key, F3_key, F4_key, F5_key]
    for i, elem in enumerate(_):
        Globs().flag_list[i] = _[i] 
# ---------------------------------------------   

def handle_pg_event(DS, space, numb_list, lett_list, nono_list,
     dot_list, funk_list, ij_flag, queue):
    """ Handle keyboard events """
    for event in pg.event.get():
        if event.type == KEYDOWN and event.key == K_ESCAPE:
            if queue.empty():
    # The last queued task is done; queue is empty, it's safe to close worker thread....
                queue.put((None, None))
                time.sleep(.001)                    # A local quirk? Win10 only??
    #....and shut down the rest.
                root.destroy()
                pg.quit()
                sys.exit()
                break
    # Disable Ctrl key 
        elif  (pg.key.get_mods() & pg.KMOD_LCTRL) or (pg.key.get_mods() & pg.KMOD_RCTRL):
            break
    # A function key event
        elif  event.type == KEYDOWN and event.key in funk_list:
            func_key(pg.key.name(event.key))
    # spacebar removes all sprites
        elif  event.type == KEYDOWN and event.key == pg.K_SPACE:
            for sprite in sprite_group:
                sprite_group.remove(sprite)        
                sprite.clear_all()
    # alt/opt creates sprite bedlam                  
        elif  pg.key.get_mods() & pg.KMOD_ALT:
            for sprite in sprite_group:
                sprite.disturb_event()
        if not queue.full():
            if event.type == KEYDOWN and event.key in numb_list:
                if (ord(event.unicode) in nono_list):
                    break
                else:
                    queue.put((event.unicode, ij_flag))
                    queue_display(queue, DS)
            if event.type == KEYDOWN and event.key in lett_list:
                if (ord(event.unicode) in dot_list):
                    ij_flag = True
    # Add acceptable character to the queue 
                queue.put((event.unicode, ij_flag))
                queue_display(queue, DS)
# --------------------------------------------- 

def clear_callback(surf,rect):
    """ sprite_group.clear """
    color = backgrnd
    
    # Enlarge the area cleared to catch occasional debris left in the sprite's wake.
    rect = rect.inflate(2,2)      
    surf.fill(color, rect)
# --------------------------------------------- 

def draw(DS, space, static_lines, dynamic_lines):
    """ Options for drawing on DS """
    F3_key = Globs().flag_list[2]
    
    # Clear area on DS swept by the seesaw
    wx, wy = Globs().w_graphic[0], Globs().w_graphic[1]
    pg.draw.rect(DS, backgrnd, ((0,290), (910, 310)), 0)
    pg.draw.rect(DS, black, (wx-68, wy-90, 266, 275), 1)
    
    # Clear only sprite-areas that have been updated
    if not F3_key:
        sprite_group.clear(DS,clear_callback)
    else:    
        pg.draw.rect(DS, backgrnd, ((0,0), (1100, 290)), 0)
        
    # Show the pivot
    pg.draw.circle(DS,(0,0,0), (350,460), 7, 1)
    
    # This for purists: Don't use debug.draw. 
    for line in static_lines:
        aint=int(line.a.x),int(line.a.y)
        bint=int(line.b.x),int(line.b.y)
        pg.draw.line(DS, linecolor, aint, bint, 6)
    for line in dynamic_lines:
        body = line.body
        pv1 = body.position + line.a.rotated(body.angle) 
        pv2 = body.position + line.b.rotated(body.angle)
        p1 = int(pv1.x),int(pv1.y) 
        p2 = int(pv2.x),int(pv2.y) 
        pg.draw.line(DS, linecolor, p1, p2, 5)
        
    # Draw all the sprites contained in sprite_group.
    if not F3_key: sprite_group.draw(DS)    
# --------------------------------------------- 
    """
# Use debug.draw
    draw_options = pymunk.pygame_util.DrawOptions(DS)
    space.debug_draw(draw_options) 
# OPTION: Don't show constraints  (stackoverflow.com/questions/53023396)
#        draw_options.flags ^= draw_options.DRAW_CONSTRAINTS    
# Color match lines
    for line in static_lines:
        pg.draw.line(DS, pg.Color('#0485d1'), line.a, line.b, 5)
# Draw all contained in sprite_group.
    sprite_group.draw(DS)
    """
# --------------------------------------------- 
    
    if F3_key == 1: 
    
    # Include the calculated profile as a red outline on the animated glyph.
    # 'verts' is a list of the segments' end-points. 
        for obj in sprite_group:
            verts=[]
    # Allow for two-part glyphs
            for n in range(2):
                shape = obj.shape[n]
                
    # shape's elements are segments and so have 4 attributes: (body, a, b, radius)
                for i in range(len(shape)):
                    seg_ends = (shape[i].a, shape[i].b)
                    verts += seg_ends
                    
    # 'verts' become 'pts' after rotation/translation of the shape's body.
                pts = [v.rotated(obj.body.angle) + obj.body.position 
                    for v in verts]
                    
    # Slice 'pts' into lists of beginning- and end-points .... 
                pts = [((pt.int_tuple)) for pt in pts]
                begs = pts[0::2]
                ends = pts[1::2]
    # ... and draw the segments separately.
                for i in range(len(begs)):
                    pg.draw.line(DS, red, begs[i], ends[i], 2)
        pg.display.flip()
# ---------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    Layout(root).game_loop()
    root.mainloop()
