from __future__ import print_function
import math
import imageio
import skvideo.io
import numpy as np
import cv2

from tqdm import tqdm
from PIL import Image
from timeit import default_timer as timer
from util import DataLoader


def selectBetterBitrate(height, fps):   
    #print(height,fps)
    if (140 < height) and (height < 200):
        bitrate = "280k"
    elif (200 < height) and (height < 250):
        bitrate = "400k"    
    elif((300 < height) and (height < 400)) and ((20 < fps) and (fps < 40)):
        bitrate = "1M"
    elif((300 < height) and (height < 400)) and ((40 < fps) and (fps < 70)):
        bitrate = "1.5M"
    elif((400 < height) and (height < 500)) and ((20 < fps) and (fps < 40)):
        bitrate = "2.5M"
    elif((400 < height) and (height < 500)) and ((40 < fps) and (fps < 70)):
        bitrate = "4M"
    elif((700 < height) and (height < 800)) and ((20 < fps) and (fps < 40)):
        bitrate = "5M"
    elif((700 < height) and (height < 800)) and ((40 < fps) and (fps < 70)):
        bitrate = "7.5M"
    elif((1000 < height) and (height < 1100)) and ((20 < fps) and (fps < 40)):
        bitrate = "8M"
    elif((1000 < height) and (height < 1100)) and ((40 < fps) and (fps < 70)):
        bitrate = "12M"
    elif((1300 < height) and (height < 1600)) and ((20 < fps) and (fps < 40)):
        bitrate = "16M"
    elif((1300 < height) and (height < 1600)) and ((40 < fps) and (fps < 70)):
        bitrate = "24M"
    elif((1800 < height) and (height < 2400)) and ((20 < fps) and (fps < 40)):
        bitrate = "40M"
    elif((1800 < height) and (height < 2400)) and ((40 < fps) and (fps < 70)):
        bitrate = "55M"
    elif((2400 < height) and (height < 3000)) and ((20 < fps) and (fps < 40)):
        bitrate = "50M"
    elif((2400 < height) and (height < 3000)) and ((40 < fps) and (fps < 70)):
        bitrate = "70M"
    else:
        print(">> Unknow resolution.")
        exit()
    print(">> BITRATE: ",bitrate)
    return bitrate

def scale_lr_imgs(imgs):
    """Scale low-res images prior to passing to ESRGAN"""
    return imgs / 255.

def unscale_hr_imgs(imgs):
    """Un-Scale high-res images"""
    imgs = (imgs + 1.) * 127.5
    imgs = np.clip(imgs, 0., 255.)
    return imgs.astype('uint8') 

def downsample(img_hr,scale):
    lr_shape = (int(img_hr.shape[1]/scale), int(img_hr.shape[0]/scale))  
    img_lr = cv2.resize(cv2.GaussianBlur(img_hr,(5,5),0),lr_shape, interpolation = cv2.INTER_CUBIC)
    #img_lr = cv2.resize(cv2.GaussianBlur(img_hr,(9,9),0),lr_shape, interpolation = cv2.INTER_CUBIC)
    return img_lr

def sr_genarator(model,img_lr,scale):
    """Predict sr frame given a LR frame"""
    # Predict high-resolution version (add batch dimension to image)
    img_lr = scale_lr_imgs(img_lr)
    #img_sr = model.predict(np.expand_dims(img_lr, 0))
    img_sr = model.predict(img_lr.reshape(1,img_lr.shape[0],img_lr.shape[1],img_lr.shape[2]))
    img_sr = unscale_hr_imgs(img_sr)
    # Remove batch dimension
    img_sr = img_sr.reshape(img_sr.shape[1], img_sr.shape[2], img_sr.shape[3])
    return img_sr


def write_srvideo(model=None,lr_videopath=None,sr_videopath=None,scale=None,print_frequency=False,crf=15,fps=None,gpu=False):
    """Generate SR video given LR video """
    videogen = skvideo.io.FFmpegReader(lr_videopath)
    t_frames, height, width, _  = videogen.getShape() 
    print(">> Inputshape: ",videogen.getShape())
    metadata = skvideo.io.ffprobe(lr_videopath)
    #print(json.dumps(metadata["video"], indent=4))
    _fps = metadata['video']['@r_frame_rate'] if (fps == None) else str(fps)
    codec = 'h264_nvenc' if (gpu == 'True') else 'libx264' 
    writer = skvideo.io.FFmpegWriter(sr_videopath, 
    inputdict={'-r': _fps, '-width': str(width*scale), '-height': str(height*scale)},
    outputdict={'-vcodec': codec, '-r': _fps, '-crf': str(crf), '-pix_fmt': 'yuv420p',
                '-b:v': selectBetterBitrate(height*scale,int(_fps.split('/')[0])/int(_fps.split('/')[1]))})
    count = 0
    time_elapsed = 0
    print(">> Writing video...")
    for frame in tqdm(videogen):
        frame = downsample(frame,scale)
        start = timer()
        img_sr = sr_genarator(model,frame,scale=scale)
        writer.writeFrame(img_sr)
        end = timer()
        elapsed = end - start
        time_elapsed +=(elapsed)
        count +=1
        if (print_frequency): 
            if(count % print_frequency == 0):
                print("")
                print('... Time per Frame: '+str(elapsed)+'s')
                print('... FPS: '+str(1./elapsed))
                #print('... Estimated time: '+str(np.mean(time_elapsed)*(t_frames-count)/60.)+'min')
    writer.close()
    videogen = skvideo.io.FFmpegReader(sr_videopath)
    print(">> Outputshape: ",videogen.getShape())
    print('>> Video resized in '+str(time_elapsed)+'s')
    print('>> Average FTP '+str(count/time_elapsed))
    return time_elapsed


def write_sr_images(model=None, lr_imagepath=None, sr_imagepath=None,scale=None):
    print(">> Writing image...")
    time_elapsed = []
    # Load the images to perform test on images
    img_lr = DataLoader.load_img(lr_imagepath,colorspace='RGB')
        
    # Create super resolution images
    start = timer()
    img_sr = sr_genarator(model,img_lr,scale)    
    end = timer()
    time_elapsed.append(end - start)   

    img_sr = Image.fromarray(img_sr.astype(np.uint8))
    img_sr.save(sr_imagepath)
    print('>> Image resized in '+str(np.mean(time_elapsed))+'s')
    return time_elapsed