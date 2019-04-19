import copy
import cv2
import numpy as np

#--------------------------------------------------------------------------------
def getHoughThreshold(extent):
  shorter = extent[0]
  if extent[1] < shorter:
    shorter = extent[1]
  return (int) (shorter * 0.33)

#--------------------------------------------------------------------------------
def seperateLines(lines, w, h):
  vLines = []
  hLines = []

  if lines is not None:
    for i in range(len(lines)):
      for rho,theta in lines[i]:

        # 세로
        if theta <= np.pi/180 * 0.5 or 179.5 * np.pi/180 <= theta:
          vLines.append(int(rho))

        # 세로
        elif 89.5 * np.pi/180 <= theta and theta <= 91.5 * np.pi/180:
          hLines.append(int(rho))

    if len(vLines) > 0:
      vLines.append(w)

    if len(hLines)> 0:
      hLines.append(h)

    vLines.sort()
    hLines.sort()

  return vLines, hLines

#--------------------------------------------------------------------------------
def getHorizontalCoverage(image, x1, x2, y, threshold):
  (h, w) = image.shape[:2]
  y1 = max([0, y-threshold])
  y2 = min([y+threshold, h])

  subImage = image[y1:y2, x1:x2]
  resized = cv2.resize(subImage, (x2 - x1, 1), interpolation=cv2.INTER_AREA)
  count = cv2.countNonZero(resized)

  if x2 - x1 > 5:
    # 75% 0이 아니면 선으로 간주
    return (count / (x2 - x1)) > 0.5
  else:
    # 판정 구간이 5픽셀 미만이면 0만 아니면 선으로 간주
    return count > 0

#--------------------------------------------------------------------------------
def getVerticalCoverage(image, x, y1, y2, threshold):
  (h, w) = image.shape[:2]
  x1 = max([0, x-threshold])
  x2 = min([x+threshold, w])

  subImage = image[y1:y2, x1:x2]
  resized = cv2.resize(subImage, (1, y2 - y1), interpolation=cv2.INTER_AREA)
  count = cv2.countNonZero(resized)

  if y2 - y1 > 5:
    # 75% 0이 아니면 선으로 간주
    return (count / (y2 - y1)) > 0.5
  else:
    # 판정 구간이 5픽셀 미만이면 0만 아니면 선으로 간주
    return count > 0

#--------------------------------------------------------------------------------
def getHorizontalSegments(canny, hLines, vLines, minLength, lineThreshold):
  hSegments = []

  for i in range(len(hLines)):
    y = hLines[i]
  
    # 모든 세로 선과 교차 테스트한다
    lastX = 0
    ongoing = False
    segmentBegin = 0

    for j in range(len(vLines)):
      x = vLines[j]

      # 가로 커버리지를 구한다
      covered = getHorizontalCoverage(canny, lastX, x, y, lineThreshold)

      # 선으로 판정되면
      if covered:
        if not ongoing:
          ongoing = True
          segmentBegin = lastX
      else:
        if ongoing:
          if lastX - segmentBegin >= minLength:
            hSegments.append((segmentBegin, lastX, y))
          ongoing = False

      lastX = x
    
    if ongoing:
      if lastX - segmentBegin >= minLength:
        hSegments.append((segmentBegin, lastX, y))
  
  return hSegments

#--------------------------------------------------------------------------------
def getVerticalSegments(canny, hLines, vLines, minLength, lineThreshold):
  vSegments = []

  for i in range(len(vLines)):
    x = vLines[i]
  
    # 모든 가로 선과 교차 테스트한다
    lastY = 0
    ongoing = False
    segmentBegin = 0

    for j in range(len(hLines)):
      y = hLines[j]

      # 가로 커버리지를 구한다
      covered = getVerticalCoverage(canny, x, lastY, y, lineThreshold)

      # 선으로 판정되면
      if covered:
        if not ongoing:
          ongoing = True
          segmentBegin = lastY
      else:
        if ongoing:
          if lastY - segmentBegin >= minLength:
            vSegments.append((x, segmentBegin, lastY))
          ongoing = False

      lastY = y
    
    if ongoing:
      if lastY - segmentBegin >= minLength:
        vSegments.append((x, segmentBegin, lastY))
  
  return vSegments

#--------------------------------------------------------------------------------
def detectRectangle(hSegments, vSegments):

  rects = []
  maxRect = None
  maxArea = 0

  for h1 in range(len(hSegments)):
    for h2 in range(len(hSegments)):
      if h1 != h2:
        (x11, x12, y1) = hSegments[h1]
        (x21, x22, y2) = hSegments[h2]

        if x11 == x21 and x12 == x22:
          for v1 in range(len(vSegments)):
            for v2 in range(len(vSegments)):
              if v1 != v2:
                (x3, y31, y32) = vSegments[v1]
                (x4, y41, y42) = vSegments[v2]

                if y31 == y41 and y32 == y42:
                  if (x3 == x11 and x4 == x12) or (x3 == x12 and x4 == x11):
                    rects.append((x11, y1, x12, y2))

                    area = (x12 - x11) * (y2 - y1)
                    if area > maxArea:
                      maxArea = area
                      maxRect = (x11, y1, x12, y2)

  return maxRect, rects

