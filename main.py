'''Training neural network models on CIFAR-10 dataset with PyTorch'''

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import numpy as np
import time
import matplotlib.pyplot as plt

from models import *

device = 'cuda' if torch.cuda.is_available() else 'cpu'

# Data Transformation
print("--> Preparing Data...")

transform_train = transforms.Compose([
    transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),   # these normalization values are commonly used for CIFAR10 dataset
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
])

# Loading CIFAR-10 Dataset
trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download=True, transform=transform_train)
testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)

batch_size = 256
trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size, shuffle=True)
testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size, shuffle=False)

# Definition of Classes
classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

# Model Initialization
print("--> Initializing Model...")

net = VGG('VGG16')                      # model called net is an instance of class VGG
net = net.to(device)                    # moves model to device to ensure the next computations are performed on the specified device
if device == 'cuda':
    net = torch.nn.DataParallel(net)    # wraps model with DataParallel to parallelize training process on GPUs if available
    cudnn.benchmark = True              # enables cuDNN benchmarking mode for best algorithm during convolutional operations

criterion = nn.CrossEntropyLoss()                                                           # applies softmax   
optimizer = optim.SGD(net.parameters(), lr=0.1, momentum=0.9, weight_decay=0.001)         # used to update parameters (weights and biases) to minimize loss function
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer=optimizer, T_max=60, eta_min=0.001)   # improves convergence with decreasing lr

# Training Image Visualization Method
def imshow(img):                                    # takes input parameter pytorch tensor of 1 image
    img = img / 2 + 0.5                             # unnormalize
    npimg = img.numpy()                             # convert to numpy array
    plt.imshow(np.transpose(npimg, (1, 2, 0)))      # change order of dimensions from pytorch (channels, height, wdith) -> plt (height, width, channels)
    plt.show()

########################################################################

# Training Method
total_train_loss = []                                           # list to track total training loss for learning curve

def train(epoch):
    train_loss = 0.0                                            # tracks the running training loss for each epoch
    net.train()                                                 # enable training mode on the model

    for batch_index, data in enumerate(trainloader, 0):         # iterate thru mini-batches, batch_index = current mini-batch, data = trainloader data
        inputs, labels = data                                   # unpack mini-batch data to input image and corresponding ground-truth labels [inputs, labels]
        inputs, labels = inputs.to(device), labels.to(device)   # send inputs and labels to specified device for computations

        optimizer.zero_grad()                                   # zero all parameter gradients
        outputs = net(inputs)                                   # forward pass to get predictions from model
        loss = criterion(outputs, labels)                       # loss calculation compares predicted outputs and ground-truth labels

        loss.backward()                                         # backward pass to compute gradients
        optimizer.step()                                        # update model's weights and biases with gradients
        
        train_loss += loss.item()                               # update current mini-batch loss to running loss
        
        if batch_index % 195 == 194:                            # print avg loss for current mini-batch, # of training examples/batch size = 50000/256 = 195
            avg_train_loss = train_loss / 195                   # avg loss calculation, divide by total # of mini-batches
            total_train_loss.append(avg_train_loss)             # update the total training loss list with the next avg training loss for the current mini-batch
            train_loss = 0.0                                    # reset running training loss
            return avg_train_loss                               # return avg training loss to be displayed

# Testing Method
total_test_loss = []                                            # list to track total test loss for learning curve

def test(epoch):
    test_loss = 0.0                                             # tracks the test loss for the current epoch
    net.eval()                                                  # enable testing mode on the model
    correct = 0
    total = 0

    with torch.no_grad():                                       # disable gradient calculations since we're not training
        for data in testloader:                                 # iterate over mini-batches in test dataset
            inputs, labels = data                               # assign input image and ground truth label for each mini-batch
            inputs, labels = inputs.to(device), labels.to(device)

            outputs = net(inputs)                               # forward pass: test images sent through network for predictions
            loss = criterion(outputs, labels)

            test_loss += loss.item()                            # calculate test loss
            _, predicted = torch.max(outputs.data, 1)           # predicted class indices are obtained

            # updates total image count for each mini-batch
            # labels is the ground truth class labels 
            total += labels.size(0)
        
            # compares predicted class indices with ground truth class indicies element-wise (T/F 1/0), returns a Boolean tensor
            # .sum() calculates the number of correct predictions since 1 is true and 0 is false
            # .item() extracts numerical value of the summation (integer)
            correct += (predicted == labels).sum().item()

    avg_test_loss = test_loss / len(testloader)                 # avg test loss calculation, divide by the size of the entire test set
    test_accuracy = 100 * correct / total                       # calculation of the model's accuracy on the entire test set

    total_test_loss.append(avg_test_loss)                       # update the total test loss list with the avg test loss for the current epoch
    return avg_test_loss, test_accuracy                         # return tuple of avg test loss and test accuracy to be displayed

