import numpy as np
import pandas as pd
import os, sys, random
import numpy as np
import pandas as pd
import cv2
import shutil

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from torch import Tensor

from torch.utils.data import Dataset, DataLoader
from torch.utils.data.dataloader import _utils

from random import choice

from skimage import io
from PIL import Image, ImageOps

import glob

# from torchsummary import summary
import logging

import matplotlib.pyplot as plt

import torch.nn.functional as F

import warnings

warnings.filterwarnings("ignore")
from torchvision.models import resnet34, resnet50

seed = 1  # seed必须是int，可以自行设置
torch.manual_seed(seed)
torch.cuda.manual_seed(seed)  # 让显卡产生的随机数一致
torch.cuda.manual_seed_all(seed)  # 多卡模式下，让所有显卡生成的随机数一致？这个待验证
np.random.seed(seed)  # numpy产生的随机数一致
random.seed(seed)

# CUDA中的一些运算，如对sparse的CUDA张量与dense的CUDA张量调用torch.bmm()，它通常使用不确定性算法。
# 为了避免这种情况，就要将这个flag设置为True，让它使用确定的实现。
torch.backends.cudnn.deterministic = True

# 设置这个flag可以让内置的cuDNN的auto-tuner自动寻找最适合当前配置的高效算法，来达到优化运行效率的问题。
# 但是由于噪声和不同的硬件条件，即使是同一台机器，benchmark都可能会选择不同的算法。为了消除这个随机性，设置为 False
torch.backends.cudnn.benchmark = False

import numpy as np
import pandas as pd
import os, sys, random
import numpy as np
import pandas as pd
import cv2
import shutil

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from torch import Tensor

from torch.utils.data import Dataset, DataLoader
from torch.utils.data.dataloader import _utils

from random import choice

from skimage import io
from PIL import Image, ImageOps

import glob

# from torchsummary import summary
import logging

import matplotlib.pyplot as plt

import torch.nn.functional as F
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import torchvision.models as models
# from tqdm.notebook import tqdm
from tqdm import tqdm
from sklearn.utils import shuffle
# from apex import amp

import random

import time

from torch.optim.lr_scheduler import StepLR
from torch.nn.parameter import Parameter

# from albumentations.augmentations.transforms import Lambda, ShiftScaleRotate, HorizontalFlip, Normalize, RandomBrightnessContrast, RandomResizedCrop
# from albumentations.pytorch import ToTensor
# from albumentations import Compose, OneOrOther
#
# import warnings
# import torch_xla
# import torch_xla.debug.metrics as met
# import torch_xla.distributed.data_parallel as dp
# import torch_xla.distributed.parallel_loader as pl
# import torch_xla.utils.utils as xu
# import torch_xla.core.xla_model as xm
# import torch_xla.distributed.xla_multiprocessing as xmp
# import torch_xla.test.test_utils as test_utilsget_My_resnet34
import warnings

warnings.filterwarnings("ignore")
from pretrainedmodels import se_resnext101_32x4d, se_resnet152, xception, inceptionv4, inceptionresnetv2
from torchvision.models import resnet34, resnet50, efficientnet_v2_s, mobilenet_v2, inception_v3, vgg16_bn, efficientnet_b3


def get_My_resnet34():
    model = resnet34(pretrained=True)
    output_channels = model.fc.in_features
    model = list(model.children())[:-2]
    return model, output_channels


def get_My_resnet50(pretrained=None):
    model = resnet50(pretrained=pretrained)
    output_channels = model.fc.in_features
    model = list(model.children())[:-2]
    return model, output_channels

def get_My_VGG16_bn(pretrained=True):
    model = vgg16_bn(pretrained=pretrained)
    output_channels = model.classifier[0].in_features
    model = list(model.children())[:-1]
    return model, output_channels



def get_My_se_resnet152():
    model = se_resnet152(pretrained=None)
    output_channels = model.last_linear.in_features
    model = nn.Sequential(*list(model.children())[:-2])
    return model, output_channels


