import time
import copy
import os
import cv2
import glob
import numpy as np
import imageio
import videostream
import gifwriter
import detect
import frameclipper
import scenewriter

showMainScene = False

# 파일 기록 여부
scenewriter.writeFiles = True

debugRectDetection = False
debugFrameError = False
stopOnError = True               # 에러 발생 시 재생 정지
startFramePos = 0                # 0

font = cv2.FONT_HERSHEY_SIMPLEX

#--------------------------------------------------------------------------------
def nothing(x):
  pass

################################################################################
def createUI():
  # 에지 디텍션 필터
  cv2.namedWindow('UI', cv2.WINDOW_AUTOSIZE);
  cv2.createTrackbar('Threshold1', 'UI', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold1', 'UI', 150)
  cv2.createTrackbar('Threshold2', 'UI', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold2', 'UI', 100)

  # 프레임 변화 추적용
  cv2.createTrackbar('Threshold3', 'UI', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold3', 'UI', 200)
  cv2.createTrackbar('Threshold4', 'UI', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold4', 'UI', 100)

  # contour
  cv2.createTrackbar('Epsilon', 'UI', 0, 100, nothing)
  cv2.setTrackbarPos('Epsilon', 'UI', 5)

################################################################################
# rectCannyShown = False

def showRectDetection(clipper):
  debugFrame = clipper.getCurrentFrame().copy()

  detected = clipper.getDetected()

  if detected is not None:

    if detected.maxRect is not None:
      (x1, y1, x2, y2) = detected.maxRect
      cv2.rectangle(debugFrame, (x1,y1), (x2, y2), (0, 0, 255), 3)
    else:
      if detected.contours is not None:
        cv2.drawContours(debugFrame, detected.contours, -1, (0, 255, 0, 1), 1)
      if detected.approxContours is not None:
        cv2.drawContours(debugFrame, detected.approxContours, -1, (0, 255, 255, 1), 2)

      if clipper.detectedAtLeastOnce():
        print('{} : no rectangle'.format(clipper.currentFrameNum))
        #clipper.setPlaying(False)
        # rectCannyShown = True

    cv2.imshow('canny', detected.dilatedCanny)

  cv2.imshow('Frame',debugFrame)

################################################################################
# rectCannyShown = False

def showFrameError(clipper, thres3, thres4):
  debugFrame = clipper.getCurrentFrame().copy()

  e = clipper.sceneWriter.frameError

  if clipper.isPlaying():
    if e is not None and e.isError: #e.maxFeatureError > scenewriter.featureErrorThreshold:
      clipper.setPlaying(False)
  else:
    if e is not None and e.before is not None and e.next is not None:
      e = scenewriter.calcualteFrameError(e.before, e.next, thres3, thres4)

  if e is not None:

    debugTarget = cv2.cvtColor(e.diffcanny,cv2.COLOR_GRAY2BGR)
    (h, w) = debugTarget.shape[:2]

    for i in range(1, len(e.wr)):
      cv2.line(debugTarget, (e.wr[i], 0), (e.wr[i], h), (128, 128, 128), 1)

    for i in range(1, len(e.hr)):
      cv2.line(debugTarget, (0, e.hr[i]), (w, e.hr[i]), (128, 128, 128), 1)

    c = 0
    for i in range(len(e.hr) - 1):
      for j in range(len(e.wr) - 1):

        (x1, y1, x2, y2) = (e.wr[j], e.hr[i], e.wr[j+1], e.hr[i+1])

        feText = '{fe:0.3f}'.format(fe=e.featureErrors[c])
        meText = '{me:0.3f}'.format(me=e.meanErrors[c])

        feSize = cv2.getTextSize(feText, font, 0.75, 1)
        meSize = cv2.getTextSize(meText, font, 0.75, 1)

        # 텍스트 위치 계산, 베이스라인을 기준으로 렌더링되므로 높이는 전체를 내려줘야 한다
        x = int((x2+x1)/2 - max(feSize[0][0], meSize[0][0])/2)
        yf = int((y2+y1)/2 - (feSize[0][1] + meSize[0][1]) / 2 + feSize[0][1])
        ym = int((y2+y1)/2 - (feSize[0][1] + meSize[0][1]) / 2 + feSize[0][1] + meSize[0][1])

        if e.featureErrors[c] > scenewriter.featureErrorThreshold:
          fc = (0,0,255)
        else:
          fc = (255,255,255)

        if e.meanErrors[c] > scenewriter.meanErrorThreshold:
          mc = (0,0,255)
        else:
          mc = (255,255,255)

        cv2.putText(debugTarget,feText,(x,yf), font, 0.75, fc, 1, cv2.LINE_AA)
        cv2.putText(debugTarget,meText,(x,ym), font, 0.75, mc, 1, cv2.LINE_AA)

        c+=1

    cv2.imshow('old', e.before)
    cv2.imshow('new', e.next)
    # cv2.imshow('oldc', e.oldDil)
    # cv2.imshow('newc', e.newDil)
    cv2.imshow('xor', e.diff)
    cv2.imshow('canny', debugTarget)

    # new test
    # diff = cv2.absdiff(e.before, e.next)
    # diffcanny = cv2.Canny(diff, thres3, thres4, apertureSize = 3)
    # cv2.imshow('xorcolor', e.diffcanny)

  cv2.imshow('Frame',debugFrame)

################################################################################
def main():

  createUI()

  # Create a VideoCapture object and read from input file
  # If the input is the camera, pass 0 instead of the video file name
  #path = 'S:\\_Reference\\Conference\\GDC2018\\video_high\\1024795.mp4'
  #path = 'S:\\DSquare\\[참고자료]\\오픈월드\\1025765 - Procedurally Crafting Manhattan for \'Marvel\'s Spider-Man\'.mp4'
  
  list = []

  folder = 'S:\\DSquare\\[참고자료]\\오픈월드'
  for file in os.listdir(folder):
      if file.endswith(".mp4"):
          pathName = os.path.join(folder, file)
          print(pathName)
          list.append(pathName)

  for path in list:
    
    # 클리퍼를 생성한다
    clipper = frameclipper.FrameClipper(path, startFramePos)

    # 비디오가 열렸나 확인
    if not clipper.isOpened():
      continue

    # 비디오를 읽는다
    breaked = False
    while clipper.more():

      time_1 = time.time()

      thres1 = cv2.getTrackbarPos('Threshold1', 'UI')
      thres2 = cv2.getTrackbarPos('Threshold2', 'UI')
      thres3 = cv2.getTrackbarPos('Threshold3', 'UI')
      thres4 = cv2.getTrackbarPos('Threshold4', 'UI')
      epsilon = cv2.getTrackbarPos('Epsilon', 'UI') /100

      clipper.do(thres1, thres2, thres3, thres4, epsilon)

      time_2 = time.time()

      # Display the resulting frame
      if debugRectDetection:
        showRectDetection(clipper)
      elif debugFrameError:
        showFrameError(clipper, thres3, thres4)
      else:
        if showMainScene:
          cv2.imshow('Frame', clipper.getCurrentFrame())
        pass

      # Press Q on keyboard to  exit
      key = cv2.waitKey(1)

      # # esc 누르면 종료
      if key & 0xFF == 27:
        breaked = True
        break

      if key & 0xff == ord(' '):
          clipper.setPlaying(not clipper.isPlaying())
      
      if key & 0xff == ord('t'):
        print('time=', (int)((time_2 - time_1) * 1000))

    clipper.close()

    if breaked:
      break

  # Closes all the frames
  cv2.destroyAllWindows()

  while gifwriter.getActiveThreads() > 0:
    print('wait to writing {} gifs...'.format(gifwriter.getActiveThreads()))
    time.sleep(1)

################################################################################
if __name__ == "__main__":
  main()