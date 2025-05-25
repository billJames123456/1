import os
import re
import random
import timm
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import torch.nn.functional as F
from torch.optim.lr_scheduler import ReduceLROnPlateau
from copy import deepcopy
import numpy as np

# ============================
# 可调参数设置
# ============================
SEED = 42
DATA_DIR = "/home/idal-01/zhihao/project/MDDProject/DataBase/ShabbyOperate/new_train"
save_path = "/home/idal-01/zhihao/project/MDDProject/DataBase/ShabbyOperate/ShabbyNet.pth"
acc_door = 0.64
NUM_CLASSES = 6
BATCH_SIZE = 32
LEARNING_RATE = 5e-5
WEIGHT_DECAY = 1e-4
NUM_EPOCHS = 100
EARLY_STOPPING_PATIENCE = 100
LR_SCHEDULER_PATIENCE = 50
LR_SCHEDULER_FACTOR = 0.2
LAMBDA_LOC = 0.1
LABEL_SMOOTHING = 0.01
GPU = 1

# 设置随机种子
def set_seed(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(SEED)

# 自定义数据集类
class LesionDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.image_files = os.listdir(image_dir)
        self.transform = transform

        # 解析标签 (从文件名中提取)
        self.labels = []
        self.bboxes = []
        for img_name in self.image_files:
            pattern = r'_([\d\.]+)_([\d\.]+)_([\d\.]+)_([\d\.]+)_(\d+)\.(jpg|png)$'
            match = re.search(pattern, img_name)
            if match:
                x, y, h, w, label = map(float, match.groups()[:-1])
                label = int(label) - 1  # 转换类别为整数
                self.labels.append(label)
                self.bboxes.append(torch.tensor([x, y, h, w], dtype=torch.float32))  # 添加边界框
            else:
                raise ValueError(f"Filename {img_name} doesn't match the expected pattern.")

        self.labels = np.array(self.labels)
        self.bboxes = np.array(self.bboxes)

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.image_dir, img_name)
        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        # 标签
        label = self.labels[idx]
        bbox = self.bboxes[idx]
        return image, label, bbox

class ShabbyModel(nn.Module):
    def __init__(self, num_classes):
        super(ShabbyModel, self).__init__()

        # Backbone: 使用预训练的ResNeXt-50 32x4d
        resnext = models.resnext50_32x4d(weights='DEFAULT')

        # 提取前三层的输出
        self.conv1 = resnext.conv1
        self.bn1 = resnext.bn1
        self.relu = resnext.relu
        self.maxpool = resnext.maxpool
        self.layer1 = resnext.layer1
        self.layer2 = resnext.layer2
        self.layer3 = resnext.layer3
        # 不使用 layer4

        # ROI Pooling 层
        self.roi_pooling = nn.AdaptiveAvgPool2d((7, 7))

        # 分类分支
        self.classification_head = nn.Sequential(
            nn.Linear(1024 * 7 * 7, 512),  # 1024 对应 ResNeXt 第三层输出通道数
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, num_classes)
        )

        # 位置回归分支
        self.localization_head = nn.Sequential(
            nn.Linear(1024 * 7 * 7, 512),  # 1024 对应 ResNeXt 第三层输出通道数
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 4)  # 对应回归4个边界框参数
        )

    def forward(self, x):
        # ResNeXt backbone 提取特征
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)

        x = self.layer2(x)
        x = self.layer3(x)
        # 不使用 layer4

        # ROI Pooling
        pooled_features = self.roi_pooling(x)
        flattened_features = pooled_features.view(pooled_features.size(0), -1)

        # 分类和定位输出
        class_logits = self.classification_head(flattened_features)
        bbox = self.localization_head(flattened_features)

        return class_logits, bbox

class LabelSmoothingLoss(nn.Module):
    def __init__(self, num_classes, smoothing=0.0):
        super(LabelSmoothingLoss, self).__init__()
        self.confidence = 1.0 - smoothing
        self.smoothing = smoothing
        self.num_classes = num_classes

    def forward(self, logits, target):
        log_probs = F.log_softmax(logits, dim=-1)
        true_dist = torch.zeros_like(log_probs)
        true_dist.fill_(self.smoothing / (self.num_classes - 1))
        true_dist.scatter_(1, target.data.unsqueeze(1), self.confidence)
        return torch.mean(torch.sum(-true_dist * log_probs, dim=-1))

# 多任务Loss定义
class MultiTaskLoss(nn.Module):
    def __init__(self, num_classes, lambda_loc=1.0, smoothing=0.0):
        super(MultiTaskLoss, self).__init__()
        self.classification_loss = LabelSmoothingLoss(num_classes, smoothing=smoothing)
        self.localization_loss = nn.SmoothL1Loss()
        self.lambda_loc = lambda_loc

    def forward(self, class_logits, bbox_pred, class_labels, bbox_labels):
        cls_loss = self.classification_loss(class_logits, class_labels)
        loc_loss = self.localization_loss(bbox_pred, bbox_labels)
        total_loss = cls_loss + self.lambda_loc * loc_loss
        return total_loss

