import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

import torchvision
from torchvision import datasets, models, transforms

from tensorboardX import SummaryWriter

import numpy as np
import matplotlib.pyplot as plt

import os
import logging

from configs import Config
from models import *
from data_loader import myData
from utils import log

# log
log = log('./log.log',level=logging.INFO)

# configuration
cf = Config()
batch_size = cf.batch_size
num_epochs = cf.num_epochs
num_workers = cf.num_workers
leaning_rate = cf.learning_rate
momentum = cf.momentum
weight_decay = cf.weight_decay
show_every = cf.show_every
save_every = cf.save_every
test_every = cf.test_every
image_every = cf.image_every
save_path = cf.save_path
log.info('配置加载完成')

# dataset
data_transforms = transforms.Compose([
    transforms.ToTensor(),
])

trainSet = myData(dataPath='./train.csv',
                  transform=data_transforms)
testSet = myData(dataPath='./test.csv',
                 transform=data_transforms)

trainLoader = DataLoader(dataset=trainSet,
                         batch_size=batch_size,
                         shuffle=True,
                         num_workers=num_workers)
testLoader = DataLoader(dataset=testSet,
                        batch_size=batch_size,
                        shuffle=False,
                        num_workers=num_workers)
log.info('数据集准备完成')

# net
net = SiameseUnet(3,2)
# gpu
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
if cf.use_gpu:
    log.info(device)
    net = net.to(device)

# net.train()

# optimizer and criterion
# criterion = loss()
criterion = nn.BCEWithLogitsLoss(pos_weight=torch.Tensor([0.3,0.7]))

optimizer = optim.SGD(net.parameters(), lr=leaning_rate,
                      momentum=momentum, weight_decay=weight_decay)

writer = SummaryWriter('./tensorboard/')
data = next(iter(trainLoader))
img1, img2, gt = data[0].to(device), data[1].to(device), data[2].to(device)
writer.add_graph(net,(img1,img2)) # 网络结构
iter = 0 # 折线图横坐标

idx_loss = '_4'
idx_img = '_2'

# train
log.info('开始训练')
for epoch in range(1,num_epochs+1):
    running_loss = 0.0
    for batch, data in enumerate(trainLoader, 1):
        img1, img2, gt = data[0].to(device), data[1].to(
            device), data[2].to(device)
        optimizer.zero_grad()
        output = net(img1, img2)
        # print(output.shape,gt.shape,gt.reshape((-1, gt.shape[2], gt.shape[3])).shape)
        # print(output,gt)
        # loss = criterion(output, gt.reshape((-1, gt.shape[2], gt.shape[3])))
        loss = criterion(output, gt)
        log.debug("output.shape:{},gt.shape:{}".format(output.shape,gt.shape))
        loss.backward()
        optimizer.step()

        writer.add_scalar('train/weighed/loss'+idx_loss,loss.item(),iter) # 绘制折线图
        iter += 1

        running_loss += loss.item()
        if iter % show_every == 0:
            print('[%d, %5d] loss: %.5f' %
                  (epoch, batch , running_loss / show_every))
            log.info('损失：'+'[%d, %5d] loss: %.5f' %
                     (epoch, batch, running_loss / show_every))
            running_loss = 0.0
        if iter % save_every == 0:
            model_name = '{}Siamese-weighed-epoch-{}-batch-{}.pt'.format(
                save_path, epoch, batch)
            log.info('保存模型：'+model_name)
            torch.save(net.state_dict(), model_name)

        if iter % test_every == 0:
            error = 0.0
            for _,data in enumerate(testLoader,1):
                img1, img2, gt = data[0].to(device), data[1].to(
            device), data[2].to(device)
                output = net.forward(img1,img2)
                # loss = criterion(output, gt.reshape((-1, gt.shape[2], gt.shape[3])))
                loss = criterion(output, gt)
                error += loss.item()
            writer.add_scalar('test/weighed/loss'+idx_loss,error,iter) # 绘制折线图

        if iter % image_every == 0:
            # print(gt,output)
            # 这里的 gt 是归一化后的 gt, 因此进行保存时需要更改
            gt[gt>0]=1
            writer.add_images('input_image1'+idx_img,img1,global_step=iter//image_every)
            writer.add_images('input_image2'+idx_img,img2,global_step=iter//image_every)
            writer.add_images('output_image'+idx_img,torch.argmax(output,dim=1,keepdim=True),global_step=iter//image_every)
            writer.add_images('gt_image'+idx_img,gt[:,0:1,:,:],global_step=iter//image_every,)

log.info('训练结束')
writer.close()