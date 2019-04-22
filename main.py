import time
import copy
import os
import cv2
import numpy as np
import imageio
import videostream
import gifwriter
import detect
import frameclipper
import scenewriter
import sys
import argparse
from tqdm import tqdm

# 파일 기록 여부
scenewriter.writeFiles = True

stopOnError = True               # 에러 발생 시 재생 정지
startFramePos = 0                # 0

font = cv2.FONT_HERSHEY_SIMPLEX

#--------------------------------------------------------------------------------
def nothing(x):
  pass

################################################################################
def createUI():
  # 에지 디텍션 필터
  cv2.namedWindow('Frame', )

  cv2.createTrackbar('Threshold1', 'Frame', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold1', 'Frame', 20)  #150)
  cv2.createTrackbar('Threshold2', 'Frame', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold2', 'Frame', 15)  #100)

  # 프레임 변화 추적용
  cv2.createTrackbar('Threshold3', 'Frame', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold3', 'Frame', 200)
  cv2.createTrackbar('Threshold4', 'Frame', 0, 500, nothing)
  cv2.setTrackbarPos('Threshold4', 'Frame', 100)

  # contour
  cv2.createTrackbar('Epsilon', 'Frame', 0, 100, nothing)
  cv2.setTrackbarPos('Epsilon', 'Frame', 5)

  # debug
  cv2.createTrackbar('Show Rect', 'Frame', 0, 1, nothing)
  cv2.setTrackbarPos('Show Rect', 'Frame', 1)

################################################################################
# rectCannyShown = False

def showRectDetection(clipper):
  debugFrame = clipper.getCurrentFrame().copy()

  if clipper.detectedAtLeastOnce():
    if clipper.isPlaying():
      clipper.setPlaying(False)
    #clipper.rectDetector.clipRectDetectedOnce = False

  detected = clipper.getDetected()

  if detected is not None:

    debugCanny = cv2.cvtColor(detected.dilatedCanny, cv2.COLOR_GRAY2BGR)

    if detected.maxRect is not None:
      (x1, y1, x2, y2) = detected.maxRect
      dist = 5
      cv2.rectangle(debugFrame, (x1,y1), (x2, y2), (0, 0, 255), 1)
      cv2.rectangle(debugFrame, (x1-dist,y1-dist), (x2+dist, y2+dist), (0, 255, 255), 1)
      cv2.rectangle(debugCanny, (x1,y1), (x2, y2), (0, 0, 255), 1)
    else:
      if detected.contours is not None:
        cv2.drawContours(debugCanny, detected.contours, -1, (0, 255, 0, 1), 1)
      if detected.approxContours is not None:
        cv2.drawContours(debugCanny, detected.approxContours, -1, (0, 255, 255, 1), 2)

      if clipper.detectedAtLeastOnce():
        #print('{} : no rectangle'.format(clipper.currentFrameNum))
        #clipper.setPlaying(False)
        # rectCannyShown = True
        pass

    cv2.imshow('canny', debugCanny)

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
def str2bool(v):
  if v.lower() in ('yes', 'true', 't', 'y', '1'):
    return True
  elif v.lower() in ('no', 'false', 'f', 'n', '0'):
    return False
  else:
    raise argparse.ArgumentTypeError('Boolean value expected.')

################################################################################
def main():

  parser = argparse.ArgumentParser()

  parser.add_argument('infolder', help='the folder which contains video files to process')
  parser.add_argument('-o', '--outfolder', help='folder to store the split scenes')
  parser.add_argument('-s', '--showgui', type=str2bool, nargs='?', const=True, default=False, help='show ui for image processing threshold variables')

  args = parser.parse_args()

  infolder = args.infolder
  outfolder = args.outfolder
  if outfolder is None:
    outfolder = infolder

  # 처리 중인 씬 표시
  showMainScene = args.showgui
  debugRectDetection = False      # 디버그 옵션
  debugFrameError = False

  if args.showgui:
    createUI()

  # Create a VideoCapture object and read from input file
  # If the input is the camera, pass 0 instead of the video file name
  #path = 'S:\\_Reference\\Conference\\GDC2018\\video_high\\1024795.mp4'
  #path = 'S:\\DSquare\\[참고자료]\\오픈월드\\1025765 - Procedurally Crafting Manhattan for \'Marvel\'s Spider-Man\'.mp4'
  
  list = []

  try:
    for file in os.listdir(infolder):
        if file.endswith(".mp4"):
            pathName = os.path.join(infolder, file)
            print(pathName)
            list.append(pathName)
  except:
    print('listing video files from {} failed'.format(infolder))
    return

  for i in range(len(list)):
    
    path = list[i]
    print('')
    print('[{}/{}] {}'.format(i, len(list), path))

    # 클리퍼를 생성한다
    try:
      clipper = frameclipper.FrameClipper(path, outfolder, startFramePos)
    except:
      print('something went wrong, processing next video...')
      continue

    # 비디오가 열렸나 확인
    if not clipper.isOpened():
      #print('opening \'{}\' failed, skipping.'.format(path))
      continue

    lastFrame = 0
    totalFrames = int(clipper.getTotalFrames())
    pbar = tqdm(total=totalFrames)

    # 비디오를 읽는다
    breaked = False
    endFrame = None
    while clipper.more():

      time_1 = time.time()

      if args.showgui:
        thres1 = cv2.getTrackbarPos('Threshold1', 'Frame')
        thres2 = cv2.getTrackbarPos('Threshold2', 'Frame')
        thres3 = cv2.getTrackbarPos('Threshold3', 'Frame')
        thres4 = cv2.getTrackbarPos('Threshold4', 'Frame')
        epsilon = cv2.getTrackbarPos('Epsilon', 'Frame') /100
        debugRectDetection = cv2.getTrackbarPos('Show Rect', 'Frame') > 0
      else:
        thres1 = 20
        thres2 = 15
        thres3 = 200
        thres4 = 100
        epsilon = 5 / 100

      clipper.do(thres1, thres2, thres3, thres4, epsilon)

      # qa 프레임이 감지됐다
      if endFrame is None and clipper.qaFrame is not None:
        pbar.close()

        endFrame = clipper.qaFrame
        print('beginning of q&a session detected at frame {}'.format(endFrame))
        
        pbar = tqdm(total=endFrame)
        lastFrame = 0

      pbar.update(int(clipper.getCurrentFrameNum() - lastFrame))
      lastFrame = int(clipper.getCurrentFrameNum())

      time_2 = time.time()

      # Display the resulting frame
      if debugRectDetection:
        showRectDetection(clipper)
      elif debugFrameError:
        showFrameError(clipper, thres3, thres4)
      elif showMainScene:
        cv2.imshow('Frame', clipper.getCurrentFrame())

      if showMainScene:
        
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

        if key & 0xff == ord('s'):
          showMainScene = not showMainScene

    clipper.close()

    if breaked:
      break

    pbar.close()

  # Closes all the frames
  cv2.destroyAllWindows()

  while gifwriter.getActiveThreads() > 0:
    print('wait to writing {} gifs...'.format(gifwriter.getActiveThreads()))
    time.sleep(1)

################################################################################
if __name__ == "__main__":
  main()