# 训练和评估函数
def train_and_evaluate(model, train_loader, val_loader, optimizer, criterion, num_epochs=10):
    device = torch.device(f"cuda:{GPU}" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    scheduler = ReduceLROnPlateau(optimizer, mode='min', patience=LR_SCHEDULER_PATIENCE, factor=LR_SCHEDULER_FACTOR,
                                  verbose=True)
    best_model_wts = deepcopy(model.state_dict())
    best_val_metric = 0.0
    early_stopping_counter = 0

    for epoch in range(num_epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_steps = 0

        all_train_labels = []
        all_train_preds = []

        for images, labels, bboxes in tqdm(train_loader, desc=f"Epoch {epoch + 1}/{num_epochs} Training"):
            images, labels, bboxes = images.to(device), labels.to(device), bboxes.to(device)

            optimizer.zero_grad()
            class_logits, bbox_preds = model(images)
            loss = criterion(class_logits, bbox_preds, labels, bboxes)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

            # 保存每轮训练中的真实标签和预测结果
            _, preds = torch.max(class_logits, 1)
            all_train_labels.extend(labels.cpu().numpy())
            all_train_preds.extend(preds.cpu().numpy())

            train_steps += 1

        train_loss /= train_steps

        # 计算训练集上的准确率和 F1 分数
        train_accuracy = accuracy_score(all_train_labels, all_train_preds)
        train_macro_f1 = f1_score(all_train_labels, all_train_preds, average='macro')

        # Validation phase
        model.eval()
        val_loss = 0.0
        val_steps = 0

        all_val_labels = []
        all_val_preds = []

        with torch.no_grad():
            for images, labels, bboxes in tqdm(val_loader, desc=f"Epoch {epoch + 1}/{num_epochs} Validation"):
                images, labels, bboxes = images.to(device), labels.to(device), bboxes.to(device)

                class_logits, bbox_preds = model(images)
                loss = criterion(class_logits, bbox_preds, labels, bboxes)
                val_loss += loss.item()

                # 保存验证集上的真实标签和预测结果
                _, preds = torch.max(class_logits, 1)
                all_val_labels.extend(labels.cpu().numpy())
                all_val_preds.extend(preds.cpu().numpy())

                val_steps += 1

        val_loss /= val_steps

        # 计算验证集上的准确率和 F1 分数
        val_accuracy = accuracy_score(all_val_labels, all_val_preds)
        val_macro_f1 = f1_score(all_val_labels, all_val_preds, average='macro')

        # 打印每个 epoch 的指标
        print(f"\nEpoch {epoch + 1}/{num_epochs}")
        print(f"Train Loss: {train_loss:.4f}, Validation Loss: {val_loss:.4f}")
        print(f"Train Accuracy: {train_accuracy:.4f}, Validation Accuracy: {val_accuracy:.4f}")
        print(f"Train F1 (Macro): {train_macro_f1:.4f}, Validation F1 (Macro): {val_macro_f1:.4f}")

        # Learning rate scheduling
        scheduler.step(val_loss)

        # Early Stopping & Model Saving
        if val_macro_f1 > best_val_metric:
            best_val_metric = val_macro_f1
            best_model_wts = deepcopy(model.state_dict())
            torch.save(best_model_wts, save_path)
            print(f"Model saved with validation F1 (Macro): {best_val_metric:.4f}")

        if early_stopping_counter >= EARLY_STOPPING_PATIENCE:
            print("Early stopping triggered")
            break

    model.load_state_dict(best_model_wts)

# 主程序
if __name__ == "__main__":
    transform = transforms.Compose([
        #transforms.Resize((224, 224)),
        transforms.ToTensor(),
        #transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    dataset = LesionDataset(DATA_DIR, transform=transform)

    # Stratified split
    train_indices, val_indices = train_test_split(np.arange(len(dataset)),
                                                  test_size=0.5,
                                                  stratify=dataset.labels,
                                                  random_state=SEED)

    train_dataset = torch.utils.data.Subset(dataset, train_indices)
    val_dataset = torch.utils.data.Subset(dataset, val_indices)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    model = ShabbyModel(num_classes=NUM_CLASSES)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    criterion = MultiTaskLoss(num_classes=NUM_CLASSES, lambda_loc=LAMBDA_LOC, smoothing=LABEL_SMOOTHING)

    train_and_evaluate(model, train_loader, val_loader, optimizer, criterion, num_epochs=NUM_EPOCHS)
