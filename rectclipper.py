import copy
import cv2
import numpy as np
import detect

################################################################################
class Detected:
  def __init__(self, canny, dilatedCanny, maxRect, contours, approx):
    self.canny = canny
    self.dilatedCanny = dilatedCanny
    self.maxRect = maxRect
    self.contours = contours
    self.approxContours = approx

SecondTimeCoverage = 0.5

################################################################################
def checkBorder(img):
  if img is not None:
    avgDiff, stdDev = cv2.meanStdDev(img)
    maxDev = max(stdDev[0], stdDev[1], stdDev[2])
    return maxDev < 15

  return True

################################################################################
class RectDetector:
  #------------------------------------------------------------------------------
  def __init__(self):
    self.maxRect = None

    self.clipRectDetectedOnce = False

    self.lastClipRect = None
    self.newClipRect = None
    self.contours = None
    self.approxContours = None

    # 디버그
    self.canny = None
    self.dilatedCanny = None
 
  #------------------------------------------------------------------------------
  def clip(self, frame, clipRect):
    # 감지된 영역이 있으면
    if clipRect is not None:
      (x1, y1, x2, y2) = clipRect
      return frame[y1:y2, x1:x2]
    else:
      return None

  #------------------------------------------------------------------------------
  def getLastDetectedRectangle(self):
    return self.lastClipRect

  #------------------------------------------------------------------------------
  def getDetectedContours(self):
    return self.contours, self.approxContours

  #------------------------------------------------------------------------------
  def detectAndClip(self, frame, thres1, thres2, epsilon):

    # 클립 영역을 검출하자
    clipRect = None

    if not self.clipRectDetectedOnce:
      (clipRect, detected) = self.detectFirstTime(frame, thres1, thres2, epsilon)
    else:
      (clipRect, detected) = self.detectSecondTime(frame, thres1, thres2)

    return self.clip(frame, clipRect), detected

  #------------------------------------------------------------------------------
  def clipSafeRegion(self, frame):

    (h, w) = frame.shape[:2]

    rf = 5
    rn = 2

    l, r, u, d = None, None, None, None

    lcr = self.lastClipRect

    if lcr[0] - rf >= 0:
      l = frame[lcr[1]:lcr[3], lcr[0]-rf:lcr[0]-rn]

    if lcr[1] - rf >= 0:
      u = frame[lcr[1]-rf:lcr[1]-rn, lcr[0]:lcr[2]]

    if lcr[2] + rf < w:
      r = frame[lcr[1]:lcr[3],lcr[2]+rn:lcr[2]+rf]

    if lcr[3] + rf < h:
      d = frame[lcr[3]+rn:lcr[3]+rf,lcr[0]:lcr[2]]

    return l,r,u,d

  #------------------------------------------------------------------------------
  def detectFirstTime(self, frame, thres1, thres2, epsilon):

    # 먼저 외곽선 검출 후 딜레이션한다
    (canny, dilatedCanny) = detect.cannyAndDilate(frame, thres1, thres2, 3)

    # 기존에 감지된 영역이 없는 경우, 새로 검출을 시도한다
    (maxRect, contours, approxContours) = detect.detectMaximumRectangle(dilatedCanny, epsilon)

    if maxRect is not None:

      # 검출에 성공, 이제 이 영역을 PT 영역으로 간주한다
      self.clipRectDetectedOnce = True
      self.lastClipRect = copy.deepcopy(maxRect)

      # 디버그 정보를 기록한다
      detected = Detected(canny, dilatedCanny, copy.deepcopy(self.lastClipRect), contours, approxContours)
    
    else:
      # 디버그 정보를 기록한다
      detected = Detected(canny, dilatedCanny, None, contours, approxContours)

    return (maxRect, detected)

  #------------------------------------------------------------------------------
  def detectSecondTime(self, frame, thres1, thres2):

    # 먼저 외곽선 검출 후 딜레이션한다
    (canny, dilatedCanny) = detect.cannyAndDilate(frame, thres1, thres2, 3)

    # TODO) 여기서 새 영역 검출을 시도해야 하는데 일단 스킵하고 전화면을 캡처한다
    detected = Detected(canny, dilatedCanny, None, None, None)
    clipRect = None

    # 기존에 검출된 영역이 있다, 해당 영역과 겹치는지 확인한다
    if detect.detectRectangleByPixelCount(dilatedCanny, self.lastClipRect, 3, SecondTimeCoverage):

      # 색상까지 검사해서 최종 확인한다
      l,r,u,d = self.clipSafeRegion(frame)

      ok = True
      ok = ok and checkBorder(l)
      ok = ok and checkBorder(r)
      ok = ok and checkBorder(u)
      ok = ok and checkBorder(d)

      # 해당 영역과 겹친다, 기존 클립 영역을 사용한다
      if ok:
        detected = Detected(canny, dilatedCanny, copy.deepcopy(self.lastClipRect), None, None)
        clipRect = copy.deepcopy(self.lastClipRect)
      else:
        pass

    return (clipRect, detected)

  #------------------------------------------------------------------------------
  def detectedAtLeastOnce(self):
    return self.clipRectDetectedOnce