def get_My_se_resnext101_32x4d():
    model = se_resnext101_32x4d(pretrained=None)
    output_channels = model.last_linear.in_features
    model = nn.Sequential(*list(model.children())[:-2])
    return model, output_channels


def get_My_inceptionv4():
    model = inceptionv4(pretrained=None)
    output_channels = model.last_linear.in_features
    model = list(model.children())[:-2]

    model = nn.Sequential(*model)
    return model, output_channels


def get_My_inceptionv3():
    model = inception_v3(pretrained=True)
    output_channels = model.fc.in_features
    voidLayer = nn.Sequential()
    model.AuxLogits = voidLayer
    model = list(model.children())[:-1]

    model = nn.Sequential(*model)
    return model, output_channels


def get_My_inceptionresnetv2():
    model = inceptionresnetv2(pretrained=None)
    output_channels = model.fc.in_features
    model = list(model.children())[:-2]

    model = nn.Sequential(*model)
    return model, output_channels


def get_My_xception():
    model = xception(pretrained=None)
    output_channels = model.last_linear.in_features
    model = list(model.children())[:-2]

    model = nn.Sequential(*model)
    return model, output_channels


def get_My_efficientnetb3():
    model = efficientnet_b3(pretrained=True)
    output_channels = model.classifier[1].in_features
    model = list(model.children())[:-2]
    return model, output_channels


def get_My_mobilenetv2():
    model = mobilenet_v2(weights=None)
    output_channels = model.last_channel
    model = list(model.children())[:-1]

    model = nn.Sequential(*model)
    return model, output_channels


