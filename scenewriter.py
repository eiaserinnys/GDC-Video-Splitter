import os
import errno
import cv2
import imageio
import gifwriter

writeFiles = True
showDebug = False

################################################################################
class FrameError:
  def __init__(self, isError, mfe, mme, msd, before, next, diff, diffcanny, featureErrors, meanErrors, stdDevs, wr, hr):
    self.isError = isError
    self.maxFeatureError = mfe
    self.maxMeanError = mme
    self.maxStdDev = msd
    self.before = before
    self.next = next
    # self.oldDil = oldDil
    # self.newDil = newDil
    # self.xored = xored
    self.diff = diff
    self.diffcanny = diffcanny
    self.featureErrors = featureErrors
    self.meanErrors = meanErrors
    self.stdDevs = stdDevs
    self.wr = wr
    self.hr = hr

################################################################################
featureErrorThreshold = 100 #0.4
meanErrorThreshold = 0.05

def calcualteFrameError(before, next, thres3, thres4):
  kernel = (3, 3)

  # oldCanny = cv2.Canny(before, thres3, thres4, apertureSize = 3)
  # oldDil = cv2.dilate(oldCanny, np.ones(kernel, np.uint8))

  # newCanny = cv2.Canny(next, thres3, thres4, apertureSize = 3)
  # newDil = cv2.dilate(newCanny, np.ones(kernel, np.uint8))

  # xored = cv2.bitwise_xor(oldDil, newDil)

  diff = cv2.absdiff(before, next)
  diffcanny = cv2.Canny(diff, thres3, thres4, apertureSize = 3)

  (h, w) = diffcanny.shape[:2]

  # 잘라서 체크한다
  cut = 4
  hd = h / cut
  wd = w / cut

  wr = []
  hr = []

  for i in range(0, cut):
    wr.append((int)(i * wd))
    hr.append((int)(i * hd))

  wr.append(w)
  hr.append(h)

  maxError = 0
  maxDiffMean = 0
  maxStdDev = 0

  featureErrors = []
  meanErrors = []
  stdDevs = []

  # 자른 영역을 순회하면서 최대 에러를 카운트한다
  for i in range(len(hr) - 1):
    for j in range(len(wr) - 1):
      
      # 차이에 의한 에러
      (x1, y1, x2, y2) = (wr[j], hr[i], wr[j+1], hr[i+1])
      # oldSub = oldDil[y1:y2, x1:x2]
      # xorSub = xored[y1:y2, x1:x2]

      # keyNonZero = cv2.countNonZero(oldSub) + 1
      # xorNonZero = cv2.countNonZero(xorSub) + 1

      # error = xorNonZero / keyNonZero
      
      diffsub = diffcanny[y1:y2, x1:x2]
      error = cv2.countNonZero(diffsub)

      featureErrors.append(error)

      if error > maxError:
        maxError = error

      # 명도에 의한 에러
      lg = cv2.cvtColor(before[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
      ng = cv2.cvtColor(next[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
      lm = lg.mean() + 128

      m, s = cv2.meanStdDev(ng)

      nm = m + 128

      if lm > 0:
        diffMean = abs(nm / lm - 1)
      else:
        diffMean = nm / 255

      meanErrors.append(diffMean)

      if maxDiffMean < diffMean:
        maxDiffMean = diffMean

      if maxStdDev < s:
        maxStdDev = s

      stdDevs.append(s)

  isError = maxError > featureErrorThreshold or maxDiffMean > meanErrorThreshold

  return FrameError(isError, maxError, maxDiffMean, maxStdDev, before, next, diff, diffcanny, featureErrors, meanErrors, stdDevs, wr, hr)

################################################################################
class SceneWriter:

  #------------------------------------------------------------------------------
  def __init__(self, outputPath, fps):
    self.outputPath = outputPath
    self.fps = fps
    self.inTransition = True
    self.stableCount = 0
    self.snapshotTaken = False
    self.unstableCount = 0
    self.unstableMemento = 15
    self.lastStableFrame = None
    self.writtenFrame = 0
    self.gifWriter = None
    self.mp4Writer = None
    self.previousFrames = []
    self.previousUncutFrames = []
    self.writingUncut = False
    self.frameError = None
    self.createFolder(outputPath)

  #------------------------------------------------------------------------------
  def close(self):
    self.endGifWriter()
    self.endMp4Writer()

  #------------------------------------------------------------------------------
  def endGifWriter(self):
    if self.gifWriter is not None:
      self.gifWriter.stop()
      self.gifWriter = None

  #------------------------------------------------------------------------------
  def endMp4Writer(self):
    if self.mp4Writer is not None:
      self.mp4Writer.stop()
      self.mp4Writer = None

  #------------------------------------------------------------------------------
  def createFolder(self, outputPath):
    try:
      os.mkdir(outputPath)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            print ("Creation of the directory %s failed" % outputPath)
            raise
        else:
          print ("the directory %s already exists" % outputPath)
        pass      
    else:  
        print ("Successfully created the directory %s " % outputPath)

  #------------------------------------------------------------------------------
  def isStableInternal(self, frameNum, clipped, thres3, thres4, store):
    frameError = calcualteFrameError(self.lastStableFrame, clipped, thres3, thres4)

    if store:
      self.frameError = frameError

    if frameError.isError and not self.inTransition:
        if showDebug:
          print('{} - large error detected = {}, {}'.format(frameNum, frameError.maxFeatureError, frameError.maxMeanError))

    return not frameError.isError

  #------------------------------------------------------------------------------
  def isStable(self, frameNum, clipped, thres3, thres4):

    if self.lastStableFrame is not None and clipped is not None:
        return self.isStableInternal(frameNum, clipped, thres3, thres4, False)

    # 베이스 프레임이 없으면 어쨌든 안정화되지 않음
    return False

  #------------------------------------------------------------------------------
  def checkAndWrite(self, frameNum, frame, clipped, thres3, thres4):

    if self.lastStableFrame is not None:

      if clipped is not None:

        if not self.isStableInternal(frameNum, clipped, thres3, thres4, True):
          self.processTransitionFrame(frameNum, clipped)

        elif self.inTransition:
          self.processStableFrame(frameNum, clipped)
      
      self.processUncutFrame(frameNum, frame, clipped)

    self.preserveFrame(clipped)

  #------------------------------------------------------------------------------
  def isStabilized(self):
      return not self.inTransition

  #------------------------------------------------------------------------------
  def appendGifFrame(self, frame):
    if writeFiles and self.gifWriter is not None:
      self.gifWriter.append(frame)

  #------------------------------------------------------------------------------
  def appendMp4Frame(self, frame):
    if writeFiles and self.mp4Writer is not None:
      self.mp4Writer.append(frame)

  #------------------------------------------------------------------------------
  def processTransitionFrame(self, frameNum, clipped):

    self.unstableCount += 1

    if self.unstableCount >= self.unstableMemento:

      # 처음 트랜지션에 진입하면
      if not self.inTransition:
        self.inTransition = True

        # gif를 쓰기 시작한다
        self.writtenFrame += 1
        # fileName = '{no:04d}t-{f:06d}.gif'.format(no=self.writtenFrame, f=int(frameNum))
        # self.gifWriter = gifwriter.GifWriter(self.outputPath + '\\' + fileName, self.fps, 0.5)
        fileName = '{no:04d}t-{f:06d}.mp4'.format(no=self.writtenFrame, f=int(frameNum))
        self.gifWriter = gifwriter.GifWriter(self.outputPath + '\\' + fileName, self.fps, 1)

        # 트랜지션에 진입하기 전 프레임도 gif에 먼저 추가한다
        if writeFiles:
          for f in self.previousFrames:
            self.appendGifFrame(f)

      # 안정화 구간을 리셋
      self.stableCount = 0
      self.snapshotTaken = False

      # 기준 프레임을 변경한다
      self.lastStableFrame = clipped.copy()

      # 프레임을 gif에 추가한다
      self.appendGifFrame(clipped)

  #------------------------------------------------------------------------------
  def processStableFrame(self, frameNum, clipped):
    # 안정화 시간을  증가한다
    self.stableCount += 1

    # 트랜지션 중이면 프레임을 추가한다
    self.appendGifFrame(clipped)

    if self.stableCount > self.fps * 1.5:

      # 일정 시간 이상 정지하면 트랜지션 종료로 간주한다
      if showDebug:
        print('{} - transition stablized'.format(frameNum))

      # 안정화되었다
      self.inTransition = False
      self.unstableCount = 0

      # gif 기록을 마친다
      self.endGifWriter()

    if self.stableCount > self.fps * 2 / 3 and not self.snapshotTaken:

      self.snapshotTaken = True

      # 트랜지션 완료 프레임을 덤프
      if self.frameError.maxStdDev > 5:

        self.writtenFrame += 1
        fileName = '{no:04d}f-{f:06d}.jpg'.format(no=self.writtenFrame,f=int(frameNum))
        (ch, cw) = clipped.shape[:2]

        if showDebug:
          print('Writing {} ({}x{})...'.format(fileName, cw, ch))

        if writeFiles:
          cv2.imwrite(self.outputPath + '\\' + fileName, clipped)

      else:
        if showDebug:
          print('clipped frame skipped due to low std dev ({},{},{})'.format(d[0], d[1], d[2]))

      # 기준 프레임을 변경한다
      self.lastStableFrame = clipped.copy()

  #------------------------------------------------------------------------------
  def processUncutFrame(self, frameNum, frame, clipped):

    if clipped is not None:

      if self.writingUncut:
        if showDebug:
          print('frame recovered')
        self.endMp4Writer()
        self.writingUncut = False
        self.previousUncutFrames = []

    else:

      if self.writingUncut:

        self.appendMp4Frame(frame)

      else:

        if len(self.previousUncutFrames) == 0:
          if showDebug:
            print('frame lost')

        self.previousUncutFrames.append(frame)

        if len(self.previousUncutFrames) > 5:
          self.writingUncut = True

          # mp4를 쓰기 시작한다
          self.writtenFrame += 1
          fileName = '{no:04d}t-{f:06d}.mp4'.format(no=self.writtenFrame, f=int(frameNum))
          self.mp4Writer = gifwriter.GifWriter(self.outputPath + '\\' + fileName, self.fps, 1)
     
          # 포커스를 잃은 시점부터 기록에 들어간다
          if writeFiles:
            for f in self.previousUncutFrames:
              self.appendMp4Frame(f)

          self.previousUncutFrames = []

  #------------------------------------------------------------------------------
  def preserveFrame(self, clipped):
    if clipped is not None:
      #cv2.imshow('Clipped',clipped)

      if self.lastStableFrame is None:
        self.lastStableFrame = clipped.copy()

      # 트랜지션 gif 앞에 추가할 프레임을 보존한다
      self.previousFrames.append(clipped.copy())

      while len(self.previousFrames) > self.unstableMemento:
        self.previousFrames.pop(0)
