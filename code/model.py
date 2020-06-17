import numpy as np
import mrcnn.model as modellib
import tensorflow as tf

from config import (
    EDGE_CROP,
    GAUSSIAN_NOISE,
    IMG_SIZE,
    NET_SCALING,
    UPSAMPLE_MODE
)

from mrcnn import utils
from mrcnn import visualize
from mrcnn.config import Config
from mrcnn.model import log
from tensorflow.keras import models, layers

MODEL_PATH = '/ship_detection/weights/mask_rcnn_airbus_0022.h5'
# Build U-Net model
def upsample_conv(filters, kernel_size, strides, padding):
    return layers.Conv2DTranspose(filters, kernel_size, strides=strides, padding=padding)


def upsample_simple(filters, kernel_size, strides, padding):
    return layers.UpSampling2D(strides)


def make_model(input_shape):
    if UPSAMPLE_MODE == 'DECONV':
        upsample = upsample_conv
    else:
        upsample = upsample_simple

    input_img = layers.Input(input_shape[1:], name='RGB_Input')
    pp_in_layer = input_img
    if NET_SCALING is not None:
        pp_in_layer = layers.AvgPool2D(NET_SCALING)(pp_in_layer)

    pp_in_layer = layers.GaussianNoise(GAUSSIAN_NOISE)(pp_in_layer)
    pp_in_layer = layers.BatchNormalization()(pp_in_layer)

    c1 = layers.Conv2D(8, (3, 3), activation='relu',
                       padding='same')(pp_in_layer)
    c1 = layers.Conv2D(8, (3, 3), activation='relu', padding='same')(c1)
    p1 = layers.MaxPooling2D((2, 2))(c1)

    c2 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(p1)
    c2 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(c2)
    p2 = layers.MaxPooling2D((2, 2))(c2)

    c3 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(p2)
    c3 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(c3)
    p3 = layers.MaxPooling2D((2, 2))(c3)

    c4 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(p3)
    c4 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(c4)
    p4 = layers.MaxPooling2D(pool_size=(2, 2))(c4)

    c5 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(p4)
    c5 = layers.Conv2D(128, (3, 3), activation='relu', padding='same')(c5)

    u6 = upsample(64, (2, 2), strides=(2, 2), padding='same')(c5)
    u6 = layers.concatenate([u6, c4])
    c6 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(u6)
    c6 = layers.Conv2D(64, (3, 3), activation='relu', padding='same')(c6)

    u7 = upsample(32, (2, 2), strides=(2, 2), padding='same')(c6)
    u7 = layers.concatenate([u7, c3])
    c7 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(u7)
    c7 = layers.Conv2D(32, (3, 3), activation='relu', padding='same')(c7)

    u8 = upsample(16, (2, 2), strides=(2, 2), padding='same')(c7)
    u8 = layers.concatenate([u8, c2])
    c8 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(u8)
    c8 = layers.Conv2D(16, (3, 3), activation='relu', padding='same')(c8)

    u9 = upsample(8, (2, 2), strides=(2, 2), padding='same')(c8)
    u9 = layers.concatenate([u9, c1], axis=3)
    c9 = layers.Conv2D(8, (3, 3), activation='relu', padding='same')(u9)
    c9 = layers.Conv2D(8, (3, 3), activation='relu', padding='same')(c9)

    d = layers.Conv2D(1, (1, 1), activation='sigmoid')(c9)
    d = layers.Cropping2D((EDGE_CROP, EDGE_CROP))(d)
    d = layers.ZeroPadding2D((EDGE_CROP, EDGE_CROP))(d)
    if NET_SCALING is not None:
        d = layers.UpSampling2D(NET_SCALING)(d)

    seg_model = models.Model(inputs=[input_img], outputs=[d])
    return seg_model


def load_from_path(weight_file_path):
    seg_model = make_model((1, IMG_SIZE, IMG_SIZE, 3))
    seg_model.load_weights(weight_file_path)
    return seg_model


def make_model_rcnn():

    class DetectorConfig(Config):
        # Give the configuration a recognizable name
        NAME = 'airbus'

        GPU_COUNT = 1
        IMAGES_PER_GPU = 9

        BACKBONE = 'resnet50'

        NUM_CLASSES = 2  # background and ship classes

        IMAGE_MIN_DIM = 384
        IMAGE_MAX_DIM = 768
        RPN_ANCHOR_SCALES = (4, 8, 16, 32, 64)
        TRAIN_ROIS_PER_IMAGE = 64
        MAX_GT_INSTANCES = 14
        DETECTION_MAX_INSTANCES = 10
        DETECTION_MIN_CONFIDENCE = 0.95
        DETECTION_NMS_THRESHOLD = 0.0

        STEPS_PER_EPOCH = 15
        VALIDATION_STEPS = 10

        ## balance out losses
        LOSS_WEIGHTS = {
            "rpn_class_loss": 30.0,
            "rpn_bbox_loss": 0.8,
            "mrcnn_class_loss": 6.0,
            "mrcnn_bbox_loss": 1.0,
            "mrcnn_mask_loss": 1.2
        }

    class InferenceConfig(DetectorConfig):
        GPU_COUNT = 1
        IMAGES_PER_GPU = 1

    inference_config = InferenceConfig()

    # Recreate the model in inference mode
    model = modellib.MaskRCNN(mode='inference',
                              config=inference_config,
                              model_dir='../data/')
    model.load_weights(MODEL_PATH, by_name=True)

    return model


def predict_rcnn(model, img):
    prediction = model.detect(img)
    mask = prediction[0]['masks']
    zero_masks = np.zeros((*mask.shape[:2], 1))
    if mask.shape[2] == 0:
        mask = zero_masks
    mask = np.squeeze(mask)
    return mask * 255
