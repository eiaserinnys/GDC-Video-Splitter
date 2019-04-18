# lastClipStable = False
# lastClipRect = None
# lastClipped = None
# lastMean = 128
# lastEntropy = 100

# minEntropy = 100000
# minEntropyMean = 128
# minEntropyClip = None
# minEntropyFrame = 0

# frameCount = 0
# minorCount = 0

    # # 이전 프레임과의 차이를 계산
    # diffGray = None

    # clipEntropy = 0
    # clipMean = 0

    # if clipped is not None:
    #   cv2.imshow('Clipped', clipped)

    #   newKeyframe = False
    #   newSubFrame = False

    #   score = 0

    #   newClip = True

    #   if lastClipped is not None:
    #     (lh, lw) = lastClipped.shape[:2]
    #     (nh, nw) = clipped.shape[:2]

    #     if lh == nh and lw == nw:

    #       newClip = False

    #       lg = cv2.cvtColor(cv2.resize(lastClipped, None, fx=0.5, fy= 0.5), cv2.COLOR_BGR2GRAY)
    #       ng = cv2.cvtColor(cv2.resize(clipped, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)

    #       # 구조적 유사도
    #       (score, diff) = compare_ssim(lg, ng, full=True)
    #       diff = (diff * 255).astype("uint8")

    #       # 밝기
    #       clipMean = ng.mean()

    #       # 엔트로피
    #       clipEntropy = shannon_entropy(ng)

    #       #print('ssim:{s}, entropy:{e}, mean:{m}'.format(s=score, e=clipEntropy, m=clipMean))

    #       if score < 0.9:
    #         # 구조적 유사도가 90% 이하로 떨어지면 새 이미지로 간주한다
    #         newKeyframe = True

    #       elif abs(clipMean / lastMean - 1) > 0.05:
    #         # 밝기가 5% 이상 변하면 새 서브 프레임 구간으로 간주한다
    #         newSubFrame = True
    
    #   if newClip:
    #       # 새 이미지
    #       newKeyframe = True
    #       ng = cv2.cvtColor(cv2.resize(clipped, None, fx=0.5, fy=0.5), cv2.COLOR_BGR2GRAY)
    #       clipMean = ng.mean()
    #       clipEntropy = shannon_entropy(ng)

    #   if newKeyframe:

    #     if minEntropyClip is not None:
    #       fileName = 'frame{no:04d}-{sub:03d}-{total:d}.png'.format(no=frameCount, sub=minorCount, total=minEntropyFrame)
    #       (ch, cw) = minEntropyClip.shape[:2]
    #       print('Writing {} ({}x{})...'.format(fileName, cw, ch))
    #       cv2.imwrite(outputPath + '\\' + fileName, minEntropyClip)

    #       lastClipped = minEntropyClip.copy()
    #       lastEntropy = minEntropy









    #     else:
    #       lastClipped = clipped.copy()
    #       lastEntropy = clipEntropy
    #       lastMean = clipMean

    #     # 새로운 키 프레임
    #     frameCount += 1
    #     minorCount = 1

    #     # 엔트로피 키 프레임
    #     minEntropy = clipEntropy
    #     minEntropyClip = clipped.copy()
    #     minEntropyFrame = totalFrameCount

    #   else:
    #     if newSubFrame:
    #       # 새 서브 프레임 구간이 시작

    #       # 기존 프레임을 덤프
    #       if minEntropyClip is not None:
    #         fileName = 'frame{no:04d}-{sub:03d}-{total:d}.png'.format(no=frameCount, sub=minorCount, total=minEntropyFrame)
    #         (ch, cw) = minEntropyClip.shape[:2]
    #         print('Writing {} ({}x{})...'.format(fileName, cw, ch))
    #         cv2.imwrite(outputPath + '\\' + fileName, minEntropyClip)

    #       minorCount += 1

    #       lastClipped = minEntropyClip.copy()
    #       lastMean = clipMean
    #       lastEntropy = minEntropy

    #       minEntropy = clipEntropy
    #       minEntropyClip = clipped.copy()
    #       minEntropyFrame = totalFrameCount

    #     else:
    #       # 이전과 비슷한 프레임이 유지되는 중이다
    #       if clipEntropy < minEntropy:
    #         minEntropy = clipEntropy
    #         minEntropyClip = clipped.copy()
    #         minEntropyFrame = totalFrameCount

    #         lastClipped = clipped.copy()
    #         lastMean = clipMean
    #         lastEntropy = clipEntropy


  # morphSize = 50
  # erodedH = cv2.erode(first, np.ones((1,morphSize), np.uint8))
  # dilatedH = cv2.dilate(erodedH, np.ones((1,morphSize), np.uint8))
  # erodedV = cv2.erode(first, np.ones((morphSize,1), np.uint8))
  # dilatedV = cv2.dilate(erodedV, np.ones((morphSize,1), np.uint8))
  
  # dilated = cv2.add(dilatedH, dilatedV)

  # Canny 결과를 Hough를 거쳐 가로세로 직선 성분을 구한다
#   thres = cv2.getTrackbarPos('HoughThreshold', 'UI')
#   #lines = cv2.HoughLines(dilated,1,np.pi/180,thres)
#   lines = None
#   vLines, hLines = detect.seperateLines(lines, w, h)

#   hSegments = detect.getHorizontalSegments(first, hLines, vLines, houghThres, lineThreshold)
#   vSegments = detect.getVerticalSegments(first, hLines, vLines, houghThres, lineThreshold)

#   time_5 = time.time()

#   #debugRender(hLines, vLines, hSegments, vSegments)

  # # 가로 선과 세로 선 조합을 바탕으로 가능한 사각형을 찾아낸다
#   maxRect, rects = detect.detectRectangle(hSegments, vSegments)

  # # 클립 영역 디버그 렌더
  # for i in range(len(rects)):
  #   (x1, y1, x2, y2) = rects[i]
  #   cv2.rectangle(frame, (x1,y1), (x2, y2), rectColor, 1)
