import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import DataLoader, Dataset
import torch.nn.functional as F
from PIL import Image
import os
from tqdm import tqdm
import random
# 注:本人找不到convnext作为backbone的版本了 这个resnext50是早期版本 但是可以作为参考
# ============================
# 超参数设置
# ============================
SEED = 42
TRAIN_DIR = "/home/idal-01/zhihao/project/MDDProject/DataBase/ShabbyOperate/new_train"  # 你的训练数据路径
MODEL_SAVE_PATH = "/home/idal-01/zhihao/project/MDDProject/ShabbyNet/Reconstruction/autoencoder.pth"  # 保存整个模型的路径
BACKBONE_SAVE_PATH = "/home/idal-01/zhihao/project/MDDProject/ShabbyNet/Reconstruction/backbone.pth"  # 保存编码器的路径
BATCH_SIZE = 64
LEARNING_RATE = 5e-5
WEIGHT_DECAY = 1e-4
NUM_EPOCHS = 200
GPU = 1
STEP_SIZE = 50  # 每经过多少个 epoch 调整学习率
GAMMA = 0.5  # 学习率调整的乘法因子

# 设置随机种子
def set_seed(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(SEED)

# 数据集类，返回增强后的图像
class ReconstructionDataset(Dataset):
    def __init__(self, image_dir, transform=None):
        self.image_dir = image_dir
        self.image_files = os.listdir(image_dir)
        self.transform = transform

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.image_dir, img_name)
        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, image  # 返回相同的图像作为输入和目标

# 修改 ResNeXt50Backbone 的编码器部分
class ResNeXt50Encoder(nn.Module):
    def __init__(self):
        super(ResNeXt50Encoder, self).__init__()
        resnext = models.resnext50_32x4d(pretrained=True)

        # 只保留前三层
        self.conv1 = resnext.conv1
        self.bn1 = resnext.bn1
        self.relu = resnext.relu
        self.maxpool = resnext.maxpool
        self.layer1 = resnext.layer1
        self.layer2 = resnext.layer2
        self.layer3 = resnext.layer3

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        return x

# 对称解码器部分
class ResNeXt50Decoder(nn.Module):
    def __init__(self):
        super(ResNeXt50Decoder, self).__init__()

        # 使用 ConvTranspose2d 逆向应用与编码器对称的层
        self.layer3 = nn.Sequential(
            nn.ConvTranspose2d(1024, 512, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(512),
            nn.ReLU()
        )

        self.layer2 = nn.Sequential(
            nn.ConvTranspose2d(512, 256, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(256),
            nn.ReLU()
        )

        self.layer1 = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU()
        )

        # 还原初始输入的卷积
        self.upsample1 = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU()
        )

        self.final_upsample = nn.Sequential(
            nn.ConvTranspose2d(64, 3, kernel_size=7, stride=1, padding=3, output_padding=0),
            nn.Sigmoid()  # 将输出限制在 [0, 1] 之间
        )

    def forward(self, x):
        x = self.layer3(x)
        x = self.layer2(x)
        x = self.layer1(x)
        x = self.upsample1(x)
        x = self.final_upsample(x)
        return x

# 主模型：编码器 + 解码器
class AutoEncoder(nn.Module):
    def __init__(self):
        super(AutoEncoder, self).__init__()
        self.encoder = ResNeXt50Encoder()
        self.decoder = ResNeXt50Decoder()

    def forward(self, x):
        x = self.encoder(x)
        x = self.decoder(x)
        return x

# 训练主函数
def train_autoencoder(model, train_loader, optimizer, scheduler, criterion, num_epochs, model_save_path, backbone_save_path):
    device = torch.device(f"cuda:{GPU}" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    best_loss = float('inf')  # 保存最好的模型，初始为正无穷大

    for epoch in range(num_epochs):
        model.train()
        epoch_loss = 0.0
        epoch_mse = 0.0
        epoch_mae = 0.0
        total_target_sum = 0.0
        total_target_square_sum = 0.0
        total_samples = 0

        for img, target in tqdm(train_loader, desc=f"Epoch {epoch + 1}/{num_epochs}"):
            img, target = img.to(device), target.to(device)

            # 前向传播
            output = model(img)

            # 计算重构损失
            loss = criterion(output, target)
            mse = F.mse_loss(output, target, reduction='sum')  # 使用 'sum' 来计算总的 SSE
            mae = F.l1_loss(output, target, reduction='mean')

            epoch_loss += loss.item()
            epoch_mse += mse.item()
            epoch_mae += mae.item()

            # 计算目标值的总和与平方和，用于计算 R²
            total_target_sum += target.sum().item()
            total_target_square_sum += (target ** 2).sum().item()
            total_samples += target.numel()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # 更新学习率
        scheduler.step()

        # 计算平均损失
        avg_loss = epoch_loss / len(train_loader)
        avg_mse = epoch_mse / total_samples  # MSE
        avg_mae = epoch_mae / len(train_loader)  # MAE

        # 计算 R²
        target_mean = total_target_sum / total_samples
        sst = total_target_square_sum - total_samples * (target_mean ** 2)  # Total Sum of Squares
        r2 = 1 - (epoch_mse / sst) if sst != 0 else 0  # R²

        # 计算 NSR 和 PSNR
        target_variance = sst / total_samples  # 计算方差
        nsr = avg_mse / target_variance if target_variance != 0 else float('inf')
        psnr = 20 * torch.log10(1.0 / torch.sqrt(torch.tensor(avg_mse)))

        # 打印指标
        print(
            f"Epoch [{epoch + 1}/{NUM_EPOCHS}], Loss: {avg_loss:.4f}, MSE: {avg_mse:.4f}, MAE: {avg_mae:.4f}, NSR: {nsr:.4f}, PSNR: {psnr:.4f} dB, R²: {r2:.4f}")

        # 保存最优的编码器和整个模型
        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.encoder.state_dict(), backbone_save_path)
            torch.save(model.state_dict(), model_save_path)
            print(f"Model and encoder saved at epoch {epoch + 1} with loss: {avg_loss:.4f}")

if __name__ == "__main__":
    # 数据增强和数据集加载
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])

    train_dataset = ReconstructionDataset(TRAIN_DIR, transform=transform)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)

    # 模型定义
    autoencoder = AutoEncoder()

    # 损失函数和优化器
    criterion = nn.MSELoss()  # 使用均方误差损失来衡量重构图像与原始图像之间的差距
    optimizer = optim.Adam(autoencoder.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)

    # 学习率调度器
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=STEP_SIZE, gamma=GAMMA)

    # 训练并保存最优的编码器和整个模型
    train_autoencoder(autoencoder, train_loader, optimizer, scheduler, criterion, num_epochs=NUM_EPOCHS,
                      model_save_path=MODEL_SAVE_PATH, backbone_save_path=BACKBONE_SAVE_PATH)
