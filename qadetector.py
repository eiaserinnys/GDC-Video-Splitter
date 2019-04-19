# import the necessary packages
from threading import Thread
import sys
import cv2
import math
import detect
import rectclipper
 
# import the Queue class from Python 3
if sys.version_info >= (3, 0):
  from queue import Queue
 
# otherwise, import the Queue class for Python 2.7
else:
  from Queue import Queue

class QADetector:
  def __init__(self, path):
    self.fps = 1
    self.totalFrames = 1

    self.qaBegin = None

    # initialize the file video stream along with the boolean
    # used to indicate if the thread should be stopped or not
    self.stream = cv2.VideoCapture(path)

    if self.stream.isOpened():
      self.totalFrames = self.stream.get(cv2.CAP_PROP_FRAME_COUNT)

      self.fps = round(self.stream.get(cv2.CAP_PROP_FPS))
      print('"Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}'.format(self.fps))
      
    self.started = False
    self.stopped = False
    self.finished = False

  def start(self, rect, thres1, thres2):

    if not self.started:
      self.started = True

      # start a thread to read frames from the file video stream
      t = Thread(target=self.update, args=(rect, thres1, thres2))
      t.daemon = True
      t.start()

    return self

  def update(self, rect, thres1, thres2):

    framePointer = self.totalFrames - 1

    # keep looping backward
    # if the thread indicator variable is set, stop the thread
    sleepCount = 0
    while framePointer > 0 and not self.stopped and not self.finished:

      self.stream.set(cv2.CAP_PROP_POS_FRAMES, framePointer)

      (grabbed, frame) = self.stream.read()

      if not grabbed:
        self.finished = True
        return

      # 먼저 외곽선 검출 후 딜레이션한다
      (canny, dilatedCanny) = detect.cannyAndDilate(frame, thres1, thres2, 3)

      # 기존에 검출된 영역이 있다, 해당 영역과 겹치는지 확인한다
      if detect.detectRectangleByPixelCount(dilatedCanny, rect, 3, rectclipper.SecondTimeCoverage):
        self.qaBegin = int(framePointer + self.fps)
        self.finished = True

      framePointer -= self.fps

      sleepCount += 1

      # cpu를 너무 잡아먹지 않도록
      if sleepCount > 10:
        time.sleep(0)

  def stop(self):
    # indicate that the thread should be stopped
    self.stopped = True

  def isOpened(self):
    return self.stream.isOpened()

  def isStarted(self):
    return self.started
