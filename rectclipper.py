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
  def detect(self, frame, thres1, thres2, epsilon):
    (h, w) = frame.shape[:2]

    # 미디언 블러
    median = cv2.medianBlur(frame, 5)

    # Canny 에지 디텍션
    canny = cv2.Canny(median, thres1, thres2, apertureSize = 3)

    # 캐니 에지를 딜레이션으로 이어 붙인다
    dilatedCanny = cv2.dilate(canny, np.ones((3,3), np.uint8))

    # 기존 검출 영역이 있으면 해당 영역을 먼저 테스트해본다
    if self.lastClipRect is not None:

      (x1, y1, x2, y2) = self.lastClipRect

      threshold = 3

      top = detect.getHorizontalCoverage(dilatedCanny, x1, x2, y1, threshold)
      bottom = detect.getHorizontalCoverage(dilatedCanny, x1, x2, y2, threshold)

      left = detect.getVerticalCoverage(dilatedCanny, x1, y1, y2, threshold)
      right = detect.getVerticalCoverage(dilatedCanny, x2, y1, y2, threshold)

      count = 0

      if top:
        count += 1
      if bottom:
        count += 1
      if left:
        count += 1
      if right:
        count += 1
      
      if count >= 3:
        return Detected(canny, dilatedCanny, copy.deepcopy(self.lastClipRect), None, None)

    # 영역 감지
    maxRect = None
    (maxRect, contours, approxContours) = detect.detectMaximumRectangle(dilatedCanny, w, h, epsilon)

    return Detected(canny, dilatedCanny, maxRect, contours, approxContours)

  #------------------------------------------------------------------------------
  def getValidClipRect(self, clipRect):

    rectToReturn = None

    # 감지된 영역이 있으면
    if clipRect is not None:

      # 이전 검출 영역과 비슷한 지 확인한다
      clipRect = detect.checkLastClipRect(clipRect, self.lastClipRect)

      # 감지된 영역을 사용한다
      rectToReturn = clipRect

      # 한 번도 감지된 적이 없으면 보존한다
      if not self.clipRectDetectedOnce:
        self.clipRectDetectedOnce = True
        self.lastClipRect = copy.deepcopy(clipRect)
        
    # 감지된 영역이 없지만 한 번이라도 감지된 적이 있으면 마지막 영역을 사용한다
    # elif self.clipRectDetectedOnce:
    #   rectToReturn = self.lastClipRect

    return rectToReturn
  
  #------------------------------------------------------------------------------
  def clip(self, frame, clipRect):
    # 감지된 영역이 있으면
    if clipRect is not None:
      (x1, y1, x2, y2) = clipRect
      return frame[y1:y2, x1:x2]
    else:
      return None

  #------------------------------------------------------------------------------
  def getDetectedRectangle(self):
    return self.maxRect

  #------------------------------------------------------------------------------
  def getDetectedContours(self):
    return self.contours, self.approxContours

  #------------------------------------------------------------------------------
  def detectAndClip(self, frame, thres1, thres2, epsilon):

    # 새로 검출한다
    detected = self.detect(frame, thres1, thres2, epsilon)

    # 검출된 영역을 기록과 비교해서 안정화한다
    clipRect = self.getValidClipRect(detected.maxRect)

    return self.clip(frame, clipRect), detected

  #------------------------------------------------------------------------------
  def detectedAtLeastOnce(self):
    return self.clipRectDetectedOnce