#--------------------------------------------------------------------------------
def checkLastClipRect(maxRect, lastClipRect):

  if maxRect is not None:
    (x1, y1, x2, y2) = maxRect

    # 가급적 지난 클립 영역과 일치시킨다
    if lastClipRect is not None:
      (lx1, ly1, lx2, ly2) = lastClipRect

      dist = 0
      dist += abs(lastClipRect[0] - maxRect[0])
      dist += abs(lastClipRect[1] - maxRect[1])
      dist += abs(lastClipRect[2] - maxRect[2])
      dist += abs(lastClipRect[3] - maxRect[3])

      if dist < 20:
        maxRect = copy.deepcopy(lastClipRect)
      else:
        #print('new rect({},{},{},{}) detected'.format(x1,y1,x2,y2))
        
        #maxRect = copy.deepcopy(lastClipRect)

        # 기존 클립 영역과 너무 다르면 없는 셈 친다
        maxRect = None

    else:
      #print('initial rect({},{},{},{}) detected'.format(x1,y1,x2,y2))
      pass

  return maxRect

#--------------------------------------------------------------------------------
def isContourRectangle(approx):

  l = len(approx)

  for i in range(l):
    (x1, y1) = approx[i][0][0], approx[i][0][1]
    (x2, y2) = approx[(i+1)%l][0][0], approx[(i+1)%l][0][1]
    angle = np.arctan2(y2 - y1, x2 - x1)

    if -1 * np.pi / 180 < angle and angle < 1 * np.pi / 180:
      pass
    elif 89 * np.pi / 180 < angle and angle < 91 * np.pi / 180:
      pass
    elif -89 * np.pi / 180 > angle and angle > -91 * np.pi / 180:
      pass
    elif angle > 179 * np.pi / 180:
      pass
    elif angle < -179 * np.pi / 180:
      pass
    else:
      return False

  return True

#--------------------------------------------------------------------------------
def detectRectangleByPixelCount(dilatedCanny, rect, threshold):
  (x1, y1, x2, y2) = rect

  top = getHorizontalCoverage(dilatedCanny, x1, x2, y1, threshold)
  bottom = getHorizontalCoverage(dilatedCanny, x1, x2, y2, threshold)

  left = getVerticalCoverage(dilatedCanny, x1, y1, y2, threshold)
  right = getVerticalCoverage(dilatedCanny, x2, y1, y2, threshold)

  count = 0

  if top:
    count += 1
  if bottom:
    count += 1
  if left:
    count += 1
  if right:
    count += 1
  
  return count >= 3

#--------------------------------------------------------------------------------
def detectMaximumRectangle(dilatedCanny, epsilon):

  (h, w) = dilatedCanny.shape[:2]

  maxArea = 0
  maxRect = None

  nontrivContours = []
  approxContours = []

  # 칸토어를 찾는다
  contours, hierarchy = cv2.findContours(dilatedCanny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

  for i in range(len(contours)):

      cnt = contours[i]
      box = cv2.boundingRect(cnt)

      # 화면 면적의 40%가 넘는 큰 칸토어에 대해서만 처리한다
      if box[2] * box[3] > (w * h * 0.4):

        area = box[2] * box[3]

        approx = cv2.approxPolyDP(cnt, epsilon * cv2.arcLength(cnt, True), True)

        nontrivContours.append(cnt)
        approxContours.append(approx)

        if detectRectangleByPixelCount(dilatedCanny, (box[0], box[1], box[0] + box[2], box[1] + box[3]), 5):
          if area > maxArea:
            box = cv2.boundingRect(approx)
            maxRect = (box[0], box[1], box[0] + box[2], box[1] + box[3])
            maxArea = area

        else:
          pass

  return maxRect, nontrivContours, approxContours

#--------------------------------------------------------------------------------
def cannyAndDilate(frame, thres1, thres2, dilate):

  # 미디언 블러
  #median = cv2.medianBlur(frame, 5)

  # Canny 에지 디텍션
  canny = cv2.Canny(frame, thres1, thres2, apertureSize = 3)

  # 캐니 에지를 딜레이션으로 이어 붙인다
  dilatedCanny = cv2.dilate(canny, np.ones((dilate,dilate), np.uint8))

  return (canny, dilatedCanny)

#--------------------------------------------------------------------------------
def debugRender(hLines, vLines, hSegments, vSegments):
  # 가로 선 디버그 렌더
  for i in range(len(hLines)):
    y = hLines[i]
    cv2.line(frame,(0,y),(w,y),grayColor,1)

  for i in range(len(hSegments)):
    (x1, x2, y) = hSegments[i]
    cv2.line(frame,(x1,y),(x2,y),(128, 128, 128),2)

  # 세로 선 디버그 렌더
  for i in range(len(vLines)):
    x = vLines[i]
    cv2.line(frame,(x,0),(x,h),grayColor,1)

  for i in range(len(vSegments)):
    (x, y1, y2) = vSegments[i]
    cv2.line(frame,(x,y1),(x,y2),(128, 128, 128),2)