class baseline(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(baseline, self).__init__()
        # 压缩32倍，通道变为2048
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        self.MLP = nn.Sequential(
            nn.Linear(in_features=out_channels + gender_length, out_features=1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            # nn.Linear(512, 1)
            # nn.Linear(512, 230)
        )

        self.classifier = nn.Linear(512, 230)

    def forward(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.classifier(self.MLP(torch.cat((x, gender_encode), dim=-1)))

    def manifold(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((x, gender_encode), dim=-1))


class baselineMAE(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(baselineMAE, self).__init__()
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        self.MLP = nn.Sequential(
            nn.Linear(in_features=out_channels + gender_length, out_features=1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
        )

        self.classifier = nn.Linear(512, 1)

    def forward(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.classifier(self.MLP(torch.cat((x, gender_encode), dim=-1)))

    def manifold(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((x, gender_encode), dim=-1))


class baselineLDL(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(baselineLDL, self).__init__()
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        self.MLP = nn.Sequential(
            nn.Linear(in_features=out_channels + gender_length, out_features=1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
        )

        self.classifier = nn.Linear(512, 228)

    def forward(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.classifier(self.MLP(torch.cat((x, gender_encode), dim=-1)))

    def manifold(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)

        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((x, gender_encode), dim=-1))


class baseline_inceptionv3(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(baseline_inceptionv3, self).__init__()
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        self.MLP = nn.Sequential(
            nn.Linear(in_features=out_channels + gender_length, out_features=1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            # nn.Linear(512, 1)
            nn.Linear(512, 230)
        )

    def forward(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = torch.flatten(x, 1)
        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((x, gender_encode), dim=-1))


class baseline_VGG16(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(baseline_VGG16, self).__init__()
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        self.MLP = nn.Sequential(
            nn.Linear(self.out_channels + gender_length, 4096),
            nn.ReLU(True),
            nn.Dropout(p=0.5),
            nn.Linear(4096, 4096),
            nn.ReLU(True),
            nn.Dropout(p=0.5),
            nn.Linear(4096, 230),
        )

    def forward(self, x, gender):
        # print(f"x is {x.shape}")
        x = self.backbone(x)
        x = torch.flatten(x, 1)
        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((x, gender_encode), dim=-1))


class Res50Align(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(Res50Align, self).__init__()
        self.backbone = nn.Sequential(*backbone)
        self.out_channels = out_channels

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        # self.MLP = nn.Sequential(
        #     nn.Linear(in_features=out_channels + gender_length, out_features=1024, bias=False),
        #     nn.BatchNorm1d(1024),
        #     nn.ReLU(inplace=True),
        #     nn.Linear(1024, 512, bias=False),
        #     nn.BatchNorm1d(512),
        #     nn.ReLU(inplace=True),
        #     nn.Linear(512, 230, bias=False),
        #     # nn.BatchNorm1d(2048, affine=False)
        # )
        self.MLP = nn.Sequential(
            nn.Linear(in_features=out_channels + gender_length, out_features=1024, bias=False),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, 1024, bias=False),
            nn.BatchNorm1d(1024),
            nn.ReLU(inplace=True),
            nn.Linear(1024, 1024, bias=False),
            # nn.BatchNorm1d(2048, affine=False)
        )

    def forward(self, x, gender):
        x = self.backbone(x)
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)
        gender_encode = self.gender_encoder(gender)

        logits = self.MLP(torch.cat((x, gender_encode), dim=-1))

        return logits


class classify(nn.Module):

    def __init__(self, backbone) -> None:
        super(classify, self).__init__()
        self.backbone = backbone

        self.classifier = nn.Linear(512, 230)

    def forward(self, x, gender):
        x = self.backbone(x, gender)
        return self.classifier(x)


class ResAndFPN(nn.Module):

    def __init__(self, gender_length, num_classes, backbone, out_channels) -> None:
        super(ResAndFPN, self).__init__()
        # Backbone
        self.out_channels = out_channels
        self.stage01 = nn.Sequential(*backbone[0:5])  # 3 -> 256
        self.stage2 = backbone[5]    # 256 -> 512
        self.stage3 = backbone[6]    # 512 -> 1024
        self.stage4 = backbone[7]    # 1024 -> 2048

        # Top layer
        self.toplayer = nn.Conv2d(2048, 256, kernel_size=1, stride=1, padding=0)  # Reduce channels
        # Smooth layers
        self.smooth1 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.smooth2 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        self.smooth3 = nn.Conv2d(256, 256, kernel_size=3, stride=1, padding=1)
        # Lateral layers
        self.latlayer1 = nn.Conv2d(1024, 256, kernel_size=1, stride=1, padding=0)
        self.latlayer2 = nn.Conv2d(512, 256, kernel_size=1, stride=1, padding=0)
        self.latlayer3 = nn.Conv2d(256, 256, kernel_size=1, stride=1, padding=0)

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(256, num_classes)

    def _upsample_add(self, x, y):
        _, _, H, W = y.size()
        return F.interpolate(x, size=(H, W), mode='bilinear', align_corners=True) + y
    def forward(self, x):
        #   Bottom-up
        c2 = self.stage01(x)    # [B, 3, 512 ,512] -> [B, 256, 128, 128]
        c3 = self.stage2(c2)    # [B, 256, 128 ,128] -> [B, 512, 64, 64]
        c4 = self.stage3(c3)    # [B, 512, 64, 64] -> [B, 1024, 32, 32]
        c5 = self.stage4(c4)    # [B, 1024, 32, 32] -> [B, 2048, 16 ,16]

        #   Top-down
        p5 = self.toplayer(c5)  # 2048 -> 256, [16 ,16]
        p4 = self._upsample_add(p5, self.latlayer1(c4))  # 1024 -> 256, [32, 32]
        p3 = self._upsample_add(p4, self.latlayer2(c3))  # 512 -> 256, [64, 64]
        p2 = self._upsample_add(p3, self.latlayer3(c2))  # 256 -> 256, [128, 128]

        # Smooth
        p4 = self.smooth1(p4)   # [B, 256, 32, 32]
        p3 = self.smooth2(p3)   # [B, 256, 64, 64]
        p2 = self.smooth3(p2)   # [B, 256, 128, 128]
        return p2, p3, p4, p5


class SEBlock(nn.Module):
    def __init__(self, channel, ration=16):
        super(SEBlock, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel // ration, bias=False),
            nn.ReLU(),
            nn.Linear(channel // ration, channel, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        b, c, h, w = x.size()
        # b, c ,h, w --> b, c, 1, 1
        avg = self.avg_pool(x).view([b, c])  #torch.Size([2, 64])
        fc = self.fc(avg).view([b, c, 1, 1])  #torch.Size([2, 64, 1, 1])

        return x * fc


class channel_attention(nn.Module):
    def __init__(self, channel, ration=16):
        super(channel_attention, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(channel, channel//ration, bias=False),
            nn.ReLU(),
            nn.Linear(channel//ration, channel, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):           #torch.Size([2, 64, 5, 5])
        b, c, h, w = x.size()
        avg_pool = self.avg_pool(x).view([b, c])  #torch.Size([2, 64])
        max_pool = self.max_pool(x).view([b, c])  #torch.Size([2, 64])

        avg_fc = self.fc(avg_pool)  #torch.Size([2, 64])
        max_fc = self.fc(max_pool)  #torch.Size([2, 64])

        out = self.sigmoid(max_fc+avg_fc).view([b, c, 1, 1])  ##torch.Size([2, 64, 1, 1])
        return x * out

#空间注意力
class spatial_attention(nn.Module):
    def __init__(self, kernel_size=7):
        super(spatial_attention, self).__init__()

        self.conv = nn.Conv2d(in_channels=2, out_channels=1, kernel_size=kernel_size, stride=1,
                              padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        b, c, h, w = x.size()
        #通道的最大池化
        max_pool = torch.max(x, dim=1, keepdim=True).values  #torch.Size([2, 1, 5, 5])
        avg_pool = torch.mean(x, dim=1, keepdim=True)        #torch.Size([2, 1, 5, 5])
        pool_out = torch.cat([max_pool, avg_pool], dim=1)    #torch.Size([2, 2, 5, 5])
        conv = self.conv(pool_out)                           #torch.Size([2, 1, 5, 5])
        out = self.sigmoid(conv)

        return out * x

#将通道注意力和空间注意力进行融合
class CBAM(nn.Module):
    def __init__(self, channel, ration=16, kernel_size=7):
        super(CBAM, self).__init__()
        self.channel_attention = channel_attention(channel, ration)
        self.spatial_attention = spatial_attention(kernel_size)

    def forward(self, x):
        out = self.channel_attention(x)    #torch.Size([2, 64, 5, 5])
        out = self.spatial_attention(out)  #torch.Size([2, 64, 5, 5])

        return out


class eca_layer(nn.Module):
    """Constructs a ECA module.
    Args:
        channel: Number of channels of the input feature map
        k_size: Adaptive selection of kernel size
    """

    def __init__(self, channel, k_size=3):
        super(eca_layer, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.conv = nn.Conv1d(1, 1, kernel_size=k_size, padding=(k_size - 1) // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x: input features with shape [b, c, h, w]
        b, c, h, w = x.size()

        # feature descriptor on the global spatial information
        y = self.avg_pool(x)

        # Two different branches of ECA module
        y = self.conv(y.squeeze(-1).transpose(-1, -2)).transpose(-1, -2).unsqueeze(-1)

        # Multi-scale information fusion
        y = self.sigmoid(y)

        return x * y.expand_as(x)


class CA_Block(nn.Module):
    def __init__(self, channel, reduction=16):  # 64 16
        super(CA_Block, self).__init__()

        self.conv_1x1 = nn.Conv2d(channel, channel // reduction, kernel_size=1, stride=1, bias=False)

        self.relu = nn.ReLU()
        self.bn = nn.BatchNorm2d(channel // reduction)

        self.F_h = nn.Conv2d(in_channels=channel // reduction, out_channels=channel, kernel_size=1, stride=1,
                             bias=False)
        self.F_w = nn.Conv2d(in_channels=channel // reduction, out_channels=channel, kernel_size=1, stride=1,
                             bias=False)

        self.sigmoid_h = nn.Sigmoid()
        self.sigmoid_w = nn.Sigmoid()

    def forward(self, x):  # torch.Size([2, 64, 5, 5])
        _, _, h, w = x.size()
        # (b, c, h, w) --> (b, c, h, 1)  --> (b, c, 1, h)
        x_h = torch.mean(x, dim=3, keepdim=True).permute(0, 1, 3, 2)  # dimension维度      #torch.Size([2, 64, 1, 5])
        # (b, c, h, w) --> (b, c, 1, w)
        x_w = torch.mean(x, dim=2, keepdim=True)  # torch.Size([2, 64, 1, 5])
        # (b, c, 1, w) cat (b, c, 1, h) --->  (b, c, 1, h+w)
        # (b, c, 1, h+w) ---> (b, c/r, 1, h+w)
        x_cat_conv_relu = self.relu(
            self.bn(self.conv_1x1(torch.cat((x_h, x_w), 3))))  # torch.Size([2, 64, 1, 10])  torch.Size([2, 4, 1, 10])
        # (b, c/r, 1, h+w) ---> (b, c/r, 1, h)  、 (b, c/r, 1, w)
        x_cat_conv_split_h, x_cat_conv_split_w = x_cat_conv_relu.split([h, w],
                                                                       3)  # torch.Size([2, 4, 1, 5])    torch.Size([2, 4, 1, 5])
        # (b, c/r, 1, h) ---> (b, c, h, 1)
        s_h = self.sigmoid_h(
            self.F_h(x_cat_conv_split_h.permute(0, 1, 3, 2)))  # torch.Size([2, 4, 5, 1])    torch.Size([2, 64, 5, 1])
        # (b, c/r, 1, w) ---> (b, c, 1, w)
        s_w = self.sigmoid_w(self.F_w(x_cat_conv_split_w))  # torch.Size([2, 4, 1, 5])    torch.Size([2, 64, 1, 5])
        # s_h往宽方向进行扩展， s_w往高方向进行扩展
        out = (s_h.expand_as(x) * s_w.expand_as(x)) * x  # torch.Size([2, 64, 5, 5])

        return out


class ResAndFusion(nn.Module):

    def __init__(self, gender_length, backbone, out_channels) -> None:
        super(ResAndFusion, self).__init__()
        # Backbone
        self.out_channels = int(out_channels + out_channels/2 + out_channels/4 + out_channels/8)
        self.stage01 = nn.Sequential(*backbone[0:5])  # 3 -> 256
        self.stage2 = backbone[5]    # 256 -> 512
        self.stage3 = backbone[6]    # 512 -> 1024
        self.stage4 = backbone[7]    # 1024 -> 2048

        self.gender_encoder = nn.Sequential(
            nn.Linear(1, gender_length),
            nn.BatchNorm1d(gender_length),
            nn.ReLU()
        )

        # self.SeBlock = SEBlock(self.out_channels)
        self.ECA = eca_layer(self.out_channels)

        self.MLP = nn.Sequential(
            nn.Linear(in_features=self.out_channels + gender_length, out_features=1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 228)
        )

        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x, gender):
        #   Bottom-up
        c2 = self.stage01(x)    # [B, 3, 512 ,512] -> [B, 256, 128, 128]
        c3 = self.stage2(c2)    # [B, 256, 128 ,128] -> [B, 512, 64, 64]
        c4 = self.stage3(c3)    # [B, 512, 64, 64] -> [B, 1024, 32, 32]
        c5 = self.stage4(c4)    # [B, 1024, 32, 32] -> [B, 2048, 16 ,16]

        #   interpolate
        _, _, H, W = c2.size()
        p5 = F.interpolate(c5, size=(H, W), mode='bilinear', align_corners=True)
        p4 = F.interpolate(c4, size=(H, W), mode='bilinear', align_corners=True)
        p3 = F.interpolate(c3, size=(H, W), mode='bilinear', align_corners=True)

        # concat
        fusion_feature = torch.cat((p5, p4, p3, c2), dim=1)
        # fusion_feature = self.SeBlock(fusion_feature)
        fusion_feature = self.ECA(fusion_feature)

        fusion_vector = self.avgpool(fusion_feature)
        fusion_vector = torch.squeeze(fusion_vector)
        fusion_vector = fusion_vector.view(-1, self.out_channels)

        # encode gender
        gender_encode = self.gender_encoder(gender)

        return self.MLP(torch.cat((fusion_vector, gender_encode), dim=-1))


class Pooling_attention(nn.Module):
    def __init__(self, input_channels, kernel_size=1):
        super(Pooling_attention, self).__init__()
        self.pooling_attention = nn.Sequential(
            nn.Conv2d(input_channels, 1, kernel_size=kernel_size, padding=kernel_size // 2),
            nn.ReLU()
        )

    def forward(self, x):
        return self.pooling_attention(x)


class Part_Relation(nn.Module):
    def __init__(self, input_channels, reduction=[16], level=1):
        super(Part_Relation, self).__init__()

        modules = []
        for i in range(level):
            output_channels = input_channels // reduction[i]
            modules.append(nn.Conv2d(input_channels, output_channels, kernel_size=1))
            modules.append(nn.BatchNorm2d(output_channels))
            modules.append(nn.ReLU())
            input_channels = output_channels

        self.pooling_attention_0 = nn.Sequential(*modules)
        self.pooling_attention_1 = Pooling_attention(input_channels, 1)
        self.pooling_attention_3 = Pooling_attention(input_channels, 3)
        self.pooling_attention_5 = Pooling_attention(input_channels, 5)

        self.last_conv = nn.Sequential(
            nn.Conv2d(3, 1, kernel_size=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        input = x
        x = self.pooling_attention_0(x)
        x = torch.cat([self.pooling_attention_1(x), self.pooling_attention_3(x), self.pooling_attention_5(x)], dim=1)
        x = self.last_conv(x)
        return input - input * x

        model = nn.Sequential(*model)
        return model, output_channels


class BAA_New(nn.Module):
    def __init__(self, gender_encode_length, backbone, out_channels):
        super(BAA_New, self).__init__()
        self.backbone0 = nn.Sequential(*backbone[0:5])
        self.part_relation0 = Part_Relation(256)
        self.out_channels = out_channels
        self.backbone1 = backbone[5]
        self.part_relation1 = Part_Relation(512, [4, 8], 2)
        self.backbone2 = backbone[6]
        self.part_relation2 = Part_Relation(1024, [8, 8], 2)
        self.backbone3 = backbone[7]
        self.part_relation3 = Part_Relation(2048, [8, 16], 2)

        # 3.788
        # self.part_relation0 = Part_Relation(256)
        # self.part_relation1 = Part_Relation(512, 32)
        # self.part_relation2 = Part_Relation(1024, 8, 2)
        # self.part_relation3 = Part_Relation(2048, 8, 2)

        self.gender_encoder = nn.Linear(1, gender_encode_length)
        self.gender_bn = nn.BatchNorm1d(gender_encode_length)

        self.fc = nn.Sequential(
            nn.Linear(out_channels + gender_encode_length, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 1)
        )

        # self.fc0 = nn.Linear(out_channels + gender_encode_length, 1024)
        # self.bn0 = nn.BatchNorm1d(1024)
        #
        # self.fc1 = nn.Linear(1024, 512)
        # self.bn1 = nn.BatchNorm1d(512)
        #
        # self.output = nn.Linear(512, 1)

    def forward(self, image, gender):
        x = self.part_relation0(self.backbone0(image))
        # x  = self.backbone0(image)
        x = self.part_relation1(self.backbone1(x))
        # x = self.backbone1(x)
        x = self.part_relation2(self.backbone2(x))
        # x = self.backbone2(x)
        x = self.part_relation3(self.backbone3(x))
        # x = self.backbone3(x)
        feature_map = x
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)
        image_feature = x

        gender_encode = self.gender_bn(self.gender_encoder(gender))
        gender_encode = F.relu(gender_encode)

        x = torch.cat([x, gender_encode], dim=1)

        x = self.fc(x)

        # x = F.relu(self.bn0(self.fc0(x)))
        #
        # x = F.relu(self.bn1(self.fc1(x)))
        #
        # x = self.output(x)

        return feature_map, gender_encode, image_feature, x

    def fine_tune(self, need_fine_tune=True):
        self.train(need_fine_tune)


class BAA_Base(nn.Module):
    def __init__(self, gender_encode_length, backbone, out_channels):
        super(BAA_New, self).__init__()
        self.backbone0 = nn.Sequential(*backbone[0:5])
        self.part_relation0 = Part_Relation(256)
        self.out_channels = out_channels
        self.backbone1 = backbone[5]
        self.part_relation1 = Part_Relation(512, [4, 8], 2)
        self.backbone2 = backbone[6]
        self.part_relation2 = Part_Relation(1024, [8, 8], 2)
        self.backbone3 = backbone[7]
        self.part_relation3 = Part_Relation(2048, [8, 16], 2)

        # 3.788
        # self.part_relation0 = Part_Relation(256)
        # self.part_relation1 = Part_Relation(512, 32)
        # self.part_relation2 = Part_Relation(1024, 8, 2)
        # self.part_relation3 = Part_Relation(2048, 8, 2)

        self.gender_encoder = nn.Linear(1, gender_encode_length)
        self.gender_bn = nn.BatchNorm1d(gender_encode_length)

        self.fc = nn.Sequential(
            nn.Linear(out_channels + gender_encode_length, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 1)
        )

        # self.fc0 = nn.Linear(out_channels + gender_encode_length, 1024)
        # self.bn0 = nn.BatchNorm1d(1024)
        #
        # self.fc1 = nn.Linear(1024, 512)
        # self.bn1 = nn.BatchNorm1d(512)
        #
        # self.output = nn.Linear(512, 1)

    def forward(self, image, gender):
        x = self.part_relation0(self.backbone0(image))
        # x  = self.backbone0(image)
        x = self.part_relation1(self.backbone1(x))
        # x = self.backbone1(x)
        x = self.part_relation2(self.backbone2(x))
        # x = self.backbone2(x)
        x = self.part_relation3(self.backbone3(x))
        # x = self.backbone3(x)
        feature_map = x
        x = F.adaptive_avg_pool2d(x, 1)
        x = torch.squeeze(x)
        x = x.view(-1, self.out_channels)
        image_feature = x

        gender_encode = self.gender_bn(self.gender_encoder(gender))
        gender_encode = F.relu(gender_encode)

        x = torch.cat([x, gender_encode], dim=1)

        x = self.fc(x)

        # x = F.relu(self.bn0(self.fc0(x)))
        #
        # x = F.relu(self.bn1(self.fc1(x)))
        #
        # x = self.output(x)

        return x

    def fine_tune(self, need_fine_tune=True):
        self.train(need_fine_tune)


class Self_Attention_Adj(nn.Module):
    def __init__(self, feature_size, attention_size):
        super(Self_Attention_Adj, self).__init__()
        self.queue = nn.Parameter(torch.empty(feature_size, attention_size))
        nn.init.kaiming_uniform_(self.queue)

        self.key = nn.Parameter(torch.empty(feature_size, attention_size))
        nn.init.kaiming_uniform_(self.key)

        self.leak_relu = nn.LeakyReLU()

        self.softmax = nn.Softmax(dim=1)

    def forward(self, x):
        x = x.transpose(1, 2)
        Q = self.leak_relu(torch.matmul(x, self.queue))
        K = self.leak_relu(torch.matmul(x, self.key))

        return self.softmax(torch.matmul(Q, K.transpose(1, 2)))


class Graph_GCN(nn.Module):
    def __init__(self, node_size, feature_size, output_size):
        super(Graph_GCN, self).__init__()
        self.node_size = node_size
        self.feature_size = feature_size
        self.output_size = output_size
        self.weight = nn.Parameter(torch.empty(feature_size, output_size))
        nn.init.kaiming_uniform_(self.weight)

    def forward(self, x, A):
        x = torch.matmul(A, x.transpose(1, 2))
        return (torch.matmul(x, self.weight)).transpose(1, 2)


class Graph_BAA(nn.Module):
    def __init__(self, backbone):
        super(Graph_BAA, self).__init__()
        self.backbone = backbone
        # freeze image backbone
        for param in self.backbone.parameters():
            param.requires_grad = False

        self.adj_learning = Self_Attention_Adj(2048, 256)
        self.gconv = Graph_GCN(16 * 16, 2048, 1024)

        self.fc0 = nn.Linear(1024 + 32, 1024)
        self.bn0 = nn.BatchNorm1d(1024)

        # self.fc1 = nn.Linear(1024, 512)
        # self.bn1 = nn.BatchNorm1d(512)

        self.output = nn.Linear(1024, 1)

    def forward(self, image, gender):
        # input image to backbone, 16*16*2048
        feature_map, gender, image_feature, cnn_result = self.backbone(image, gender)
        node_feature = feature_map.view(-1, 2048, 16 * 16)
        A = self.adj_learning(node_feature)
        x = F.leaky_relu(self.gconv(node_feature, A))
        x = torch.squeeze(F.adaptive_avg_pool1d(x, 1))
        graph_feature = x
        x = torch.cat([x, gender], dim=1)

        x = F.relu(self.bn0(self.fc0(x)))
        # x = F.relu(self.bn1(self.fc1(x)))

        return image_feature, graph_feature, gender, (self.output(x), cnn_result)

    def fine_tune(self, need_fine_tune=True):
        self.train(need_fine_tune)
        self.backbone.eval()


class Ensemble(nn.Module):
    def __init__(self, model):
        super(Ensemble, self).__init__()
        self.model = model
        # freeze image backbone
        for param in self.model.parameters():
            param.requires_grad = False

        # self.image_encoder = nn.Sequential(
        #     nn.Linear(2048, 1024),
        #     nn.BatchNorm1d(1024),
        #     nn.ReLU()
        # )

        self.fc = nn.Sequential(
            nn.Linear(1024 + 2048 + 32, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),

            nn.Linear(512, 1)
        )

    def forward(self, image, gender):
        image_feature, graph_feature, gender, result = self.model(image, gender)
        # image_feature = self.image_encoder(image_feature)
        if self.training:
            return (self.fc(torch.cat([image_feature, graph_feature, gender], dim=1)) + result[0]) / 2
        else:
            return (self.fc(torch.cat([image_feature, graph_feature, gender], dim=1)) + result[0]) / 2

    def fine_tune(self, need_fine_tune=True):
        self.train(need_fine_tune)
        self.model.eval()


if __name__ == '__main__':
    res50 = baseline(32, *get_My_resnet50())
    res34 = baseline(32, *get_My_resnet34())
    mbnet = baseline(32, *get_My_mobilenetv2())
    effiNet = baseline(32, *get_My_efficientnetb3())
    xceptNet = baseline(32, *get_My_xception())
    inceptNetv3 = baseline(32, *get_My_inceptionv3())
    inceptNetv4 = baseline(32, *get_My_inceptionv4())
    inceptRes = baseline(32, *get_My_inceptionresnetv2())
    se_res152 = baseline(32, *get_My_se_resnet152())
    se_resnext = baseline(32, *get_My_se_resnext101_32x4d())

    print(f'res50:{sum(p.nelement() for p in res50.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'res34:{sum(p.nelement() for p in res34.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'mbnet:{sum(p.nelement() for p in mbnet.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'effiNet:{sum(p.nelement() for p in effiNet.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'xceptNet:{sum(p.nelement() for p in xceptNet.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'inceptNetv3:{sum(p.nelement() for p in inceptNetv3.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'inceptNetv4:{sum(p.nelement() for p in inceptNetv4.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'inceptRes:{sum(p.nelement() for p in inceptRes.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'se_res152:{sum(p.nelement() for p in se_res152.parameters() if p.requires_grad == True) / 1e6}M')
    print(f'se_resnext:{sum(p.nelement() for p in se_resnext.parameters() if p.requires_grad == True) / 1e6}M')

