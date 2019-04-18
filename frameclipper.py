import copy
import os
import cv2
import numpy as np
import videostream
import detect
import scenewriter
import rectclipper

################################################################################
class FrameClipper:

  #------------------------------------------------------------------------------
  def __init__(self, pathname, outfolder, framePos=0):

    completed = False

    # 출력 폴더를 자른다
    self.outputPath = os.path.join(outfolder, os.path.splitext(os.path.basename(pathname))[0])
    self.debug = False

    # 완료 마커가 있는지 체크
    try:
      open(os.path.join(self.outputPath, "completed"), "r")
      completed = True
    except:
      pass

    # 시작 프레임 위치가 설정되어 있으면 디버그 모드
    if framePos > 0:
      self.outputPath = 'debug'
      self.debug = True

    if not completed:
      # 완료 마커가 없으면 재생 시작
      self.fvs = videostream.FileVideoStream(pathname, framePos).start()

      if self.fvs.isOpened():
        print('output to {}'.format(self.outputPath))
        self.extent = self.fvs.getExtent()
        self.rectDetector = rectclipper.RectDetector()
        self.sceneWriter = scenewriter.SceneWriter(self.outputPath, self.fvs.getFPS())
      else:
        print("Error opening video stream or file")

    else:
      print('already processed - {}'.format(pathname))
      self.fvs = None

    self.play = True

    self.lastFrameNum = 0
    self.lastFrame = None

    self.currentFrameNum = 0
    self.currentFrame = None
    self.buffer = []

    self.waitForBufferEmptied = False

    self.clipped = None
    self.detected = None

  #------------------------------------------------------------------------------
  def close(self):
    if self.fvs is not None:

      if self.fvs.finished:
        if scenewriter.writeFiles:
          # 완료 마커를 기록한다
          try:
            f = open(os.path.join(self.outputPath, "completed"), "w+")
            f.write('completed')
            close(f)
          except:
            pass

      self.fvs.stop()
      self.fvs = None

    if self.sceneWriter is not None:
      self.sceneWriter.close()
      self.sceneWriter = None

  #------------------------------------------------------------------------------
  def isOpened(self):
    if self.fvs is not None:
      return self.fvs.isOpened()
    return False

  #------------------------------------------------------------------------------
  def isPlaying(self):
    return self.play

  #------------------------------------------------------------------------------
  def getTotalFrames(self):
    if self.fvs is not None:
      return self.fvs.totalFrames
    return 0

  #------------------------------------------------------------------------------
  def setPlaying(self, value):
    self.play = value
    print('play flag changed - {}'.format(value))

  #------------------------------------------------------------------------------
  def getCurrentFrame(self):
      return self.currentFrame

  #------------------------------------------------------------------------------
  def more(self):
    if len(self.buffer) > 0:
      return True
    return self.fvs.more()

  #------------------------------------------------------------------------------
  def fillBuffer(self):
    buffered = len(self.buffer)
    toBuffer = 30 - buffered

    for i in range(0, toBuffer):
      if self.fvs.more():
        f = self.fvs.tryRead()
        if f is not None:
          self.buffer.append(f)
        else:
          break
      else:
        break

  #------------------------------------------------------------------------------
  def peekLastBuffered(self):
    bufferLen = len(self.buffer)
    if bufferLen > 0:
      return self.buffer[bufferLen-1]
    return None
  
  #------------------------------------------------------------------------------
  def getNextFrame(self):
    if len(self.buffer) > 0:
      f = self.buffer[0]
      self.buffer.pop(0)
      return f

    self.waitForBufferEmptied = False

    return self.fvs.read()

  #------------------------------------------------------------------------------
  def getCurrentFrameNum(self):
    return self.lastFrameNum

  #------------------------------------------------------------------------------
  def do(self, thres1, thres2, thres3, thres4, epsilon):

    if self.more() and self.isPlaying():
      # 다음 프레임을 받아온다
      (self.currentFrameNum, self.currentFrame) = self.getNextFrame()
      self.lastFrameNum = self.currentFrameNum
      self.lastFrame = self.currentFrame.copy()

      # 가장 큰 사각형을 감지해서 자른다
      (self.clipped, self.detected) = self.rectDetector.detectAndClip(self.currentFrame, thres1, thres2, epsilon)

      # 변경 감지를 해보자
      self.sceneWriter.checkAndWrite(self.currentFrameNum, self.currentFrame, self.clipped, thres3, thres4)

      # 프레임이 스테이블하면 앞으로 진행한다
      if self.sceneWriter.isStabilized() and not self.waitForBufferEmptied:
        self.peekForward(thres1, thres2, thres3, thres4, epsilon)

    else:
      # 기존 프레임을 사용한다
      self.currentFrameNum = self.lastFrameNum
      self.currentFrame = self.lastFrame.copy()

      # 디버깅 용도, 클리핑 영역 검출을 계속 시도한다
      # 가장 큰 사각형을 감지해서 자른다
      (self.clipped, self.detected) = self.rectDetector.detectAndClip(self.currentFrame, thres1, thres2, epsilon)

  #------------------------------------------------------------------------------
  def peekForward(self, thres1, thres2, thres3, thres4, epsilon):
    while True:
      # 안정화되었다, 프레임 패스트 포워딩을 시도한다
      # 먼저 버퍼를 충분히 채운다
      self.fillBuffer()

      # 버퍼의 마지막 프레임을 꺼내서
      lastFrame = self.peekLastBuffered()
      if lastFrame is not None:

        # 방금 자른 곳을 다시 잘라본다
        (peekClipped, peekDetected) = self.rectDetector.detectAndClip(lastFrame[1], thres1, thres2, epsilon)

        if peekClipped is not None:
          if self.sceneWriter.isStable(lastFrame[0], peekClipped, thres3, thres4):
            # 변경 감지에 아무 것도 걸리지 않으면 이 구간은 스킵한다
            self.buffer = []
          else:
            # 변경 감지에 뭔가 걸렸다, 미리 로드한 프레임을 소진할 때까지 스트림에서 읽지 않는다
            self.waitForBufferEmptied = True
            break
        else:
          break
      else:
        break

  #------------------------------------------------------------------------------
  def retryClip(self, thres1, thres2):
    self.clipped = self.rectDetector.detectAndClip(self.currentFrame, thres1, thres2)

  #------------------------------------------------------------------------------
  def getDetected(self):
    return self.detected

  #------------------------------------------------------------------------------
  def detectedAtLeastOnce(self):
    return self.rectDetector.clipRectDetectedOnce