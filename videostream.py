# import the necessary packages
from threading import Thread
import sys
import cv2
import time
 
# import the Queue class from Python 3
if sys.version_info >= (3, 0):
  from queue import Queue
 
# otherwise, import the Queue class for Python 2.7
else:
  from Queue import Queue

class FileVideoStream:
  def __init__(self, path, framePos=0, queueSize=256):
    self.fps = 1

    # initialize the file video stream along with the boolean
    # used to indicate if the thread should be stopped or not
    self.stream = cv2.VideoCapture(path)

    if self.stream.isOpened():
      if framePos > 0:
        self.stream.set(cv2.CAP_PROP_POS_FRAMES, framePos)

      self.fps = self.stream.get(cv2.CAP_PROP_FPS)
      print('"Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}'.format(self.fps))
      
    self.stopped = False
    self.finished = False
 
    # initialize the queue used to store frames read from
    # the video file
    self.Q = Queue(maxsize=queueSize)

  def getFPS(self):
    return self.fps

  def start(self):
    # start a thread to read frames from the file video stream
    t = Thread(target=self.update, args=())
    t.daemon = True
    t.start()
    return self

  def update(self):
    # keep looping infinitely
    while True:
      # if the thread indicator variable is set, stop the
      # thread
      if self.stopped or self.finished:
        return
 
      # otherwise, ensure the queue has room in it
      if not self.Q.full():
        # read the next frame from the file
        f = self.stream.get(cv2.CAP_PROP_POS_FRAMES)
        (grabbed, frame) = self.stream.read()
 
        # f = self.stream.get(cv2.CAP_PROP_POS_FRAMES)
        # self.stream.set(cv2.CAP_PROP_POS_FRAMES, f + 1)

        # if the `grabbed` boolean is `False`, then we have
        # reached the end of the video file
        if not grabbed:
          self.finished = True
          return
 
        # add the frame to the queue
        self.Q.put((f, frame))

      else:
          time.sleep(0)

    else:
        pass

  def read(self):
    # return next frame in the queue
    return self.Q.get()

  def tryRead(self):
    try:
      return self.Q.get_nowait()
    except:
      return None

  def more(self):
    # return True if there are still frames in the queue
    return (self.Q.qsize() > 0 or not self.finished) and not self.stopped

  def stop(self):
    # indicate that the thread should be stopped
    self.stopped = True

  def isOpened(self):
      return self.stream.isOpened()

  def getExtent(self):
      return (self.stream.get(cv2.CAP_PROP_FRAME_WIDTH), self.stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
