"""
ImageProcessor.py
Object to handle all processing of images/data.

author: @saharae, @justjoshtings
created: 11/12/2022
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import random
import cv2
import copy
import torchvision.transforms as T
import torchvision.transforms.functional as TF
import torch
from PIL import Image
from matplotlib import cm


class ImageProcessor:
    '''
    Object to handle processor of images.
    '''
    def __init__(self, log_file=None):
        '''
        Params:
            self: instance of object
            log_file (str): default is None to not have logging, otherwise, specify logging path ../filepath/log.log

        '''
    def binarize(self, img, threshold=128):
        """
        Function to binarize images at some threshold pixel value.
        Set to 0 or 255.

        Parameters:
        img: image in numpy matrix
        threshold: pixel threshold to binarize

        Return:
        img: binarized image in numpy matrix
        """
        # Binarize the image
        if np.max(img) > 1:
            img[img > threshold] = 255.
            img[img <= threshold] = 0.
        else:
            img[img > (threshold/255.)] = 255.
            img[img <= (threshold/255.)] = 0.    

        return img
    
    def rescale(self, img):
        """
        Function to rescale image from 0 to 255 to between 0 and 1. 
        
        Parameters:
            img: image in numpy matrix

        Return:
            img: rescaled image in numpy matrix
        """
        if np.max(img) > 1:
            img = np.multiply(img, 1./255)

        return img

    def mask_max_pixel_normalize(self, img, threshold=0.8):
        """
        Function to normalize max pixel intensity to 1 by a threshold multiplier. 
        
        Parameters:
            img: image in numpy matrix
            threshold: threshold multiplier to reset max pixel intensity to 1
                        ie: max pixel value is 0.9, if current pixel value is > 0.9*0.8 then set to 1.

        Return:
            normalized_mask: normalized mask image
        """
        max_R_value = img[::,::,0].max()
        max_G_value = img[::,::,1].max()
        max_B_value = img[::,::,2].max()

        normalized_R_channel = copy.deepcopy(img[::,::,0])
        normalized_G_channel = copy.deepcopy(img[::,::,1])
        normalized_B_channel = copy.deepcopy(img[::,::,2])

        normalized_R_channel[normalized_R_channel > (max_R_value*threshold)] = 1.
        normalized_G_channel[normalized_G_channel > (max_G_value*threshold)] = 1.
        normalized_B_channel[normalized_B_channel > (max_B_value*threshold)] = 1.

        normalized_mask = np.dstack((normalized_R_channel,normalized_G_channel,normalized_B_channel))

        return normalized_mask

    def mask_argmax(self, predicted_mask):
        """
        Function to argmax across the third dimension and set the pixel of the highest channel to 1
        and everything else to 0

        Parameters:
            predicted_mask: predicted mask

        Return:
            predicted_mask_argmax: 
        """
        idx = predicted_mask.argmax(axis=2)
        predicted_mask_argmax = np.zeros_like(predicted_mask)

        class1 = predicted_mask_argmax[::,::,0]
        class2 = predicted_mask_argmax[::,::,1]
        class3 = predicted_mask_argmax[::,::,2]
        class4 = predicted_mask_argmax[::,::,3]

        class1[np.where(idx==0)] = 1
        class2[np.where(idx==1)] = 1
        class3[np.where(idx==2)] = 1
        class4[np.where(idx==3)] = 1

        predicted_mask_argmax = np.dstack((class1,class2,class3,class4))

        return predicted_mask_argmax

    def one_hot_encode(self, img, class_map=None):
        """
        Function to one hot encode ground truth masks

        Parameters:
            img: mask image where each channel represents a color channel
            class_map: class_df

        Return:
            frame: one hot encoded image where each channel represents a class
        """

        if class_map is None:
            class_map = pd.DataFrame({'name':['Sky', 'Big Rocks', 'Small Rocks', 'Unlabeled'], 
                                    'r':[255,0,0,0], 
                                    'g':[0,0,255,0],
                                    'b':[0,255,0,0]})

        img_copy = copy.deepcopy(img)
        frame = np.zeros((img.shape[0], img.shape[1], len(class_map))).astype('int')

        class_channel = 0

        for index, row in class_map.iterrows():
            new_img = copy.deepcopy(img_copy[::,::,::])

            R = new_img[::,::,0]
            G = new_img[::,::,1]
            B = new_img[::,::,2]

            # OHE each class type
            new_img[(R == row['r']/255) & (G == row['g']/255) & (B == row['b']/255)] = 2
            new_img[new_img < 2] = 0
            new_img[new_img == 2] = 1

            new_channel = copy.deepcopy(new_img[::,::,0])

            # Take first layer since they are all the same and put into OHE mask
            frame[::,::,class_channel] = new_channel

            class_channel+=1

        return frame

    def reverse_one_hot_encode(self, img, class_map=None):
        """
        Function to reverse one hot encode 4 class channel to 3 channel RGB mask

        Parameters:
            img: image of one hot encoded mask image where each channel represents a class
            class_map: class_df

        Return:
            rgb_img: reversed one hot encoded image of RGB channels
        """

        if class_map is None:
            class_map = pd.DataFrame({'name':['Sky', 'Big Rocks', 'Small Rocks', 'Unlabeled'], 
                                    'r':[255.,0.,0.,0.], 
                                    'g':[0.,0.,255.,0.],
                                    'b':[0.,255.,0.,0.]})
            
        img = self.binarize(img)

        all_red_channels = []
        all_green_channels = []
        all_blue_channels = []

        class_channel = 0

        for index, row in class_map.iterrows():

            current_class_channel = copy.deepcopy(img[::,::,class_channel])

            temp_rgb = np.zeros((img.shape[0], img.shape[1], 3))

            # if pixel value > 128 then put 0s in R, 255 in g, 255 in b
            # or corresponding RGB for each class

            if row['r'] > 0:
                temp_rgb[::,::,0] = current_class_channel
            if row['g'] > 0:
                temp_rgb[::,::,1] = current_class_channel
            if row['b'] > 0:
                temp_rgb[::,::,2] = current_class_channel

            all_red_channels.append(copy.deepcopy(temp_rgb[::,::,0]))
            all_green_channels.append(copy.deepcopy(temp_rgb[::,::,1]))
            all_blue_channels.append(copy.deepcopy(temp_rgb[::,::,2]))

            class_channel += 1

        red_stack = np.dstack(tuple(all_red_channels))
        green_stack = np.dstack(tuple(all_green_channels))
        blue_stack = np.dstack(tuple(all_blue_channels))

        rgb_img = np.zeros((img.shape[0], img.shape[1], 3))

        rgb_img[::,::,0] = np.max(red_stack, axis=2)
        rgb_img[::,::,1] = np.max(green_stack, axis=2)
        rgb_img[::,::,2] = np.max(blue_stack, axis=2)

        return rgb_img

    def data_augmentation(self, image, mask):
        '''
        Function to perform data augmentation
        
        Parameters:
            image: image in numpy (x,y,3)
            mask: ground truth mask in numpy (x,y,3)
        
        Returns:
            

        Image Only:
            - Color jitters: hue/contrast/brightness

        Both Image and Mask:
            - Random horizontal and vertical flips
        '''
        pil_image = Image.fromarray((image * 255).astype(np.uint8))
        pil_mask = Image.fromarray((mask * 255).astype(np.uint8))

        # 1. Image and Mask:
        # 1A. VerticalFlip
        if random.random() > 0.2:
            pil_image = TF.vflip(pil_image)
            pil_mask  = TF.vflip(pil_mask)
        
        # 1B. Horitonal Flifp
        if random.random() > 0.2:
            pil_image = TF.hflip(pil_image)
            pil_mask  = TF.hflip(pil_mask)

        # 2. Image Only
        transform_img = RandomChoice([
                    T.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.5, hue=0.5)
                ])

        pil_image, = transform_img([pil_image,])

        img = np.asarray(pil_image)/255
        msk = np.asarray(pil_mask)/255

        return img, msk

    def preprocessor_images(self, image, b_threshold=128):
        """
        Function to combine preprocessing steps to feed into ImageDataGenerator.
        'Masks' have to binarize then rescale. 'Images' just have to rescale.

        Parameters:
        image: image in numpy (x,y,3)
        b_threshold: binary threshold value for pixels, default at 128.

        Return:
        final_img: final image to return from preprocessor after going through 
                all processing steps.
        """
        final_img = self.rescale(image)

        return final_img

    def preprocessor_masks(self, image, b_threshold=128, class_map=None):
        """
        Function to combine preprocessing steps to feed into ImageDataGenerator.
        'Masks' have to binarize then rescale. 'Images' just have to rescale.

        Parameters:
        image: image in numpy (x,y,3)
        class_map: mapping dataframe of classes and their corresponding RGB values for one hot encoding into separate channels
        b_threshold: binary threshold value for pixels, default at 128.

        Return:
        final_img: final image to return from preprocessor after going through 
                all processing steps.
        """
        image = self.mask_max_pixel_normalize(image)
        image = self.one_hot_encode(image, class_map)
        final_img = self.rescale(image)

        return final_img

class RandomChoice(torch.nn.Module):
    def __init__(self, transforms):
       super().__init__()
       self.transforms = transforms

    def __call__(self, imgs):
        t = random.choice(self.transforms)
        return [t(img) for img in imgs]