# Class Accuracy Method
def classAccuracy():
    correct_pred = {classname: 0 for classname in classes}
    total_pred = {classname: 0 for classname in classes}

    with torch.no_grad():
        for data in testloader:
            images, labels = data
            images, labels = images.to(device), labels.to(device)
            outputs = net(images)
            _, predictions = torch.max(outputs, 1)

            for label, prediction in zip(labels, predictions):
                if label == prediction:
                    correct_pred[classes[label]] += 1
                total_pred[classes[label]] += 1

    for classname, correct_count in correct_pred.items():
        accuracy = 100 * float(correct_count) / total_pred[classname]
        print(f'Accuracy for class: {classname:5s} is {accuracy:.1f}%')

# Train and Test Loop
num_epochs = 60
start_time = time.time()

for epoch in range(num_epochs):
    avg_train_loss = train(epoch)
    test_data = test(epoch)
    avg_test_loss, test_accuracy = test_data
    scheduler.step()

    print(f'[Epoch {epoch + 1:>5}]\t Avg Training Loss: {avg_train_loss:.3f}\t Avg Test Loss: {avg_test_loss:.3f}\t Test Accuracy: {test_accuracy:.1f}%')

end_time = time.time()
total_time = end_time - start_time
print(f'Training and testing completed in {total_time:.2f} seconds.')

# Learning Curve
plt.plot(range(num_epochs), total_train_loss, label='Training Loss')
plt.plot(range(num_epochs), total_test_loss, label='Test Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.title('Learning Curve')
plt.grid()
plt.legend()
plt.show()

#############################################################################

# Training
# print("--> Training Model...")

# num_epochs = 40                 # set number of epochs (number of times dataset is seen by model)
# tick = time.time()              # record start time to track total training time

# for epoch in range(num_epochs): # training loop processes entire training dataset num_epochs times with the model
#     train_loss = 0.0            # tracks running loss to be printed
#     net.train()                 # model set to training mode

#     for i, data in enumerate(trainloader, 0):   # iterate thru mini-batches, i = current mini-batch, data = trainloader data
#         inputs, labels = data                   # unpack mini-batch data to input image and corresponding ground-truth labels [inputs, labels]
#         inputs, labels = inputs.to(device), labels.to(device)

#         optimizer.zero_grad()                   # zero all parameter gradients

#         outputs = net(inputs)                   # forward pass to get predictions from model
#         loss = criterion(outputs, labels)       # loss calculation compares predicted outputs and ground-truth labels

#         loss.backward()                         # backward pass to compute gradients
#         optimizer.step()                        # update model's weights and biases with gradients
        
#         train_loss += loss.item()               # update current mini-batch loss to running loss
#         if i % 195 == 194:                      # print avg loss for current mini-batch, # training examples/batch size = 50000/256 = 195
#             print(f'[Epoch {epoch + 1:>5}] avg loss: {train_loss / 195:.3f}')
#             train_loss = 0.0                    # reset running loss
#     scheduler.step()

# tock = time.time()
# trainingTime = tock - tick
# print(f"Training completed in {trainingTime:.2f} seconds.")

# # Testing on the Entire Test Dataset
# print("--> Testing Model...")

# correct = 0     # tracks correct predictions
# total = 0       # tracks total images covered
# test_loss = 0.0 # tracks running loss during testing
# net.eval()      # model set to testing mode

# with torch.no_grad():               # disable gradient calculations since we're not training
#     for data in testloader:         # iterate over mini-batches in test dataset
#         inputs, labels = data       # assign input image and ground truth label for each mini-batch
#         inputs, labels = inputs.to(device), labels.to(device)

#         outputs = net(inputs)       # forward pass: test images sent through network for predictions
#         loss = criterion(outputs, labels)

#         test_loss += loss.item()    # calculate test loss
#         _, predicted = torch.max(outputs.data, 1)       # predicted class indices are obtained

#         # updates total image count for each mini-batch
#         # labels is the ground truth class labels 
#         total += labels.size(0)
        
#         # compares predicted class indices with ground truth class indicies element-wise (T/F 1/0), returns a Boolean tensor
#         # .sum() calculates the number of correct predictions since 1 is true and 0 is false
#         # .item() extracts numerical value of the summation (integer)
#         correct += (predicted == labels).sum().item()

# avg_test_loss = test_loss / len(testloader)
# print(f'Average test loss: {avg_test_loss:.3f}')
# print(f'Accuracy of the network on 10000 test images: {100 * correct // total}%')

# # Check Accuracy for Each Class
# correct_pred = {classname: 0 for classname in classes}
# total_pred = {classname: 0 for classname in classes}

# with torch.no_grad():
#     for data in testloader:
#         images, labels = data
#         images, labels = images.to(device), labels.to(device)
#         outputs = net(images)
#         _, predictions = torch.max(outputs, 1)

#         for label, prediction in zip(labels, predictions):
#             if label == prediction:
#                 correct_pred[classes[label]] += 1
#             total_pred[classes[label]] += 1

# for classname, correct_count in correct_pred.items():
#     accuracy = 100 * float(correct_count) / total_pred[classname]
#     print(f'Accuracy for class: {classname:5s} is {accuracy:.1f}%')