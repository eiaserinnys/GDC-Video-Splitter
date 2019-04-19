from threading import Thread
from threading import Lock
import cv2
import sys
import time
import os
import imageio

# import the Queue class from Python 3
if sys.version_info >= (3, 0):
  from queue import Queue
 
# otherwise, import the Queue class for Python 2.7
else:
  from Queue import Queue

################################################################################
class AtomicInteger():
  def __init__(self, value=0):
    self._value = value
    self._lock = Lock()

  def inc(self):
    with self._lock:
      self._value += 1
      return self._value

  def dec(self):
    with self._lock:
      self._value -= 1
      return self._value

  @property
  def value(self):
    with self._lock:
      return self._value

  @value.setter
  def value(self, v):
    with self._lock:
      self._value = v
      return self._value

threads = AtomicInteger()

################################################################################
def getActiveThreads():
  return threads.value

################################################################################
class GifWriter:

  #------------------------------------------------------------------------------
  def __init__(self, pathName, fps, scale):
    self.pathName = pathName
    self.fps = fps
    self.toWrite = []
    self.Q = None
    self.scale = scale
    self.stopped = False

    filename, file_extension = os.path.splitext(pathName)
    self.mp4 = file_extension == '.mp4'

  #------------------------------------------------------------------------------
  def convertImage(self, img):

    if self.scale != 1:
      img = cv2.resize(img, None, fx=self.scale, fy=self.scale)

    if self.mp4:
      # 패딩을 추가한다
      (h, w) = img.shape[:2]

      pw, ph = w, h

      blockSize = 16
      if w % blockSize != 0:
        pw = int(w / blockSize + 1)*blockSize
      if h % blockSize != 0:
        ph = int(h / blockSize + 1)*blockSize

      l = int((pw-w) / 2)
      r = (pw-w) - l

      t = int((ph-h) / 2)
      b = (ph-h) - t

      img = cv2.copyMakeBorder(img,t,b,l,r,cv2.BORDER_CONSTANT,value=0)

    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)    

  #------------------------------------------------------------------------------
  def append(self, img):
    if self.Q is None:
      self.toWrite.append(img)
      # 일정 길이 이상의 움직임이 있을 때만 애니메이션으로 간주 (슬라이드 전환을 배제하기 위해서)
      if len(self.toWrite) > self.fps * 3:

        # 동시에 3개만 진행한다
        while threads.value > 2:
          time.sleep(0.1)

        threads.inc()
        #print('writing {}...', self.pathName)
        self.Q = Queue()
        t = Thread(target=self.update, args=())
        t.daemon = True
        t.start()
    else:
      self.Q.put(img)
      
  #------------------------------------------------------------------------------
  def isActive(self):
    return self.Q is not None

  #------------------------------------------------------------------------------
  def stop(self):
    # indicate that the thread should be stopped
    self.stopped = True

  #------------------------------------------------------------------------------
  def update(self):

    gifWriter = imageio.get_writer(self.pathName, mode='I', fps=self.fps)

    for f in self.toWrite:
      gifWriter.append_data(self.convertImage(f))

    self.toWrite = None

    # keep looping infinitely
    while True:

      while not self.Q.empty():
        img = self.Q.get()
        gifWriter.append_data(self.convertImage(img))

      # if the thread indicator variable is set, stop the
      # thread
      if self.stopped:
        gifWriter.close()
        gifWriter = None
        threads.dec()
        return
 
      time.sleep(0)

