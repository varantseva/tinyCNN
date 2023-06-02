# -*- coding: utf-8 -*-
"""cnn.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Fq-sc6eYO9rP836ShIKzQtU7_z4C9K8X
"""

import os
import numpy as np
import torch.nn as nn 
import json
from torchvision import transforms
from PIL import Image
import random
import torch.optim as optim
import torch
import torch.nn.functional as F


"""Чтение патчей и лейблов из JSONов"""

def load_patches(patch_dir):
    patches = []
    labels = []
    for filename in os.listdir(patch_dir):
        if filename.endswith('.json'):
            with open(os.path.join(patch_dir, filename), 'r') as f:
                patch_data = json.load(f)
                patch_matrix = np.array(patch_data['data'])
                label = patch_data['label']
                image = Image.fromarray(patch_matrix, mode='L')
                tensor = transforms.ToTensor()(image)
                tensor = tensor.unsqueeze(0)
                patches.append(tensor)
                labels.append(label)
    return patches, labels


patches_dir = "patches/patches/fht/jsons"
patches, labels = load_patches(patches_dir)

"""Модель сетки"""

class TinyCNN(nn.Module):
    def __init__(self):
        super(TinyCNN, self).__init__()
        self.conv1 = nn.Conv2d(1, 8, kernel_size=(4, 4), stride=(2, 2))
        self.conv2 = nn.Conv2d(8, 8, kernel_size=(3, 1), stride=(1, 1))
        self.conv3 = nn.Conv2d(8, 8, kernel_size=(1, 2), stride=(1, 1))
        self.conv4 = nn.Conv2d(8, 20, kernel_size=(3, 3), stride=(2, 2))
        self.conv5 = nn.Conv2d(20, 16, kernel_size=(1, 1), stride=(1, 1))
        self.conv6 = nn.Conv2d(16, 12, kernel_size=(1, 1), stride=(1, 1))
        self.conv7 = nn.Conv2d(12, 20, kernel_size=(2, 2), stride=(1, 1))
        self.conv8 = nn.Conv2d(20, 48, kernel_size=(3, 3), stride=(2, 2))

        self.fc1 = nn.Linear(192, 128)
        self.fc2 = nn.Linear(128, 16)
    
    def simrelu(self, x):
        return torch.clamp(x, -1, 1)
    
    def forward(self, x):
        x = torch.from_numpy(x)
        x = self.conv1(x)
        x = self.simrelu(x)
        x = self.conv2(x)
        x = self.simrelu(x)
        x = self.conv3(x)
        x = self.simrelu(x)
        x = self.conv4(x)
        x = self.simrelu(x)
        x = self.conv5(x)
        x = self.simrelu(x)
        x = self.conv6(x)
        x = self.simrelu(x)
        x = self.conv7(x)
        x = self.simrelu(x)
        x = self.conv8(x)
        x = self.simrelu(x)
        x = x.view(x.size(0), -1)
        x = self.fc1(x)
        x = self.simrelu(x)
        x = self.fc2(x)
        return x

def train_model(model, triplet_loss, optimizer, triplets, num_epochs):
    for epoch in range(num_epochs):
        running_loss = 0.0
        for batch_idx, (anchor, positive, negative) in enumerate(triplets):
            optimizer.zero_grad()
            anchor_output = model(anchor)
            positive_output = model(positive)
            negative_output = model(negative)
            loss = triplet_loss(anchor_output, positive_output, negative_output)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
        print('Epoch %d, loss: %.3f' % (epoch+1, running_loss / len(triplets)))

"""Функция разбиения данных на патчи по 8129"""

def generate_triplets(patches, labels, num_triplets=8129, patch_shape=(32, 32)):
    triplets = []
    for i in range(num_triplets):
        # Случайно выбираем патч из списка
        random_index = random.randint(0, len(patches) - 1)
        anchor_patch = np.array(patches[random_index])
        anchor_label = labels[random_index]

        # Случайно выбираем положительный патч из того же класса
        positive_patches = [p for p, l in zip(patches, labels) if
                            l == anchor_label and not np.array_equal(p, anchor_patch)]
        if not positive_patches:
            # Если нет других патчей из этого класса, то берем тот же патч
            positive_patch = anchor_patch
        else:
            positive_patch = np.array(positive_patches[random.randint(0, len(positive_patches) - 1)])

        # Случайно выбираем отрицательный патч из другого класса
        negative_labels = [l for l in set(labels) if l != anchor_label]
        negative_patches = [p for p, l in zip(patches, labels) if l in negative_labels]
        negative_patch = np.array(negative_patches[random.randint(0, len(negative_patches) - 1)])

        anchor_patch = F.interpolate(torch.from_numpy(anchor_patch), size=(32, 32), mode='nearest').numpy()
        positive_patch = F.interpolate(torch.from_numpy(positive_patch), size=(32, 32), mode='nearest').numpy()
        negative_patch = F.interpolate(torch.from_numpy(negative_patch), size=(32, 32), mode='nearest').numpy()

        triplets.append([anchor_patch, positive_patch, negative_patch])
    return np.array(triplets)

num_triplets = 3000
training_triplets = generate_triplets(patches, labels, num_triplets)

tinyCNN = TinyCNN()
triplet_loss = nn.TripletMarginLoss(margin=1.5, p=2)
optimizer = optim.Adam(tinyCNN.parameters(), lr=0.001)

num_epochs = 100
train_model(tinyCNN, triplet_loss, optimizer, training_triplets, num_epochs)